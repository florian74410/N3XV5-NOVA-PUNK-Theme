# NovaBar Next 0.5.0 · validation

Validation locale du 31 octobre 2026, Linux x86_64, Python 3.12 / Qt 6.8.3.

- 64 tests unittest réussis : régressions existantes, migrations, thèmes, icônes Holo, contrôleur CPU, permissions, absence de sonde, downloader et checksum.
- Vérification visuelle des thèmes et d’un panneau Holo avec données absentes ; aucune valeur matérielle illustrative au démarrage normal.
- Compilation PyInstaller : runtime, installateur hors ligne et downloader.
- Auto-test du runtime compilé avec version attendue 0.5.0 : réussi.
- Auto-test graphique du downloader compilé, sans réseau ni installation : réussi.
- Tests des archives runtime et installateur : réussis.
- Paquet DEB 0.5.0 amd64 généré, extrait sans installation système ; auto-test de l’exécutable extrait : réussi.
- Paquet RUN 0.5.0 généré : intégrité SHA-256 et auto-test natif `--verify` réussis.
- Génération des manifestes de release testée avec fixtures multi-OS : réussie.
- `git diff --check` : réussi.

## Limites de cette validation

Aucune écriture sur un CPU réel n’a été effectuée. Les backends Intel/CPUFreq ont été testés sur des fichiers temporaires reproduisant le contrat sysfs, y compris refus d’écriture et lecture après écriture. Le comportement matériel, les permissions locales, X11/Wayland, Windows et macOS demandent une validation sur leurs environnements réels.

La CI est configurée pour les builds natifs Linux, Windows et macOS Intel/ARM. Une version du code source n’implique pas qu’une release stable et ses exécutables soient déjà publiés. Le downloader échoue explicitement si aucun manifeste bootstrap stable n’est disponible.

## Complément 0.5.1

68 tests locaux réussis ; rendu des compte-tours, transparence des surfaces Holo, détails réseau par interface et absence de valeurs inventées vérifiés. Runtime, archive d’installation et exécutable extrait du DEB testés. Voir [la note 0.5.1](UPDATE_V051.md). Les nouveaux builds multi-OS restent à suivre dans GitHub Actions.
