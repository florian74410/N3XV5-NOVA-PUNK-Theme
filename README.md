# N3XVS HUD Theme — 1.0

Pack de thème interactif multi-modules pour Linux (Windows/macOS à étudier ultérieurement).

## État

**Structure initiale uniquement.** Aucun exécutable validé ; la version NovaBar 0.8.2.2 installée reste inchangée.

- `App/Core/` : état, communication intermodules, cycles de vie et logique système
- `App/GraphicEngine/` : interfaces de rendu 2D / 3D, thèmes et effets
- `App/Settings/` : écran de configuration, schémas, journalisation (les données utilisateurs restent hors dépôt)
- `App/Modules/{Top,Right,Left,Bottom}/` : zones du HUD indépendantes
- `App/Assets/` : bibliothèque centrale, originaux non modifiés et dérivés
- `Linux/STABLE_BUILD/` : paquet complet **uniquement après validation**
- `Linux/STABLE_UPDATE/` : mises à jour **uniquement après validation**
- `Update/Modules/` : fichiers et métadonnées de mises à jour par module

Règle de promotion : développement → vérifications → test réel Linux XFCE → validation explicite → STABLE_BUILD / STABLE_UPDATE.

La collecte du patrimoine graphique 0.1 à 1.0 aura lieu **sans supprimer les anciens dépôts**. Voir `App/Assets/README.md`.
