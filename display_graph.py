import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from math import isnan

if __name__ == "__main__":
        
    benders_df = pd.read_csv('resultats-benders-set-1a-carla.csv', sep=';')
    cp_df = pd.read_csv('resultats-cp-set-1a.csv', sep=';')

    
    print(len(benders_df), len(cp_df))

    list_benders_makespan = list(benders_df['BD_Makespan'])
    list_cp_makespan = list(cp_df['CP_Makespan'])


    for i in range(len(list_benders_makespan)) : 
        benders_value = list_benders_makespan[i]
        cp_value = list_cp_makespan[i]

        if isnan(benders_value) or isnan(cp_value) : 
            break 

        if benders_value != cp_value : 
            print('ERROR')
            print(f'indice : {i+1}   benders value : {int(list_benders_makespan[i])}     cp value : {int(list_cp_makespan[i])} ')
        
        else : 
            print('OK')
            print(f'indice : {i+1}   benders value : {int(list_benders_makespan[i])}     cp value : {int(list_cp_makespan[i])} ')
        

benders_time = np.array(benders_df['BD_Runtime (s)'])
cp_time = np.array(cp_df['CP_Runtime (s)'])


benders_sorted = np.sort(benders_time)
cp_sorted = np.sort(cp_time)

y_benders = np.arange(1, len(benders_sorted) + 1) / len(benders_sorted) * 100
y_cp = np.arange(1, len(cp_sorted) + 1) / len(cp_sorted) * 100

plt.figure(figsize=(10, 6))

plt.plot(benders_sorted, y_benders, label='Décomposition de Benders', color='#1f77b4', linewidth=2.5, drawstyle='steps-post')
plt.plot(cp_sorted, y_cp, label='Constraint Programming (CP)', color='#d62728', linewidth=2.5, drawstyle='steps-post')

plt.xscale('log') # Logarithmique pour voir de 0.01s à 3000s
plt.grid(True, which="both", linestyle="--", alpha=0.5)

plt.xlabel("Temps de résolution (secondes) - Échelle Log", fontsize=12)
plt.ylabel("Instances résolues (%)", fontsize=12)
plt.title("Profil de performance : Benders vs CP", fontsize=14, fontweight='bold', pad=15)
plt.legend(fontsize=11, loc='lower right')

plt.xlim(0.05, 3500)
plt.ylim(0, 102)

plt.tight_layout()
plt.show()