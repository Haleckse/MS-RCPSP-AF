import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import re

def generate_speedup_histogram(file_cp, file_bd, title, output_path, limit_x=500):
    """
    Generates a bar chart showing the distribution of speedup factors (CP_Time / BD_Time).
    """
    if not os.path.exists(file_cp) or not os.path.exists(file_bd):
        return
        
    sep_cp = ';' if ';' in open(file_cp).readline() else ','
    sep_bd = ';' if ';' in open(file_bd).readline() else ','
    
    df_cp = pd.read_csv(file_cp, sep=sep_cp)
    df_bd = pd.read_csv(file_bd, sep=sep_bd)
    
    merged = pd.merge(df_cp, df_bd, on="Instance")
    
    x = pd.to_numeric(merged["CP_Runtime (s)"], errors='coerce').fillna(limit_x).values
    y = pd.to_numeric(merged["BD_Runtime (s)"], errors='coerce').fillna(limit_x).values
    
    # Calculate speedup (CP / Benders)
    speedups = x / y
    
    # Classify speedups into bins
    bins = {
        "CP is faster\n(Speedup < 1x)": np.sum(speedups < 0.99),
        "Similar\n(1x - 2x)": np.sum((speedups >= 0.99) & (speedups < 2.0)),
        "Moderate\n(2x - 10x)": np.sum((speedups >= 2.0) & (speedups < 10.0)),
        "Significant\n(10x - 100x)": np.sum((speedups >= 10.0) & (speedups < 100.0)),
        "Large\n(100x - 1000x)": np.sum((speedups >= 100.0) & (speedups < 1000.0)),
        "Extreme\n(> 1000x)": np.sum(speedups >= 1000.0)
    }
    
    plt.figure(figsize=(10, 6))
    
    labels = list(bins.keys())
    values = list(bins.values())
    
    # Plot bars with a nice gradient of blues/purples
    colors = ['#d62728', '#c7c7c7', '#aec7e8', '#1f77b4', '#9467bd', '#bcbd22']
    bars = plt.bar(labels, values, color=colors, edgecolor='grey', alpha=0.85)
    
    # Add values on top of the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height + 1, f'{int(height)}', 
                 ha='center', va='bottom', fontsize=11, fontweight='bold')
                 
    plt.ylabel("Number of instances", fontsize=12)
    plt.title(title, fontsize=13, fontweight='bold', pad=15)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Speedup histogram saved: {output_path}")

def generate_global_comparison_bars(files, title, output_path, limit_x=500):
    """
    Generates a side-by-side bar chart showing both Average Solve Time and Success Rate (%).
    """
    valid_data = {}
    for name, info in files.items():
        path = info["filepath"]
        if os.path.exists(path):
            sep = ';' if ';' in open(path).readline() else ','
            df = pd.read_csv(path, sep=sep)
            
            runtimes = pd.to_numeric(df[info["time_col"]], errors='coerce').fillna(limit_x).values
            
            # Solved means runtime < limit_x
            solved_mask = runtimes < limit_x
            success_rate = np.mean(solved_mask) * 100
            
            # Average runtime of solved instances (to avoid timeout bias)
            avg_solved_runtime = np.mean(runtimes[solved_mask]) if np.sum(solved_mask) > 0 else limit_x
            
            valid_data[name] = {
                "success_rate": success_rate,
                "avg_runtime": avg_solved_runtime
            }
            
    if not valid_data:
        return
        
    labels = list(valid_data.keys())
    success_rates = [valid_data[l]["success_rate"] for l in labels]
    avg_runtimes = [valid_data[l]["avg_runtime"] for l in labels]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # X axis positions
    x = np.arange(len(labels))
    width = 0.35
    
    # Plot success rate (bars)
    color_success = '#1f77b4'
    rects1 = ax1.bar(x - width/2, success_rates, width, label='Success Rate (%)', color=color_success, alpha=0.8)
    ax1.set_ylabel('Solved instances (%)', color=color_success, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color_success)
    ax1.set_ylim(0, 110)
    
    # Plot average runtime (bars)
    ax2 = ax1.twinx()
    color_time = '#d62728'
    rects2 = ax2.bar(x + width/2, avg_runtimes, width, label='Avg Solve Time (s)', color=color_time, alpha=0.8)
    ax2.set_ylabel('Average runtime of solved (seconds)', color=color_time, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=color_time)
    ax2.set_ylim(0, max(avg_runtimes) * 1.15)
    
    # Add values on top of bars
    for rect in rects1:
        height = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width()/2.0, height + 1, f'{height:.1f}%', 
                 ha='center', va='bottom', color='black', fontweight='bold')
                 
    for rect in rects2:
        height = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width()/2.0, height + (max(avg_runtimes)*0.01), f'{height:.2f}s', 
                 ha='center', va='bottom', color='black', fontweight='bold')
                 
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=11)
    
    plt.title(title, fontsize=13, fontweight='bold', pad=15)
    
    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Global comparison bar chart saved: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    
    # -------------------------------------------------------------
    # 1. Set 1a
    # -------------------------------------------------------------
    dir_set1a = os.path.join(project_dir, "graph/set-1a")
    os.makedirs(dir_set1a, exist_ok=True)
    
    file_cp_set1a = os.path.join(base_dir, "cp_classic_500s.csv")
    file_bd_set1a = os.path.join(base_dir, "benders_500s.csv")
    file_cp_dist_set1a = os.path.join(base_dir, "cp_distribute_500s.csv")
    file_cp_dist_sym_set1a = os.path.join(base_dir, "cp_distribute_symmetry_500s.csv")
    
    print("\n--- Generating Set 1a Bar and Histogram charts ---")
    generate_speedup_histogram(
        file_cp=file_cp_set1a,
        file_bd=file_bd_set1a,
        title="Benders Speedup over CP Classic (Set 1a)",
        output_path=os.path.join(dir_set1a, "benders-speedup-histogram.png")
    )
    
    generate_global_comparison_bars(
        files={
            "Benders": {"filepath": file_bd_set1a, "time_col": "BD_Runtime (s)"},
            "CP Classic": {"filepath": file_cp_set1a, "time_col": "CP_Runtime (s)"},
            "CP Distribute": {"filepath": file_cp_dist_set1a, "time_col": "CP_Runtime (s)"},
            "CP Distribute\n+ Symmetry": {"filepath": file_cp_dist_sym_set1a, "time_col": "CP_Runtime (s)"}
        },
        title="Success Rate and Average Runtime Comparison (Set 1a)",
        output_path=os.path.join(dir_set1a, "global-comparison-bar.png")
    )
    
    # -------------------------------------------------------------
    # 2. Subset 1 (MSLIB1)
    # -------------------------------------------------------------
    dir_subset1 = os.path.join(project_dir, "graph/subset-1")
    os.makedirs(dir_subset1, exist_ok=True)
    
    file_cp_sub1 = os.path.join(base_dir, "cp_classic_subset1.csv")
    file_bd_sub1 = os.path.join(base_dir, "benders_subset1.csv")
    file_cp_dist_sub1 = os.path.join(base_dir, "cp_distribute_subset1.csv")
    file_cp_dist_sym_sub1 = os.path.join(base_dir, "cp_distribute_symmetry_subset1.csv")
    
    print("\n--- Generating Subset 1 Bar and Histogram charts ---")
    generate_speedup_histogram(
        file_cp=file_cp_sub1,
        file_bd=file_bd_sub1,
        title="Benders Speedup over CP Classic (Subset 1 - 200 instances)",
        output_path=os.path.join(dir_subset1, "benders-speedup-histogram.png")
    )
    
    generate_global_comparison_bars(
        files={
            "Benders": {"filepath": file_bd_sub1, "time_col": "BD_Runtime (s)"},
            "CP Classic": {"filepath": file_cp_sub1, "time_col": "CP_Runtime (s)"},
            "CP Distribute": {"filepath": file_cp_dist_sub1, "time_col": "CP_Runtime (s)"},
            "CP Distribute\n+ Symmetry": {"filepath": file_cp_dist_sym_sub1, "time_col": "CP_Runtime (s)"}
        },
        title="Success Rate and Average Runtime Comparison (Subset 1)",
        output_path=os.path.join(dir_subset1, "global-comparison-bar.png")
    )
