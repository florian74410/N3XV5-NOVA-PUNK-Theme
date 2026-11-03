# N3XV5 TOP HUD — V1.3 (branche de prévalidation)

Branche de travail : `work/top-hud-v1.3-live-plugins`.

## Structure attendue

- `Settings/HTML/index.html` — interface TOP HUD
- `Settings/CSS/hud-top.css` — box néon, compte-tours et jauges
- `Settings/JS/hud-top.js` — animations, graphes et interactions
- `Bridge/local_live_server.py` — serveur HTTP local et relevés Linux en lecture seule
- `Bridge/legacy_readonly_bridge.py` — liaison facultative aux collecteurs NovaBar existants

L'archive V1.3 a été préparée séparément et **son code doit être importé depuis l'archive de test**. La présence de ce README ne signifie pas que la conversion est déjà publiée ou stable.

## Sécurité

Ne pas déplacer cette version vers `Linux/STABLE_BUILD` sans validation utilisateur sur XFCE. L'installation système NovaBar 0.8.2.2 doit rester intacte.
