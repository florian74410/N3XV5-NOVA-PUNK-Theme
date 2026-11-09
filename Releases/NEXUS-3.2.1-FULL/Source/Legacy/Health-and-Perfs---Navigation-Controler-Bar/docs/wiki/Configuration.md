# ⚙️ Préférences, thèmes et profils

> Chaque compte dispose de ses propres choix, même après les mises à jour.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

## 🎛️ Écran Préférences

Depuis la roue dentée, configurez : **position**, **écran**, **longueur**, **épaisseur**, **opacité**, **rétractation**, **délai**, **taux d'actualisation**, **répertoire Console**, **raccourcis** et **démarrage automatique** suivant le mode d'installation.

| Réglage | Plage | Défaut |
|---|---|---|
| Épaisseur | 50–150 px | 72 px |
| Longueur | 25–100 % | 100 % |
| Opacité des panneaux | 0–100 % | 88 % |
| Délai avant rétractation | 3–120 s | 15 s |
| Lecture des sondes | 1–30 s | 2 s |
| Thème | `cyber-futuriste` | Electric Blue |

Le réglage d'opacité concerne les **fonds** des modules : textes, icônes et bordures restent affichables. Les emplacements de plugins peuvent être réordonnés dans la barre. Le système valide les valeurs avant de les enregistrer.

## 📁 Fichiers persistants

Les fichiers de configuration et le programme sont **séparés** :

```text
Documents/NovaBar/
├── App/
│   ├── Profiles/<compte>.json
│   └── Settings/plugin_sources.json
├── Profiles/<compte>.json
├── Plugins/
├── Themes/
├── Reports/
└── Updates/
```

Le dossier système des préférences est distinct : Linux `~/.config/health-perfs-bar/settings.json` (ou `$XDG_CONFIG_HOME`), Windows `%APPDATA%/HealthPerfsBar`, macOS `~/Library/Application Support/HealthPerfsBar`. La variable `HEALTHBAR_DATA_DIR` est utile pour des tests isolés.

## 🧲 Démarrage automatique

- **Linux :** fichier XDG sous `~/.config/autostart/`.
- **Windows :** registre `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **macOS :** `~/Library/LaunchAgents/com.healthperfs.bar.plist`.
- **Flatpak :** l'interface désactive la configuration d'autostart classique, car le sandbox et le lanceur diffèrent.

## 🔐 Confidentialité

L'identité et les préférences sont stockées localement. Le catalogue de plugins et la recherche de nouvelles versions contactent GitHub **lorsqu'ils sont déclenchés**. La Console exécute seulement les scripts locaux choisis par l'utilisateur après confirmation, avec ses propres droits. Les valeurs des sondes ne sont pas envoyées automatiquement à GitHub ni à un serveur de mesures.

---

<sub>⚡ NovaBar • CYBER NEXUS HUD · Les illustrations sont documentaires, les fonctions non livrées sont signalées.</sub>

## Préférences Next

`retract_mode` : always / auto / manual ; `always_on_top` et `holo_enabled` : booléens. `theme` : blue-neon / green-matrix / red-blood ; cyber-futuriste reste accepté. Les autres préférences et profils sont conservés.
