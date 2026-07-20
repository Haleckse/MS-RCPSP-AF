import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Chemins des fichiers de résultats
    fichier_classic = os.path.join(base_dir, "cp_classic_500s.csv")
    fichier_symmetry = os.path.join(base_dir, "cp_symmetry_500s.csv")
    
    if not os.path.exists(fichier_classic) or not os.path.exists(fichier_symmetry):
        print("Erreur : Fichiers de résultats manquants.")
        return

    # Charger les données
    df_classic = pd.read_csv(fichier_classic, sep=';')
    df_symmetry = pd.read_csv(fichier_symmetry, sep=';')
    
    # Fusionner les runtimes
    df = df_classic[['Instance', 'CP_Optimal', 'CP_Runtime (s)']].merge(
        df_symmetry[['Instance', 'CP_Optimal', 'CP_Runtime (s)']], 
        on='Instance', 
        suffixes=('_classic', '_symmetry')
    )
    
    # Parser les paramètres sf
    def parse_sf(inst):
        m_sf = re.search(r'sf([\d\.]+)', inst)
        return float(m_sf.group(1)) if m_sf else np.nan

    df['sf'] = df['Instance'].apply(parse_sf)
    
    # Remplacer les temps à 0.0 par une petite valeur pour le log scale
    df['CP_Runtime (s)_classic'] = df['CP_Runtime (s)_classic'].clip(lower=0.01)
    df['CP_Runtime (s)_symmetry'] = df['CP_Runtime (s)_symmetry'].clip(lower=0.01)

    # Style du graphique
    plt.figure(figsize=(9, 8))
    
    # Couleurs par valeur de sf
    colors = {0.0: '#1f77b4', 0.5: '#2ca02c', 0.75: '#ff7f0e', 1.0: '#d62728'}
    labels = {
        0.0: 'sf = 0.00 (variable/random)',
        0.5: 'sf = 0.50 (polyvalence moyenne)',
        0.75: 'sf = 0.75 (polyvalence élevée)',
        1.0: 'sf = 1.00 (polyvalence totale / RCPSP)'
    }
    
    # Tracer les points groupe par groupe pour la légende
    for sf_val in sorted(df['sf'].unique()):
        group = df[df['sf'] == sf_val]
        plt.scatter(
            group['CP_Runtime (s)_classic'], 
            group['CP_Runtime (s)_symmetry'], 
            color=colors.get(sf_val, 'gray'),
            label=labels.get(sf_val, f'sf = {sf_val}'),
            alpha=0.7,
            edgecolors='k',
            s=60
        )
        
    # Ligne d'égalité y = x (diagonale)
    lims = [0.01, 550]
    plt.plot(lims, lims, 'k--', alpha=0.75, zorder=0, label='y = x (Temps identiques)')
    
    # Tracer la zone de timeout (500s)
    plt.axvline(x=500, color='gray', linestyle=':', alpha=0.5)
    plt.axhline(y=500, color='gray', linestyle=':', alpha=0.5)
    
    # Annotation pour guider la lecture
    plt.text(10, 1, "Bris de symétrie\nplus rapide (y < x)", 
             fontsize=10, color='darkgreen', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.5'))
    plt.text(0.05, 100, "Classique\nplus rapide (y > x)", 
             fontsize=10, color='darkred', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.5'))

    # Configurer les échelles log
    plt.xscale('log')
    plt.yscale('log')
    plt.xlim(lims)
    plt.ylim(lims)
    
    plt.xlabel('Temps de résolution - CP Classique (s)', fontsize=12)
    plt.ylabel('Temps de résolution - CP Bris de symétrie (s)', fontsize=12)
    plt.title('Comparaison des runtimes : CP Classique vs CP Bris de symétrie (Set 1a)', fontsize=13, fontweight='bold', pad=15)
    
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.legend(loc='lower right', frameon=True, facecolor='white', edgecolor='gray')
    
    # Sauvegarder le graphique
    output_dir = os.path.join(os.path.dirname(base_dir), "graph")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "comparaison-runtime-classic-vs-symmetry.png")
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Graphique sauvegardé avec succès sous : {output_path}")

if __name__ == '__main__':
    main()
