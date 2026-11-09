# 📦 Installation

> Le format dépend du système ; la configuration et les plugins doivent rester indépendants des binaires.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

## 🐧 Linux Mint XFCE / Ubuntu x86_64

**Paquet Debian natif — recommandé pour le monitoring matériel :**

```bash
cd "$(xdg-user-dir DOWNLOAD)"
sudo apt install ./NovaBar_0.3.6_amd64.deb
novabar
```

Vous pouvez aussi double-cliquer le `.deb` pour passer par le gestionnaire de paquets local. Le nom exact peut changer après une nouvelle version.

**Flatpak — plus isolé :**

```bash
flatpak install --user ./NovaBar_0.3.6_x86_64.flatpak
flatpak run io.github.florian74410.NovaBar
```

Le runtime Freedesktop 25.08 est nécessaire. Certains capteurs et le démarrage automatique sont limités dans le sandbox.

**Lanceur historique autonome :**

```bash
sh CyberNexusHUD-Linux-x86_64.run --check
sh CyberNexusHUD-Linux-x86_64.run
```

Ne confondez pas les trois méthodes : un ancien runtime installé par `.run` **n'est pas désinstallé** automatiquement par `.deb` ou Flatpak. Évitez deux instances concurrentes.

## 🪟 Windows 10 et 11

Utilisez [CyberNexusHUD-Setup-Windows.exe](../../Executable/Windows/CyberNexusHUD-Setup-Windows.exe), puis suivez l'assistant. Le lanceur installe et configure NovaBar dans l'environnement du compte utilisateur.

## 🍎 macOS 12+

Choisissez le [DMG Apple Silicon](../../Executable/MacOS/CyberNexusHUD-macOS-arm64.dmg) ou le [DMG Intel](../../Executable/MacOS/CyberNexusHUD-macOS-x86_64.dmg). Les paquets actuels ne sont pas signés/notarisés : le système peut en limiter l'ouverture.

## 🛠️ Désinstallation

| Installation | Commande / méthode | Données locales |
|---|---|---|
| `.deb` | `sudo apt remove novabar` | Conservées |
| Flatpak | `flatpak uninstall --user io.github.florian74410.NovaBar` | Conserver les données, ne pas forcer `--delete-data` |
| `.run` | Supprimer le runtime utilisateur après fermeture et désactiver autostart | Ne pas supprimer `Documents/NovaBar` |
| Windows / macOS | Outils de désinstallation et retrait de l'app | Sauvegarder les profils si nécessaire |

Les [paquets officiels et leurs empreintes](../../Executable/README.md) sont tous regroupés sous `Executable/`. Consultez également [Mises à jour](Mises-a-jour.md).

---

<sub>NovaBar • CYBER NEXUS HUD • Documentation maintenue dans le dépôt. Les illustrations utilisent des valeurs d'exemple ; les sondes réelles dépendent du système et du matériel.</sub>
