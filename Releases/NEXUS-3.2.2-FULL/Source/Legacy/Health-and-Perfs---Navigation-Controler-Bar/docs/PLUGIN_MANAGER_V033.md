# NovaBar 0.3.3 — Plugin Manager 2-en-1 (Plugins + Sources)

## Objectif
NovaBar ne nécessite **plus de réinstaller son lanceur pour importer ou mettre à jour un plugin compatible**. Le lanceur installe une fois le runtime 0.3.3, puis le Plugin Manager télécharge et extrait les ZIP directement dans le profil de l'utilisateur. Une nouvelle fonctionnalité qui requiert une *nouvelle API du moteur*, un capteur non exposé ou une modification du runtime devra toutefois mettre à jour NovaBar.

## Interface
Fenêtre compacte `NovaBar • PLUGIN CONTROL CENTER` avec deux onglets :
- **Plugins** : tableau scrollable `Plugin | Installée | Dernière | Source | Statut`, sélection de ligne → bouton **Installer** ou **Mettre à jour** ; actions Activer/Désactiver, Importer ZIP local, Restaurer la version précédente.
- **Sources** : tableau scrollable `Source | Dépôt | Branche | Dossier | État`, commandes Ajouter, Modifier, Supprimer, Recharger. Nouvelle source initialisée par défaut avec `main` et `Plugins`. Sources multiples, modifiables indépendamment, appartenant à l'utilisateur.

L'interface reprend le thème bleu électrique PCB, sans ouvrir une fenêtre par plugin. Le téléchargement/synchronisation utilise un thread Qt ; une barre d'activité et un état sont visibles.

## Catalogue distant
- **Fournisseur actuellement supporté** : dépôts GitHub publics en HTTPS, par exemple
  `https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar` + `main` + `Plugins`.
- Une source peut être désactivée sans être supprimée.
- GitHub API liste les blobs du dépôt ; seuls les fichiers à la racine du dossier source de forme `plugin-id-vMAJEUR.MINEUR.CORRECTIF.zip` sont retenus.
- La dernière version supérieure parmi les sources activées est proposée ; un plugin déjà installé ne disparaît pas si sa source est débranchée.
- Le catalogue ne lance jamais une commande `git clone`, `pip`, `bash` ou `install.sh`.

## Installation sécurisée
1. Sélection de la ligne affichant version installée et dernière version disponible.
2. Clic Installer / Mettre à jour ; téléchargement HTTPS limité en taille dans un dossier temporaire.
3. Vérification du SHA du blob Git enregistré dans le catalogue, puis de l'empreinte SHA-256 locale.
4. Validation par le moteur de plugin : ID, version, permissions, structure ZIP, taille décompressée et chemins.
5. Popup listant les dépendances, les permissions, la compatibilité minimale du runtime et le SHA-256 ; confirmation explicite.
6. Extraction atomique dans `Documents/NovaBar/Plugins/<id>`, sans exécuter le code téléchargé.
7. Maintien de l'état actif, conservation de l'ancienne version pour rollback, génération du rapport d'installation.

Les dépendances nécessaires à l'API en cours sont déjà fournies par l'installateur NovaBar ; des dépendances nouvelles ne sont **pas** installées automatiquement. Si la version minimale NovaBar exigée par un plugin dépasse celle du runtime, une mise à jour du moteur est indiquée.

## Emplacement des données
`Documents/NovaBar/App/Settings/plugin_sources.json` (sauf configuration personnalisée du dossier de documents), indépendant des exécutables stockés dans des dossiers versionnés. Les préférences ne sont jamais effacées par la mise à jour du runtime.

## Limites / évolutions
- Pas encore de GitLab / Gitea / dépôt SSH privé : adapter de catalogue à développer.
- Les plugins API 2 actuels déclarent des capteurs et des vues intégrées à NovaBar. Les nouvelles catégories et les moteurs de rendu réellement externes demanderont un système de runtime de plugin isolé et versionné.
- La mise à jour des plugins est indépendente du lanceur **pour les fonctionnalités prises en charge par l'API installée**.
- Les paquets ne sont pas signés par un éditeur indépendant ; ne configurez que des sources de confiance.
- L'installateur v0.3.3 (après build et tests) sera la mise à jour initiale unique pour obtenir ce gestionnaire.
