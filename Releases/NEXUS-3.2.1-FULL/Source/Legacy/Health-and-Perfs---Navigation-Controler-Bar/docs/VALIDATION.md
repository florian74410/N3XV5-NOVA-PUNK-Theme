# Validation v0.1.0

Vérifications locales sur Linux, Qt 6.8.3, rendu offscreen :

- Tests de stockage des préférences, refus des valeurs invalides et récupération d’un fichier corrompu.
- Ajout de paquet déclaratif, activation, mise à jour, préservation de l’état et restauration.
- Rejet des chemins interdits, code exécutable, mauvais identifiants/API et paquet modifié.
- Simulation d’une erreur disque au remplacement : l’installation précédente reste disponible.
- Génération/retrait de l’autostart Linux et échappement des chemins à espaces et caractères réservés.
- Création et rendu de la coque en haut, en bas, à droite ; boutons de navigation visibles.
- Rendus aux largeurs 800, 1024, 1366 et 2048 ; disposition compacte ou détaillée.
- Rétractation/retour et conservation des dimensions ; préférences enregistrées/annulées.
- Inspection visuelle de docs/preview.png à 2048 × 205.
- Build PyInstaller Linux réussi ; lancement du binaire autonome avec --preview vérifié.

Le premier pipeline GitHub a également passé les 10 tests sur Windows Server 2022
et fabriqué le Setup Windows. Cela ne remplace pas une ouverture manuelle sur Windows 10/11.

Les tests utilisent des profils temporaires et ne modifient pas l’autostart de la session de travail.
Les avertissements Qt « propagateSizeHints / raise » sont propres au plugin de rendu offscreen.

Restent à vérifier sur machines réelles : composition transparente, multiécran avec DPI différents,
interaction avec les bureaux/panneaux, autostart à la reconnexion, installateurs Windows/macOS,
Bazzite/Wayland et plein écran. Le pipeline de builds n’équivaut pas à ces tests manuels.

Correction de transparence : test pixel alpha du fond général à 0 et des fonds de modules/boutons
à 0 %, 35 % et 100 %, avec maintien des textes opaques. 11 tests locaux passent.


## Exécution vérifiée pour V0.2 — 31/10/2026

CI : https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/actions/runs/41149562691

- Ubuntu 22.04 : **SUCCESS** (tests + binaire + archive Linux).
- Windows Server 2022 : **SUCCESS** (tests + compilation + installeur Inno Setup).
- macOS 15 Apple Silicon : **SUCCESS** (tests + compilation + DMG arm64).
- Suite : 13 tests Python (11 fondation + 2 plugins/télémétrie), avec paquets ZIP v2 créés en test.

Cette validation en environnement CI n'est pas un essai matériel sur Windows 7,
Bazzite/Wayland ou Mac Intel anciens. Les contrôles PWM/Turbo restent absents.

## CYBER NEXUS HUD / NovaBar 0.3

25 tests locaux après vérification des migrations et des liens internes de bundles : acceptation des conditions, profil local,
préservation de l’e-mail lors d’un changement de préférences, refus d’une autre famille d’OS ou
High Sierra, raccourcis en double, conservation d’une version existante, absence d’activation
si le binaire échoue, manifeste officiel et versions, refus des chemins ZIP et des liens externes, refus d’envoi
SMTP sans confirmation, et conservation de l’état actif en cas de mauvais SHA-256.
Aperçus des deux pages inspectés. Les tests utilisent des répertoires temporaires.

Validation native locale 0.3 : runtime et lanceur PyInstaller construits ; lanceur autonome
ouvert en aperçu ; installation du vrai runtime dans un dossier temporaire, test de l’exécutable
staged avec version 0.3.0 attendue, création du profil et activation testées sans enregistrer
l’autostart ni créer de raccourci sur la machine de travail. Archive runtime créée, extraite
avec l’extracteur de l’updater, puis vrai binaire extrait exécuté en self-test : succès.
Les deux pages ont été inspectées à partir des captures du lanceur.

Le chemin source a également été exécuté en entier : venv privé, téléchargement des dépendances,
compilation PyInstaller sur l’hôte Linux, self-test du binaire produit et activation temporaire : succès.

## NovaBar 0.3.1 — bord supérieur et exécutables

- Géométrie de fenêtre vérifiée à 100 % sur 1366, 1920, 2560 et 3840 pixels logiques,
  avec écran sélectionné, origines négatives et écran décalé en hauteur. Gauche, droite,
  centre et bord supérieur correspondent exactement à l’écran ; aucune marge extérieure.
- Alpha nul du fond général et alpha des fonds de modules/boutons vérifiés après ajout des reflets.
- Fichier Linux .run : contrôle SHA-256 embarqué et refus d’un téléchargement corrompu.
- Aucun nouveau plugin développé. Les effets sont des simulations vectorielles 2D et ne requièrent pas RTX.
- Les tests offscreen ne remplacent pas un contrôle du placement sous XFCE/Wayland sur machine réelle.

## NovaBar 0.3.3 — compacité et fermeture

- Hauteur par défaut réduite de 200 à 72 px, limite stricte 50–150 px ; migration du seul ancien défaut 200 px,
  conservation des tailles personnalisées et des profils déjà versionnés.
- Bouton Quitter visible à droite et raccourci Ctrl+Q ; commandes sur une seule ligne.
- Mise en page compacte avec typographie non étirée ; mise à l’échelle uniforme des cadrans détaillés.
- Vérification des hauteurs 50/72/96/150 px et de la visibilité de Quitter, activation du bouton testée.
- Les invariants de transparence, d’ancrage au bord et de largeur restent contrôlés.

Les tailles antérieures hors plage sont bornées à 50–150 px ; l’ancien défaut 200 px devient 72 px.
34 tests locaux passent, y compris les régressions CPU Holo déjà présentes sur le dépôt.
Les zones de clic, drag et ancrage des hologrammes utilisent le même calcul de rectangles que
la disposition responsive des modules, vérifié sur plusieurs largeurs et après réorganisation.
