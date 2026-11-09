> **0.6.11 :** [cockpit à grandes icônes, NEXUS organisé et icônes système](../UPDATE_V0611.md). Mise à jour via **Paramètres → Upgrade**.

> **0.6.10 :** [barre inférieure autonome et bords invisibles](Docks.md) · [Upgrade intégré](Mises-a-jour.md).

<p align="center"><img src="assets/banner.svg" alt="NovaBar — Wiki CYBER NEXUS HUD" width="100%"></p>
<h1 align="center">⚡ NovaBar — Documentation officielle</h1>
<p align="center"><strong>Votre PC. Votre cockpit.</strong> · Une barre néon compacte et modulaire sous Linux, Windows et macOS.</p>
<p align="center"><a href="Premiers-pas.md">🚀 Commencer</a> · <a href="Installation.md">📦 Installer</a> · <a href="Architecture.md">🏗️ Architecture</a> · <a href="Depannage.md">🧰 Assistance</a></p>

![NovaBar — aperçu néon généré par l'application](../../Assets/Previews/novabar-v051-transparent-holo.png)

<sub>📸 Capture d'aperçu fournie par le projet. Les valeurs visibles sont des exemples, pas une lecture du PC du visiteur.</sub>

## 🌌 Explorez NovaBar

| Espace | Description | Documentation |
|:---|:---|:---|
| 🌡️ **Monitoring** | CPU, GPU, RAM, stockage, ventilateurs et réseau | [Voir les capteurs](Capteurs.md) |
| 🎛️ **Cockpit néon** | Barre collée au bord, 50–150 px, transparence et rétractation | [Guide de l'interface](Interface.md) |
| 🧠 **CPU Core Matrix** | Tableau Holo détaillé du processeur | [Voir le panneau Holo](Holo-CPU.md) |
| 🧩 **Plugin Control Center** | Plugins ZIP, versions, sources GitHub, restauration | [Gérer les extensions](Plugins.md) |
| 🔄 **Mises à jour** | Installeurs Linux, Windows, macOS et conservation des données | [Cycle de mise à jour](Mises-a-jour.md) |
| 🏗️ **Architecture** | Python / PySide6, collecteur et stockage local | [Schéma du fonctionnement](Architecture.md) |

## 🧭 Sommaire complet

- [🏠 Accueil](Home.md)
- [🚀 Premiers pas](Premiers-pas.md)
- [📦 Installation](Installation.md)
- [🎛️ Interface](Interface.md)
- [📊 Capteurs](Capteurs.md)
- [🧠 Holo CPU](Holo-CPU.md)
- [🧩 Plugins & Sources](Plugins.md)
- [⚙️ Configuration](Configuration.md)
- [🔄 Mises à jour](Mises-a-jour.md)
- [🏗️ Architecture](Architecture.md)
- [🛠️ Dépannage](Depannage.md)
- [❓ FAQ](FAQ.md)
- [🤝 Contribuer](Contribuer.md)

## ✅ Livré / ⏳ Prévu

**Disponible dans le code :** modules adaptatifs, télémétrie locale en lecture seule, Plugin Manager 2-en-1, fontes et halos cyan, bouton Quitter, profil local, cadrans CPU/GPU/RAM/SSD et Holo compacts transparents pour les six modules avec leurs plugins actifs. Le bouton **? Wiki** fait partie de l'intégration **v0.3.6** et ouvre ce guide dans le navigateur.

**Non disponible à ce stade :** contrôle PWM, signatures d’éditeur des installateurs et comportement garanti sur tous les compositeurs Wayland.

> ⚠️ Ce wiki est publié dans **`docs/wiki/`** (compatible avec la structure des Wikis GitHub). Ces pages du dépôt sont la référence. Le workflow de synchronisation met aussi à jour le Wiki natif lorsqu’il est initialisé et accessible.

---

<sub>NovaBar • CYBER NEXUS HUD • Documentation maintenue dans le dépôt. Les illustrations utilisent des valeurs d'exemple ; les sondes réelles dépendent du système et du matériel.</sub>

- [CPU Mode et priorité OS](CPU-Mode.md)
- [Downloader](Downloader.md)

## Version 0.5.1

Compte-tours proportionnels, Holo plus petits et transparents, débits par interface : [notes de mise à jour](../UPDATE_V051.md). Les visuels sont regroupés dans [Assets](../../Assets/README.md).

## Version 0.5.2

Holo lisibles sur fond clair, faibles débits visibles, connexion active prioritaire et graphique UP vert / DOWN rouge / ping bleu : [guide 0.5.2](../UPDATE_V052.md).

## Style Holo 0.5.3

Les six panneaux ont maintenant un **fond uni sombre à 85 % d’opacité**, teinté selon le thème. Les tableaux et graphiques partagent ce fond. Les cadres néon fins ont des angles biseautés et des détails diagonaux. Les valeurs sont blanches, les libellés gris bleuté et les titres accentués ; Green Matrix ne recolore plus toutes les écritures en vert. Les couleurs du réseau restent UP vert / DOWN rouge / ping bleu.

![Holo CPU et Réseau](../../Assets/Previews/novabar-v053-cpu-network.png)

*Données de démonstration. [Guide 0.5.3](../UPDATE_V053.md).*
