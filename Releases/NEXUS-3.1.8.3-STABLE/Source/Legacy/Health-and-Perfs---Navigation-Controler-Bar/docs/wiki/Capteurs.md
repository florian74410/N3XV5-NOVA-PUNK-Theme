# 📊 Capteurs et données

> Les mesures sont locales et en lecture seule ; aucune donnée inventée si la sonde manque.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

## Les six modules

| Module | Informations accessibles suivant l'OS | Origine |
|---|---|---|
| 🌡️ **CPU** | Fréquence GHz, charge %, température, modèle, cœurs | `psutil`, sondes OS et module CPU |
| 🎮 **GPU** | Température, charge, VRAM, fréquence, puissance | `nvidia-smi` quand NVIDIA compatible |
| 🧠 **RAM** | Mémoire utilisée/disponible et taux d'utilisation | `psutil.virtual_memory` |
| 💾 **Disque** | Espace utilisé/libre, activité de lecture/écriture | `psutil.disk_usage`, compteurs I/O |
| 🌀 **Ventilateurs** | Vitesse RPM | `psutil.sensors_fans` |
| 🌐 **Réseau** | Débits entrants / sortants | Compteurs réseau, différences dans le temps |

### Mesure absente : « — »

Le symbole **—** signifie que l'information est indisponible ou non remontée par la sonde : il ne signifie **ni 0, ni défaut matériel**. Les watts individuels par cœur CPU ne sont pas inventés. La puissance CPU de package n'est connue que si une sonde adaptée est accessible (notamment Intel RAPL sur certains Linux).

### Unités

- **°C** pour les températures ; **GHz** pour la fréquence CPU/GPU ; **RPM** pour les ventilateurs.
- La RAM et le stockage sont calculés en unités binaires et affichés sous l'appellation « GB » dans certaines vues.
- Les débits réseau sont des **MB/s** (octets par seconde), pas des Mb/s.
- Le rafraîchissement capteurs par défaut est de **2 secondes**, indépendamment des animations graphiques plus rapides.

### Limites matérielles

Le collecteur GPU actuel utilise notamment `nvidia-smi` : une carte AMD ou Intel peut ne pas afficher de température GPU. Des capteurs CPU/fans peuvent manquer faute de pilote ou de permissions ; cela ne doit pas être présenté comme une erreur générale.

![Chemin des mesures vers le HUD](assets/architecture.svg)

---

<sub>NovaBar • CYBER NEXUS HUD • Documentation maintenue dans le dépôt. Les illustrations utilisent des valeurs d'exemple ; les sondes réelles dépendent du système et du matériel.</sub>

## Réseau détaillé — 0.5.1

Le panneau Réseau liste les interfaces exposées par le système : état, vitesse de lien en Mbit/s et débits reçus/émis en MB/s. Les débits sont calculés par différence entre deux relevés ; le premier reste inconnu. Les compteurs globaux regroupent les interfaces et peuvent inclure des interfaces virtuelles ; ils ne représentent pas forcément un seul transfert Internet. Aucune adresse IP ni MAC n’est nécessaire pour ces détails.

## Réseau et ping — 0.5.2

Les petits débits utilisent B/s, kB/s ou MB/s. La connexion active/route par défaut passe avant Docker et les interfaces déconnectées. Le ping ICMP vise **1.1.1.1**, toutes les 10 secondes, avec un délai borné ; une absence de réponse ne signifie pas une coupure Internet.

Le Holo conserve 120 secondes d’historique : **UP vert**, **DOWN rouge**, **ping bleu en histogramme**. Débits et ping ont deux échelles distinctes ; les couleurs ne changent pas avec le thème. [Guide détaillé](../UPDATE_V052.md).
