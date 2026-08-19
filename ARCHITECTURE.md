# Architecture — YouTube Downloader Ultimate 1.1.0

La v1.1.0 sépare volontairement l'interface graphique de la logique métier.

- `main.py` : point d'entrée minimal.
- `youtube_downloader/ui.py` : orchestration de la fenêtre principale.
- `youtube_downloader/ui_download.py` : onglet téléchargement direct.
- `youtube_downloader/ui_search.py` : recherche YouTube et preview FFplay.
- `youtube_downloader/youtube_service.py` : téléchargement, recherche et preview yt-dlp.
- `youtube_downloader/dependencies.py` : FFmpeg, FFplay et Deno.
- `youtube_downloader/update_service.py` : vérification et préparation des mises à jour.
- `youtube_downloader/settings.py` : préférences utilisateur avec écriture atomique.
- `youtube_downloader/models.py` : requêtes et résultats typés.
- `youtube_downloader/logs.py` : buffer thread-safe et adaptateur yt-dlp.
- `updater.py` : remplacement autonome du binaire après fermeture.

## Principes appliqués

1. **Responsabilité unique** : chaque module a un rôle précis.
2. **Pas de blocage de l'UI** : réseau, yt-dlp et installations tournent hors du thread Tkinter.
3. **UI thread-safe** : les retours des workers passent par `after()`.
4. **Options yt-dlp centralisées** : un changement YouTube se corrige dans un seul fichier.
5. **Exceptions ciblées** : suppression des `except:` silencieux.
6. **TLS vérifié** : suppression de `nocheckcertificate=True`.
7. **Écritures atomiques** : settings et téléchargements d'update évitent les fichiers partiels.
8. **Extraction d'archives protégée** : validation des chemins avant extraction d'une mise à jour.
9. **Versions comparées numériquement** : `1.10` est correctement supérieur à `1.9`.
10. **Commentaires utiles** : les commentaires expliquent les raisons et contraintes, pas la syntaxe évidente.

## Validation

Le projet est vérifié avec Python 3.11 avant le build Windows, puis compilé avec PyInstaller dans une CI isolée de la branche principale.
