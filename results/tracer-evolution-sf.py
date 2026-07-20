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
    
    # Parser les paramètres sf
    def parse_sf(inst):
        m_sf = re.search(r'sf([\d\.]+)', inst)
        return float(m_sf.group(1)) if m_sf else np.nan

    df_bd['sf'] = df_bd['Instance'].apply(parse_sf)
    df_cpc['sf'] = df_cpc['Instance'].apply(parse_sf)
    df_cps['sf'] = df_cps['Instance'].apply(parse_sf)
    df_cpd['sf'] = df_cpd['Instance'].apply(parse_sf)
    df_cpds['sf'] = df_cpds['Instance'].apply(parse_sf)
    
    # Calculer les métriques par sf
    sf_vals = sorted(df_bd['sf'].unique())
    
    stats = []
    for sf in sf_vals:
        bd_sub = df_bd[df_bd['sf'] == sf]
        cpc_sub = df_cpc[df_cpc['sf'] == sf]
        cps_sub = df_cps[df_cps['sf'] == sf]
        cpd_sub = df_cpd[df_cpd['sf'] == sf]
        cpds_sub = df_cpds[df_cpds['sf'] == sf]
        
        stats.append({
            'sf': sf,
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
    
    # X-ticks labels
    x_labels = [f"sf={val:.2f}\n(var)" if val == 0.0 else f"sf={val:.2f}" for val in sf_vals]
    
    # 1. Taux de succès
    ax1.plot(sf_vals, df_stats['bd_success'], marker='o', linewidth=2, color='#1f77b4', label='Benders (LBBD)')
    ax1.plot(sf_vals, df_stats['cpc_success'], marker='s', linewidth=2, color='red', label='CP Classique')
    ax1.plot(sf_vals, df_stats['cps_success'], marker='x', linewidth=2, linestyle='--', color='green', label='CP avec bris de symétrie')
    ax1.plot(sf_vals, df_stats['cpd_success'], marker='^', linewidth=2, color='purple', label='CP Distribute')
    ax1.plot(sf_vals, df_stats['cpds_success'], marker='d', linewidth=2, linestyle='--', color='orange', label='CP Distribute + Symétrie')
    
    ax1.set_title('Taux de succès selon le facteur de compétences (sf)', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel('Facteur de compétences (sf)', fontsize=11)
    ax1.set_ylabel('Taux de succès (%)', fontsize=11)
    ax1.set_xticks(sf_vals)
    ax1.set_xticklabels(x_labels)
    ax1.set_ylim(60, 105)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower left', framealpha=0.9)
    
    # 2. Temps moyen de calcul
    ax2.plot(sf_vals, df_stats['bd_time'], marker='o', linewidth=2, color='#1f77b4', label='Benders (LBBD)')
    ax2.plot(sf_vals, df_stats['cpc_time'], marker='s', linewidth=2, color='red', label='CP Classique')
    ax2.plot(sf_vals, df_stats['cps_time'], marker='x', linewidth=2, linestyle='--', color='green', label='CP avec bris de symétrie')
    ax2.plot(sf_vals, df_stats['cpd_time'], marker='^', linewidth=2, color='purple', label='CP Distribute')
    ax2.plot(sf_vals, df_stats['cpds_time'], marker='d', linewidth=2, linestyle='--', color='orange', label='CP Distribute + Symétrie')
    
    ax2.set_title('Temps de calcul moyen selon le facteur de compétences (sf)', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('Facteur de compétences (sf)', fontsize=11)
    ax2.set_ylabel('Temps moyen (s)', fontsize=11)
    ax2.set_xticks(sf_vals)
    ax2.set_xticklabels(x_labels)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', framealpha=0.9)
    
    # Ajuster la disposition
    plt.tight_layout()
    
    # Sauvegarder l'image
    output_dir = os.path.join(os.path.dirname(base_dir), "graph")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "evolution-performance-sf.png")
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Graphique sauvegardé avec succès sous : {output_path}")

if __name__ == '__main__':
    main()
