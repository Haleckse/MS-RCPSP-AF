import networkx as nx
import matplotlib.pyplot as plt

# 1. Création du graphe orienté
G = nx.DiGraph()

# 2. Ajout des arêtes avec leurs capacités
# (S -> Ouvriers) : Capacité = 1 (1 personne physique)
G.add_edge('S', 'Ouvrier 1', capacity=1)
G.add_edge('S', 'Ouvrier 2', capacity=1)
G.add_edge('S', 'Ouvrier 3', capacity=1)

# (Ouvriers -> Tâches) : Compétences (Capacité infinie)
INF = float('inf')
G.add_edge('Ouvrier 1', 'Tâche A', capacity=INF)
G.add_edge('Ouvrier 2', 'Tâche B', capacity=INF)
G.add_edge('Ouvrier 3', 'Tâche C', capacity=INF)

# (Tâches -> Puits) : Demande (Besoins)
G.add_edge('Tâche A', 'P', capacity=0) # Pas besoin de la tâche A
G.add_edge('Tâche B', 'P', capacity=2) # Besoin de 2 personnes
G.add_edge('Tâche C', 'P', capacity=1) # Besoin de 1 personne

# 3. Calcul du Flot Max et de la Coupe Min
cut_value, partition = nx.minimum_cut(G, 'S', 'P')
reachable, non_reachable = partition

print(f"--- RÉSULTATS DU CALCUL ---")
print(f"Valeur de la coupe minimale (Flot Max) : {cut_value}")
print(f"Noeuds côté Source (accessibles) : {reachable}")
print(f"Noeuds côté Puits (isolés, en déficit) : {non_reachable}")

# 4. Identification de l'arête spécifique qui forme la coupe
# Une arête (u, v) est dans la coupe si u est côté Source et v est côté Puits
cut_edges = []
for u, v in G.edges():
    if u in reachable and v in non_reachable:
        cut_edges.append((u, v))

print(f"Arête(s) saturée(s) formant la coupe : {cut_edges}")

# ==========================================
# 5. VISUALISATION DU GRAPHE
# ==========================================

# Définition des positions manuellement pour un bel affichage de gauche à droite
pos = {
    'S': (0, 1),
    'Ouvrier 1': (1, 2), 'Ouvrier 2': (1, 1), 'Ouvrier 3': (1, 0),
    'Tâche A': (2, 2), 'Tâche B': (2, 1), 'Tâche C': (2, 0),
    'P': (3, 1)
}

plt.figure(figsize=(10, 6))

# Dessin des noeuds
nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='lightblue', edgecolors='black')
nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

# Séparation des arêtes normales et des arêtes coupées
normal_edges = [e for e in G.edges() if e not in cut_edges]

# Dessin des arêtes normales (en gris)
nx.draw_networkx_edges(G, pos, edgelist=normal_edges, arrows=True, arrowsize=20, edge_color='gray')

# Dessin de la COUPE MINIMALE (en rouge épais)
nx.draw_networkx_edges(G, pos, edgelist=cut_edges, arrows=True, arrowsize=20, edge_color='red', width=3.0)

# Ajout des étiquettes de capacité sur les flèches
edge_labels = {}
for u, v, data in G.edges(data=True):
    cap = data['capacity']
    edge_labels[(u, v)] = 'inf' if cap == INF else str(cap)
    
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=10)

plt.title("Réseau de Flot - Détection du goulot de compétence (Ligne Rouge)", fontsize=14)
plt.axis('off')
plt.tight_layout()
plt.show()