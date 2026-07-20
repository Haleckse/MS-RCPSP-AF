import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def tracer_profil_performance(fichier_1, fichier_2, label_1, label_2, color_1, color_2, 
                              col_temps_1, col_temps_2, title, output_filename, separateur=';'):
    """
    Lit deux fichiers de résultats et trace leur profil de performance cumulatif.
    
    :param fichier_1: Chemin vers le premier fichier CSV.
    :param fichier_2: Chemin vers le deuxième fichier CSV.
    :param label_1: Label de la première courbe.
    :param label_2: Label de la deuxième courbe.
    :param color_1: Couleur de la première courbe.
    :param color_2: Couleur de la deuxième courbe.
    :param col_temps_1: Nom de la colonne contenant le temps pour le premier fichier.
    :param col_temps_2: Nom de la colonne contenant le temps pour le deuxième fichier.
    :param title: Titre du graphique.
    :param output_filename: Nom du fichier image de sortie.
    :param separateur: Le caractère séparateur du CSV.
    """
    
    # 1. Vérification de l'existence des fichiers
    if not os.path.exists(fichier_1):
        raise FileNotFoundError(f"Le fichier {fichier_1} est introuvable.")
    if not os.path.exists(fichier_2):
        raise FileNotFoundError(f"Le fichier {fichier_2} est introuvable.")

    # 2. Lecture des données
    df_1 = pd.read_csv(fichier_1, sep=separateur)
    df_2 = pd.read_csv(fichier_2, sep=separateur)

    # Vérification de la présence des colonnes de temps
    if col_temps_1 not in df_1.columns:
        raise ValueError(f"La colonne '{col_temps_1}' est absente du fichier {fichier_1}.")
    if col_temps_2 not in df_2.columns:
        raise ValueError(f"La colonne '{col_temps_2}' est absente du fichier {fichier_2}.")

    # 3. Extraction et tri des temps pour le profil cumulatif
    temps_1 = np.array(df_1[col_temps_1])
    temps_2 = np.array(df_2[col_temps_2])

    sorted_1 = np.sort(temps_1)
    sorted_2 = np.sort(temps_2)

    # Calcul du pourcentage d'instances résolues (Axe Y)
    y_1 = np.arange(1, len(sorted_1) + 1) / len(sorted_1) * 100
    y_2 = np.arange(1, len(sorted_2) + 1) / len(sorted_2) * 100

    # 4. Tracé du graphique
    plt.figure(figsize=(10, 6))

    # Tracé en escalier (steps-post)
    plt.plot(sorted_1, y_1, label=label_1, color=color_1, linewidth=2.5, drawstyle='steps-post')
    plt.plot(sorted_2, y_2, label=label_2, color=color_2, linewidth=2.5, drawstyle='steps-post')

    plt.xscale('log') # Échelle logarithmique
    plt.grid(True, which="both", linestyle="--", alpha=0.5)

    plt.xlabel("Temps de résolution (secondes) - Échelle Log", fontsize=12)
    plt.ylabel("Instances résolues (%)", fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold', pad=15)
    plt.legend(fontsize=11, loc='lower right')

    plt.xlim(0.01, 600)
    plt.ylim(0, 102)

    plt.tight_layout()
    
    # Save the figure
    output_dir = os.path.join(os.path.dirname(os.path.dirname(fichier_1)), 'graph')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    plt.savefig(output_path, dpi=300)
    print(f"Graphique sauvegardé sous : {output_path}")
    
    # Try to show, but don't block if there is no display
    try:
        plt.show()
    except Exception as e:
        print(f"Impossible d'afficher le graphique (mode non-interactif) : {e}")

# ==========================================
# Point d'entrée principal :
# ==========================================
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Fichiers sources communs
    fichier_benders = os.path.join(base_dir, "benders_500s.csv")
    fichier_cp = os.path.join(base_dir, "cp_classic_500s.csv")
    fichier_cp_carla = os.path.join(base_dir, "cp_symmetry_500s.csv")

    # 1. Benders (bleu) vs CP (rouge)
    print("Génération du graphique Benders vs CP...")
    tracer_profil_performance(
        fichier_1=fichier_benders,
        fichier_2=fichier_cp,
        label_1="Benders",
        label_2="CP",
        color_1="blue",
        color_2="red",
        col_temps_1="BD_Runtime (s)",
        col_temps_2="CP_Runtime (s)",
        title="Profil de performance : Benders vs CP (Set 1a - 500s)",
        output_filename="profil-performance-benders-vs-cp.png"
    )

    # 2. CP avec bris de symétrie (vert) vs CP classique (rouge)
    print("\nGénération du graphique CP classique vs CP bris de symétrie...")
    tracer_profil_performance(
        fichier_1=fichier_cp_carla,
        fichier_2=fichier_cp,
        label_1="CP bris de symétrie",
        label_2="CP classique",
        color_1="green",
        color_2="red",
        col_temps_1="CP_Runtime (s)",
        col_temps_2="CP_Runtime (s)",
        title="Profil de performance : CP classique vs CP avec bris de symétrie (Set 1a - 500s)",
        output_filename="profil-performance-cp-carla-vs-cp.png"
    )

    # 3. CP distribute (violet) vs CP classique (rouge)
    fichier_cp_distribute = os.path.join(base_dir, "cp_distribute_500s.csv")
    print("\nGénération du graphique CP classique vs CP distribute...")
    tracer_profil_performance(
        fichier_1=fichier_cp_distribute,
        fichier_2=fichier_cp,
        label_1="CP distribute",
        label_2="CP classique",
        color_1="purple",
        color_2="red",
        col_temps_1="CP_Runtime (s)",
        col_temps_2="CP_Runtime (s)",
        title="Profil de performance : CP classique vs CP distribute (Set 1a - 500s)",
        output_filename="profil-performance-cp-distribute-vs-cp.png"
    )

    # 4. CP distribute + symétrie (orange) vs CP classique (rouge)
    fichier_cp_distribute_symmetry = os.path.join(base_dir, "cp_distribute_symmetry_500s.csv")
    print("\nGénération du graphique CP classique vs CP distribute + symétrie...")
    tracer_profil_performance(
        fichier_1=fichier_cp_distribute_symmetry,
        fichier_2=fichier_cp,
        label_1="CP distribute + symétrie",
        label_2="CP classique",
        color_1="orange",
        color_2="red",
        col_temps_1="CP_Runtime (s)",
        col_temps_2="CP_Runtime (s)",
        title="Profil de performance : CP classique vs CP distribute + symétrie (Set 1a - 500s)",
        output_filename="profil-performance-cp-distribute-symmetry-vs-cp.png"
    )