import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def tracer_profil_performance(configs, title, output_filename, output_dir, limit_x=500):
    """
    Traces the performance profile for a list of solver configurations in English.
    Removes the vertical bar at the end (timeout) by only plotting solved instances,
    while keeping the percentage relative to the total number of instances.
    """
    valid_configs = []
    for c in configs:
        if os.path.exists(c['filepath']):
            valid_configs.append(c)
        else:
            print(f"Info: File not found for {c['label']} ({c['filepath']}). Skipped.")
            
    if not valid_configs:
        print(f"No files found for graph '{title}'. Skipping generation.")
        return

    plt.figure(figsize=(10, 6))
    
    for c in valid_configs:
        # Detect CSV separator
        with open(c['filepath'], 'r') as file:
            first_line = file.readline()
            sep = ';' if ';' in first_line else ','
        df = pd.read_csv(c['filepath'], sep=sep)
        
        total_n = len(df)
        if total_n == 0:
            continue
            
        # Extract runtimes and handle missing values by filling with limit_x (timeout)
        times = pd.to_numeric(df[c['time_col']], errors='coerce').fillna(limit_x).values
        
        # Filter out instances that timed out or are unsolved (runtimes >= limit_x)
        # This removes the vertical bar at the timeout limit
        solved_times = np.sort(times[times < limit_x])
        
        if len(solved_times) == 0:
            print(f"Info: No instances solved within limit for {c['label']}. Drawing nothing.")
            continue
            
        # Calculate Y percentage relative to the total number of instances
        y = np.arange(1, len(solved_times) + 1) / total_n * 100
        
        linestyle = c.get('linestyle', '-')
        plt.plot(solved_times, y, label=c['label'], color=c['color'], 
                 linewidth=2.5, drawstyle='steps-post', linestyle=linestyle)
        
    plt.xscale('log')
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    
    plt.xlabel("Resolution time (seconds) - Log Scale", fontsize=12)
    plt.ylabel("Solved instances (%)", fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold', pad=15)
    plt.legend(fontsize=11, loc='lower right')
    
    plt.xlim(0.01, limit_x)
    plt.ylim(0, 102)
    
    plt.tight_layout()
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Graph saved as: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    
    # -------------------------------------------------------------
    # Dataset Configurations
    # -------------------------------------------------------------
    datasets = {
        "set-1a": {
            "name": "Set 1a (500s)",
            "output_dir": os.path.join(project_dir, "graph/set-1a"),
            "files": {
                "benders": os.path.join(base_dir, "benders_500s.csv"),
                "cp_classic": os.path.join(base_dir, "cp_classic_500s.csv"),
                "cp_symmetry": os.path.join(base_dir, "cp_symmetry_500s.csv"),
                "cp_distribute": os.path.join(base_dir, "cp_distribute_500s.csv"),
                "cp_distribute_symmetry": os.path.join(base_dir, "cp_distribute_symmetry_500s.csv")
            },
            "limit_x": 500
        },
        "subset-1": {
            "name": "Subset 1 of MSLIB1 (500s)",
            "output_dir": os.path.join(project_dir, "graph/subset-1"),
            "files": {
                "benders": os.path.join(base_dir, "benders_subset1.csv"),
                "cp_classic": os.path.join(base_dir, "cp_classic_subset1.csv"),
                "cp_symmetry": os.path.join(base_dir, "cp_symmetry_subset1.csv"),
                "cp_distribute": os.path.join(base_dir, "cp_distribute_subset1.csv"),
                "cp_distribute_symmetry": os.path.join(base_dir, "cp_distribute_symmetry_subset1.csv")
            },
            "limit_x": 500
        }
    }

    # -------------------------------------------------------------
    # Loop over datasets and generate comparisons
    # -------------------------------------------------------------
    for ds_key, ds in datasets.items():
        print(f"\n=======================================================")
        print(f" Generating graphs for: {ds['name']}")
        print(f"=======================================================")
        
        # 1. CP vs Benders
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["benders"], "label": "Benders", "color": "blue", "time_col": "BD_Runtime (s)"},
                {"filepath": ds["files"]["cp_classic"], "label": "CP Classic", "color": "red", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Performance Profile: CP vs Benders ({ds['name']})",
            output_filename="profil-performance-benders-vs-cp.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )
        
        # 2. CP vs CP Symmetry
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["cp_symmetry"], "label": "CP with symmetry breaking", "color": "green", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_classic"], "label": "CP Classic", "color": "red", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Performance Profile: CP Classic vs CP with symmetry breaking ({ds['name']})",
            output_filename="profil-performance-cp-symmetry-vs-cp.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )
        
        # 3. CP vs CP Distribute
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["cp_distribute"], "label": "CP Distribute", "color": "purple", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_classic"], "label": "CP Classic", "color": "red", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Performance Profile: CP Classic vs CP Distribute ({ds['name']})",
            output_filename="profil-performance-cp-distribute-vs-cp.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )
        
        # 4. CP vs CP Distribute Symmetry
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["cp_distribute_symmetry"], "label": "CP Distribute + Symmetry", "color": "orange", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_classic"], "label": "CP Classic", "color": "red", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Performance Profile: CP Classic vs CP Distribute + Symmetry ({ds['name']})",
            output_filename="profil-performance-cp-distribute-symmetry-vs-cp.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )
        
        # 5. CP Distribute vs CP Distribute Symmetry
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["cp_distribute"], "label": "CP Distribute", "color": "purple", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_distribute_symmetry"], "label": "CP Distribute + Symmetry", "color": "orange", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Performance Profile: CP Distribute vs CP Distribute + Symmetry ({ds['name']})",
            output_filename="profil-performance-cp-distribute-vs-symmetry.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )
        
        # 6. Combined chart (All curves)
        tracer_profil_performance(
            configs=[
                {"filepath": ds["files"]["benders"], "label": "Benders", "color": "blue", "time_col": "BD_Runtime (s)"},
                {"filepath": ds["files"]["cp_classic"], "label": "CP Classic", "color": "red", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_symmetry"], "label": "CP with symmetry breaking", "color": "green", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_distribute"], "label": "CP Distribute", "color": "purple", "time_col": "CP_Runtime (s)"},
                {"filepath": ds["files"]["cp_distribute_symmetry"], "label": "CP Distribute + Symmetry", "color": "orange", "time_col": "CP_Runtime (s)"}
            ],
            title=f"Comparative Performance Profile: All Methods ({ds['name']})",
            output_filename="profil-performance-complet.png",
            output_dir=ds["output_dir"],
            limit_x=ds["limit_x"]
        )