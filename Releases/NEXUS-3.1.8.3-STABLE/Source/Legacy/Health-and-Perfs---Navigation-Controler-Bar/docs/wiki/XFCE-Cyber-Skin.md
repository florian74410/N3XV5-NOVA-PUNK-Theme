> **0.6.11 :** NovaBar affiche les icônes StatusNotifier/AppIndicator et XApp de Linux Mint dans la barre inférieure, avec leurs actions et menus. Les icônes exclusivement XEmbed restent sur le panneau XFCE. [Notes du cockpit](../UPDATE_V0611.md).

# Barre inférieure XFCE / NovaBar 0.6.10

La 0.6.10 remplace l’habillage seul de la 0.6.9 par une **barre NovaBar autonome**. Le message « Aucun panneau XFCE fixé au bord inférieur » ne bloque plus son affichage.

Activer **Préférences → Docks → Barre inférieure NovaBar**. Le panneau XFCE inférieur est masqué pendant la session et restauré à la fermeture. Le panneau supérieur XFCE reste indépendant. La configuration et les plugins XFCE sont conservés.

Le menu **Système → Afficher les icônes XFCE pendant 30 s** permet d’accéder aux applets natives. NovaBar propose ses propres fenêtres, lanceurs, horloge et liens vers les outils système ; il n’héberge pas encore les applets tierces.

Le diagnostic depuis l’icône NovaBar indique la géométrie de la barre et le nombre de fenêtres XFCE masquées. Si ce nombre vaut zéro, la barre NovaBar fonctionne quand même. Ces fonctions nécessitent une session **X11**.

Le mode d’habillage XFCE historique reste facultatif lorsque la barre autonome est désactivée. Les réglages d’origine sont sauvegardés et restaurables.

[Les quatre surfaces](Docks.md) · [Mises à jour](Mises-a-jour.md)
