import sys
import networkx as nx
import re
import random
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from docplex.cp.config import context
from docplex.cp.model import CpoModel

import time
from utils import parse_instance

import json


context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'


# MASTER PROBLEM (SCHEDULING) 

def solve_master_problem(data, timelimit, benders_cuts=None):
    """
    Ne gère que le temps et les capacités globales (Relaxed CP model).
    """
    # SETS 
    nb_tasks = data['nActs']          # |A| : Set of activities (i)
    nb_skills = data['nSkills']       # |L| : Set of skills (l)
    nb_worker = data['nResources']    # |W| : Set of MS resources (w)
    nb_ressource = data.get('nb_ressource', 0) # |CR| : Set of cumulative resources (k)
    
    # PARAMETERS 
    durations_tasks = data['dur']     # p_i : Processing time of activity i
    horizon = sum(durations_tasks) + 10  
    skills_requirement = data['sreq'] # a_{i,l} : Number of workers mastering skill l required for act i
    skills_per_worker = data['mastery'] # m_{w,l} : 1 if worker w masters skill l
    ressource_requirement = data.get('ressource_requirement', [[0]*nb_ressource for _ in range(nb_tasks)]) # b_{i,k}
    ressource_capa = data.get('ressource_capa', []) # B_k
    
    number_of_worker = [sum(row) for row in skills_requirement] # q_i : Minimum total number of workers for act i

    successors = [[] for _ in range(nb_tasks)] # E : Precedence constraints
    for p, s in zip(data['pred'], data['succ']):
        successors[p - 1].append(s - 1)

    # N_l : Total number of workers mastering skill l
    skill_resource = [sum(skills_per_worker[w][l] for w in range(nb_worker)) for l in range(nb_skills)]
    
    # MODEL

    mdl = CpoModel()

    # DECISION VARIABLES

    # act_i : Interval variable for the global execution of activity i
    act = [mdl.interval_var(size=durations_tasks[i], name=f"act{i}") for i in range(nb_tasks)]

    # endBeforeStart(act_i, act_m) for (i,m) in E
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    # sum(pulse(act_i, b_{i,k})) <= B_k
    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))


    # sum(pulse(act_i, q_i)) <= |W|
    worker_usage_list = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0 and number_of_worker[i] > 0]
    if worker_usage_list:
        worker_usage = mdl.sum(worker_usage_list)
        mdl.add(worker_usage <= nb_worker)

    # sum(pulse(act_i, a_{i,l})) <= N_l
    for l in range(nb_skills):
        skill_usage_list = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if durations_tasks[i] > 0 and skills_requirement[i][l] > 0]
        if skill_usage_list:
            skill_usage = mdl.sum(skill_usage_list)
            mdl.add(skill_usage <= skill_resource[l])

    # C_max >= act_i.end AND min C_max
    obj = mdl.max([mdl.end_of(t) for t in act])

    # ADDING BENDERS CUT
    if benders_cuts:
        for cut_idx, cut_info in enumerate(benders_cuts):
            
            A_S = cut_info['A_S']                  # {A}_S : minimal conflicting subset of tasks
            S = cut_info['S']                      # S     : corresponding set of saturated skills
            WS_capacity = cut_info['WS_capacity']  # |W_S| : capacity of the qualified workforce
            
            conflict_pulses = []
            
            # for i in A_S:
            for i in range(nb_tasks):

                if durations_tasks[i] > 0:
                    demand_for_S = sum(skills_requirement[i][l] for l in S) 
                    if demand_for_S > 0:
                        conflict_pulses.append(mdl.pulse(act[i], demand_for_S))
                        
            if conflict_pulses:
                cut_skill_demand = mdl.sum(conflict_pulses)
                mdl.add(cut_skill_demand <= WS_capacity)
                
        print(f" -> {len(benders_cuts)} Coupe(s) injectée(s) au Maître.")
                
    mdl.add(mdl.minimize(obj))

    print(" -> Résolution du probleme maitre...")
    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        makespan = msol.get_objective_values()[0] # C_max
        schedule = {}
        
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                start_time = msol.get_var_solution(act[i]).get_start()
                schedule[i] = [start_time + j for j in range(durations_tasks[i])]
                
        return msol, makespan, schedule
    else:
        return None, None, None


# SUBPROBLEM (AFFECTATION) 

def solve_subproblem(data, schedule):
    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    skills_requirement = data['sreq'] # a_{i,l}
    skills_per_worker = data['mastery'] # m_{w,l}

    max_time = max([max(times) + 1 for times in schedule.values() if times])
    
    # Subproblem is solved for each time period t independently (Allocation Flexibility)
    for t in range(max_time):
        active_tasks = [i for i in range(nb_tasks) if i in schedule and t in schedule[i]]
        if not active_tasks: continue
        
        G = nx.DiGraph()
        G.add_node('SOURCE')
        G.add_node('SINK')
        
        total_demand = 0
        node_to_task_skill = {} 

        # Build demand side of the bi-part graph 
        for i in active_tasks:
            for l in range(nb_skills):
                req = skills_requirement[i][l] 
                if req > 0:
                    node_name = f'Task_{i}_Skill_{l}'
                    G.add_node(node_name)
                    G.add_edge(node_name, 'SINK', capacity=req)
                    node_to_task_skill[node_name] = {'task': i, 'skill': l, 'demand': req}
                    total_demand += req
                    
        # Build supply side of the bi-part graph
        for w in range(nb_worker):
            worker_node = f'Worker_{w}'
            G.add_node(worker_node)
            G.add_edge('SOURCE', worker_node, capacity=1)
            
            for i in active_tasks:
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0 and skills_per_worker[w][l] == 1:
                        node_name = f'Task_{i}_Skill_{l}'
                        G.add_edge(worker_node, node_name, capacity=float('inf'))
                            
        flow_value, _ = nx.maximum_flow(G, 'SOURCE', 'SINK')
        
        # Subproblem is infeasible if max flow < total demand (D_l)
        if flow_value < total_demand:
            # Generate Logic-Based Benders Cut via Min-Cut 
            cut_value, partition = nx.minimum_cut(G, 'SOURCE', 'SINK')
            reachable, non_reachable = partition 
            
            # Extract nodes on the Sink side of the cut (where d_{s,l} = 0)
            P_NR = [n for n in non_reachable if n.startswith('Task_')]
            
            # {A}_S : Minimal conflicting subset of tasks
            A_S = list(set(node_to_task_skill[n]['task'] for n in P_NR))
            # S : Corresponding set of saturated skills
            S = list(set(node_to_task_skill[n]['skill'] for n in P_NR))
            
            # W_S : Subset of workers mastering at least one skill in S
            W_S = [w for w in range(nb_worker) if any(skills_per_worker[w][l] == 1 for l in S)]
            
            # Return the cut informations
            return False, {'A_S': A_S, 'S': S, 'WS_capacity': len(W_S)}, t
            
    return True, None, None


# MAIN LOOP

def run_benders_lbbd(filepath, timelimit):
    data = parse_instance(filepath) 
    
    benders_cuts = [] # \Omega : Set of Benders cuts
    iteration = 1

    total_start_time = time.time()
    t_master = 0
    t_sub = 0
    
    print("="*60)
    print(f" DÉBUT DE LA RÉSOLUTION LBBD : {filepath}")
    print("="*60)
    
    while True:
        print(f"\n--- ITÉRATION {iteration} ---")
        
        start_m = time.time()
        msol, makespan, schedule = solve_master_problem(data, timelimit, benders_cuts)
        t_master += (time.time() - start_m)
        
        if not msol:
            print(" -> [STOP] Le Maître n'a plus aucune solution possible ou Timeout atteint.")
            return False, "N/A", (time.time() - total_start_time), iteration
            
        print(f" -> Le Maître propose un Makespan de {makespan} h.")
        
        start_s = time.time()
        is_feasible, conflict_tasks, error_time = solve_subproblem(data, schedule)
        t_sub += (time.time() - start_s)
        
        current_runtime = time.time() - total_start_time
        print(f" -> Maître: {t_master:.2f}s | Sous-Pb: {t_sub:.2f}s | Temps total: {current_runtime:.2f}s")

        if current_runtime > timelimit:
            print(" -> [TIMEOUT] Temps limite global atteint pour LBBD.")
            return False, "N/A", current_runtime, iteration

        if is_feasible:
            print("\n" + "*"*60)
            print(" SUCCESS ! Planning validé par Flot Max.")
            print(f" MAKESPAN FINAL : {makespan} h")
            print("*"*60)

            with open("solution.json", "w") as f:
                json.dump(schedule, f)
            return True, makespan, current_runtime, iteration 
        else:
            print(f" -> [REJET] Conflit d'affectation détecté t = {error_time}.")
            print(f" -> Tâches impliquées générant la coupe : {conflict_tasks}")
            benders_cuts.append(conflict_tasks) # Add cut S to Omega
            print(" -> Redémarrage de la boucle...")
            
        iteration += 1

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <chemin_vers_instance> <timelimit>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    timelimit = int(sys.argv[2])
    
    run_benders_lbbd(filepath, timelimit)