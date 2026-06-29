import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def plot_relais_specialistes():
    # --- CONFIGURATION DES COULEURS ---
    # Worker 1 (Possède S1, S2) : Bleu
    # Worker 2 (Possède S1, S3) : Rouge
    colors = {1: '#1f77b4', 2: '#d62728'}
    
    # --- DONNÉES DU SCÉNARIO 1 : SANS FLEXIBILITÉ (AF) ---
    # Format : 'Nom de Tâche': [(début, durée, id_worker, compétence)]
    scenario_1 = {
        'Tâche C (Besoin S3)': [(5, 5, 2, 'S3')],   # W2 bloqué sur C de 5h à 10h
        'Tâche B (Besoin S2)': [(0, 5, 1, 'S2')],   # W1 bloqué sur B de 0h à 5h
        'Tâche A (Besoin S1)': [(5, 10, 1, 'S1')],  # W1 fait A d'une traite de 5h à 15h
    }
    makespan_1 = 15

    # --- DONNÉES DU SCÉNARIO 2 : AVEC FLEXIBILITÉ (AF) ---
    scenario_2 = {
        'Tâche C (Besoin S3)': [(5, 5, 2, 'S3')],   # W2 bascule sur C à 5h
        'Tâche B (Besoin S2)': [(0, 5, 1, 'S2')],   # W1 fait B de 0h à 5h
        'Tâche A (Besoin S1)': [(0, 5, 2, 'S1'),    # W2 commence A (0h à 5h)
                                (5, 5, 1, 'S1')],   # W1 prend le relais (5h à 10h)
    }
    makespan_2 = 10

    # --- CRÉATION DE LA FIGURE ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle("Démonstration : L'impact de la Flexibilité d'Allocation (AF)", fontsize=16, fontweight='bold')

    def draw_gantt(ax, title, data, makespan):
        y_ticks = []
        y_labels = []
        
        for i, (task_name, blocks) in enumerate(data.items()):
            y_ticks.append(i)
            y_labels.append(task_name)
            
            # Tracé de l'enveloppe globale grise (pour bien voir la durée de la tâche)
            task_start = min([b[0] for b in blocks])
            task_total_dur = sum([b[1] for b in blocks])
            ax.barh(y=i, width=task_total_dur, left=task_start, 
                    color='#eaeaea', edgecolor='gray', alpha=0.4, height=0.6)
            
            # Tracé des blocs d'affectation
            for (start, dur, w_id, skill) in blocks:
                ax.barh(y=i, width=dur, left=start, height=0.5, 
                        color=colors[w_id], edgecolor='white', linewidth=1.5)
                
                # Texte au centre du bloc
                ax.text(start + dur/2, i, f"W{w_id} ({skill})", 
                        va='center', ha='center', color='white', fontsize=10, fontweight='bold')

        ax.set_title(f"{title}\nMakespan = {makespan} heures", fontsize=12, fontweight='bold', pad=15)
        ax.set_xlabel("Temps (Heures)", fontsize=10, fontweight='bold')
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels, fontsize=10, fontweight='bold')
        ax.set_xlim(0, 16)
        ax.set_xticks(range(0, 17))
        ax.grid(axis='x', linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)

    # --- DESSIN DES DEUX SOUS-GRAPHIQUES ---
    draw_gantt(ax1, "SCÉNARIO 1 : Sans Flexibilité (Un worker doit terminer ce qu'il commence)", scenario_1, makespan_1)
    draw_gantt(ax2, "SCÉNARIO 2 : Avec Flexibilité (Passage de relais autorisé)", scenario_2, makespan_2)

    # --- LÉGENDE GLOBALE ---
    legend_patches = [
        mpatches.Patch(color=colors[1], label="Worker 1 {S1, S2}"),
        mpatches.Patch(color=colors[2], label="Worker 2 {S1, S3}")
    ]
    fig.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(0.95, 0.95), 
               title="Compétences de l'Équipe", fontsize=10, title_fontsize=11)

    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Ajustement pour le titre global
    
    # Sauvegarde et affichage
    plt.savefig("demonstration_af_relais.png", dpi=300)
    print("Le graphique a été généré et sauvegardé sous 'demonstration_af_relais.png'.")
    plt.show()

if __name__ == "__main__":
    plot_relais_specialistes()