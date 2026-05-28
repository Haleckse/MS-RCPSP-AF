import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random

def parse_instance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()

    data = {}
    
    clean_lines = []
    for line in file_content.split('\n'):
        line = line.split('%')[0].strip()
        if line:
            clean_lines.append(line)
    content = " ".join(clean_lines)

    statements = content.split(';')

    for statement in statements:
        statement = statement.strip()
        if not statement or '=' not in statement:
            continue
            
        var_name, raw_value = statement.split('=', 1)
        var_name = var_name.strip()
        raw_value = raw_value.strip()

        if raw_value.startswith('[|') and raw_value.endswith('|]'):
            matrix_content = raw_value[2:-2].strip()
            matrix = []
            for row in matrix_content.split('|'):
                row = row.strip()
                if row:
                    elements = []
                    for x in row.split(','):
                        x = x.strip()
                        if not x: continue
                        if x == 'true': elements.append(1)
                        elif x == 'false': elements.append(0)
                        else: elements.append(int(x))
                    matrix.append(elements)
            data[var_name] = matrix

        elif raw_value.startswith('[') and raw_value.endswith(']') and '{' in raw_value:
            list_content = raw_value[1:-1].strip()
            raw_sets = re.findall(r'\{(.*?)\}', list_content)
            processed_sets = []
            for s in raw_sets:
                s = s.strip()
                if not s:
                    processed_sets.append(set()) # Ensemble vide
                else:
                    processed_sets.append({int(x) for x in s.split(',') if x.strip()})
            data[var_name] = processed_sets

        elif raw_value.startswith('[') and raw_value.endswith(']'):
            list_content = raw_value[1:-1].strip()
            data[var_name] = [int(x.strip()) for x in list_content.split(',') if x.strip()]

        else:
            if raw_value.lower() == 'true':
                data[var_name] = True
            elif raw_value.lower() == 'false':
                data[var_name] = False
            else:
                try:
                    data[var_name] = int(raw_value)
                except ValueError:
                    try:
                        data[var_name] = float(raw_value)
                    except ValueError:
                        data[var_name] = raw_value

    # Création du calendrier de présence si absent du .dzn
    nb_worker = data['nResources']
    horizon = sum(data['dur']) + 10
    if 'worker_availability' not in data:
        data['worker_availability'] = [[1] * horizon for _ in range(nb_worker)]

    return data



def plot_gantt(msol, nb_tasks, nb_worker, nb_skills, durations_tasks, V, itvs, par, InTech):
    """
    Génère, affiche et sauvegarde le diagramme de Gantt du MS-RCPSP-AF
    """
    if not msol:
        print("[Graphique] Aucune solution fournie. Impossible de tracer le Gantt.")
        return

    # --- CONFIGURATION DU GRAPHIQUE GANTT ---
    fig, ax = plt.subplots(figsize=(14, 8))
    
    random.seed(42)
    colors_worker = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(nb_worker)]
    
    for i in range(nb_tasks):
        if durations_tasks[i] > 0:
            t_sol = msol.get_var_solution(itvs[i])
            task_start = t_sol.get_start()
            task_end = t_sol.get_end()
            
            # Tracé de l'enveloppe globale
            ax.barh(y=i, width=durations_tasks[i], left=task_start, 
                    color='#eaeaea', edgecolor='gray', alpha=0.4, height=0.6)
            
            # Analyse heure par heure
            for v in V[i]:
                p_sol = msol.get_var_solution(par[i][v])
                p_start = p_sol.get_start()
                p_end = p_sol.get_end()
                
                active_workers = []
                for o in range(nb_worker):
                    for l in range(nb_skills):
                        # LA CORRECTION EST ICI : On vérifie si la clé existe dans le dictionnaire
                        if (o, i, l, v) in InTech:
                            w_sol = msol.get_var_solution(InTech[(o, i, l, v)])
                            # Filtre strict de synchronisation
                            if w_sol.is_present() and w_sol.get_start() == p_start and w_sol.get_end() == p_end:
                                # On évite d'ajouter le même worker deux fois s'il utilise 2 skills en même temps
                                if o not in active_workers:
                                    active_workers.append(o)
                
                # Sous-blocs colorés
                if active_workers:
                    num_w = len(active_workers)
                    height_sub = 0.55 / num_w 
                    
                    for idx, worker_id in enumerate(active_workers):
                        y_pos = i - 0.275 + (idx * height_sub) + (height_sub / 2)
                        ax.barh(y=y_pos, width=1, left=p_start, height=height_sub, 
                                color=colors_worker[worker_id], edgecolor='white', linewidth=0.5)

            ax.text(task_start - 0.5, i, f"Tâche {i:2d}", va='center', ha='right', fontsize=9, fontweight='bold')

    # --- PERSONNALISATION GRAPHIQUE ---
    ax.set_xlabel("Temps (Heures / Périodes)", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel("Identifiant des Tâches", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_title(f"MS-RCPSP-AF : Ordonnancement Continu et Flexibilité d'Affectation\nMakespan Optimal Trouvé = {msol.get_objective_value()} heures", 
                 fontsize=14, fontweight='bold', pad=20)
    
    ax.set_yticks(range(nb_tasks))
    ax.set_yticklabels([f"T{i}" for i in range(nb_tasks)], fontsize=9)
    ax.set_ylim(-1, nb_tasks)
    
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)

    legend_patches = [mpatches.Patch(color=colors_worker[o], label=f"Worker {o+1}") for o in range(nb_worker)]
    ax.legend(handles=legend_patches, bbox_to_anchor=(1.02, 1), loc='upper left', title="Équipe (Workers)", borderaxespad=0.)

    plt.tight_layout()
    
    output_filename = "gantt_mspsp_af.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\n[Graphique] Le diagramme de Gantt a été généré et sauvegardé avec succès : '{output_filename}'")
    
    plt.show() 