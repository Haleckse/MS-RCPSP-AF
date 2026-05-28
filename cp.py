from docplex.cp.config import context
context.solver.agent = 'local'
context.solver.local.execfile = '/home/atsan/cplex/cpoptimizer/bin/x86-64_linux/cpoptimizer'

from docplex.mp.environment import Environment
from docplex.cp.model import CpoModel, CpoStepFunction, INTERVAL_MIN, INTERVAL_MAX
import os
import sys

from utils import  parse_instance
from utils import plot_gantt

def solve_cp(filename, timelimit, display_gantt=False):

    data = parse_instance('datas/instances/' + filename)

    nb_tasks = data['nActs']
    nb_skills = data['nSkills']
    nb_worker = data['nResources']
    nb_ressource = 0  

    durations_tasks = data['dur']
    horizon = sum(durations_tasks) + 10  
    skills_requirement = data['sreq']
    skills_per_worker = data['mastery']
    
    _pred = data['pred']
    _succ = data['succ']
    successors = [[] for _ in range(nb_tasks)]
    for p, s in zip(_pred, _succ):
        successors[p - 1].append(s - 1)

    ressource_capa = []
    ressource_requirement = [[0] * nb_ressource for _ in range(nb_tasks)]
    worker_availability = [[1] * horizon for _ in range(nb_worker)]
    
    number_of_worker = [sum(row) for row in skills_requirement]
    V = {i : [j for j in range(durations_tasks[i])] for i in range(nb_tasks)}

    pres_tech = [CpoStepFunction() for _ in range(nb_worker)]
    avTech = [0 for t in range(horizon)]
    
    for o in range(nb_worker):
        for t, val in enumerate(worker_availability[o]):
            pres_tech[o].add_value(t, t+1, val)
            avTech[t] += val

    dispo_skill = [[] for l in range(nb_skills)]
    for l in range(nb_skills):
        for t in range(horizon):
            val = sum(worker_availability[o][t] * skills_per_worker[o][l] for o in range(nb_worker))
            dispo_skill[l].append(val)


    ### Création du model
    mdl = CpoModel()

    # Variables de tâches
    itvs = [mdl.interval_var(name=f"itvs{i}") for i in range(nb_tasks)]
    for i in range(nb_tasks):
        itvs[i].set_size(durations_tasks[i])

    par = [[mdl.interval_var(name=f"par{i}_{v}") for v in V[i]] for i in range(nb_tasks)]
    for i in range(nb_tasks):
        for v in V[i]:
            par[i][v].set_size(1)

    InTech = {}
    for o in range(nb_worker):
        for i in range(nb_tasks):
            if durations_tasks[i] > 0:
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0 and skills_per_worker[o][l] == 1:
                        for v in V[i]:
                            InTech[(o, i, l, v)] = mdl.interval_var(name=f"InTech_{o}_{i}_{l}_{v}", optional=True)

    nSk = {}
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            for l in range(nb_skills):
                if skills_requirement[i][l] > 0:
                    for v in V[i]:
                        nSk[(l, i, v)] = mdl.integer_var(min=skills_requirement[i][l], 
                                                         max=number_of_worker[i], 
                                                         name=f"nSk_{l}_{i}_{v}")

    ### CONSTRAINTS

    # Contrainte de partitionnement + contrainte de continuité des taches (pas de préemption)
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:  
            mdl.add(mdl.span(itvs[i], [par[i][v] for v in V[i]]))
            for v in range(len(V[i])-1):
                mdl.add(mdl.start_at_end(par[i][v+1], par[i][v]))

    # Limite de capacité des ressources materielles
    for k in range(nb_ressource):
        ressources = [mdl.pulse(itvs[i], ressource_requirement[i][k]) for i in range(nb_tasks) if ressource_requirement[i][k] > 0]
        if ressources:
            mdl.add(mdl.sum(ressources) <= int(ressource_capa[k]))

    # Worker fait une chose a la fois + on n'affecte pas un worker absent
    for o in range(nb_worker):
        worker_vars = [InTech[key] for key in InTech if key[0] == o]
        if worker_vars:
            mdl.add(mdl.no_overlap(worker_vars))
            for var in worker_vars:
                mdl.add(mdl.forbid_extent(var, pres_tech[o]))

    # Contrainte de respect de la demande en skill + respect de la demande en nombre de worker 
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            for v in V[i]:
                for l in range(nb_skills):
                    if skills_requirement[i][l] > 0:
                        valid_workers = [InTech[(o, i, l, v)] for o in range(nb_worker) if (o, i, l, v) in InTech]
                        mdl.add(mdl.alternative(par[i][v], valid_workers, nSk[(l, i, v)]))

                req_total = number_of_worker[i]
                all_valid_workers = [InTech[(o, i, l, v)] for o in range(nb_worker) for l in range(nb_skills) if (o, i, l, v) in InTech]
                mdl.add(mdl.alternative(par[i][v], all_valid_workers, req_total))

    


    # Contraites redondantes
    tech_usage_list = [mdl.pulse(par[i][v], number_of_worker[i]) for i in range(nb_tasks) for v in V[i] if durations_tasks[i] > 0]
    if tech_usage_list:
        tech_usage = mdl.sum(tech_usage_list)
        for t in range(horizon):
            mdl.add(mdl.always_in(tech_usage, (t, t+1), 0, avTech[t]))

    for l in range(nb_skills):
        sku_c_list = [mdl.pulse(par[i][v], skills_requirement[i][l]) for i in range(nb_tasks) for v in V[i] if skills_requirement[i][l] > 0]
        if sku_c_list:
            sku_usage = mdl.sum(sku_c_list)
            for t in range(horizon):            
                mdl.add(mdl.always_in(sku_usage, (t, t+1), 0, dispo_skill[l][t]))

    for i in range(nb_tasks):
        for succ in successors[i]:
            mdl.add(mdl.end_before_start(itvs[i], itvs[succ]))

    obj1 = mdl.max([mdl.end_of(t) for t in itvs])
    mdl.add(mdl.minimize(obj1))

    print("solving cp model....")
    msol = mdl.solve(TimeLimit=timelimit, LogVerbosity='Quiet')

    if msol:
        print(msol.get_objective_values()[0], msol.get_objective_bounds()[0], msol.get_objective_gaps()[0], msol.get_solve_time())
        if display_gantt: 
            plot_gantt(msol, nb_tasks, nb_worker, nb_skills, durations_tasks, V, itvs, par, InTech)
    else:
        print("No solution found.")
        
    return (msol, par, InTech)

if __name__ == "__main__":
    MSPSP_cp(sys.argv[1], int(sys.argv[2]), display_gantt=False)