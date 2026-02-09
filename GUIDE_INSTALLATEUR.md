# 📦 GUIDE COMPLET : CRÉER L'INSTALLATEUR WINDOWS (SETUP.EXE)

Ce guide vous explique pas à pas comment transformer votre logiciel en un fichier d'installation professionnel (`setup.exe`) que vos utilisateurs pourront installer facilement (comme n'importe quel logiciel Windows).

---

## 🛠️ ÉTAPE 1 : INSTALLER LES OUTILS (À faire une seule fois)

Pour fabriquer l'installateur, nous utilisons un logiciel gratuit et standard appelé **Inno Setup**.

1.  **Téléchargez Inno Setup** :
    *   Allez sur : [https://jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
    *   Cliquez sur le lien **"Random Site"** en dessous de **"Stable Release"**.
    *   Lancez le fichier téléchargé (`innosetup-x.x.x.exe`) et installez-le en faisant "Suivant" partout.

---

## 📂 ÉTAPE 2 : PRÉPARER VOS FICHIERS

Avant de créer l'installateur, assurez-vous que tous les ingrédients sont dans votre dossier de projet (`C:\Users\PC-GARFIELD\Downloads\testy crousty`).

Il vous faut impérativement :
1.  **L'exécutable du logiciel** :
    *   Il doit être dans le dossier `dist` et s'appeler `YouTubeDownloader_v25.exe`.
    *   *(C'est généré automatiquement quand vous lancez `build.bat`)*.

2.  **FFMPEG (Le moteur vidéo)** :
    *   Vous devez avoir le fichier `ffmpeg.exe` directement dans le dossier `testy crousty`.
    *   *Pourquoi ?* Pour que l'installateur puisse le copier chez l'utilisateur. S'il n'est pas là, l'installateur se créera quand même, mais l'utilisateur devra installer FFMPEG lui-même.

---

## 🚀 ÉTAPE 3 : GÉNÉRER L'INSTALLATEUR

C'est l'étape magique ! J'ai déjà écrit le script de configuration pour vous (`setup.iss`).

1.  Allez dans votre dossier `testy crousty`.
2.  Trouvez le fichier **`setup.iss`** (c'est un fichier avec une icône Inno Setup).
3.  **Double-cliquez dessus**. Inno Setup va s'ouvrir.
4.  Dans Inno Setup, cliquez sur le bouton **Play** (la flèche verte ▶️) ou appuyez sur **F9**.

**C'est tout !**
L'ordinateur va travailler quelques secondes.
Une fois fini, vous trouverez un nouveau fichier dans votre dossier `testy crousty` :
👉 **`YouTubeDownloader_Setup_v25.exe`**

C'est ce fichier que vous donnez à vos amis/utilisateurs !

---

## 🔄 COMMENT METTRE À JOUR POUR LA VERSION 26 ?

Quand vous sortirez la version 26, voici comment refaire l'installateur :

1.  **Modifiez le script `setup.iss`** :
    *   Ouvrez `setup.iss` avec le Bloc-notes (ou Inno Setup).
    *   Changez la ligne 4 : `#define MyAppVersion "25.0"` ➔ `"26.0"`.
    *   Changez la ligne 7 : `YouTubeDownloader_v25.exe` ➔ `YouTubeDownloader_v26.exe`.
    *   Changez la ligne 25 : `OutputBaseFilename=YouTubeDownloader_Setup_v25` ➔ `_v26`.

2.  **Compilez** :
    *   Appuyez sur **Play** (F9) dans Inno Setup.

Et voilà, vous avez votre `YouTubeDownloader_Setup_v26.exe` !
