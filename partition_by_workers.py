import os
import glob
import shutil

source_dir = "/home/haleckse/MS-RCPSP-AF/datas/subsets-sorted"
target_dir = "/home/haleckse/MS-RCPSP-AF/datas/subsets_by_workers"

print(f"Reading instances from {source_dir}...")
files = glob.glob(os.path.join(source_dir, "*.msrcp"))

instances = []
for f in files:
    with open(f, 'r') as file:
        lines = [line.strip() for line in file if line.strip() and not line.startswith('\\*')]
        parts = lines[0].split()
        m = int(parts[1])
        instances.append((m, os.path.basename(f), f))

# Sort by number of workers m ascending, then by filename
instances.sort(key=lambda x: (x[0], x[1]))

print(f"Total instances parsed: {len(instances)}")

# Clean and recreate target directory
if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
os.makedirs(target_dir, exist_ok=True)

# Copy instances into 33 subsets of 200 instances each
subsets_summary = []
num_subsets = 33
instances_per_subset = 200

for i in range(num_subsets):
    subset_name = f"subset_{i+1}"
    subset_path = os.path.join(target_dir, subset_name)
    os.makedirs(subset_path, exist_ok=True)
    
    sub = instances[i*instances_per_subset : (i+1)*instances_per_subset]
    for item in sub:
        src_file = item[2]
        dst_file = os.path.join(subset_path, item[1])
        shutil.copy2(src_file, dst_file)
        
    m_min = sub[0][0]
    m_max = sub[-1][0]
    m_avg = sum(x[0] for x in sub) / len(sub)
    subsets_summary.append((i+1, len(sub), m_min, m_max, round(m_avg, 1)))
    print(f"Created {subset_name} with {len(sub)} instances (Workers: min={m_min}, max={m_max}, avg={m_avg:.1f})")

print("\nPartitioning complete! All 6600 instances successfully partitioned into 33 subsets in:")
print(f"-> {target_dir}")
