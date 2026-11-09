# 🧩 Plugin Control Center

> Deux onglets, versions et sources GitHub sans réinstaller le lanceur pour chaque plugin compatible.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

![Schéma du Plugin Manager](assets/plugins.svg)

## 🖥️ Les deux onglets

| Onglet | Ce que vous contrôlez |
|---|---|
| **Plugins** | Nom, version installée, dernière version, source, statut ; Installer / Mettre à jour ; Activer / Désactiver ; Importer ZIP ; Restaurer |
| **Sources** | Nom de source, dépôt GitHub, branche, dossier, état ; Ajouter / Modifier / Supprimer / Recharger |

Le catalogue initial pointe vers [les plugins officiels](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/tree/main/Plugins). D'autres sources GitHub publiques HTTPS peuvent être ajoutées **volontairement**. Une source supprimée ne désinstalle pas les plugins déjà installés.

## 🔁 Installer un plugin

1. Depuis la barre, cliquez sur **Extensions**.
2. Sous **Sources**, contrôlez ou ajoutez les URL de dépôts de confiance.
3. Cliquez sur **Synchroniser** pour récupérer le catalogue.
4. Sélectionnez une ligne **Plugins** et comparez **Installée** et **Dernière**.
5. Cliquez sur **Installer** ou **Mettre à jour** ; examinez les informations de compatibilité et les permissions déclarées.
6. Confirmez. **Activez** le plugin, ou restaurez la version précédente au besoin.

Les ZIP compatibles n'exigent pas une mise à jour du lanceur NovaBar, **tant que le runtime existant sait déjà gérer leur API**.

## 📜 Format d'extension

Le programme accepte les manifestes déclaratifs **API v1** et les descriptions de capteurs **API v2**. Exemple simplifié :

```json
{
  "id": "cpu-temperature-viewer",
  "name": "CPU Temperature Viewer",
  "slot": "cpu",
  "version": "1.0.0",
  "api_version": 2,
  "kind": "builtin-sensor",
  "sensor_keys": ["cpu_temperature_c"]
}
```

Ce fichier exemple représente des métadonnées déclaratives, **pas** un script exécutable ou une sonde arbitraire. Les seules vues Holo actuellement reconnues par le runtime sont les valeurs de `cpu-core-matrix` associées au plugin `cpu-manager-viewer`.

## 🛡️ Vérifications

- Contrôle du catalogue GitHub, de l'intégrité du ZIP et du manifeste.
- Rejet des chemins échappant au paquet, exécutables/scripts ou permissions invalides.
- Confirmation utilisateur, installation préparée de façon atomique et **rollback** vers la version précédente.
- **Aucune signature d'éditeur indépendante** : une empreinte SHA ne garantit pas que l'auteur du plugin est fiable.

## 💾 Où sont conservés les modules ?

`Documents/NovaBar/Plugins/` (chemin de documents du compte utilisateur) ; sources dans `Documents/NovaBar/App/Settings/plugin_sources.json`. Ils sont conservés lorsque les binaires sont remplacés. [Voir les profils](Configuration.md).

---

<sub>⚡ NovaBar • CYBER NEXUS HUD · Les illustrations sont documentaires, les fonctions non livrées sont signalées.</sub>

## Plugins Next 0.5

CPU Manager/Viewer 2.1.0 et les six autres ZIP 1.1.0 déclarent le kit Holo partagé. Les anciens ZIP restent lisibles ; leurs versions et activations sont conservées. Les Holo GPU, FANS, NETWORK, SSD, RAM et CPU utilisent les données du collecteur natif : le logo en haut à droite ouvre le panneau au clic uniquement. Le contrôle CPU Mode appartient au service de l’hôte et n’exécute pas de code fourni par le ZIP.
