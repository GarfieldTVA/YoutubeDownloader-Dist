import os
import sys
import threading
import subprocess
import urllib.request
import zipfile
import tarfile
import io
import shutil
import tkinter.messagebox
import tkinter.filedialog
from PIL import Image
import customtkinter as ctk
import yt_dlp

import json
import time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CURRENT_VERSION = "1.0.5"
# URL pour vérifier les mises à jour (JSON)
# Format attendu du JSON: {"version": "25.0", "url": "https://lien/vers/nouveau.exe"}
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/GarfieldTVA/YoutubeDownloader-Dist/main/version.json" 

class MyLogger:
    def __init__(self, callback, log_list=None):
        self.callback = callback
        self.log_list = log_list

    def debug(self, msg):
        # On capture tout dans les logs détaillés
        if self.log_list is not None:
            self.log_list.append(f"[DEBUG] {msg}")
            
        if msg.startswith('[download]'):
            return
        # Affiche les messages importants qui ne sont pas du debug pur
        if not msg.startswith('[debug] '):
            self.callback(msg)

    def info(self, msg):
        if self.log_list is not None:
            self.log_list.append(f"[INFO] {msg}")

        if not msg.startswith('[download]'):
            self.callback(msg)

    def warning(self, msg):
        if self.log_list is not None:
            self.log_list.append(f"[WARNING] {msg}")

    def error(self, msg):
        if self.log_list is not None:
            self.log_list.append(f"[ERROR] {msg}")
        self.callback(f"Erreur: {msg}")

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("YouTube Downloader Ultimate - V25 (Auto-Update)")
        self.geometry("900x750")
        
        self.full_logs = []  # Stockage des logs complets

        # Initialisation du dossier de données (AppData) pour éviter les erreurs de permission
        if sys.platform == "win32":
            self.app_data = os.path.join(os.getenv('APPDATA'), 'YouTubeDownloader')
        elif sys.platform == "darwin":
            self.app_data = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "YouTubeDownloader")
        else: # Linux / Unix
            self.app_data = os.path.join(os.path.expanduser("~"), ".config", "YouTubeDownloader")

        if not os.path.exists(self.app_data):
            try:
                os.makedirs(self.app_data)
            except Exception as e:
                print(f"Erreur création AppData: {e}")

        # Chargement des paramètres (Thème)
        self.load_settings()

        # Dossier de téléchargement par défaut : Mes Documents/Downloads (au lieu de getcwd qui peut être System32)
        self.download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(self.download_folder):
             self.download_folder = os.path.expanduser("~")

        self.ffmpeg_path = self.check_ffmpeg()
        self.deno_path = self.check_and_install_deno() # Installation Deno
        
        # Ajout de bin (AppData) au PATH pour que yt-dlp trouve Deno
        bin_path = os.path.join(self.app_data, "bin")
        if os.path.exists(bin_path):
            if bin_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + bin_path
                self.full_logs.append(f"[INFO] Ajout de {bin_path} au PATH")

        # Configuration de la grille principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Création des onglets
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tab_download = self.tabview.add("Téléchargement Direct")
        self.tab_search = self.tabview.add("Recherche YouTube")
        
        self.setup_download_tab()
        self.setup_search_tab()

        if not self.ffmpeg_path:
            threading.Thread(target=self.auto_install_ffmpeg, daemon=True).start()

        # Vérification des mises à jour au démarrage (si compilé en EXE)
        if getattr(sys, 'frozen', False):
             threading.Thread(target=self.check_for_updates, daemon=True).start()

    def check_ffmpeg(self):
        candidates = []
        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
        # 1. Dans le dossier temporaire PyInstaller (si bundled)
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(sys._MEIPASS, exe_name))
            candidates.append(os.path.join(os.path.dirname(sys.executable), exe_name))
        
        # 2. Dans le dossier courant (si dev)
        candidates.append(os.path.join(os.getcwd(), exe_name))
        
        # 3. Dans AppData (téléchargé auto)
        candidates.append(os.path.join(self.app_data, exe_name))

        for path in candidates:
            if os.path.exists(path):
                return path

        # 4. Sinon PATH
        if shutil.which("ffmpeg"):
            return shutil.which("ffmpeg")
        return None

    def auto_install_ffmpeg(self):
        if sys.platform != 'win32':
            # Sur Linux/Mac, c'est mieux de passer par le gestionnaire de paquets
            msg = "Sur Linux/macOS, veuillez installer FFmpeg via votre terminal :\n\n"
            if sys.platform == "darwin":
                msg += "brew install ffmpeg"
            else:
                msg += "sudo apt install ffmpeg  (ou équivalent)"
            
            self.after(0, lambda: tkinter.messagebox.showinfo("Installation FFmpeg", msg))
            return

        try:
            print("Début installation automatique FFmpeg...")
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = os.path.join(self.app_data, "ffmpeg.zip")
            exe_path = os.path.join(self.app_data, "ffmpeg.exe")
            
            # Téléchargement
            if not os.path.exists(exe_path):
                urllib.request.urlretrieve(url, zip_path)
            
                # Extraction
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith("bin/ffmpeg.exe"):
                            with zip_ref.open(file) as source, open(exe_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                        elif file.endswith("bin/ffplay.exe"):
                            play_path = os.path.join(self.app_data, "ffplay.exe")
                            with zip_ref.open(file) as source, open(play_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                                
                # Nettoyage
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    
                self.ffmpeg_path = exe_path
                print("FFmpeg et FFplay installés avec succès !")
            
        except Exception as e:
            print(f"Erreur installation FFmpeg: {e}")

    def check_and_install_deno(self):
        # Vérifie si Deno est présent dans AppData/bin
        bin_dir = os.path.join(self.app_data, "bin")
        deno_exe = os.path.join(bin_dir, "deno.exe" if sys.platform == "win32" else "deno")
        
        if os.path.exists(deno_exe):
            return deno_exe
        
        # Sinon on regarde dans le PATH
        if shutil.which("deno"):
             return shutil.which("deno")
        
        # Sinon on lance l'installation
        threading.Thread(target=self.install_deno_thread, daemon=True).start()
        return None

    def check_for_updates(self):
        try:
            self.full_logs.append("[UPDATE] Vérification des mises à jour...")
            print(f"Vérification màj sur : {UPDATE_CHECK_URL}")
            
            # Timeout court pour ne pas bloquer
            with urllib.request.urlopen(UPDATE_CHECK_URL, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            remote_version = data.get("version", "0.0")
            
            # Gestion multi-plateforme des URLs
            download_url = ""
            assets = data.get("assets", {})
            
            if assets:
                if sys.platform == "win32":
                    download_url = assets.get("windows", data.get("url", ""))
                elif sys.platform == "darwin":
                    download_url = assets.get("macos", assets.get("darwin", ""))
                else: # Linux
                    download_url = assets.get("linux", "")
            else:
                # Fallback ancien format (probablement Windows exe)
                download_url = data.get("url", "")
                if sys.platform != "win32" and download_url.endswith(".exe"):
                    self.full_logs.append("[UPDATE] URL détectée pour Windows (.exe), ignorée sur cet OS.")
                    download_url = ""

            # Comparaison très basique de chaînes (suffisant pour x.x)
            if remote_version > CURRENT_VERSION and download_url:
                self.full_logs.append(f"[UPDATE] Nouvelle version détectée : {remote_version}")
                msg = f"Une nouvelle version ({remote_version}) est disponible !\nVoulez-vous l'installer maintenant ?"
                
                # On demande à l'utilisateur via le thread principal
                self.after(0, lambda: self.ask_update(msg, download_url))
            else:
                self.full_logs.append("[UPDATE] Logiciel à jour.")
                
        except Exception as e:
            self.full_logs.append(f"[UPDATE] Erreur vérification màj : {e}")
            print(f"Update check failed: {e}")

    def ask_update(self, msg, url):
        if tkinter.messagebox.askyesno("Mise à jour disponible", msg):
            threading.Thread(target=self.perform_update, args=(url,), daemon=True).start()

    def perform_update(self, url):
        try:
            self.log_status("Téléchargement de la mise à jour...")
            self.full_logs.append("[UPDATE] Téléchargement de la nouvelle version...")
            
            # Détection du type de fichier via l'URL
            is_zip = url.lower().endswith(".zip")
            is_tar = url.lower().endswith(".tar.gz") or url.lower().endswith(".tgz")
            
            # Nom temporaire pour le téléchargement
            if is_zip:
                download_target = os.path.join(self.app_data, "update_tmp.zip")
            elif is_tar:
                download_target = os.path.join(self.app_data, "update_tmp.tar.gz")
            else:
                # Direct binary
                ext = os.path.splitext(sys.executable)[1]
                download_target = os.path.join(self.app_data, f"update_tmp{ext}")

            current_exe = sys.executable

            # Télécharger la mise à jour avec vérification basique
            try:
                self.full_logs.append(f"[UPDATE] Téléchargement de : {url}")
                # Utiliser un User-Agent pour éviter certains rejets
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                # Ouvrir la connexion pour vérifier la taille
                with urllib.request.urlopen(req) as response:
                    file_size = int(response.getheader('Content-Length', 0))
                    self.full_logs.append(f"[UPDATE] Taille du fichier à télécharger : {file_size} octets")
                    
                    # Télécharger par blocs pour éviter les timeouts
                    with open(download_target, 'wb') as f:
                        downloaded = 0
                        block_size = 8192
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            downloaded += len(buffer)
                            f.write(buffer)
                            
                        # Force l'écriture sur le disque
                        f.flush()
                        os.fsync(f.fileno())

                    self.full_logs.append(f"[UPDATE] Téléchargement terminé : {downloaded} octets reçus")
                    
                    if file_size > 0 and downloaded < file_size:
                        raise Exception(f"Téléchargement incomplet ({downloaded}/{file_size} octets)")

            except Exception as dl_error:
                raise Exception(f"Erreur lors du téléchargement: {dl_error}")

            # Extraction si nécessaire
            new_exe_name = download_target # Par défaut, c'est ce qu'on a téléchargé
            
            if is_zip or is_tar:
                self.full_logs.append("[UPDATE] Extraction de l'archive...")
                extract_dir = os.path.join(self.app_data, "update_extracted")
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
                os.makedirs(extract_dir)
                
                try:
                    if is_zip:
                        with zipfile.ZipFile(download_target, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                    elif is_tar:
                        with tarfile.open(download_target, 'r:gz') as tar_ref:
                            tar_ref.extractall(extract_dir)
                            
                    # Recherche de l'exécutable dans le dossier extrait
                    found_exe = None
                    current_name_base = os.path.splitext(os.path.basename(sys.executable))[0]
                    
                    # Stratégie 1: Chercher un fichier contenant le nom actuel
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if current_name_base.lower() in file.lower() or "youtubedownloader" in file.lower():
                                full_path = os.path.join(root, file)
                                # Ignorer les fichiers manifest ou autres petits fichiers
                                if os.path.getsize(full_path) > 1024 * 1024: # > 1MB
                                    found_exe = full_path
                                    break
                        if found_exe: break
                    
                    # Stratégie 2: Le plus gros fichier
                    if not found_exe:
                        all_files = []
                        for root, dirs, files in os.walk(extract_dir):
                            for file in files:
                                all_files.append(os.path.join(root, file))
                        if all_files:
                            all_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
                            if os.path.getsize(all_files[0]) > 1024 * 1024:
                                found_exe = all_files[0]

                    if not found_exe:
                         raise Exception("Aucun exécutable valide trouvé dans l'archive")
                         
                    new_exe_name = found_exe
                    self.full_logs.append(f"[UPDATE] Exécutable extrait : {new_exe_name}")
                    
                    # Permission exécution sur Linux/Mac
                    if sys.platform != "win32":
                         import stat
                         st = os.stat(new_exe_name)
                         os.chmod(new_exe_name, st.st_mode | stat.S_IEXEC)

                except Exception as extract_error:
                    raise Exception(f"Erreur extraction: {extract_error}")
            
            else:
                 # Vérification binaire simple
                 if downloaded < 1000000: # Moins de 1 Mo est suspect
                        with open(download_target, 'rb') as f:
                            header = f.read(4)
                            # Vérification Magic Number
                            if header.startswith(b'MZ') or header.startswith(b'\x7fELF'):
                                pass 
                            elif b'<!DOCTYPE html>' in header or b'<html' in header:
                                raise Exception("Le fichier téléchargé semble être une page Web (Erreur 404/403 ?)")
                            else:
                                self.full_logs.append("[UPDATE] Attention: Fichier petit mais semble être binaire")
            
            self.full_logs.append("[UPDATE] Téléchargement terminé. Préparation du redémarrage...")
            self.log_status("Mise à jour prête. Redémarrage...")
            
            # Utilisation du WRAPPER updater embarqué
            if getattr(sys, 'frozen', False):
                # On est dans l'exe PyInstaller
                base_path = sys._MEIPASS
                
                # Nom de l'updater selon l'OS
                updater_name = "updater.exe" if sys.platform == "win32" else "updater"
                updater_src = os.path.join(base_path, updater_name)
                
                # On extrait l'updater dans un dossier temporaire (pas à côté de l'exe pour éviter les locks)
                import tempfile
                tmp_dir = tempfile.gettempdir()
                updater_dest = os.path.join(tmp_dir, f"updater_v25_{int(time.time())}" + (".exe" if sys.platform == "win32" else ""))
                
                try:
                    # Vérifier si l'updater existe (si compilé avec)
                    if not os.path.exists(updater_src):
                        raise Exception(f"Updater introuvable dans le paquet ({updater_name})")
                        
                    shutil.copy2(updater_src, updater_dest)
                    
                    # Permission exécution sur Linux/Mac
                    if sys.platform != "win32":
                         import stat
                         st = os.stat(updater_dest)
                         os.chmod(updater_dest, st.st_mode | stat.S_IEXEC)
                         
                except Exception as e:
                    print(f"Erreur extraction updater: {e}")
                    raise e

                # Arguments pour l'updater : PID, NewFile, TargetFile
                pid = os.getpid()
                
                # Lancement de l'updater détaché
                if sys.platform == "win32":
                    subprocess.Popen([updater_dest, str(pid), new_exe_name, current_exe], close_fds=True)
                else:
                    # Sur Linux/Mac, start_new_session=True détache le processus
                    subprocess.Popen([updater_dest, str(pid), new_exe_name, current_exe], start_new_session=True)
                
                # Fermeture immédiate de l'application principale
                self.quit()
                sys.exit(0)
            
            else:
                # Mode DEV (pas de frozen)
                print("Mode DEV: Pas de redémarrage automatique via wrapper.")
                tkinter.messagebox.showinfo("Dev", "Mise à jour téléchargée. Redémarrez manuellement.")
            
        except Exception as e:
            self.full_logs.append(f"[UPDATE] Echec mise à jour : {e!r}")
            self.after(0, lambda: tkinter.messagebox.showerror("Erreur Mise à jour", f"Echec : {e!r}"))

    def install_deno_thread(self):
        try:
            print("Vérification moteur JS (Deno)...")
            bin_dir = os.path.join(self.app_data, "bin")
            if not os.path.exists(bin_dir):
                os.makedirs(bin_dir)
            
            deno_filename = "deno.exe" if sys.platform == "win32" else "deno"
            deno_exe = os.path.join(bin_dir, deno_filename)
            if os.path.exists(deno_exe):
                return

            self.full_logs.append("[INFO] Téléchargement du moteur JS (Deno)...")
            
            # Choix de l'URL selon l'OS
            base_url = "https://github.com/denoland/deno/releases/latest/download/"
            zip_name = "deno.zip"
            
            if sys.platform == "win32":
                url = base_url + "deno-x86_64-pc-windows-msvc.zip"
            elif sys.platform == "darwin":
                import platform
                if platform.machine() == "arm64":
                    url = base_url + "deno-aarch64-apple-darwin.zip"
                else:
                    url = base_url + "deno-x86_64-apple-darwin.zip"
            else:
                url = base_url + "deno-x86_64-unknown-linux-gnu.zip"

            zip_path = os.path.join(self.app_data, zip_name)
            
            self.full_logs.append(f"[INFO] URL Deno: {url}")
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(deno_filename):
                        with zip_ref.open(file) as source, open(deno_exe, "wb") as target:
                            shutil.copyfileobj(source, target)
            
            # Permission exécutable pour Linux/Mac
            if sys.platform != "win32":
                try:
                    import stat
                    st = os.stat(deno_exe)
                    os.chmod(deno_exe, st.st_mode | stat.S_IEXEC)
                except:
                    pass

            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            print("Deno installé !")
            self.full_logs.append("[INFO] Deno installé avec succès !")
            
            # Ajout au PATH dynamique
            if bin_dir not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + bin_dir

        except Exception as e:
            print(f"Erreur installation Deno: {e}")
            self.full_logs.append(f"[ERROR] Echec installation Deno: {e}")

    def load_settings(self):
        self.settings_file = os.path.join(self.app_data, "settings.json")
        self.settings = {"appearance_mode": "Dark"}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                print(f"Erreur chargement settings: {e}")
        
        ctk.set_appearance_mode(self.settings["appearance_mode"])

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Erreur sauvegarde settings: {e}")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        self.settings["appearance_mode"] = new_appearance_mode
        self.save_settings()

    def setup_download_tab(self):
        self.tab_download.grid_columnconfigure(0, weight=1)
        self.tab_download.grid_rowconfigure(5, weight=1) # Push logs to bottom

        # --- CONTENEUR PRINCIPAL (Centré) ---
        self.main_container = ctk.CTkFrame(self.tab_download, fg_color="transparent")
        self.main_container.grid(row=0, column=0, padx=40, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)

        # 1. URL INPUT (Style "Hero")
        self.lbl_url = ctk.CTkLabel(self.main_container, text="Lien de la vidéo / playlist", font=ctk.CTkFont(size=14, weight="bold"), text_color=("gray20", "#aaaaaa"))
        self.lbl_url.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.frame_url_input = ctk.CTkFrame(self.main_container, fg_color=("#EBEBEB", "#2b2b2b"), corner_radius=10, border_width=1, border_color=("#D0D0D0", "#3a3a3a"))
        self.frame_url_input.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        self.frame_url_input.grid_columnconfigure(0, weight=1)

        self.entry_url = ctk.CTkEntry(self.frame_url_input, placeholder_text="https://www.youtube.com/watch?v=...", 
                                      height=50, border_width=0, fg_color="transparent", font=ctk.CTkFont(size=15), text_color=("gray10", "white"))
        self.entry_url.grid(row=0, column=0, padx=15, sticky="ew")

        self.btn_paste = ctk.CTkButton(self.frame_url_input, text="COLLER", width=80, height=36, 
                                       fg_color=("#C0C0C0", "#444444"), hover_color=("#A0A0A0", "#555555"), text_color=("black", "white"), corner_radius=8, command=self.paste_url)
        self.btn_paste.grid(row=0, column=1, padx=10, pady=7)

        # 2. PARAMÈTRES (Grille 2 colonnes)
        self.frame_settings = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frame_settings.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.frame_settings.grid_columnconfigure((0, 1), weight=1)

        # Colonne Gauche : Format & Qualité
        self.frame_left = ctk.CTkFrame(self.frame_settings, fg_color=("#EBEBEB", "#232323"), corner_radius=10)
        self.frame_left.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.frame_left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_left, text="Format & Qualité", font=ctk.CTkFont(size=13, weight="bold"), text_color=("gray20", "gray")).pack(padx=15, pady=(15, 10), anchor="w")
        
        self.type_var = ctk.StringVar(value="video")
        self.seg_type = ctk.CTkSegmentedButton(self.frame_left, values=["Vidéo", "Audio"], variable=self.type_var, command=self.update_resolutions_seg)
        self.seg_type.pack(padx=15, pady=(0, 15), fill="x")
        self.seg_type.set("Vidéo")

        self.res_var = ctk.StringVar(value="Best (H.264)")
        self.option_res = ctk.CTkOptionMenu(self.frame_left, variable=self.res_var, values=["Best (H.264)", "1080p", "720p", "480p", "4K (VP9)"],
                                            fg_color=("#DBDBDB", "#333333"), button_color=("#DBDBDB", "#333333"), text_color=("gray10", "gray90"))
        self.option_res.pack(padx=15, pady=(0, 20), fill="x")

        # Colonne Droite : Options & Dossier
        self.frame_right = ctk.CTkFrame(self.frame_settings, fg_color=("#EBEBEB", "#232323"), corner_radius=10)
        self.frame_right.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.frame_right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_right, text="Options & Destination", font=ctk.CTkFont(size=13, weight="bold"), text_color=("gray20", "gray")).pack(padx=15, pady=(15, 10), anchor="w")

        # Playlist Switch
        self.playlist_var = ctk.BooleanVar(value=False)
        self.check_playlist = ctk.CTkSwitch(self.frame_right, text="Télécharger la playlist", variable=self.playlist_var)
        self.check_playlist.pack(padx=15, pady=(5, 10), anchor="w")

        # Dossier Bouton (Full Width)
        self.btn_folder = ctk.CTkButton(self.frame_right, text="📂 Choisir le dossier", fg_color=("#DBDBDB", "#333333"), hover_color=("#C9C9C9", "#404040"), 
                                        text_color=("gray10", "white"), anchor="w", command=self.choose_folder)
        self.btn_folder.pack(padx=15, pady=(5, 5), fill="x")
        
        self.label_folder = ctk.CTkLabel(self.frame_right, text=self.truncate_path(self.download_folder), text_color=("gray40", "gray"), font=ctk.CTkFont(size=11))
        self.label_folder.pack(padx=15, pady=(0, 15), anchor="w")

        # Thème
        self.lbl_theme = ctk.CTkLabel(self.frame_right, text="Thème :", font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray20", "gray"))
        self.lbl_theme.pack(padx=15, pady=(0, 0), anchor="w")

        self.option_theme = ctk.CTkOptionMenu(self.frame_right, values=["System", "Dark", "Light"],
                                              command=self.change_appearance_mode_event,
                                              fg_color=("#DBDBDB", "#333333"), button_color=("#DBDBDB", "#333333"), text_color=("gray10", "gray90"))
        self.option_theme.pack(padx=15, pady=(0, 15), fill="x")
        self.option_theme.set(self.settings.get("appearance_mode", "Dark"))

        # 3. ACTION (Bouton Géant)
        self.btn_download = ctk.CTkButton(self.main_container, text="LANCER LE TÉLÉCHARGEMENT", height=60, 
                                          font=ctk.CTkFont(size=18, weight="bold"), 
                                          fg_color="#00A36C", hover_color="#008558", # Jade Green
                                          corner_radius=15, command=self.start_download_thread)
        self.btn_download.grid(row=3, column=0, sticky="ew", pady=(20, 10))

        # Status & Progress (Juste en dessous)
        self.progress_bar = ctk.CTkProgressBar(self.main_container, height=10, progress_color="#00A36C")
        self.progress_bar.grid(row=4, column=0, sticky="ew", padx=5)
        self.progress_bar.set(0)

        self.label_status = ctk.CTkLabel(self.main_container, text="Prêt", text_color="gray", font=ctk.CTkFont(size=12))
        self.label_status.grid(row=5, column=0, pady=5)

        # Cookies (Discret, en bas à droite)
        self.cookies_var = ctk.StringVar(value="Sans Cookies")
        self.option_cookies = ctk.CTkOptionMenu(self.tab_download, variable=self.cookies_var, 
                                                values=["Sans Cookies", "Chrome", "Firefox", "Edge", "Opera", "Brave"], 
                                                width=100, height=24, font=ctk.CTkFont(size=11),
                                                fg_color=("#DBDBDB", "#333333"), button_color=("#DBDBDB", "#333333"), text_color=("gray10", "gray"))
        self.option_cookies.place(relx=0.95, rely=0.98, anchor="se")

        # Logs (Discret, en bas à gauche)
        self.btn_view_logs = ctk.CTkButton(self.tab_download, text="Logs", width=60, height=24, 
                                           fg_color="transparent", border_width=1, border_color=("#aaaaaa", "#444444"), text_color=("gray20", "gray"), 
                                           font=ctk.CTkFont(size=11), command=self.open_log_window)
        self.btn_view_logs.place(relx=0.05, rely=0.98, anchor="sw")

    def paste_url(self):
        try:
            text = self.clipboard_get()
            self.entry_url.delete(0, 'end')
            self.entry_url.insert(0, text)
        except:
            pass

    def truncate_path(self, path, length=50):
        if len(path) > length:
            return "..." + path[-(length-3):]
        return path

    def choose_folder(self):
        folder = tkinter.filedialog.askdirectory()
        if folder:
            self.download_folder = folder
            self.label_folder.configure(text=self.truncate_path(self.download_folder))

    def update_resolutions_seg(self, value):
        # Callback pour le SegmentedButton
        if value == "Audio":
            self.option_res.configure(state="disabled")
            self.type_var.set("audio") # Compatibilité avec le reste du code
        else:
            self.option_res.configure(state="normal")
            self.type_var.set("video")

    def update_resolutions(self):
        # Ancienne méthode gardée au cas où, mais remplacée par update_resolutions_seg
        pass


    def start_download_thread(self):
        url = self.entry_url.get()
        if not url:
            self.label_status.configure(text="Erreur : Veuillez entrer une URL", text_color="red")
            return
        
        self.btn_download.configure(state="disabled")
        self.label_status.configure(text="Analyse en cours...", text_color="white")
        self.progress_bar.set(0)
        
        threading.Thread(target=self.download_task, args=(url,), daemon=True).start()

    def log_status(self, msg):
        self.after(0, lambda: self.label_status.configure(text=str(msg)[:60] + "..."))

    def open_log_window(self):
        log_window = ctk.CTkToplevel(self)
        log_window.title("Logs Détaillés")
        log_window.geometry("800x600")
        
        textbox = ctk.CTkTextbox(log_window, width=780, height=580)
        textbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Insérer les logs
        text_content = "\n".join(self.full_logs)
        textbox.insert("1.0", text_content)
        textbox.configure(state="disabled") # Lecture seule

        # Bouton Sauvegarder
        btn_save = ctk.CTkButton(log_window, text="Sauvegarder les logs", command=self.save_logs_to_file)
        btn_save.pack(pady=10)

    def save_logs_to_file(self):
        try:
            # On propose par défaut le dossier "Documents" ou "Téléchargements" pour éviter les erreurs de permission
            default_dir = os.path.expanduser("~/Documents")
            file_path = tkinter.filedialog.asksaveasfilename(
                initialdir=default_dir,
                defaultextension=".txt",
                filetypes=[("Fichier Texte", "*.txt")],
                title="Sauvegarder les logs"
            )
            
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    for line in self.full_logs:
                        f.write(line + "\n")
                tkinter.messagebox.showinfo("Succès", f"Logs sauvegardés dans :\n{file_path}")
        except Exception as e:
            tkinter.messagebox.showerror("Erreur", f"Impossible de sauvegarder les logs : {e}")

    def download_task(self, url):
        try:
            self.full_logs.clear() # Reset logs
            download_type = self.type_var.get()
            resolution = self.res_var.get()
            
            ydl_opts = {
                'logger': MyLogger(self.log_status, self.full_logs),
                'verbose': True, # IMPORTANT pour le debug
                'progress_hooks': [self.progress_hook],
                'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'ignoreerrors': False, 
                'socket_timeout': 15,
                'noplaylist': not self.playlist_var.get(), # Gestion Playlist
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                # IMPORTANT : On active le téléchargement des scripts de résolution de challenge (EJS)
                # Cela permet à Deno de résoudre le "n challenge"
                'remote_components': ['ejs:github'],
            }

            # Gestion des cookies (contournement limite d'âge)
            browser = self.cookies_var.get()
            if browser != "Sans Cookies":
                # On passe le nom du navigateur en minuscule (chrome, firefox, etc.)
                ydl_opts['cookiesfrombrowser'] = (browser.lower(),)

            if self.ffmpeg_path:
                if os.path.isfile(self.ffmpeg_path):
                    ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
                else:
                    ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            if download_type == "audio":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                # Force MP4 container
                ydl_opts['merge_output_format'] = 'mp4'
                
                # Format selection logic for Premiere Pro compatibility (H.264)
                # vcodec^=avc1 selects H.264 video streams.
                # vcodec^=vp9 selects VP9 video streams.
                
                if resolution == "4K (VP9)":
                    # Allow VP9 for max quality
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                else:
                    # OPTIMISATION MAJEURE : On essaie de récupérer directement du H.264 si dispo
                    # pour éviter le ré-encodage très lent.
                    # vcodec^=avc1 = H.264
                    # vcodec^=vp9 = VP9 (incompatible Premiere parfois)
                    
                    # On utilise ultrafast pour la conversion si nécessaire (beaucoup plus rapide)
                    h264_convert_args = ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-c:a', 'aac']
                    
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                    
                    # On ne force la conversion que si nécessaire via postprocessor_args
                    # Mais on va tenter de télécharger le bon format d'abord
                    
                    if resolution == "Best (H.264)":
                        # Essaie H.264 en priorité, sinon VP9 et convertit
                        ydl_opts['format'] = 'bestvideo[vcodec^=avc1]+bestaudio/bestvideo+bestaudio/best'
                        # Si on tombe sur du VP9, on veut convertir vite
                        ydl_opts['postprocessor_args'] = {'videoconvertor': h264_convert_args}
                        
                    elif resolution == "1080p":
                         ydl_opts['format'] = 'bestvideo[height<=1080][vcodec^=avc1]+bestaudio/bestvideo[height<=1080]+bestaudio/best[height<=1080]'
                         ydl_opts['postprocessor_args'] = {'videoconvertor': h264_convert_args}
                         
                    elif resolution == "720p":
                         ydl_opts['format'] = 'bestvideo[height<=720][vcodec^=avc1]+bestaudio/bestvideo[height<=720]+bestaudio/best[height<=720]'
                         ydl_opts['postprocessor_args'] = {'videoconvertor': h264_convert_args}
                         
                    elif resolution == "480p":
                         ydl_opts['format'] = 'bestvideo[height<=480][vcodec^=avc1]+bestaudio/bestvideo[height<=480]+bestaudio/best[height<=480]'
                         ydl_opts['postprocessor_args'] = {'videoconvertor': h264_convert_args}

                # Fallback si FFmpeg manquant
                if not self.ffmpeg_path:
                    print("FFmpeg manquant : fallback sur 'best' (fichier unique)")
                    ydl_opts['format'] = 'best'
                    if 'merge_output_format' in ydl_opts:
                        del ydl_opts['merge_output_format']
                    if 'postprocessor_args' in ydl_opts:
                        del ydl_opts['postprocessor_args']

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, lambda: self.finish_download("Téléchargement terminé avec succès !"))
            
        except Exception as e:
            # RETRY LOGIC (SAFE MODE)
            # Si le mode normal échoue (ex: format non disponible), on tente le mode "Bourrin"
            # On utilise le client 'android' qui contourne souvent les blocages et on prend 'best'
            print(f"Erreur Standard: {e}")
            if "Requested format is not available" in str(e) or "HTTP Error" in str(e):
                self.after(0, lambda: self.label_status.configure(text="Mode Standard échoué. Tentative Mode Compatibilité..."))
                
                try:
                    self.full_logs.append("[INFO] PASSAGE EN MODE COMPATIBILITÉ (SAFE MODE)")
                    
                    safe_opts = {
                        'logger': MyLogger(self.log_status, self.full_logs),
                        'verbose': True,
                        'progress_hooks': [self.progress_hook],
                        'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'nocheckcertificate': True,
                        'ignoreerrors': False,
                        'socket_timeout': 30, # Plus long
                        'format': 'best',     # Le plus simple possible
                        'noplaylist': not self.playlist_var.get(), # Gestion Playlist
                        # Avec Deno installé, on peut utiliser le client par défaut
                        # qui gère mieux les cookies que Android/iOS
                        'remote_components': ['ejs:github'],
                    }
                    
                    self.full_logs.append("[INFO] Mode Robuste activé (Deno Engine)")
                    
                    # On s'assure que les cookies sont bien utilisés pour Android
                    browser = self.cookies_var.get()
                    if browser != "Sans Cookies":
                        safe_opts['cookiesfrombrowser'] = (browser.lower(),)
                    
                    if self.ffmpeg_path:
                        if os.path.isfile(self.ffmpeg_path):
                            safe_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
                        else:
                            safe_opts['ffmpeg_location'] = self.ffmpeg_path

                        # On essaie quand même de convertir en MP4 à la fin si c'est de la vidéo
                        if self.type_var.get() != "audio":
                             safe_opts['postprocessors'] = [{
                                'key': 'FFmpegVideoConvertor',
                                'preferedformat': 'mp4',
                            }]

                    with yt_dlp.YoutubeDL(safe_opts) as ydl:
                        ydl.download([url])
                        
                    self.after(0, lambda: self.finish_download("Téléchargement terminé (Mode Compatibilité) !"))
                    return

                except Exception as e2:
                    print(f"Erreur Safe Mode: {e2}")
                    self.after(0, lambda: self.finish_download(f"Echec Total : {str(e2)}", error=True))
                    return

            self.after(0, lambda: self.finish_download(f"Erreur : {str(e)}", error=True))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '')
            try:
                val = float(p) / 100
                self.after(0, lambda: self.progress_bar.set(val))
                self.after(0, lambda: self.label_status.configure(text=f"Téléchargement : {d.get('_percent_str')}"))
            except:
                pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.label_status.configure(text="Traitement / Conversion..."))

    def finish_download(self, message, error=False):
        color = "red" if error else "green"
        self.label_status.configure(text=message, text_color=color)
        self.btn_download.configure(state="normal")
        if not error:
            self.progress_bar.set(1)

    # ------------------------------------------------------------------
    # GESTION DE LA RECHERCHE
    # ------------------------------------------------------------------
    def setup_search_tab(self):
        self.tab_search.grid_columnconfigure(0, weight=1)
        self.tab_search.grid_rowconfigure(1, weight=1)

        # Zone de recherche
        self.frame_search_input = ctk.CTkFrame(self.tab_search, fg_color="transparent")
        self.frame_search_input.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.frame_search_input.grid_columnconfigure(0, weight=1)

        self.entry_search = ctk.CTkEntry(self.frame_search_input, placeholder_text="Rechercher sur YouTube...", height=40)
        self.entry_search.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.entry_search.bind("<Return>", lambda event: self.start_search_thread())

        self.btn_search = ctk.CTkButton(self.frame_search_input, text="Rechercher", width=100, height=40, command=self.start_search_thread)
        self.btn_search.grid(row=0, column=1, padx=0, pady=0)

        # Zone de résultats (Scrollable)
        self.scroll_results = ctk.CTkScrollableFrame(self.tab_search, label_text="Résultats", fg_color="transparent")
        self.scroll_results.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.scroll_results.grid_columnconfigure(0, weight=1)

    def start_search_thread(self):
        query = self.entry_search.get()
        if not query:
            return
        
        # Nettoyer les résultats précédents
        for widget in self.scroll_results.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(self.scroll_results, text="Recherche en cours...")
        loading_label.pack(pady=20)

        threading.Thread(target=self.search_task, args=(query, loading_label), daemon=True).start()

    def search_task(self, query, loading_label):
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True, # Remis à True pour la vitesse et fiabilité
                'default_search': 'ytsearch15', 
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'socket_timeout': 10,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch15:{query}", download=False)

            self.after(0, lambda: self.display_results(info['entries'], loading_label))

        except Exception as e:
            print(f"Erreur recherche: {e}")
            self.after(0, lambda: loading_label.configure(text=f"Erreur : {e}"))

    def display_results(self, entries, loading_label):
        loading_label.destroy()
        
        if not entries:
            ctk.CTkLabel(self.scroll_results, text="Aucun résultat trouvé.").pack(pady=20)
            return

        for entry in entries:
            if entry: 
                self.create_result_item(entry)

    def create_result_item(self, entry):
        # Frame pour un résultat (Style Carte plus propre)
        item_frame = ctk.CTkFrame(self.scroll_results, fg_color="#232323", corner_radius=12, border_width=1, border_color="#333333")
        item_frame.pack(fill="x", padx=10, pady=8)
        item_frame.grid_columnconfigure(1, weight=1)

        # Extraction des données
        title = entry.get('title', 'Titre inconnu')
        
        # Formatage durée (secondes -> MM:SS)
        duration_sec = entry.get('duration')
        if duration_sec:
            m, s = divmod(duration_sec, 60)
            h, m = divmod(m, 60)
            if h > 0:
                duration = f"{int(h)}:{int(m):02d}:{int(s):02d}"
            else:
                duration = f"{int(m):02d}:{int(s):02d}"
        else:
            duration = "??"

        url = entry.get('webpage_url', entry.get('url', ''))
        channel = entry.get('uploader', 'Chaîne inconnue')
        thumbnail_url = entry.get('thumbnail', '')
        
        # Si thumbnail est une liste
        if isinstance(thumbnail_url, list):
             try:
                 thumbnail_url = thumbnail_url[-1].get('url') if isinstance(thumbnail_url[-1], dict) else thumbnail_url[-1]
             except:
                 thumbnail_url = ''
        elif isinstance(thumbnail_url, dict):
             thumbnail_url = thumbnail_url.get('url', '')
        
        # Fallback: Construction manuelle URL miniature via ID si absente
        if not thumbnail_url and entry.get('id'):
            # mqdefault (320x180) respecte le ratio 16:9 mieux que hqdefault (480x360 - 4:3)
            thumbnail_url = f"https://i.ytimg.com/vi/{entry.get('id')}/mqdefault.jpg"

        # 1. Miniature (Plus grande et placeholder)
        lbl_thumb = ctk.CTkLabel(item_frame, text="", width=192, height=108, fg_color="#111111", corner_radius=8)
        lbl_thumb.grid(row=0, column=0, rowspan=2, padx=12, pady=12)
        
        # On lance le chargement si URL existe
        if thumbnail_url and isinstance(thumbnail_url, str) and thumbnail_url.startswith('http'):
             threading.Thread(target=self.load_thumbnail, args=(thumbnail_url, lbl_thumb), daemon=True).start()
        else:
             lbl_thumb.configure(text="No Image")

        # 2. Informations (Meilleur espacement)
        frame_info = ctk.CTkFrame(item_frame, fg_color="transparent")
        frame_info.grid(row=0, column=1, rowspan=2, padx=5, pady=10, sticky="nsew")
        frame_info.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(frame_info, text=title, anchor="w", justify="left", wraplength=400, font=ctk.CTkFont(size=16, weight="bold"))
        lbl_title.pack(fill="x", pady=(5, 5))
        
        lbl_details = ctk.CTkLabel(frame_info, text=f"👤 {channel}   •   ⏱️ {duration}", anchor="w", justify="left", text_color="#aaaaaa", font=ctk.CTkFont(size=13))
        lbl_details.pack(fill="x", pady=(0, 5))

        # 3. Boutons (Alignés et colorés)
        frame_actions = ctk.CTkFrame(item_frame, fg_color="transparent")
        frame_actions.grid(row=0, column=2, rowspan=2, padx=15, pady=10)

        btn_select = ctk.CTkButton(frame_actions, text="Télécharger", width=110, height=35, 
                                   fg_color="#00A36C", hover_color="#008558", font=ctk.CTkFont(weight="bold"),
                                   command=lambda u=url: self.select_video(u))
        btn_select.pack(side="top", pady=5)

        btn_preview = ctk.CTkButton(frame_actions, text="Voir / Écouter", width=110, height=30, 
                                    fg_color="#444444", hover_color="#555555", 
                                    command=lambda u=url: self.open_preview(u))
        btn_preview.pack(side="bottom", pady=5)

    def load_thumbnail(self, url, label):
        try:
            # Vérification simple de l'URL
            if not url or not url.startswith('http'):
                return

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as u:
                raw_data = u.read()
            
            image = Image.open(io.BytesIO(raw_data))
            # Ratio 16:9 - Taille augmentée pour meilleure qualité
            image = image.resize((192, 108), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(192, 108))
            
            def update():
                if label.winfo_exists():
                    label.configure(image=photo, text="")
            self.after(0, update)
        except Exception as e:
            # En cas d'erreur, on laisse le placeholder ou on met une icône d'erreur
            print(f"Erreur chargement miniature ({url}): {e}")
            pass

    def open_preview(self, url):
        # Lancement du lecteur intégré (FFplay)
        threading.Thread(target=self.launch_ffplay_preview, args=(url,), daemon=True).start()

    def launch_ffplay_preview(self, url):
        try:
            # 1. Récupérer l'URL directe du flux (rapide, basse qualité pour preview)
            ydl_opts = {'format': 'best[height<=480]', 'quiet': True}
            
            # Gestion des cookies pour la preview aussi
            if hasattr(self, 'cookies_var'):
                browser = self.cookies_var.get()
                if browser != "Sans Cookies":
                    ydl_opts['cookiesfrombrowser'] = (browser.lower(),)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info['url']
                title = info.get('title', 'Preview')

            # 2. Chercher ffplay
            ffplay_exe = "ffplay"
            if os.path.exists("ffplay.exe"):
                ffplay_exe = os.path.abspath("ffplay.exe")
            elif shutil.which("ffplay"):
                ffplay_exe = "ffplay"
            else:
                self.after(0, lambda: tkinter.messagebox.showerror("Erreur", "FFplay n'est pas installé. Veuillez attendre l'installation automatique ou installer FFmpeg."))
                return

            # 3. Lancer FFplay sans console
            cmd = [ffplay_exe, '-window_title', f"Preview - {title}", '-autoexit', '-x', '800', '-y', '450', stream_url]
            
            # Suppression de la fenêtre console sur Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.Popen(cmd, startupinfo=startupinfo)

        except Exception as e:
            print(f"Erreur preview: {e}")
            self.after(0, lambda: tkinter.messagebox.showerror("Erreur", f"Impossible de lancer la preview : {e}"))

    def select_video(self, url):
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, url)
        self.tabview.set("Téléchargement Direct")

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
