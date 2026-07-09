import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def tracer_profil_performance(fichier_classique, fichier_symetrie, col_temps='Runtime (s)', separateur=','):
    """
    Lit deux fichiers de résultats (CP classique et CP avec bris de symétrie) 
    et trace leur profil de performance cumulatif.
    
    :param fichier_classique: Chemin vers le fichier CSV de la variante CP classique.
    :param fichier_symetrie: Chemin vers le fichier CSV de la variante CP bris de symétrie.
    :param col_temps: Nom de la colonne contenant le temps de résolution dans les CSV.
    :param separateur: Le caractère séparateur du CSV (par défaut la virgule ',').
    """
    
    # 1. Vérification de l'existence des fichiers
    if not os.path.exists(fichier_classique):
        raise FileNotFoundError(f"Le fichier {fichier_classique} est introuvable.")
    if not os.path.exists(fichier_symetrie):
        raise FileNotFoundError(f"Le fichier {fichier_symetrie} est introuvable.")

    # 2. Lecture des données
    df_classique = pd.read_csv(fichier_classique, sep=separateur)
    df_symetrie = pd.read_csv(fichier_symetrie, sep=separateur)

    # Vérification de la présence de la colonne de temps
    if col_temps not in df_classique.columns:
        raise ValueError(f"La colonne '{col_temps}' est absente du fichier {fichier_classique}.")
    if col_temps not in df_symetrie.columns:
        raise ValueError(f"La colonne '{col_temps}' est absente du fichier {fichier_symetrie}.")

    # 3. Extraction et tri des temps pour le profil cumulatif
    temps_classique = np.array(df_classique[col_temps])
    temps_symetrie = np.array(df_symetrie[col_temps])

    classique_sorted = np.sort(temps_classique)
    symetrie_sorted = np.sort(temps_symetrie)

    # Calcul du pourcentage d'instances résolues (Axe Y)
    y_classique = np.arange(1, len(classique_sorted) + 1) / len(classique_sorted) * 100
    y_symetrie = np.arange(1, len(symetrie_sorted) + 1) / len(symetrie_sorted) * 100

    # 4. Tracé du graphique
    plt.figure(figsize=(10, 6))

    # Tracé en escalier (steps-post)
    # J'ai mis le classique en bleu et le bris de symétrie en vert pour bien les distinguer
    plt.plot(classique_sorted, y_classique, label='CP Classique', color='#1f77b4', linewidth=2.5, drawstyle='steps-post')
    plt.plot(symetrie_sorted, y_symetrie, label='CP Bris de symétrie', color='#2ca02c', linewidth=2.5, drawstyle='steps-post')

    plt.xscale('log') # Échelle logarithmique
    plt.grid(True, which="both", linestyle="--", alpha=0.5)

    plt.xlabel("Temps de résolution (secondes) - Échelle Log", fontsize=12)
    plt.ylabel("Instances résolues (%)", fontsize=12)
    plt.title("Profil de performance : CP Classique vs CP Bris de symétrie", fontsize=14, fontweight='bold', pad=15)
    plt.legend(fontsize=11, loc='lower right')

    plt.xlim(0.05, 3500)
    plt.ylim(0, 102)

    plt.tight_layout()
    plt.show()

# ==========================================
# Exemple d'utilisation de la fonction :
# ==========================================
if __name__ == "__main__":
    # Assurez-vous de modifier "Runtime (s)" si votre colonne s'appelle "CP_Runtime (s)" par exemple
    tracer_profil_performance(
         fichier_classique="/home/atsan/MS-RCPSP-AF/results/resultats-cp-set-1a-500s.csv", 
         fichier_symetrie="/home/atsan/MS-RCPSP-AF/results/resultats-cp-carla-set-1a-500s.csv", 
         col_temps="CP_Runtime (s)", 
         separateur=";" )
    pass