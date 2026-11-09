# 🤝 Contribuer

> Améliorer NovaBar sans compromettre les données utilisateur ni masquer les limitations matérielles.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

## 🔧 Développement

Le code de l'application est maintenu dans [la branche de développement](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/tree/feature/cyber-nexus-installer-v03). Python 3.10+ et Qt/PySide6 sont utilisés. Les tests du dépôt peuvent être exécutés ainsi :

```bash
python -m pip install -e .
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

## 📚 Documentation

Les pages sont stockées dans `docs/wiki/`, les diagrammes SVG dans `docs/wiki/assets/`. Les images de l'application utilisées comme référence sont dans `docs/`. Ce format Markdown est compatible avec la navigation de type GitHub Wiki (`Home.md`, `_Sidebar.md`, `_Footer.md`). **Un Wiki GitHub natif séparé n'est pas actuellement synchronisé automatiquement.**

Conventions : titres parlants, captures d'écran du programme quand elles existent, texte alternatif pour les images, liens relatifs corrects et distinction claire entre livrable / prototype / idée R&amp;D.

## 🧪 Tests prioritaires

- Linux Mint XFCE + X11 : placement au pixel, rétractation, zones cliquables, notifications.
- GPU NVIDIA/AMD/Intel : vérification des sondes réellement accessibles.
- Windows 10/11 et macOS Intel/ARM : comportement des installateurs et démarrage automatique.
- Linux Wayland/Bazzite : ancrage et clavier, sans prétendre à un support universel.
- Plugins : validation des ZIP, intégrité, permissions, compatibilité et rollback.

## 🐛 Issues et Pull Requests

[Signaler un bug](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/issues) · [Consulter les Pull Requests](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/pulls). N'incluez jamais de clés, de données privées ou de journaux bruts contenant des secrets.

---

<sub>⚡ NovaBar • CYBER NEXUS HUD · Les illustrations sont documentaires, les fonctions non livrées sont signalées.</sub>
