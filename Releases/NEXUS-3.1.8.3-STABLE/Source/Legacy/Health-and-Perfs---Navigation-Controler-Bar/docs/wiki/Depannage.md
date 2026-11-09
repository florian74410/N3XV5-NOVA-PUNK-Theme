# 🛠️ Diagnostic et résolution

> Des vérifications graduelles, sans effacer vos profils ou extensions.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

## 🚦 Diagnostic rapide

| Symptôme | Cause possible | Action conseillée |
|---|---|---|
| La barre ne s'ouvre pas | Binaire non démarré, dépendances Qt, instance déjà lancée | Tester depuis un terminal ; vérifier les bibliothèques Qt/XCB |
| Aucun relevé de GPU | `nvidia-smi` absent, carte non NVIDIA, pilotes | Tester `nvidia-smi` (si NVIDIA) et ses permissions |
| Température / RPM = **—** | Sondes non publiées par le noyau | Vérifier la disponibilité matérielle, ne pas déduire une panne |
| Holo CPU absent | Plugin CPU Manager désactivé ou incompatible | Installer/activer ce plugin dans **Extensions** |
| Bouton Wiki sans navigateur | Association URL du bureau absente | Ouvrir [Home.md](Home.md) manuellement et vérifier le navigateur par défaut |
| Barre sous une fenêtre plein écran | Gestionnaire de fenêtres / Wayland | Tester XFCE/X11, ajuster le mode plein écran |
| Double barre / mauvaises données | Deux installations/instances distinctes | Fermer l'ancienne instance `.run` et privilégier un seul format |
| Mise à jour des plugins refusée | ZIP/manifeste incompatible, GitHub hors ligne | Lire le message d'erreur, synchroniser la source et vérifier la version |

## 🐧 Linux Mint XFCE

Sous X11, les bibliothèques XCB et OpenGL doivent être installées. Si l'interface ne s'ouvre pas, essayez dans un terminal :

```bash
novabar --version
novabar
```

Pour vérifier l'installation du paquet Debian : `dpkg -s novabar`. Pour le Flatpak : `flatpak info io.github.florian74410.NovaBar`. Pour l'ancienne édition autonome : `sh CyberNexusHUD-Linux-x86_64.run --check`.

## 📁 Journaux et données

Les rapports d'installation sont enregistrés dans le répertoire de travail `Documents/NovaBar/Reports/`. Les préférences Linux sont sous `~/.config/health-perfs-bar/`. **N'effacez pas ces dossiers comme première mesure de dépannage** ; sauvegardez-les si vous envisagez une réinstallation.

## 🛡️ Signaler un problème

Ouvrez une [issue GitHub](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/issues) en précisant : OS, session X11/Wayland, format installé, version, symptômes, étapes de reproduction et messages d'erreur. Masquez les adresses privées, clés API et identifiants des captures/logs.

---

<sub>⚡ NovaBar • CYBER NEXUS HUD · Les illustrations sont documentaires, les fonctions non livrées sont signalées.</sub>
