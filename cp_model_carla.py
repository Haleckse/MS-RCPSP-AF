from docplex.cp.config import context
context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'

from docplex.mp.environment import Environment
from docplex.cp.model import CpoModel
import sys

from utils import parse_instance

def solve_cp(filename, timelimit, display_gantt=False):

    data = parse_instance(filename)

    # SETS
    nb_tasks = data['nActs']          # |A| : Nombre d'activités (i)
    nb_skills = data['nSkills']       # |L| : Nombre de compétences (l)
    nb_worker = data['nResources']    # |W| : Nombre de MS resources / workers (w)
    nb_ressource = 0                  # |CR| : Nombre de ressources cumulatives matérielles (k)

    # PARAMETERS
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

    # N_l : Capacité statique par compétence (Total number of workers mastering skill l)
    skill_resource = [sum(skills_per_worker[w][l] for w in range(nb_worker)) for l in range(nb_skills)]

    # V_i : Set of unit-duration parts
    V = {i : [j for j in range(durations_tasks[i])] for i in range(nb_tasks)}

    mdl = CpoModel()

    # DECISION VARIABLES

    # act_i : Variable d'intervalle représentant les taches
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


    # CONSTRAINTS

    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            # Activity Components Span : span(act_i, {par_{i,v}})
            mdl.add(mdl.span(act[i], [par[i][v] for v in V[i]]))

            # Strict Temporal Contiguity : startAtEnd(par_{i,v+1}, par_{i,v})
            for v in range(len(V[i])-1):
                mdl.add(mdl.start_at_end(par[i][v+1], par[i][v]))

    # Symmetry breaking constraints (Carla's proposal)
    for i in range(nb_tasks):
        if durations_tasks[i] > 1:
            for v in range(1, len(V[i])):
                no_task_starts = mdl.all([
                    mdl.start_of(par[i][v]) != mdl.start_of(act[j])
                    for j in range(nb_tasks) if durations_tasks[j] > 0
                ])
                for w in range(nb_worker):
                    for l in range(nb_skills):
                        if (w, i, l, v) in awo and (w, i, l, v - 1) in awo:
                            mdl.add(mdl.if_then(
                                no_task_starts,
                                mdl.presence_of(awo[(w, i, l, v)]) == mdl.presence_of(awo[(w, i, l, v - 1)])
                            ))

    # Cumulative Material Resource Capacity : sum(pulse(act_i, b_{i,k})) <= B_k
    for k in range(nb_ressource):
        ressources = [mdl.pulse(act[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))

    # Strict Worker Uniqueness : noOverlap({awo_{w,i,l,v}}) for each w
    for w in range(nb_worker):
        worker_vars = [awo[key] for key in awo if key[0] == w]
        if worker_vars:
            mdl.add(mdl.no_overlap(worker_vars))

    # Alternative constraints applied on par_{i,v} (Allocation Flexibility)
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            for v in V[i]:
                # Technical Skill Satisfaction : alternative(par_{i,v}, {awo}, a_{i,l})
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0:
                        valid_workers = [awo[(w, i, l, v)] for w in range(nb_worker) if (w, i, l, v) in awo]
                        mdl.add(mdl.alternative(par[i][v], valid_workers, skills_requirement[i][l]))

                # Workforce Headcount Quota Coverage : alternative(par_{i,v}, {awo_all}, q_i)
                req_total = number_of_worker[i]
                all_valid_workers = [awo[(w, i, l, v)] for w in range(nb_worker) for l in range(nb_skills) if (w, i, l, v) in awo]
                mdl.add(mdl.alternative(par[i][v], all_valid_workers, req_total))


    # Redundant Global Capacity Envelopes (wU <= |W| and sU_l <= N_l)
    tech_usage_list = [mdl.pulse(act[i], number_of_worker[i]) for i in range(nb_tasks) if durations_tasks[i] > 0]
    if tech_usage_list:
        mdl.add(mdl.sum(tech_usage_list) <= nb_worker) # wU <= |W|

    for l in range(nb_skills):
        sku_c_list = [mdl.pulse(act[i], skills_requirement[i][l]) for i in range(nb_tasks) if skills_requirement[i][l] > 0]
        if sku_c_list:
            mdl.add(mdl.sum(sku_c_list) <= skill_resource[l]) # sU_l <= N_l

    # Precedence Relations : endBeforeStart(act_i, act_m)
    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(act[i], act[succ]))

    # OBJECTIVE FUNCTION
    # Makespan Lower Bound & Minimize C_max
    obj1 = mdl.max([mdl.end_of(t) for t in act])
    mdl.add(mdl.minimize(obj1))

    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        if display_gantt:
            plot_gantt(msol, nb_tasks, nb_worker, nb_skills, durations_tasks, V, act, par, awo)
    else:
        print("No solution found.")

    return (msol, awo)
