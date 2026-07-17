from docplex.cp.config import context
from docplex.mp.environment import Environment
from docplex.cp.model import CpoModel
import sys

from utils import parse_instance
from utils import plot_gantt

# Configuration du solveur
context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'

def solve_cp(filename, timelimit, display_gantt=False):

    data = parse_instance(filename)

    # ENSEMBLES 
    nb_tasks = data['nActs']          # |A|
    nb_skills = data['nSkills']       # |L|
    nb_worker = data['nResources']    # |W|
    nb_ressource = 0                  # |CR| 

    # PARAMÈTRES
    durations_tasks = data['dur']               
    skills_requirement = data['sreq']           
    skills_per_worker = data['mastery']         
    
    _pred = data['pred']
    _succ = data['succ']
    successors = [[] for _ in range(nb_tasks)]
    for p, s in zip(_pred, _succ):
        successors[p - 1].append(s - 1)

    ressource_capa = []                         
    ressource_requirement = [[0] * nb_ressource for _ in range(nb_tasks)] 
    
    number_of_worker = [sum(row) for row in skills_requirement] # q_i

    # V_i : Ensemble des parties de durée unitaire
    V = {i : [j for j in range(durations_tasks[i])] for i in range(nb_tasks)}

    mdl = CpoModel()

    # ==========================================
    # VARIABLES DE DÉCISION
    # ==========================================

    act = [mdl.interval_var(name=f"act_{i}", size=durations_tasks[i]) for i in range(nb_tasks)]
    par = [[mdl.interval_var(name=f"par_{i}_{v}", size=1) for v in V[i]] for i in range(nb_tasks)]

    AW = {} # Détermine si le travailleur w est présent sur la partie v de la tâche i
    SW = {} # Donne la compétence l que le travailleur w utilise pour faire la partie v de la tâche i

    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            SA_i = {l + 1 for l in range(nb_skills) if skills_requirement[i][l] > 0}
            
            for v in V[i]:
                for w in range(nb_worker):
                    MS_w = {l + 1 for l in range(nb_skills) if skills_per_worker[w][l] == 1}
                    domain = [0] + list(SA_i.intersection(MS_w))
                    
                    if len(domain) > 1:
                        AW[(w, i, v)] = mdl.interval_var(optional=True, name=f"AW_{w}_{i}_{v}")
                        SW[(w, i, v)] = mdl.integer_var(domain=domain, name=f"SW_{w}_{i}_{v}")
                    else:
                        SW[(w, i, v)] = 0

    # ==========================================
    # CONTRAINTES
    # ==========================================

    for i in range(nb_tasks):
        if durations_tasks[i] > 0:  
            mdl.add(mdl.span(act[i], [par[i][v] for v in V[i]]))
            
            # Pas de préemption
            for v in range(len(V[i])-1):
                mdl.add(mdl.start_at_end(par[i][v+1], par[i][v]))

    # Disjonction temporelle des travailleurs (pas de chevauchement)
    for w in range(nb_worker):
        worker_vars = [AW[(w, i, v)] for i in range(nb_tasks) for v in V[i] if (w, i, v) in AW]
        if worker_vars:
            mdl.add(mdl.no_overlap(worker_vars))

    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            for v in V[i]:
                
                valid_AW_for_part = [AW[(w, i, v)] for w in range(nb_worker) if (w, i, v) in AW]
                
                # Allocation capacitaire globale (Alternative)
                if valid_AW_for_part:
                    mdl.add(mdl.alternative(par[i][v], valid_AW_for_part, number_of_worker[i]))
                
                for w in range(nb_worker):
                    if (w, i, v) in AW:
                        mdl.add(mdl.presence_of(AW[(w, i, v)]) == (SW[(w, i, v)] > 0))

                # =======================================================
                # CONTRAINTE DISTRIBUTE
                # =======================================================
                vars_SW = [SW[(w, i, v)] for w in range(nb_worker)]
                
                # On force la conversion en int natif Python pour éviter les erreurs de type
                cards = [int(nb_worker - number_of_worker[i])]
                values = [0]
                
                for l in range(nb_skills):
                    req = skills_requirement[i][l]
                    if req > 0:
                        cards.append(int(req))
                        values.append(int(l + 1))
                
                # distribute(cards, exprs, values)
                mdl.add(mdl.distribute(cards, vars_SW, values))

  

    # 8. Relations de précédence
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    # 9. Capacité matérielle cumulative
    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))

    # Enveloppes cumulatives redondantes (Global Capacity Envelopes)
    # 9.1 Enveloppe de capacité physique globale (nombre de travailleurs)
    total_workers_usage = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0]
    if total_workers_usage:
        mdl.add(mdl.sum(total_workers_usage) <= nb_worker)

    # 9.2 Enveloppe de capacité par compétence
    skill_capacity = [sum(skills_per_worker[w][l] for w in range(nb_worker)) for l in range(nb_skills)]
    for l in range(nb_skills):
        skill_usage = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if skills_requirement[i][l] > 0]
        if skill_usage:
            mdl.add(mdl.sum(skill_usage) <= skill_capacity[l])

    # 10. Bris de symétrie (non-rotation conditionnelle)
    for i in range(nb_tasks):
        if durations_tasks[i] > 1: 
            for v in range(1, len(V[i])): # v in V_i \ {0}
                # Au moins une tâche j débute au même instant que par_{i,v}
                any_task_starts = mdl.sum([
                    mdl.start_of(act[j]) == mdl.start_of(par[i][v]) 
                    for j in range(nb_tasks) if durations_tasks[j] > 0
                ]) >= 1
                
                # Si aucune tâche ne débute à cet instant, l'affectation du travailleur reste identique
                for w in range(nb_worker):
                    if (w, i, v) in AW:
                        mdl.add(
                            mdl.if_then(
                                any_task_starts == 0,
                                SW[(w, i, v)] == SW[(w, i, v-1)]
                            )
                        )


    # ==========================================
    # FONCTION OBJECTIF
    # ==========================================
    
    makespan = mdl.max([mdl.end_of(t) for t in act])
    
    # On repasse sur un objectif unique : minimiser le Makespan
    mdl.add(mdl.minimize(makespan))

    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        if display_gantt: 
            pass
    else:
        print("No solution found.")
        
    return (msol, AW, SW)