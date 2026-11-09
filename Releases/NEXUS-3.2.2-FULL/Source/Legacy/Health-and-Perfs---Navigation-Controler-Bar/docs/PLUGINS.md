# Contrat d’extensions — socle v1

Aucun plugin n’est livré. Les cartes matérielles visibles sont des éléments de la maquette.
Le gestionnaire permet de préparer l’ajout et la mise à jour des futurs modules sans coupler
le dessin de la barre à un collecteur matériel.

## Paquet local

Un fichier .hbp est une archive ZIP contenant exactement `manifest.json`, sans sous-dossier.
Taille du paquet : 2 Mio maximum ; manifeste : 16 Kio maximum. Format de manifeste :

```json
{
  "id": "identifiant-extension",
  "name": "Nom affiché",
  "version": "1.0.0",
  "api_version": 1,
  "kind": "declarative",
  "slot": "cpu",
  "description": "Description facultative"
}
```

Slots autorisés : cpu, gpu, ram, storage, fans, network.
Identifiant : 3 à 64 caractères minuscules/chiffres/tirets, commençant par une lettre.
Version : trois entiers séparés par des points. L’API et les champs sont validés strictement.
Ni Python, ni JavaScript, ni commande shell, ni fichier exécutable n’est accepté dans un paquet v1.

## Cycle

1. Le bouton Extensions ouvre la liste locale.
2. Importer / Mettre à jour ouvre la sélection du paquet.
3. Le manifeste et le SHA-256 sont présentés avant confirmation dans l’application.
4. Le paquet est revérifié et préparé dans un dossier temporaire.
5. Une nouvelle extension est désactivée par défaut ; activer réserve le libellé du slot.
6. Pour un même identifiant, seule une version supérieure est acceptée ; l’activation est conservée.
7. L’ancienne installation est gardée dans un dossier caché `.identifiant.previous`.
8. En cas d’erreur lors du remplacement, l’ancienne installation est rétablie.
9. Version précédente remet l’installation précédente ; un seul niveau de retour est conservé.

Le SHA-256 détecte un changement entre l’inspection et l’installation ; ce n’est pas une signature
éditeur ni une garantie d’origine. Aucun store ou serveur de mise à jour distant n’est connecté.
Les manifestes mal formés déjà présents dans le dossier utilisateur sont ignorés.
Si plusieurs extensions activées visent le même slot, le dernier identifiant dans l’ordre
alphabétique fournit le libellé ; un arbitrage interactif des conflits sera nécessaire pour le moteur futur.

## Étapes ultérieures, hors périmètre actuel

Le futur moteur d’exécution devra définir un contrat versionné de mesures et vues,
les permissions, l’isolation des processus, les délais d’expiration, les signatures et la
politique de compatibilité. Il n’est pas activé implicitement par ce gestionnaire.
Les mises à jour du programme lui-même passent par un nouveau paquet d’installation ;
le gestionnaire .hbp ne remplace pas le binaire principal.
