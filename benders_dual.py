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
    Ne gère que le temps et les capacités globales.
    """
    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    nb_ressource = data.get('nb_ressource', 0)
    durations_tasks = data['dur']
    horizon = sum(durations_tasks) + 10  
    skills_requirement = data['sreq']
    skills_per_worker = data['mastery']
    ressource_requirement = data.get('ressource_requirement', [[0]*nb_ressource for _ in range(nb_tasks)])
    ressource_capa = data.get('ressource_capa', [])
    

    number_of_worker = [sum(row) for row in skills_requirement]

    successors = [[] for _ in range(nb_tasks)]
    for p, s in zip(data['pred'], data['succ']):
        successors[p - 1].append(s - 1)

    # SKILL RESSOURCE COMPUTING
    
    # Nombre total de travailleurs qui maîtrisent la compétence l 
    skill_resource = [sum(skills_per_worker[o][l] for o in range(nb_worker)) for l in range(nb_skills)]
    

    # MODEL

    mdl = CpoModel()

    # Variable d'intervalle représentant les activités
    act = [mdl.interval_var(size=durations_tasks[i], name=f"act{i}") for i in range(nb_tasks)]

    # Contrainte de précédence des taches
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    # Limite de capacité des ressources materielles
    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))


    # --- CONTRAINTES DE CADRAGE DES SOLUTIONS DU MAITRE ---

    # On n'utilise pas plus de worker que il y en a de dispo 
    worker_usage_list = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0 and number_of_worker[i] > 0]
    if worker_usage_list:
        worker_usage = mdl.sum(worker_usage_list)
        mdl.add(worker_usage <= nb_worker)

    # On n'utilise pas plus de compétence que il y en a de dispo 
    for l in range(nb_skills):
        skill_usage_list = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if durations_tasks[i] > 0 and skills_requirement[i][l] > 0]
        if skill_usage_list:
            skill_usage = mdl.sum(skill_usage_list)
            mdl.add(skill_usage <= skill_resource[l])

    obj = mdl.max([mdl.end_of(t) for t in act])

    # ---------------------------------------------------------
    # INJECTION DES COUPES DE BENDERS (Formule A_S et a_{i,l})
    # ---------------------------------------------------------
    if benders_cuts:
        for cut_idx, cut_info in enumerate(benders_cuts):
            
            A_S = cut_info['A_S']        # Sous-ensemble des tâches coupables
            S = cut_info['S']       # Sous-ensemble des compétences en conflit
            WS_capacity = cut_info['WS_capacity']  # |W_S|
            
            conflict_pulses = []
            
            # OBoucle sur les taches de A_S 
            for i in A_S:
                if durations_tasks[i] > 0:
                    # On calcule la somme des besoins pour les compétences en conflit S
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
        makespan = msol.get_objective_values()[0]
        schedule = {}
        
        # RECONSTRUCTION DU DICTIONNAIRE SCHEDULE
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                start_time = msol.get_var_solution(act[i]).get_start()
                # On recrée la liste des heures consécutives travaillées pour que le Sous-Pb la lise
                schedule[i] = [start_time + j for j in range(durations_tasks[i])]
                
        return msol, makespan, schedule
    else:
        return None, None, None


# =============================================================================
# SUBPROBLEM (AFFECTATION)
# =============================================================================
def solve_subproblem(data, schedule):
    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    skills_requirement = data['sreq']
    skills_per_worker = data['mastery']

    max_time = max([max(times) + 1 for times in schedule.values() if times])
    
    for t in range(max_time):
        active_tasks = [i for i in range(nb_tasks) if i in schedule and t in schedule[i]]
        if not active_tasks: continue
        
        G = nx.DiGraph()
        G.add_node('SOURCE')
        G.add_node('SINK')
        
        total_demand = 0
        node_to_task_skill = {} 

        for i in active_tasks:
            for l in range(nb_skills):
                req = skills_requirement[i][l]
                if req > 0:
                    node_name = f'Task_{i}_Skill_{l}'
                    G.add_node(node_name)
                    G.add_edge(node_name, 'SINK', capacity=req)
                    node_to_task_skill[node_name] = {'task': i, 'skill': l, 'demand': req}
                    total_demand += req
                    
        for o in range(nb_worker):
            worker_node = f'Worker_{o}'
            G.add_node(worker_node)
            G.add_edge('SOURCE', worker_node, capacity=1)
            for i in active_tasks:
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0 and skills_per_worker[o][l] == 1:
                        node_name = f'Task_{i}_Skill_{l}'
                        G.add_edge(worker_node, node_name, capacity=float('inf'))
                            
        flow_value, _ = nx.maximum_flow(G, 'SOURCE', 'SINK')
        
        if flow_value < total_demand:
            cut_value, partition = nx.minimum_cut(G, 'SOURCE', 'SINK')
            reachable, non_reachable = partition
            P_NR = [n for n in non_reachable if n.startswith('Task_')]
            
            A_S = list(set(node_to_task_skill[n]['task'] for n in P_NR))
            S = list(set(node_to_task_skill[n]['skill'] for n in P_NR))
            W_S = [o for o in range(nb_worker) if any(skills_per_worker[o][l] == 1 for l in S)]
            
            return False, {'A_S': A_S, 'S': S, 'WS_capacity': len(W_S)}, t
            
    return True, None, None


# FONCTION DE COMMUNICATION 
def run_benders_lbbd(filepath, timelimit):
    data = parse_instance(filepath) 
    
    benders_cuts = [] 
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
            benders_cuts.append(conflict_tasks)
            print(" -> Redémarrage de la boucle...")
            
        iteration += 1

# PROGRAMME PRINCIPAL
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <chemin_vers_instance> <timelimit>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    timelimit = int(sys.argv[2])
    
    run_benders_lbbd(filepath, timelimit)