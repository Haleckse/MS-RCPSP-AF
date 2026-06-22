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

# =============================================================================
# HEURISTIQUE DE DÉMARRAGE (WARM-START) CORRIGÉE AVEC FLOT MAX
# =============================================================================
def get_heuristic_makespan(data):
    """
    Génère une borne supérieure rapide via un algorithme glouton (Serial Generation Scheme).
    Utilise le Flot Max pour garantir qu'il ne se coince pas dans des choix sous-optimaux.
    """
    nb_tasks = data['nActs']
    durations = data['dur']
    sreq = data['sreq']
    mastery = data['mastery']
    nb_worker = data['nResources']

    # 1. Graphe des précédences pour le tri topologique
    succs = {i: [] for i in range(nb_tasks)}
    preds = {i: [] for i in range(nb_tasks)}
    for p, s in zip(data['pred'], data['succ']):
        succs[p-1].append(s-1)
        preds[s-1].append(p-1)

    # 2. Tri topologique
    in_degree = {i: len(preds[i]) for i in range(nb_tasks)}
    queue = [i for i in range(nb_tasks) if in_degree[i] == 0]
    topo_order = []

    while queue:
        curr = queue.pop(0)
        topo_order.append(curr)
        for s in succs[curr]:
            in_degree[s] -= 1
            if in_degree[s] == 0:
                queue.append(s)

    # 3. Planification
    task_finish = {i: 0 for i in range(nb_tasks)}
    worker_free_time = {w: 0 for w in range(nb_worker)}

    for i in topo_order:
        if durations[i] == 0:
            task_finish[i] = max([task_finish[p] for p in preds[i]] + [0])
            continue

        min_start = max([task_finish[p] for p in preds[i]] + [0])
        t = min_start
        total_demand = sum(sreq[i])

        if total_demand > nb_worker:
            return None # Sécurité: Tâche impossible

        while True:
            # On utilise le Flot Max pour l'affectation à l'instant t
            G = nx.DiGraph()
            G.add_node('SOURCE')
            G.add_node('SINK')
            
            for l in range(data['nSkills']):
                if sreq[i][l] > 0:
                    G.add_edge(f'Skill_{l}', 'SINK', capacity=sreq[i][l])

            for w in range(nb_worker):
                if worker_free_time[w] <= t:
                    G.add_edge('SOURCE', f'Worker_{w}', capacity=1)
                    for l in range(data['nSkills']):
                        if sreq[i][l] > 0 and mastery[w][l] == 1:
                            G.add_edge(f'Worker_{w}', f'Skill_{l}', capacity=1)

            flow_value, flow_dict = nx.maximum_flow(G, 'SOURCE', 'SINK')

            if flow_value == total_demand:
                # Équipe trouvée ! On bloque les ouvriers
                for w in range(nb_worker):
                    if worker_free_time[w] <= t and flow_dict.get('SOURCE', {}).get(f'Worker_{w}', 0) > 0:
                        worker_free_time[w] = t + durations[i]
                task_finish[i] = t + durations[i]
                break
            else:
                t += 1 
                # Filet de sécurité: Si le temps t dépasse la dispo de TOUS les ouvriers 
                # et que ça échoue encore, la tâche est impossible avec ces compétences.
                if all(worker_free_time[w] <= t for w in range(nb_worker)):
                    return None

    return max(task_finish.values())


# =============================================================================
# MASTER PROBLEM (SCHEDULING) 
# =============================================================================
def solve_master_problem(data, timelimit, benders_cuts=None):
    # SETS 
    nb_tasks = data['nActs']          
    nb_skills = data['nSkills']       
    nb_worker = data['nResources']    
    nb_ressource = data.get('nb_ressource', 0) 
    
    # PARAMETERS 
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

    skill_resource = [sum(skills_per_worker[w][l] for w in range(nb_worker)) for l in range(nb_skills)]
    
    # --- CALCUL DE L'HEURISTIQUE (WARM-START) ---
    if not benders_cuts: 
        borne_heuristique = get_heuristic_makespan(data)
        if borne_heuristique:
            print(f" -> [HEURISTIQUE] Solution réalisable trouvée : Makespan <= {borne_heuristique}")
        else:
            print(" -> [HEURISTIQUE] Échec (Instance potentiellement complexe), lancement normal.")
    else:
        borne_heuristique = None

    # MODEL
    mdl = CpoModel()

    # DECISION VARIABLES
    act = [mdl.interval_var(size=durations_tasks[i], name=f"act{i}") for i in range(nb_tasks)]

    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))


    worker_usage_list = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0 and number_of_worker[i] > 0]
    if worker_usage_list:
        worker_usage = mdl.sum(worker_usage_list)
        mdl.add(worker_usage <= nb_worker)

    for l in range(nb_skills):
        skill_usage_list = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if durations_tasks[i] > 0 and skills_requirement[i][l] > 0]
        if skill_usage_list:
            skill_usage = mdl.sum(skill_usage_list)
            mdl.add(skill_usage <= skill_resource[l])

    obj = mdl.max([mdl.end_of(t) for t in act])

    # --- INJECTION DE LA BORNE DANS LE SOLVEUR ---
    if borne_heuristique:
        mdl.add(obj <= borne_heuristique)

    # ADDING BENDERS CUT
    if benders_cuts:
        for cut_idx, cut_info in enumerate(benders_cuts):
            
            A_S = cut_info['A_S']                  
            S = cut_info['S']                      
            WS_capacity = cut_info['WS_capacity']  
            
            conflict_pulses = []
            
            # for i in A_S: (Original version)
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
        makespan = msol.get_objective_values()[0] 
        schedule = {}
        
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                start_time = msol.get_var_solution(act[i]).get_start()
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
        
        if flow_value < total_demand:
            cut_value, partition = nx.minimum_cut(G, 'SOURCE', 'SINK')
            reachable, non_reachable = partition 
            
            P_NR = [n for n in non_reachable if n.startswith('Task_')]
            
            A_S = list(set(node_to_task_skill[n]['task'] for n in P_NR))
            S = list(set(node_to_task_skill[n]['skill'] for n in P_NR))
            W_S = [w for w in range(nb_worker) if any(skills_per_worker[w][l] == 1 for l in S)]
            
            return False, {'A_S': A_S, 'S': S, 'WS_capacity': len(W_S)}, t
            
    return True, None, None


# =============================================================================
# MAIN LOOP
# =============================================================================
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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <chemin_vers_instance> <timelimit>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    timelimit = int(sys.argv[2])
    
    run_benders_lbbd(filepath, timelimit)