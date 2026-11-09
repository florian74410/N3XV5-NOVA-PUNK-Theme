# NovaBar 0.5.1 — cadrans et Holo transparents

## Affichage

La barre conserve 72 px par défaut, une épaisseur de 50 à 150 px et la disposition adaptative. Les cadrans CPU/GPU montrent la fréquence en GHz ; ceux de RAM/SSD montrent le pourcentage d’utilisation. Le dessin utilise une échelle uniforme. À très faible largeur, les valeurs restent prioritaires sur les cadrans.

![Comparatif 0.5.1](../Assets/Previews/novabar-v051-transparent-holo.png)

*Capture du vrai rendu Qt avec données de démonstration. La grille est un fond de présentation ; elle ne fait pas partie des Holo.*

## Détails des plugins

Activez le plugin concerné dans le gestionnaire, puis cliquez sur son **logo en haut à droite**. Un second clic ferme le Holo. Le survol et le clic sur les valeurs n’ouvrent aucun panneau. La fermeture et l’épinglage restent disponibles.

| Holo | Taille initiale | Détails |
|---|---|---|
| CPU | 460 × 330 px | Modèle, cœurs/threads, fréquence, charge, température et puissance package ; fréquences/températures par cœur si disponibles |
| GPU | 380 × 280 px | Charge, température, fréquence, VRAM utilisée/totale et puissance mesurée |
| RAM | 380 × 280 px | Utilisée, disponible, totale, pourcentage |
| SSD | 380 × 280 px | Capacité du volume système, espace utilisé/libre, débits de lecture/écriture agrégés de tous les disques |
| Ventilateurs | 380 × 280 px | Noms des sondes et RPM |
| Réseau | 380 × 280 px | Débits globaux, état de chaque interface, vitesse de lien et débits individuels |

Les tableaux défilent lorsque leurs lignes dépassent la fenêtre. Les panneaux restent dans les limites de l’écran. Le fond des Holo, de leurs tableaux et de leurs zones de défilement est transparent ; les textes et circuits néon suivent le thème choisi. L’opacité des modules de la barre reste un réglage distinct.

Une valeur inconnue reste **—**. La première mesure de débit par interface attend un second relevé. La vitesse de lien en Mbit/s n’est pas le débit mesuré en MB/s. Le logiciel ne déduit pas de watts par cœur à partir du TDP ou de la puissance package.

## Installation et conservation des données

Fermez l’ancienne NovaBar avant d’installer le nouveau paquet. Une mise à jour du paquet remplace les fichiers de l’application et conserve les profils, thèmes et plugins utilisateur ; il n’est pas nécessaire de supprimer leurs dossiers.

Le DEB compilé localement a été construit sous glibc 2.39 : il cible Mint 22 / Ubuntu 24.04 et versions ultérieures compatibles. La dépendance glibc est déterminée par l’environnement de compilation. Les builds CI sur Ubuntu 22.04 doivent être validés séparément avant d’annoncer leur compatibilité avec des systèmes plus anciens.

## Vérifications

- 68 tests locaux réussis sous Python 3.12 / Qt 6.8.3.
- Pixels de fond transparents et géométrie des panneaux vérifiés.
- Rendu de la barre vérifié à 50, 72, 100 et 150 px, sur 800, 1280 et 1920 px de largeur.
- Auto-test du runtime compilé et de l’exécutable extrait du DEB réussi.
- Archives runtime et installateur hors ligne vérifiées.

Ces vérifications ne remplacent pas un essai sur bureau réel, notamment sous Wayland, Windows ou macOS.
