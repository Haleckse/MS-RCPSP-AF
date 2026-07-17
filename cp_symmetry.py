from docplex.cp.config import context
context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'

from docplex.mp.environment import Environment
from docplex.cp.model import CpoModel
import sys

from utils import parse_instance
from utils import plot_gantt

def solve_cp(filename, timelimit, display_gantt=False):

    data = parse_instance(filename)

    # ENSEMBLES 
    nb_tasks = data['nActs']          # |A| : Nombre d'activités (i)
    nb_skills = data['nSkills']       # |L| : Nombre de compétences (l)
    nb_worker = data['nResources']    # |W| : Nombre de MS resources / workers (w)
    nb_ressource = 0                  # |CR| : Nombre de ressources cumulatives matérielles (k)

    # PARAMÈTRES
    durations_tasks = data['dur']               # p_i : Durée de l'activité i
    skills_requirement = data['sreq']           # a_{i,l} : Demande en compétence l pour l'activité i
    skills_per_worker = data['mastery']         # m_{w,l} : Matrice de maîtrise (1 si w a la comp. l, 0 sinon)
    
    _pred = data['pred']
    _succ = data['succ']
    successors = [[] for _ in range(nb_tasks)]  # E : Contraintes de précédences
    for p, s in zip(_pred, _succ):
        successors[p - 1].append(s - 1)

    ressource_capa = []                         # B_k : Capacité de la ressource cumulative k
    ressource_requirement = [[0] * nb_ressource for _ in range(nb_tasks)] # b_{i,k} : Demande en ressource k
    
    number_of_worker = [sum(row) for row in skills_requirement] # q_i : Quota minimum total de workers pour i

    # N_l : Capacité statique par compétence (nombre total de travailleurs maîtrisant la compétence l)
    skill_resource = [sum(skills_per_worker[w][l] for w in range(nb_worker)) for l in range(nb_skills)]

    # V_i : Ensemble des parties de durée unitaire
    V = {i : [j for j in range(durations_tasks[i])] for i in range(nb_tasks)}

    mdl = CpoModel()

    # VARIABLES DE DÉCISION

    # act_i : Variable d'intervalle représentant les tâches
    act = [mdl.interval_var(name=f"act{i}", size=durations_tasks[i]) for i in range(nb_tasks)]

    # par_{i,v} 
    par = [[mdl.interval_var(name=f"par{i}_{v}", size=1) for v in V[i]] for i in range(nb_tasks)]

    # awo_{w,i,l,v} 
    awo = {}
    for w in range(nb_worker): 
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0 and skills_per_worker[w][l] == 1:
                        for v in V[i]:
                            awo[(w, i, l, v)] = mdl.interval_var(name=f"awo_{w}_{i}_{l}_{v}", optional=True)


    # CONTRAINTES

    for i in range(nb_tasks):
        if durations_tasks[i] > 0:  
            # Couverture des parties par l'activité globale : span(act_i, {par_{i,v}})
            mdl.add(mdl.span(act[i], [par[i][v] for v in V[i]]))
            
            # Contiguïté temporelle stricte : startAtEnd(par_{i,v+1}, par_{i,v})
            for v in range(len(V[i])-1):
                mdl.add(mdl.start_at_end(par[i][v+1], par[i][v]))

    # Capacité matérielle cumulative : sum(pulse(act_i, b_{i,k})) <= B_k
    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))

    # Unicité stricte du travailleur : noOverlap({awo_{w,i,l,v}}) pour chaque w
    for w in range(nb_worker):
        worker_vars = [awo[key] for key in awo if key[0] == w]
        if worker_vars:
            mdl.add(mdl.no_overlap(worker_vars))

    # Contraintes alternatives appliquées sur par_{i,v} (flexibilité d'affectation)
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            for v in V[i]:
                # Satisfaction technique des compétences : alternative(par_{i,v}, {awo}, a_{i,l})
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0:
                        valid_workers = [awo[(w, i, l, v)] for w in range(nb_worker) if (w, i, l, v) in awo]
                        mdl.add(mdl.alternative(par[i][v], valid_workers, skills_requirement[i][l]))
                
                # Couverture du quota de main-d'œuvre : alternative(par_{i,v}, {awo_all}, q_i)
                req_total = number_of_worker[i]
                all_valid_workers = [awo[(w, i, l, v)] for w in range(nb_worker) for l in range(nb_skills) if (w, i, l, v) in awo]
                mdl.add(mdl.alternative(par[i][v], all_valid_workers, req_total))



    for i in range(nb_tasks):
        if durations_tasks[i] > 1: 
            for v in range(1, len(V[i])): # v in V_i \ {0}
                
                # Au moins une tâche j débute au même instant que par_{i,v}
                # Vérifier si l'heure de début d'une tâche correspond à l'heure de début de la partie actuelle           
                any_task_starts = mdl.sum([
                    mdl.start_of(act[j]) == mdl.start_of(par[i][v]) 
                    for j in range(nb_tasks) if durations_tasks[j] > 0
                ]) >= 1
                
                # Si aucune tâche ne débute à cet instant, l'affectation du travailleur reste identique à l'étape v-1
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0:
                        for w in range(nb_worker):
                            key_curr = (w, i, l, v)
                            key_prev = (w, i, l, v-1)
                            
                            # Vérifier que les clés existent dans le dictionnaire awo
                            if key_curr in awo and key_prev in awo:
                                # presence_of évalue si la variable d'intervalle optionnelle est "réalisée" (valeur 1) ou non (valeur 0)
                                mdl.add(
                                    mdl.if_then(
                                        any_task_starts == 0,
                                        mdl.presence_of(awo[key_curr]) == mdl.presence_of(awo[key_prev])
                                    )
                                )


    # Enveloppes de capacité globale redondantes (wU <= |W| et sU_l <= N_l)
    tech_usage_list = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0]
    if tech_usage_list:
        mdl.add(mdl.sum(tech_usage_list) <= nb_worker) # wU <= |W|

    for l in range(nb_skills):
        sku_c_list = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if skills_requirement[i][l] > 0]
        if sku_c_list:
            mdl.add(mdl.sum(sku_c_list) <= skill_resource[l]) # sU_l <= N_l

    # Relations de précédence : endBeforeStart(act_i, act_m)
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    # FONCTION OBJECTIF
    # Minimiser le Makespan (C_max)
    obj1 = mdl.max([mdl.end_of(t) for t in act])
    mdl.add(mdl.minimize(obj1))

    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        if display_gantt: 
            plot_gantt(msol, nb_tasks, nb_worker, nb_skills, durations_tasks, V, act, par, awo)
    else:
        print("No solution found.")
        
    return (msol, awo)