# Downloader · NovaBar 0.5

Le bootstrapper **NovaBarDownloader** détecte l’OS et l’architecture, télécharge un paquet de la dernière release stable officielle, vérifie son SHA-256, puis lance son installation. Il est séparé des installateurs hors ligne afin d’éviter une boucle de téléchargement.

## Formats

| OS | Format | Installation |
|---|---|---|
| Linux x86_64 avec dpkg | `.deb` prioritaire | apt-get, autorisation native pkexec si nécessaire |
| Linux x86_64 sans dpkg ou choix manuel | `.run` | Assistant hors ligne utilisateur |
| Windows x86_64 | `.exe` | Setup utilisateur avec runtime inclus |
| macOS | DMG hors ligne | Downloader automatique indisponible, message explicite |

L’absence de `.deb` dans la release permet de choisir le `.run`. Un échec de checksum ou d’installation ne lance jamais un autre programme silencieusement. ARM Linux/Windows ne reçoit pas un paquet x86_64 de substitution.

Avant le téléchargement, choisir thème, épaisseur (50–150 px), position, repli, always-on-top et activation Holo. Les préférences sont enregistrées après installation réussie. Pour le `.run`, l’assistant hors ligne permet aussi de modifier ces choix. Les liens README et Wiki restent accessibles.

## Build et publication

```sh
python -m pip install . pyinstaller==6.16.0
python -m unittest discover -s tests -v
python scripts/build.py
```

`build.py` génère le runtime, l’installateur hors ligne et `dist/NovaBarDownloader-<platform>` (`.exe` sous Windows). Les ZIP de plugins intégrés sont générés avant la compilation. Les scripts Install-Linux/Windows démarrent le downloader depuis les sources ; `python scripts/install.py --offline` conserve le chemin de compilation local. Sur macOS, le lanceur source conserve l’assistant hors ligne.

La CI native produit les paquets sur quatre runners. Une publication par tag `v0.5.0` n’est possible qu’après succès des builds. `release_manifest.py` lie la version, les URLs et les empreintes dans `novabar-bootstrap-manifest.json`, en complément du manifeste de mise à jour des runtimes.

Une release sans ce manifeste produit une erreur explicite et renvoie vers les installateurs hors ligne. Les checksums contrôlent l’intégrité, pas une signature d’éditeur. Windows/macOS ne sont pas signés/notarisés par ce travail.

## Migration

Les dossiers de profils, sources et plugins ne sont pas effacés. L’ancienne préférence `auto_hide` est convertie vers auto/manual ; l’ancien thème reste accepté. Une première installation binaire initialise les plugins officiels. Si des plugins existent déjà, leurs versions et états d’activation restent prioritaires : mise à jour explicite via le gestionnaire.
