import os
import sys
import pandas as pd

from cp_model_carla import solve_cp
from benders import run_benders_lbbd
from checker import verify_solution
from utils import parse_instance
import json

def run_all_benchmarks(method, instances_folder, timelimit):
    print("="*67)
    print(f" DÉMARRAGE DES BENCHMARKS | Méthode : {method.upper()} | Limite : {timelimit}s")
    print("="*67)

    if not os.path.exists(instances_folder):
        print(f"Erreur : Le dossier {instances_folder} n'existe pas.")
        return

    files = [f for f in os.listdir(instances_folder) if f.endswith('.dzn')]
    files.sort()

    results = []

    for inst_num, filename in enumerate(files):
        print(f"\n[{inst_num + 1}/{len(files)}] Traitement de l'instance : {filename}...")
        filepath = os.path.join(instances_folder, filename)

        # Initialisation de la ligne de résultat
        row_data = {
            "instNum": inst_num + 1,
            "Instance": filename
        }

        # ===============
        # EXÉCUTION CP
        # ===============
        if method in ['cp', 'both']:
            print(" -> Lancement CP Classique...")
            msol, InTech = solve_cp(filepath, timelimit, display_gantt=False)
            #msol, AW, SW = solve_cp(filepath, timelimit, display_gantt=False)
            if msol:
                makespan = msol.get_objective_values()[0]
                lb = msol.get_objective_bounds()[0]
                gap = msol.get_objective_gaps()[0]
                runtime = msol.get_solve_time()
                optimal = 1 if gap <= 0.0001 else 0

                row_data.update({
                    "CP_Optimal": optimal,
                    "CP_LB": lb,
                    "CP_Makespan": makespan,
                    "CP_Gap (%)": round(gap * 100, 2),
                    "CP_Runtime (s)": round(runtime, 2)
                })
                print(f"    [CP] Makespan: {makespan} | Gap: {round(gap*100,2)}% | Temps: {round(runtime,2)}s")
            else:
                row_data.update({
                    "CP_Optimal": 0, "CP_LB": "N/A", "CP_Makespan": "N/A",
                    "CP_Gap (%)": "N/A", "CP_Runtime (s)": timelimit
                })
                print("    [CP] Aucun planning trouvé (Timeout).")

        # ---------------------------------------------------------
        # EXÉCUTION BENDERS (LBBD)
        # ---------------------------------------------------------
        if method in ['benders', 'both']:
            print(" -> Lancement LBBD...")
            bd_success, bd_makespan, bd_runtime, bd_iters = run_benders_lbbd(filepath, timelimit)

            if bd_success:
                row_data.update({
                    "BD_Optimal": 1, # Benders s'arrête uniquement quand il a prouvé l'optimalité
                    "BD_Makespan": bd_makespan,
                    "BD_Iters": bd_iters,
                    "BD_Runtime (s)": round(bd_runtime, 2)
                })
                print(f"    [BD] Makespan: {bd_makespan} | Itérations: {bd_iters} | Temps: {round(bd_runtime,2)}s")


                # Appelle du checker
                data_inst = parse_instance(filepath)
                with open("solution.json", "r") as f:
                    schedule_dict = json.load(f)
                verify_solution(data_inst, schedule_dict, bd_makespan)


            else:
                row_data.update({
                    "BD_Optimal": 0, "BD_Makespan": "N/A",
                    "BD_Iters": bd_iters if bd_iters else "N/A",
                    "BD_Runtime (s)": timelimit
                })
                print("    [BD] Aucun planning prouvé optimal trouvé (Timeout).")

        results.append(row_data)

    # ---------------------------------------------------------
    # EXPORTATION DES RÉSULTATS
    # ---------------------------------------------------------
    df = pd.DataFrame(results)

    print("\n" + "="*80)
    print("                 RÉSUMÉ DES BENCHMARKS")
    print("="*80)
    print(df.to_string(index=False))

    csv_filename = f"resultats_mspsp_{method}.csv"
    df.to_csv(csv_filename, index=False, sep=";")
    print(f"\nLes résultats ont été exportés dans le fichier : {csv_filename}")

if __name__ == "__main__":
    # Gestion des arguments de la ligne de commande
    if len(sys.argv) < 2:
        print("Usage: python benchmark.py <methode> [dossier_instances] [timelimit]")
        print("Méthodes : 'cp', 'benders', ou 'both'")
        print("Exemple  : python benchmark.py both datas/instances/ 300")
        sys.exit(1)

    # Paramètres par défaut
    methode_choisie = sys.argv[1].lower()
    DOSSIER_INSTANCES = sys.argv[2] if len(sys.argv) > 2 else "datas/instances/"
    TEMPS_LIMITE = int(sys.argv[3]) if len(sys.argv) > 3 else 3000

    if methode_choisie not in ['cp', 'benders', 'both']:
        print(f"Erreur : La méthode '{methode_choisie}' n'est pas reconnue.")
        sys.exit(1)

    run_all_benchmarks(methode_choisie, DOSSIER_INSTANCES, TEMPS_LIMITE)
