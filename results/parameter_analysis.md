# 📊 Analyse Discriminante des Paramètres du Dataset (Set 1a)

Ce document présente une analyse détaillée de l'impact des paramètres de génération des instances du jeu **Set 1a** sur les performances de résolution des trois méthodes implémentées : la **Décomposition de Benders (LBBD)**, le **CP Classique** et le **CP Distribute**.

Les résultats ont été obtenus sur un ensemble de **215 instances** avec une limite de temps (Time Limit) fixée à **500 secondes**.

---

## 📈 Tableau Comparatif Global

Ce tableau croise les taux de succès (% d'instances résolues à l'optimalité) et les temps moyens de calcul (en secondes) pour chaque méthode, regroupés par paramètre :

| Paramètre | Valeur | Benders - Succès | Benders - Temps | CP Classique - Succès | CP Classique - Temps | CP Distribute - Succès | CP Distribute - Temps |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 👥 **m** *(Effectif)* | **10** | 88.68 % | 97.75 s | 66.04 % | 272.57 s | 37.74 % | 355.67 s |
| | **13** | **100.00 %** | **0.21 s** | 61.11 % | 234.80 s | 50.00 % | 255.46 s |
| | **15** | **100.00 %** | **0.13 s** | 88.89 % | 63.40 s | 88.89 % | 64.93 s |
| | **20** | **100.00 %** | 2.11 s | 75.93 % | 166.30 s | 75.93 % | 140.60 s |
| | **25** | **100.00 %** | **0.13 s** | 90.74 % | 57.08 s | 98.15 % | 11.55 s |
| | **30** | **100.00 %** | **0.14 s** | 94.44 % | 36.42 s | **100.00 %** | 1.75 s |
| | | | | | | | |
| 📐 **nc** *(Réseau)* | **1.5** *(Lâche)* | 93.06 % | 43.79 s | 73.61 % | 172.02 s | 68.06 % | 176.29 s |
| | **1.8** *(Moyen)* | **98.59 %** | **14.75 s** | **88.73 %** | **107.84 s** | **77.46 %** | **129.39 s** |
| | **2.1** *(Dense)* | **100.00 %** | 15.42 s | 73.61 % | 173.46 s | 73.61 % | 152.57 s |
| | | | | | | | |
| 🛠️ **sf** *(Skills)* | **0.00** *(Spécialisé)*| 96.30 % | 38.23 s | **79.63 %** | 150.31 s | 70.37 % | 161.57 s |
| | **0.50** *(Moyen)* | **100.00 %** | **0.62 s** | 79.25 % | **143.79 s** | 66.04 % | 181.07 s |
| | **0.75** *(Polyvalent)*| 92.59 % | 57.39 s | 77.78 % | 166.73 s | 74.07 % | 157.87 s |
| | **1.00** *(RCPSP)* | **100.00 %** | 2.11 s | 77.78 % | 144.26 s | **81.48 %** | **111.44 s** |

*Les meilleures performances pour chaque paramètre/valeur sont mises en **gras**.*

---

## 🔍 Analyse des Facteurs de Difficulté

### 1. 👥 Le Nombre de Travailleurs ($m$) : La Criticité de la Ressource
> **Important :** C'est le paramètre le plus discriminant pour la complexité de l'affectation.

*   **Rareté ($m = 10, 13$) :** La pénurie de personnel rend la recherche d'une affectation respectant les compétences extrêmement ardue. Le solveur CP monolithique sature et Benders doit générer de nombreuses coupes de conflit pour stabiliser le problème maître.
*   **Abondance ($m = 25, 30$) :** Les contraintes d'affectation ne sont plus actives. Le problème se réduit à de l'ordonnancement temporel simple. CP Distribute résout ces instances en moins de **2 secondes** en moyenne.

### 2. 📐 La Complexité du Réseau ($nc$) : Parallélisme et Concurrence
> **Conseil :** Un réseau lâche augmente le parallélisme possible, ce qui accroît la concurrence instantanée sur les compétences.

*   **$nc = 1.5$ (Parallélisme élevé) :** C'est le cas le plus difficile pour la Décomposition de Benders (temps moyen de **43.79 s**). De nombreuses activités peuvent s'exécuter en même temps, multipliant les conflits d'affectation de travailleurs qualifiés.
*   **$nc = 1.8$ (Le "Sweet Spot") :** C'est la configuration la plus facile pour le CP Classique. Les dépendances temporelles limitent le parallélisme sans pour autant créer de longs chemins critiques difficiles à propager.

### 3. 🛠️ Le Facteur de Compétences ($sf$) : La Combinatoire de la Polyvalence
> **Remarque :** La polyvalence des travailleurs modifie la structure de recherche du sous-problème d'affectation.

*   **Polyvalence totale ($sf = 1.0$) :** Tous les travailleurs maîtrisent toutes les compétences (problème équivalent au RCPSP classique). L'affectation est triviale, Benders résout l'ensemble des instances en **2.11 s** de moyenne.
*   **Polyvalence intermédiaire ($sf = 0.75$) :** C'est le cas le plus difficile pour Benders (temps moyen de **57.39 s**). La polyvalence partielle augmente le nombre d'options de couplage dans le sous-problème sans que les contraintes d'affectation ne soient assez strictes pour couper rapidement les branches infaisables.
