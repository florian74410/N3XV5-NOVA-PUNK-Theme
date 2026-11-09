# NovaBar 0.5.2 — lisibilité Holo et graphique réseau

## Holo transparents lisibles

Les caractères et boutons reçoivent un contour sombre opaque, avec leur couleur néon à l’intérieur. Les fonds des panneaux, tableaux et graphiques restent transparents. Cette méthode améliore la lecture sur un bureau clair ou sombre sans ajouter de plaque grise ou blanche.

![Rendu sur fond clair et sombre](../Assets/Previews/novabar-v052-network-contrast.png)

*Rendu réel Qt, avec des mesures de démonstration. Les captures individuelles dans Assets gardent leur canal alpha.*

## Réseau : courbes et histogramme

| Série | Représentation | Couleur | Échelle |
|---|---|---|---|
| UP / émission | Courbe | Vert | Débit à gauche |
| DOWN / réception | Courbe | Rouge | Débit à gauche |
| Ping | Histogramme | Bleu | Millisecondes à droite |

Les couleurs de ces mesures restent les mêmes dans Blue Neon, Green Matrix et Red Blood. Le graphique conserve 120 secondes d’historique pendant la session, y compris lorsque le Holo est fermé. Il ne stocke pas ces mesures sur disque. Une donnée absente interrompt la courbe ; elle n’est pas remplacée par zéro. L’échelle des débits s’adapte aux B/s, kB/s et MB/s selon la vue ; une valeur nulle réelle reste distincte d’un capteur absent.

Le Holo Réseau mesure initialement 460 × 360 px pour accueillir le graphique et un tableau défilant. Son en-tête identifie l’interface suivie. Sur Linux, la route par défaut est prioritaire ; à défaut, le collecteur suit les interfaces actives, avec priorité aux interfaces non virtuelles. Il évite de sommer simultanément l’interface suivie et les bridges Docker. Les compteurs couvrent le trafic de la connexion, pas uniquement le trafic Internet.

## Ping et limites

Un ping **ICMP vers 1.1.1.1** est demandé toutes les 10 secondes depuis le worker de collecte. Le sous-processus est limité à 1,5 seconde ; il ne bloque pas l’interface Qt. Un histogramme est ajouté uniquement pour une nouvelle réponse, sans dupliquer la valeur mise en cache à chaque relevé de débit.

Un filtre ICMP, un refus de permission, une commande absente ou un délai dépassé affiche un état d’indisponibilité et aucune barre de ping ; cela ne prouve pas une coupure Internet. Le DEB dépend de `iputils-ping`. Le fonctionnement du ping dans un sandbox Flatpak dépend des outils et permissions de ce runtime.

## Corrections des débits

Les petits transferts sont affichés en B/s ou kB/s au lieu d’être arrondis à `0.0 MB/s`. La collecte réseau reste indépendante d’une erreur de sonde CPU. Un compteur réinitialisé ou une interface nouvellement apparue attend un second relevé ; aucune pointe artificielle n’est créée.

## Validation

75 tests locaux réussis, dont : unités des faibles débits, choix de l’interface, absence de double comptage Docker, compteur réinitialisé, panne CPU indépendante, délai/cache ICMP, historique borné, données absentes, couleurs des trois thèmes et contours de texte sur fond transparent. Le rendu Qt a été inspecté sur fond blanc et sombre. La validation native multi-OS est effectuée par GitHub Actions avant publication des paquets.
