import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Chargement des données
files = {
    "Benders": "benders_500s.csv",
    "CP Classic": "cp_classic_500s.csv",
    "CP Distribute": "cp_distribute_500s.csv",
    "CP Distribute Symmetry": "cp_distribute_symmetry_500s.csv",
    "CP Symmetry": "cp_symmetry_500s.csv"
}

all_data = []
for name, filepath in files.items():
    df = pd.read_csv(filepath, sep=';')
    opt_col = [c for c in df.columns if 'Optimal' in c][0]
    rt_col = [c for c in df.columns if 'Runtime' in c][0]

    df['Optimal'] = pd.to_numeric(df[opt_col], errors='coerce').fillna(0).astype(int)
    df['Runtime'] = pd.to_numeric(df[rt_col], errors='coerce')
    df['Method'] = name

    # 2. Extraction des paramètres depuis le nom de l'instance
    df['sf'] = df['Instance'].str.extract(r'sf([0-9.]+)').astype(float)
    df['nc'] = df['Instance'].str.extract(r'nc([0-9.]+)').astype(float)
    df['m'] = df['Instance'].str.extract(r'm([0-9]+)').astype(int)

    all_data.append(df[['Method', 'Instance', 'Optimal', 'Runtime', 'sf', 'nc', 'm']])

df_all = pd.concat(all_data, ignore_index=True)

# Couleurs demandées
colors = {
    "Benders": "blue",
    "CP Classique": "red",
    "CP GCC": "purple",
    "CP GCC + symmetrie": "orange",
    "CP Classique + symmetrie": "green"
}

params = {'m': 'Effectif de travailleurs (m)',
          'nc': 'Complexité réseau (nc)',
          'sf': 'Facteur de compétences (sf)'}

# ==========================================
# GRAPHIQUE 1 : Taux de succès
# ==========================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Taux de succès (%) en fonction des caractéristiques de l'instance", fontsize=16, fontweight='bold')

for i, (param, label) in enumerate(params.items()):
    agg_df = df_all.groupby([param, 'Method'])['Optimal'].mean().unstack() * 100
    agg_df.plot(kind='bar', ax=axes[i], color=[colors[c] for c in agg_df.columns], width=0.8)

    axes[i].set_title(f'Impact de {label}', fontsize=12)
    axes[i].set_xlabel(label, fontsize=11)
    axes[i].set_ylabel('Taux de succès (%)', fontsize=11)
    axes[i].set_ylim(0, 105)
    axes[i].grid(axis='y', linestyle='--', alpha=0.7)
    axes[i].tick_params(axis='x', rotation=0)

    if i == 1:
        axes[i].legend(title='Méthode', loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=5)
    else:
        axes[i].get_legend().remove()

plt.tight_layout()
plt.subplots_adjust(bottom=0.25)
plt.show()

# ==========================================
# GRAPHIQUE 2 : Temps de résolution
# ==========================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Temps moyen de résolution (s) en fonction des caractéristiques", fontsize=16, fontweight='bold')

for i, (param, label) in enumerate(params.items()):
    agg_df = df_all.groupby([param, 'Method'])['Runtime'].mean().unstack()

    for method in agg_df.columns:
        axes[i].plot(agg_df.index, agg_df[method], marker='o', label=method, color=colors[method], linewidth=2, markersize=8)

    axes[i].set_title(f'Impact de {label}', fontsize=12)
    axes[i].set_xlabel(label, fontsize=11)
    axes[i].set_ylabel('Temps moyen (s)', fontsize=11)
    axes[i].set_xticks(agg_df.index)
    axes[i].grid(True, linestyle='--', alpha=0.7)

    if i == 1:
        axes[i].legend(title='Méthode', loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=5)
    else:
        if axes[i].get_legend():
            axes[i].get_legend().remove()

plt.tight_layout()
plt.subplots_adjust(bottom=0.25)
plt.show()
