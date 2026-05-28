import matplotlib.pyplot as plt
import numpy as np

def tracer_temps(benders_time, cp_time, instance_name=None): 
    n = len(benders_time)
    x = np.arange(1, n + 1) if instance_name is None else instance_name
    
    plt.figure(figsize=(10, 6))
    
    # Tracé des deux courbes
    plt.plot(x, cp_time, marker='o', color='blue', linewidth=2, label='Modèle CP (Standard)')
    plt.plot(x, benders_time, marker='s', color='darkorange', linewidth=2, label='Méthode de Benders (LBBD)')
    
    # Personnalisation des axes et du titre
    plt.xlabel('Numéro de l\'instance', fontsize=12)
    plt.ylabel('Temps d\'exécution (secondes)', fontsize=12)
    plt.title('Comparaison des performances de résolution', fontsize=14, pad=15)
    
    # Ajout de la grille et de la légende
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=11)
    
    # S'assurer que tous les numéros d'instances s'affichent sur l'axe X
    if instance_name is None:
        plt.xticks(x)
    else:
        plt.xticks(rotation=45)
        
    # Ajustement des marges et affichage
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Remplacez ces listes par vos vrais résultats récupérés dans votre code
    benders = [18.43, 18.95, 97.3, 3.44, 115.17, 51.98, 1.04, 31.88, 1.25, 14.66, 11.6, 0.1, 0.5, 3.8, 0.18]
    cp =      [1010.8, 3000.03, 365.35, 15.17, 906.89, 3000.03, 13.82, 3000.05, 77.02, 2664.35, 15.74, 19.24, 1.15, 110.63, 1.49]
    instance_name = [
    'inst_set1a_sf0.5_nc1.5_n20_m10_00.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m10_01.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m10_02.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m10_03.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m10_04.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m10_05.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_00.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_01.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_02.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_03.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_04.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m13_05.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m15_00.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m15_01.dzn', 
    'inst_set1a_sf0.5_nc1.5_n20_m15_02.dzn'
]


    # Appel de la fonction
    tracer_temps(benders, cp, instance_name)