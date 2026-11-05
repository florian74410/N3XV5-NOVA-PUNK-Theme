# N3XV5 HUD Native Unified 2.2.5 — Slim Gauges & Live Metrics

Préversion native Qt pour Linux Mint XFCE/X11, **une TopBar et une Navbar Bottom**.
Basée sur le moteur NovaBar 0.8.2.2 ; toutes les fonctionnalités historiques (Holo, tâches actives, icônes, boutons et tray) sont conservées.

## Modifications 2.2.5

- Bottom : hauteur par défaut **62 px** (ancienne 70), paddings horizontaux **8 px**, verticaux **5 px**, espaces entre onglets **3 px** ; animation du contour des tâches actives maintenue.
- Top : compte-tours CPU et ventilateurs **20 secteurs LED** (10 bleu, 5 vert, 3 orange, 2 rouge) ; **pas d'aiguille**. Alignement des textes/segments de charge corrigé et bouton « Réglages » miniaturisé.
- SSD : débit constructeur **si renseigné dans l'inventaire historique**, sinon plafond nominal d'interface SATA II 300 MB/s, SATA III 600 MB/s ; un lien indéterminé ne permet pas d'affirmer qu'un disque est SATA III. Débits généralement observés pour les SSD : ~250–280 MB/s (SATA II) et ~500–560 MB/s (SATA III), selon contrôleur/SSD/charge.
- NET : débit descendant/montant **réel et instantané** via la télémétrie réseau historique, en **MB/s**. Test Internet en **Mb/s** (unités différentes) via `speedtest` ou `speedtest-cli` installés sur l'hôte, déclenché par le bouton **REFRESH — TEST DÉBIT INTERNET** des Paramètres. Test automatique horaire **optionnel, désactivé par défaut** : un test transfère potentiellement beaucoup de données.
- PWR : consommation du CPU et/ou GPU seulement si capteur réel ; mesure de décharge batterie sur portable si disponible. **Pas de faux total PC** : pour la consommation murale complète, une prise wattmètre est nécessaire.
- Paramètres : fréquence télémétrie 1–15 s, limite de FPS visuels 5–30, intensité néon, opacité Top et Bottom, contraste, activation du test horaire et REFRESH manuel. Aucune mesure Internet dans le thread UI.

## Mise à jour sur installation 2.2.4

L'installateur `update.sh` : tests hors affichage, copie de sauvegarde, arrêt ciblé du seul processus unifié, remplacement de la Top, de la Bottom, du module de métriques et du lanceur, puis redémarrage. N'affecte ni les profils, ni les scripts Turbo, ni les autres applications XFCE.

```bash
bash ./update.sh
```

`bash ./update.sh --no-start` installe sans relancer.

**Contrôle réalisé :** compilation Python, `bash -n`, tests de géométrie, stockage, puissance, conversion Speedtest, intégration et archive. **Test graphique sur XFCE réel restant à effectuer** (Qt non présent sur le banc de test).
