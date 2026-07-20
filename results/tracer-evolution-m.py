import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Chemins des fichiers de résultats
    fichier_classic = os.path.join(base_dir, "cp_classic_500s.csv")
    fichier_distribute = os.path.join(base_dir, "cp_distribute_500s.csv")
    
    if not os.path.exists(fichier_classic) or not os.path.exists(fichier_distribute):
        print("Erreur : Fichiers de résultats (CSV) manquants.")
        return

    # Charger les données
    df_cpc = pd.read_csv(fichier_classic, sep=';')
    df_cpd = pd.read_csv(fichier_distribute, sep=';')
    
    # Parser les paramètres m
    def parse_m(inst):
        m_m = re.search(r'_m(\d+)_', inst)
        return int(m_m.group(1)) if m_m else np.nan

    df_cpc['m'] = df_cpc['Instance'].apply(parse_m)
    df_cpd['m'] = df_cpd['Instance'].apply(parse_m)
    
    # Calculer les métriques par m
    m_vals = sorted(df_cpc['m'].unique())
    
    stats = []
    for m in m_vals:
        cpc_sub = df_cpc[df_cpc['m'] == m]
        cpd_sub = df_cpd[df_cpd['m'] == m]
        
        stats.append({
            'm': m,
            'cpc_success': cpc_sub['CP_Optimal'].mean() * 100,
            'cpc_time': cpc_sub['CP_Runtime (s)'].mean(),
            'cpd_success': cpd_sub['CP_Optimal'].mean() * 100,
            'cpd_time': cpd_sub['CP_Runtime (s)'].mean(),
        })
        
    df_stats = pd.DataFrame(stats)
    
    # Créer la figure à 2 sous-graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Taux de succès
    ax1.plot(m_vals, df_stats['cpc_success'], marker='s', linewidth=2.5, color='red', label='CP Classique')
    ax1.plot(m_vals, df_stats['cpd_success'], marker='^', linewidth=2.5, color='purple', label='CP Distribute')
    
    ax1.set_title('Taux de succès selon l\'effectif (m)', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel('Nombre de travailleurs (m)', fontsize=11)
    ax1.set_ylabel('Taux de succès (%)', fontsize=11)
    ax1.set_xticks(m_vals)
    ax1.set_ylim(30, 105)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower right', fontsize=10)
    
    # Mettre en valeur la zone de croisement
    ax1.axvspan(14, 16, color='gray', alpha=0.15, linestyle='--', label='Zone de transition')
    
    # 2. Temps moyen de calcul
    ax2.plot(m_vals, df_stats['cpc_time'], marker='s', linewidth=2.5, color='red', label='CP Classique')
    ax2.plot(m_vals, df_stats['cpd_time'], marker='^', linewidth=2.5, color='purple', label='CP Distribute')
    
    ax2.set_title('Temps de calcul moyen selon l\'effectif (m)', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('Nombre de travailleurs (m)', fontsize=11)
    ax2.set_ylabel('Temps moyen (s)', fontsize=11)
    ax2.set_xticks(m_vals)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=10)
    
    # Ajuster la disposition
    plt.tight_layout()
    
    # Sauvegarder l'image
    output_dir = os.path.join(os.path.dirname(base_dir), "graph")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "evolution-performance-m.png")
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Graphique sauvegardé avec succès sous : {output_path}")

if __name__ == '__main__':
    main()
