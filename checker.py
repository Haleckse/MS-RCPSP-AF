import sys
import json
import networkx as nx
from utils import parse_instance

def verify_solution(data, schedule_dict, expected_makespan):
    """
    Vérifie indépendamment si le dictionnaire 'schedule' respecte toutes 
    les contraintes du problème MS-RCPSP-AF.
    """
    errors = []
    
    # Conversion des clés du JSON (qui sont des strings) en entiers
    schedule = {int(k): v for k, v in schedule_dict.items()}
    
    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    nb_ressource = data.get('nb_ressource', 0)
    
    # ==========================================
    # VERIFICATION DE LA CONTINUITÉ (Non-Préemption)
    # ==========================================
    task_bounds = {} 
    
    for i, times in schedule.items():
        if not times: continue
        times_sorted = sorted(times)
        
        # Vérifie que les parties de la tâche se suivent sans trou (ex: [4, 5, 6])
        for v in range(len(times_sorted) - 1):
            if times_sorted[v] + 1 != times_sorted[v+1]:
                errors.append(f"[Continuité] La tâche {i} est interrompue : {times_sorted}")
                
        # Vérifie que la durée correspond bien aux données
        if len(times_sorted) != data['dur'][i]:
            errors.append(f"[Durée] La tâche {i} dure {len(times_sorted)}h au lieu de {data['dur'][i]}h")
            
        task_bounds[i] = {"start": times_sorted[0], "end": times_sorted[-1] + 1}

    # ==========================================
    # VERIFICATION DU MAKESPAN
    # ==========================================
    calculated_makespan = max([b["end"] for b in task_bounds.values()]) if task_bounds else 0
    if calculated_makespan != expected_makespan:
        errors.append(f"[Makespan] Annoncé = {expected_makespan}h, Calculé = {calculated_makespan}h")

    # ==========================================
    # VERIFICATION DES PRECEDENCES
    # ==========================================
    for p, s in zip(data['pred'], data['succ']):
        p_idx = p - 1
        s_idx = s - 1
        if p_idx in task_bounds and s_idx in task_bounds:
            if task_bounds[p_idx]["end"] > task_bounds[s_idx]["start"]:
                errors.append(f"[Précédence] Violation {p}->{s} : T{p_idx} finit à {task_bounds[p_idx]['end']}, T{s_idx} commence à {task_bounds[s_idx]['start']}")

    # ==========================================
    # VERIFICATION DES RESSOURCES MATÉRIELLES (Si existantes)
    # ==========================================
    if nb_ressource > 0:
        for t in range(calculated_makespan):
            active_tasks = [i for i, times in schedule.items() if t in times]
            for k in range(nb_ressource):
                usage = sum(data['ressource_requirement'][i][k] for i in active_tasks)
                capa = data['ressource_capa'][k]
                if usage > capa:
                    errors.append(f"[Ressource Matérielle] Dépendance k={k} dépassée à t={t} : {usage} > {capa}")

    # ==========================================
    # VÉRIFICATION DU PERSONNEL (Compétences & Présences)
    # ==========================================
    # On reconstruit un graphe indépendant heure par heure
    for t in range(calculated_makespan):
        active_tasks = [i for i, times in schedule.items() if t in times]
        if not active_tasks: continue

        G = nx.DiGraph()
        G.add_node('SOURCE')
        G.add_node('SINK')
        
        total_demand = 0
        
        # Demande des tAches à l'instant t
        for i in active_tasks:
            for l in range(nb_skills):
                demand = data['sreq'][i][l]
                if demand > 0:
                    node_task_skill = f"Task_{i}_Skill_{l}"
                    G.add_node(node_task_skill)
                    G.add_edge(node_task_skill, 'SINK', capacity=demand)
                    total_demand += demand
                    
        # Offre des ouvriers présents à l'instant t
        for w in range(nb_worker):
            if data['worker_availability'][w][t] == 1:
                worker_node = f"Worker_{w}"
                G.add_node(worker_node)
                G.add_edge('SOURCE', worker_node, capacity=1)
                
                # C. Liens de compétences (Un ouvrier ne peut faire que ce qu'il maîtrise)
                for i in active_tasks:
                    for l in range(nb_skills):
                        if data['sreq'][i][l] > 0 and data['mastery'][w][l] == 1:
                            node_task_skill = f"Task_{i}_Skill_{l}"
                            G.add_edge(worker_node, node_task_skill, capacity=1)
                            
        # Résolution
        flow_val, _ = nx.maximum_flow(G, 'SOURCE', 'SINK')
        if flow_val < total_demand:
            errors.append(f"[Personnel] Affectation impossible à l'heure t={t}. Demande={total_demand}, Personnel qualifié dispo max={flow_val}")

    # ==========================================
    # AFFICHAGES
    # ==========================================
    print("\n" + "="*50)
    print(" RÉSULTAT DE LA VÉRIFICATION INDÉPENDANTE")
    print("="*50)
    
    if errors:
        print("SOLUTION INVALIDE, Erreurs détectées :\n")
        for e in errors:
            print("  -", e)
        return False
    else:
        print("SOLUTION VALIDE")
        print(f" -> Makespan vérifié : {calculated_makespan}")
        print(f" -> Tâches vérifiées : {len(task_bounds)}")
        print(" -> Toutes les précédences, continuités et affectations RH sont respectées.")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python checker.py <fichier_instance.dzn> <fichier_solution.json> <makespan_attendu>")
        sys.exit(1)
        
    instance_path = sys.argv[1]
    solution_path = sys.argv[2]
    expected_makespan = int(sys.argv[3])
    
    # Charger les données de l'instance
    data = parse_instance(instance_path)
    
    # Charger le dictionnaire schedule depuis le JSON
    with open(solution_path, "r") as f:
        schedule = json.load(f)
        
    verify_solution(data, schedule, expected_makespan)