# Fichier : display_graph.py
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ... (Vérifications de cohérence des makespans) ...

benders_time = np.array(benders_df['BD_Runtime (s)'])
cp_time = np.array(cp_df['CP_Runtime (s)'])

# Tri des temps pour construire le profil cumulatif
benders_sorted = np.sort(benders_time)
cp_sorted = np.sort(cp_time)

y_benders = np.arange(1, len(benders_sorted) + 1) / len(benders_sorted) * 100
y_cp = np.arange(1, len(cp_sorted) + 1) / len(cp_sorted) * 100

plt.figure(figsize=(10, 6))

# Tracé en escalier (steps-post)
plt.plot(benders_sorted, y_benders, label='Décomposition de Benders', color='#1f77b4', linewidth=2.5, drawstyle='steps-post')
plt.plot(cp_sorted, y_cp, label='Constraint Programming (CP)', color='#d62728', linewidth=2.5, drawstyle='steps-post')

plt.xscale('log') # Logarithmique pour voir de 0.05s à 3000s
plt.grid(True, which="both", linestyle="--", alpha=0.5)

plt.xlabel("Temps de résolution (secondes) - Échelle Log", fontsize=12)
plt.ylabel("Instances résolues (%)", fontsize=12)
plt.title("Profil de performance : Benders vs CP", fontsize=14, fontweight='bold', pad=15)
plt.legend(fontsize=11, loc='lower right')

plt.xlim(0.05, 3500)
plt.ylim(0, 102)

plt.tight_layout()
plt.show()
