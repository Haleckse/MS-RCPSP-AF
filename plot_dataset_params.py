import csv
import re
import os
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
OUTPUT_DIR = os.path.join(BASE_DIR, "graph", "set-1a")
os.makedirs(OUTPUT_DIR, exist_ok=True)

files = {
    'Benders (LBBD)': (os.path.join(RESULTS_DIR, 'benders_500s.csv'), 'BD_Optimal', 'BD_Runtime (s)', 'blue', 'o', '-'),
    'CP Classique': (os.path.join(RESULTS_DIR, 'cp_classic_500s.csv'), 'CP_Optimal', 'CP_Runtime (s)', 'red', 's', '-'),
    'CP Classique + Sym': (os.path.join(RESULTS_DIR, 'cp_symmetry_500s.csv'), 'CP_Optimal', 'CP_Runtime (s)', 'green', 'v', '--'),
    'CP GCC (Distribute)': (os.path.join(RESULTS_DIR, 'cp_distribute_500s.csv'), 'CP_Optimal', 'CP_Runtime (s)', 'purple', '^', '-'),
    'CP GCC + Sym': (os.path.join(RESULTS_DIR, 'cp_distribute_symmetry_500s.csv'), 'CP_Optimal', 'CP_Runtime (s)', 'orange', 'd', '--'),
}

def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        headers = next(reader)
        return [dict(zip(headers, row)) for row in reader]

def main():
    params_config = [
        ('m', 'Nombre de travailleurs (m)', 'dataset_analysis_m.png'),
        ('nc', 'Complexité du réseau (nc)', 'dataset_analysis_nc.png'),
        ('sf', 'Skill Factor (sf)', 'dataset_analysis_sf.png'),
    ]

    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#cccccc'

    for key, label_x, filename in params_config:
        method_data = defaultdict(lambda: defaultdict(list))
        
        for method, (path, opt_col, time_col, color, marker, linestyle) in files.items():
            if os.path.exists(path):
                rows = load_csv(path)
                for r in rows:
                    m_match = re.search(r'sf([0-9\.]+)_nc([0-9\.]+)_n(\d+)_m(\d+)', r['Instance'])
                    if m_match:
                        sf, nc, n, m = m_match.groups()
                        val = {'m': int(m), 'nc': float(nc), 'sf': float(sf)}[key]
                        opt = r[opt_col].strip() == '1'
                        t = float(r[time_col]) if opt else 500.0
                        method_data[method][val].append(t)

        fig, ax = plt.subplots(figsize=(8, 5.5))
        ax.set_title(f'Impact de : {label_x} sur le temps moyen global', fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel(label_x, fontsize=11, fontweight='bold')
        ax.set_ylabel('Temps moyen de résolution (s)', fontsize=11, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.6)

        for method, (path, opt_col, time_col, color, marker, linestyle) in files.items():
            m_dict = method_data[method]
            x_vals = sorted(m_dict.keys())
            y_vals = [np.mean(m_dict[x]) for x in x_vals]

            if x_vals:
                ax.plot(x_vals, y_vals, label=method, color=color, marker=marker, 
                        linestyle=linestyle, linewidth=2.5, markersize=7, alpha=0.9)
                ax.set_xticks(x_vals)

        ax.set_ylim(0, 420)
        ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
        plt.tight_layout()

        out_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Graphique à forte déclivité généré : {out_path}")

if __name__ == '__main__':
    main()
