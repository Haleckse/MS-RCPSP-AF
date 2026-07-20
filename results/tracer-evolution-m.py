import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Chemins des fichiers de résultats
    fichier_benders = os.path.join(base_dir, "benders_500s.csv")
    fichier_classic = os.path.join(base_dir, "cp_classic_500s.csv")
    fichier_symmetry = os.path.join(base_dir, "cp_symmetry_500s.csv")
    fichier_distribute = os.path.join(base_dir, "cp_distribute_500s.csv")
    fichier_distribute_sym = os.path.join(base_dir, "cp_distribute_symmetry_500s.csv")
    
    files = [fichier_benders, fichier_classic, fichier_symmetry, fichier_distribute, fichier_distribute_sym]
    if not all(os.path.exists(f) for f in files):
        print("Erreur : Certains fichiers de résultats (CSV) sont manquants.")
        return

    # Charger les données
    df_bd = pd.read_csv(fichier_benders, sep=';')
    df_cpc = pd.read_csv(fichier_classic, sep=';')
    df_cps = pd.read_csv(fichier_symmetry, sep=';')
    df_cpd = pd.read_csv(fichier_distribute, sep=';')
    df_cpds = pd.read_csv(fichier_distribute_sym, sep=';')
    
    # Parser les paramètres m
    def parse_m(inst):
        m_m = re.search(r'_m(\d+)_', inst)
        return int(m_m.group(1)) if m_m else np.nan

    df_bd['m'] = df_bd['Instance'].apply(parse_m)
    df_cpc['m'] = df_cpc['Instance'].apply(parse_m)
    df_cps['m'] = df_cps['Instance'].apply(parse_m)
    df_cpd['m'] = df_cpd['Instance'].apply(parse_m)
    df_cpds['m'] = df_cpds['Instance'].apply(parse_m)
    
    # Calculer les métriques par m
    m_vals = sorted(df_cpc['m'].unique())
    
    stats = []
    for m in m_vals:
        bd_sub = df_bd[df_bd['m'] == m]
        cpc_sub = df_cpc[df_cpc['m'] == m]
        cps_sub = df_cps[df_cps['m'] == m]
        cpd_sub = df_cpd[df_cpd['m'] == m]
        cpds_sub = df_cpds[df_cpds['m'] == m]
        
        stats.append({
            'm': m,
            'bd_success': bd_sub['BD_Optimal'].mean() * 100,
            'bd_time': bd_sub['BD_Runtime (s)'].mean(),
            'cpc_success': cpc_sub['CP_Optimal'].mean() * 100,
            'cpc_time': cpc_sub['CP_Runtime (s)'].mean(),
            'cps_success': cps_sub['CP_Optimal'].mean() * 100,
            'cps_time': cps_sub['CP_Runtime (s)'].mean(),
            'cpd_success': cpd_sub['CP_Optimal'].mean() * 100,
            'cpd_time': cpd_sub['CP_Runtime (s)'].mean(),
            'cpds_success': cpds_sub['CP_Optimal'].mean() * 100,
            'cpds_time': cpds_sub['CP_Runtime (s)'].mean(),
        })
        
    df_stats = pd.DataFrame(stats)
    
    # Créer la figure à 2 sous-graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Taux de succès
    ax1.plot(m_vals, df_stats['bd_success'], marker='o', linewidth=2, color='#1f77b4', label='Benders (LBBD)')
    ax1.plot(m_vals, df_stats['cpc_success'], marker='s', linewidth=2, color='red', label='CP Classique')
    ax1.plot(m_vals, df_stats['cps_success'], marker='x', linewidth=2, linestyle='--', color='green', label='CP avec bris de symétrie')
    ax1.plot(m_vals, df_stats['cpd_success'], marker='^', linewidth=2, color='purple', label='CP Distribute')
    ax1.plot(m_vals, df_stats['cpds_success'], marker='d', linewidth=2, linestyle='--', color='orange', label='CP Distribute + Symétrie')
    
    ax1.set_title('Taux de succès selon l\'effectif (m)', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel('Nombre de travailleurs (m)', fontsize=11)
    ax1.set_ylabel('Taux de succès (%)', fontsize=11)
    ax1.set_xticks(m_vals)
    ax1.set_ylim(30, 105)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower right', framealpha=0.9, fontsize=9)
    
    # Mettre en valeur la zone de croisement
    ax1.axvspan(14, 16, color='gray', alpha=0.1, linestyle='--')
    
    # 2. Temps moyen de calcul
    ax2.plot(m_vals, df_stats['bd_time'], marker='o', linewidth=2, color='#1f77b4', label='Benders (LBBD)')
    ax2.plot(m_vals, df_stats['cpc_time'], marker='s', linewidth=2, color='red', label='CP Classique')
    ax2.plot(m_vals, df_stats['cps_time'], marker='x', linewidth=2, linestyle='--', color='green', label='CP avec bris de symétrie')
    ax2.plot(m_vals, df_stats['cpd_time'], marker='^', linewidth=2, color='purple', label='CP Distribute')
    ax2.plot(m_vals, df_stats['cpds_time'], marker='d', linewidth=2, linestyle='--', color='orange', label='CP Distribute + Symétrie')
    
    ax2.set_title('Temps de calcul moyen selon l\'effectif (m)', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('Nombre de travailleurs (m)', fontsize=11)
    ax2.set_ylabel('Temps moyen (s)', fontsize=11)
    ax2.set_xticks(m_vals)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', framealpha=0.9, fontsize=9)
    
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
