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

# =============================================================================
# CONFIGURATION CPLEX 
# =============================================================================

context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'


# =============================================================================
# MASTER PROBLEM (ORDONNANCEMENT)
# =============================================================================
def solve_master_problem(data, timelimit, benders_cuts=None):
    """
    Ne gère que le temps et les capacités globales 
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
    worker_availability = data['worker_availability']
    
    number_of_worker = [sum(row) for row in skills_requirement]
    V = {i : [j for j in range(durations_tasks[i])] for i in range(nb_tasks)}

    successors = [[] for _ in range(nb_tasks)]
    for p, s in zip(data['pred'], data['succ']):
        successors[p - 1].append(s - 1)

    # ---------------------------------------------------------
    # CALCUL DES CAPACITÉS GLOBALES 
    # ---------------------------------------------------------

    # Nombre de worker présent à l'instant t (aW[t])
    avTech = [0] * horizon
    
    # Matrice contenant le nombre d'ouvrier maitrisant le skill l présent à l'instant t (aS[l][t])
    dispo_skill = [[0] * horizon for _ in range(nb_skills)]
    
    for t in range(horizon):
        for o in range(nb_worker):
            avTech[t] += worker_availability[o][t]
            for l in range(nb_skills):
                dispo_skill[l][t] += worker_availability[o][t] * skills_per_worker[o][l]

    # ---------------------------------------------------------
    # MODÈLE 
    # ---------------------------------------------------------
    mdl = CpoModel()

    itvs = [mdl.interval_var(size=durations_tasks[i], name=f"itvs{i}") for i in range(nb_tasks)]
    par = [[mdl.interval_var(size=1, name=f"par{i}_{v}") for v in V[i]] for i in range(nb_tasks)]


    # Contrainte de partitionnement (span) + contrainte de continuité des taches (pas de préemption)
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:  
            mdl.add(mdl.span(itvs[i], [par[i][v] for v in V[i]]))
            for v in range(len(V[i])-1):
                mdl.add(mdl.start_at_end(par[i][v+1], par[i][v]))

    # Contrainte de précédence des taches
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(itvs[i], itvs[succ]))

    # Limite de capacité des ressources materielles
    for k in range(nb_ressource):
        ressources = [mdl.pulse(itvs[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))



    # --- CONTRAINTES DE CADRAGE DES SOLUTIONS DU MAITRE ---

    # A chaque t, on n'utilise pas plus de worker que il y en a de dispo 

    # Liste de tous les besoins individuels du projet entier pour chaque t
    tech_usage_list = [mdl.pulse(par[i][v], number_of_worker[i]) for i in range(nb_tasks) for v in V[i] if durations_tasks[i] > 0 and number_of_worker[i] > 0]
    if tech_usage_list:
        tech_usage = mdl.sum(tech_usage_list)
        for t in range(horizon):
            mdl.add(mdl.always_in(tech_usage, (t, t+1), 0, avTech[t]))

    # A chaque t, on n'utilise pas plus de compétence que il y en a de dispo 

    # Crée autant de liste que de skill 
    for l in range(nb_skills):
        # Liste des besoins en skill 
        sku_c_list = [mdl.pulse(par[i][v], skills_requirement[i][l]) for i in range(nb_tasks) for v in V[i] if durations_tasks[i] > 0 and skills_requirement[i][l] > 0]
        if sku_c_list:
            sku_usage = mdl.sum(sku_c_list)
            for t in range(horizon):            
                mdl.add(mdl.always_in(sku_usage, (t, t+1), 0, dispo_skill[l][t]))


    obj = mdl.max([mdl.end_of(t) for t in itvs])

    # ---------------------------------------------------------
    # INJECTION DES COUPES DE BENDERS
    # |W_S| >= Sum(D_l)
    # ---------------------------------------------------------
    if benders_cuts:
        for cut_idx, cut_info in enumerate(benders_cuts):

            # Demandes des taches de P_NR       ex : Si la tache 2 a 4 postes isolés, task_demand[2] = 4
            task_demands = cut_info['task_demands']

            # Ensemble des workers maitrisant au moins une des compétence de la partie puit de la coupe (S)
            W_S = cut_info['W_S']
            
            # cap_WS[t] = Nombre d'ouvriers de W_S disponibles à l'instant t en comptant les absences
            cap_WS = [sum(worker_availability[w][t] for w in W_S) for t in range(horizon)]
            
            # Création de la demande cumulée (Sum D_l)
            conflict_pulses = []
            for i, demand in task_demands.items():
                for v in V[i]:

                    # Etiquetage des heure/demande
                    conflict_pulses.append(mdl.pulse(par[i][v], demand))
                    
            if conflict_pulses:

                # Création d'une fonction cumulative global qui prend en compte la demande de toutes les taches à un instant t
                cut_usage = mdl.sum(conflict_pulses)

                # Contrainte cumulative : La demande ne doit pas dépasser la capacité de W_S
                for t in range(horizon):
                    mdl.add(mdl.always_in(cut_usage, (t, t+1), 0, cap_WS[t]))
                
        print(f" -> {len(benders_cuts)} Coupe(s) Min-Cut injectée(s) au Maître.")

    mdl.add(mdl.minimize(obj))

    print(" -> Résolution du probleme maitre...")
    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        makespan = msol.get_objective_values()[0]
        schedule = {}
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                schedule[i] = [msol.get_var_solution(par[i][v]).get_start() for v in V[i]]
                
        return msol, makespan, schedule
    else:
        return None, None, None


# =============================================================================
# SUBPROBLEM (AFFECTATION)
# =============================================================================
def solve_subproblem(data, schedule):
    """
    Résout le problème d'affectation par flot maximum.
    Si infaisable, extrait la coupe exacte via la Dualité (Min-Cut) 
    """
    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    skills_requirement = data['sreq']
    skills_per_worker = data['mastery']
    worker_availability = data['worker_availability']
    
    max_time = max([max(times) + 1 for times in schedule.values() if times])
    
    for t in range(max_time):
        active_tasks = [i for i in range(nb_tasks) if i in schedule and t in schedule[i]]
        if not active_tasks: continue
        
        G = nx.DiGraph()
        G.add_node('SOURCE')
        G.add_node('SINK')
        
        total_demand = 0
        post_to_task = {} # Mémorise à quelle tache appartient chaque poste

        # Décomposition en besoin unitaire de chaque taches
        for i in active_tasks:
            poste_id = 0 
            for l in range(nb_skills):
                for _ in range(skills_requirement[i][l]):
                    node_poste = f'Task_{i}_Post_{poste_id}_Skill_{l}'
                    G.add_node(node_poste)
                    G.add_edge(node_poste, 'SINK', capacity=1) # Capacité 1 vers le puits
                    post_to_task[node_poste] = i
                    poste_id += 1
                    total_demand += 1
                    
        # Noeuds workers
        for o in range(nb_worker):
            if worker_availability[o][t] == 1:
                worker_node = f'Worker_{o}'
                G.add_node(worker_node)
                G.add_edge('SOURCE', worker_node, capacity=1) # Capacité 1 depuis la source
                
                for i in active_tasks:
                    poste_id = 0
                    for l in range(nb_skills):
                        for _ in range(skills_requirement[i][l]):
                            if skills_per_worker[o][l] == 1:
                                node_poste = f'Task_{i}_Post_{poste_id}_Skill_{l}'
                                G.add_edge(worker_node, node_poste, capacity=float('inf'))
                            poste_id += 1
                            
        # Trouver flot max 
        flow_value, _ = nx.maximum_flow(G, 'SOURCE', 'SINK')
        
        # Si le affectation impossible : trouver coup min 
        if flow_value < total_demand:
            cut_value, partition = nx.minimum_cut(G, 'SOURCE', 'SINK')
            reachable, non_reachable = partition
            
            # ensemble S (les postes qui n'ont pas eu de flot, situés du côté Puit)
            P_NR = [n for n in non_reachable if n.startswith('Task_')]
            
            # L'ensemble des compétences l impliquées dans S
            required_skills = set()
            for p in P_NR:
                l = int(p.split('_Skill_')[1])
                required_skills.add(l)
                
            # Tous les opérateurs maîtrisant au moins une compétence de S
            W_S = [o for o in range(nb_worker) if any(skills_per_worker[o][l] == 1 for l in required_skills)]
            
            # D_l : Demande cumulée des tâches pour ce sous-ensemble S
            task_demands = {}
            for p in P_NR:
                task_id = post_to_task[p]
                task_demands[task_id] = task_demands.get(task_id, 0) + 1
                
            # Paquet à envoyer au master : { 'demandes': {task: qté}, 'W_S': [liste_ouvriers] }
            cut_info = {
                'task_demands': task_demands,
                'W_S': W_S
            }
            
            return False, cut_info, t
            
    return True, None, None

# =============================================================================
# FONCTION DE COMMUNICATION 
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
        
        # Master
        start_m = time.time()
        msol, makespan, schedule = solve_master_problem(data, timelimit, benders_cuts)
        t_master += (time.time() - start_m)
        
        if not msol:
            print(" -> [STOP] Le Maître n'a plus aucune solution possible ou Timeout atteint.")
            # On renvoie False car pas de solution optimale trouvée
            return False, "N/A", (time.time() - total_start_time), iteration
            
        print(f" -> Le Maître propose un Makespan de {makespan} h.")
        
        # Le Sous-Problème
        start_s = time.time()
        is_feasible, conflict_tasks, error_time = solve_subproblem(data, schedule)
        t_sub += (time.time() - start_s)
        
        current_runtime = time.time() - total_start_time
        print(f" -> Maître: {t_master:.2f}s | Sous-Pb: {t_sub:.2f}s | Temps total: {current_runtime:.2f}s")

        # Vérification du temps limite global
        if current_runtime > timelimit:
            print(" -> [TIMEOUT] Temps limite global atteint pour LBBD.")
            return False, "N/A", current_runtime, iteration

        # Gestion du résultat
        if is_feasible:
            print("\n" + "*"*60)
            print(" SUCCESS ! Planning validé par Flot Max.")
            print(f" MAKESPAN FINAL : {makespan} h")
            print("*"*60)
            # Le planning est valide, on retourne les résultats

            # Sauvegarde de la solution pour le checker
            with open("solution.json", "w") as f:
                json.dump(schedule, f)
            return True, makespan, current_runtime, iteration 
        else:
            print(f" -> [REJET] Conflit d'affectation détecté t = {error_time}.")
            print(f" -> Tâches impliquées générant la coupe : {conflict_tasks}")
            benders_cuts.append(conflict_tasks)
            print(" -> Redémarrage de la boucle...")
            
        iteration += 1

# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <chemin_vers_instance> <timelimit>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    timelimit = int(sys.argv[2])
    
    run_benders_lbbd("datas/instances/" + filepath, timelimit)