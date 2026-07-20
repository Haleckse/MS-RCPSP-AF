import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random

def parse_instance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()

    data = {}
    
    # Détecter si c'est un format SPSP
    if 'Project Module' in file_content or 'Workforce Module' in file_content:
        lines = [line.strip() for line in file_content.split('\n')]
        sections = {}
        current_section = None
        section_lines = []
        
        for line in lines:
            if (line.startswith('\\*') or line.startswith('*') or line.endswith('*\\') or line.endswith('*') or
                any(sec in line for sec in ['Project Module', 'Workforce Module', 'Skill Requirements Module', 'Skill Level Requirements Module', 'Cost Module', 'Common Resource Usage Module', 'Rework Module'])):
                m = re.search(r'([A-Za-z\s]+)', line)
                if m:
                    if current_section:
                        sections[current_section] = section_lines
                    current_section = m.group(1).strip()
                    section_lines = []
            else:
                if line:
                    section_lines.append(line)
        if current_section:
            sections[current_section] = section_lines

        # 1. Project Module
        proj_lines = [l for l in sections.get('Project Module', []) if l.strip()]
        first_line = proj_lines[0].split()
        nActs = int(first_line[0])
        nResources = int(first_line[1])
        nSkills = int(first_line[2])
        
        activity_lines = []
        for l in proj_lines[1:]:
            parts = l.split()
            if len(parts) >= 2:
                activity_lines.append(parts)
                
        dur = []
        pred = []
        succ = []
        
        for i, parts in enumerate(activity_lines):
            task_id = i + 1
            duration = int(parts[0])
            dur.append(duration)
            
            successor_count = int(parts[1])
            if len(parts) > 2:
                successors = [int(x) for x in parts[2:]]
                for s in successors:
                    pred.append(task_id)
                    succ.append(s)
                    
        # 2. Workforce Module
        wf_lines = [l for l in sections.get('Workforce Module', []) if l.strip()]
        mastery = []
        for l in wf_lines[:nResources]:
            mastery.append([int(x) for x in l.split()])
            
        # 3. Skill Requirements Module
        sreq_lines = [l for l in sections.get('Skill Requirements Module', []) if l.strip()]
        sreq = []
        for l in sreq_lines[:nActs]:
            sreq.append([int(x) for x in l.split()])
            
        data = {
            'nActs': nActs,
            'nSkills': nSkills,
            'nResources': nResources,
            'dur': dur,
            'sreq': sreq,
            'mastery': mastery,
            'pred': pred,
            'succ': succ
        }
        
        horizon = sum(dur) + 10
        data['worker_availability'] = [[1] * horizon for _ in range(nResources)]
        return data

    else:
        # Format DZN classique
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
            var_value = raw_value.strip()

            if var_value.startswith('[|') and var_value.endswith('|]'):
                matrix_content = var_value[2:-2].strip()
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

            elif var_value.startswith('[') and var_value.endswith(']') and '{' in var_value:
                list_content = var_value[1:-1].strip()
                raw_sets = re.findall(r'\{(.*?)\}', list_content)
                processed_sets = []
                for s in raw_sets:
                    s = s.strip()
                    if not s:
                        processed_sets.append(set())
                    else:
                        processed_sets.append({int(x) for x in s.split(',') if x.strip()})
                data[var_name] = processed_sets

            elif var_value.startswith('[') and var_value.endswith(']'):
                list_content = var_value[1:-1].strip()
                data[var_name] = [int(x.strip()) for x in list_content.split(',') if x.strip()]

            else:
                if var_value.lower() == 'true':
                    data[var_name] = True
                elif var_value.lower() == 'false':
                    data[var_name] = False
                else:
                    try:
                        data[var_name] = int(var_value)
                    except ValueError:
                        try:
                            data[var_name] = float(var_value)
                        except ValueError:
                            data[var_name] = var_value

        # Création du calendrier de présence si absent du .dzn
        nb_worker = data['nResources']
        horizon = sum(data['dur']) + 10
        if 'worker_availability' not in data:
            data['worker_availability'] = [[1] * horizon for _ in range(nb_worker)]

        return data



def plot_gantt(data, schedule, assignments, makespan):
    """
    Génère et affiche le diagramme de Gantt à partir des dictionnaires LBBD (avec Skills).
    """
    nb_tasks = data['nActs']
    nb_worker = data['nResources']
    durations_tasks = data['dur']

    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Couleurs personnalisées
    custom_colors = ['#1f77b4', '#d62728', '#9467bd'] 
    colors_worker = [custom_colors[o % len(custom_colors)] for o in range(nb_worker)]
    
    for task_id in range(nb_tasks):
        if durations_tasks[task_id] > 0 and task_id in schedule:
            task_times = schedule[task_id]
            if not task_times: continue
            
            task_start = min(task_times)
            
            # Tracé de l'enveloppe globale grise
            ax.barh(y=task_id, width=durations_tasks[task_id], left=task_start, 
                    color='#eaeaea', edgecolor='gray', alpha=0.4, height=0.6)
            
            # Analyse heure par heure et tracé des travailleurs
            for t in task_times:
                if t in assignments and task_id in assignments[t]:
                    
                    # On regroupe les compétences par travailleur pour cette heure
                    # format: { worker_id: [skill_1, skill_2] }
                    active_workers_dict = {}
                    for w_id, s_id in assignments[t][task_id]:
                        if w_id not in active_workers_dict:
                            active_workers_dict[w_id] = []
                        active_workers_dict[w_id].append(s_id)
                    
                    if active_workers_dict:
                        num_w = len(active_workers_dict)
                        height_sub = 0.55 / num_w 
                        
                        for idx, (worker_id, skills) in enumerate(active_workers_dict.items()):
                            y_pos = task_id - 0.275 + (idx * height_sub) + (height_sub / 2)
                            
                            # Barre de couleur du worker
                            ax.barh(y=y_pos, width=1, left=t, height=height_sub, 
                                    color=colors_worker[worker_id], edgecolor='white', linewidth=0.5)
                            
                            # NOUVEAU : Ajout du texte de la compétence (ex: S1, S2...)
                            # On ajoute +1 pour que ça affiche S1 au lieu de S0
                            skills_str = "+".join([f"S{s+1}" for s in skills])
                            ax.text(t + 0.5, y_pos, skills_str, va='center', ha='center', 
                                    fontsize=6, color='white', fontweight='bold')

            ax.text(task_start - 0.5, task_id, f"Tâche {task_id:2d}", va='center', ha='right', fontsize=9, fontweight='bold')

    # --- PERSONNALISATION GRAPHIQUE ---
    ax.set_xlabel("Temps (Heures / Périodes)", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel("Identifiant des Tâches", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_title(f"MS-RCPSP-AF (LBBD) : Ordonnancement Continu et Flexibilité\nMakespan Optimal Trouvé = {makespan} heures", 
                 fontsize=14, fontweight='bold', pad=20)
    
    ax.set_yticks(range(nb_tasks))
    ax.set_yticklabels([f"T{i}" for i in range(nb_tasks)], fontsize=9)
    ax.set_ylim(-1, nb_tasks)
    
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)

    legend_patches = [mpatches.Patch(color=colors_worker[o], label=f"Worker {o+1}") for o in range(nb_worker)]
    ax.legend(handles=legend_patches, bbox_to_anchor=(1.02, 1), loc='upper left', title="Équipe (Workers)", borderaxespad=0.)

    plt.tight_layout()
    
    output_filename = "gantt_mspsp_af_lbbd.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\n[Graphique] Le diagramme de Gantt a été généré et sauvegardé avec succès : '{output_filename}'")
    
    plt.show()