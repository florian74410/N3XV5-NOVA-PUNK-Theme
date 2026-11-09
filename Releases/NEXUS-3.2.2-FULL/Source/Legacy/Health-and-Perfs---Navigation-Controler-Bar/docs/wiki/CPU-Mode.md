# CPU Mode · NovaBar 0.5

Le bouton **CPU Mode** expose Turbo Off, Turbo On et Auto (85°C). La sélection est une demande ; le texte et l’infobulle montrent le résultat vérifié. Une erreur est affichée dans une boîte de dialogue et `CPU !` reste visible. Aucun mode n’est imposé au démarrage et le mode CPU n’est pas persisté : rouvrir NovaBar ne modifie pas le matériel.

## Politique Auto

À 85 °C ou plus : demander Turbo Off. À 80 °C ou moins : demander Turbo On. Entre les deux : conserver l’état effectif. Si la température manque ou devient invalide, demander Turbo Off et signaler l’absence de sonde. Les sondes CPU exposées par psutil sont utilisées ; la valeur la plus chaude de la première famille CPU disponible est retenue, sans repli vers une zone ACPI arbitraire.

La collecte Auto est demandée chaque seconde, sur le worker de télémétrie. Les durées des sondes et le planificateur peuvent retarder la réaction. Ce contrôle logiciel ne remplace pas la protection thermique du firmware. À la fermeture, le dernier état matériel reste en place ; NovaBar ne réactive pas le Turbo implicitement.

## Backends

| Plateforme | Contrôle | Limites |
|---|---|---|
| Linux Intel | `/sys/devices/system/cpu/intel_pstate/no_turbo` | Valeur 0 = autoriser Turbo, 1 = désactiver |
| Linux CPUFreq, dont AMD compatible | `/sys/devices/system/cpu/cpufreq/boost` | Valeur 1 = autoriser boost, 0 = désactiver |
| Windows | Indisponibilité explicite | Pas de pilote matériel livré |
| macOS | Indisponibilité explicite | Pas d’API matérielle stable intégrée |

Une écriture est suivie d’une lecture. Si le noyau refuse, si le fichier manque ou si les permissions sont insuffisantes, l’utilisateur est informé ; aucun succès n’est simulé. Autoriser Turbo ne garantit pas que le CPU atteigne une fréquence particulière.

Sur Linux, le compte doit disposer des droits d’écriture appropriés sur le seul commutateur sysfs concerné. NovaBar ne s’élève pas automatiquement et ne modifie pas les permissions du système. La configuration des droits appartient à l’administrateur ; il ne faut pas lancer toute l’interface en root. Dans Flatpak, le contrôle reste généralement inaccessible.

## Priorité de la barre

- X11 : Qt always-on-top et demande EWMH ABOVE au gestionnaire de fenêtres. Pas de réservation d’espace ni de vol de focus.
- Wayland : le compositeur décide du placement et de l’empilement ; cette version n’utilise pas layer-shell. XWayland ne garantit pas la superposition sur les fenêtres Wayland natives.
- Windows : Qt et SetWindowPos TOPMOST sans activation. Aucun contournement du plein écran exclusif, des écrans sécurisés ou de l’UAC.
- macOS : priorité Qt ; Spaces et plein écran restent gérés par macOS.

La case Always-on-top reste désactivable. Les fenêtres Holo suivent ce choix.
