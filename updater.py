import os
import sys
import time
import shutil
import subprocess
import tempfile

def log(msg):
    """Log simple pour debug si besoin"""
    try:
        log_file = os.path.join(tempfile.gettempdir(), "updater_log.txt")
        with open(log_file, "a") as f:
            f.write(f"{msg}\n")
    except:
        pass

def main():
    # Arguments attendus:
    # 1: PID du processus principal (à attendre)
    # 2: Chemin du nouveau fichier (téléchargé)
    # 3: Chemin de l'exécutable cible (l'app principale à remplacer)
    
    if len(sys.argv) < 4:
        log("Erreur: Arguments manquants")
        sys.exit(1)

    pid = int(sys.argv[1])
    new_file = sys.argv[2]
    target_file = sys.argv[3]

    log(f"Démarrage updater. PID={pid}, New={new_file}, Target={target_file}")

    # 1. Attendre la fermeture de l'application principale
    log("Attente fermeture processus...")
    max_wait = 10 # secondes
    start_time = time.time()
    
    while True:
        try:
            # os.kill(pid, 0) vérifie si le processus existe (Unix et Windows)
            os.kill(pid, 0)
            # Si pas d'exception, le processus existe encore
            time.sleep(0.5)
            if time.time() - start_time > max_wait:
                log("Timeout attente fermeture.")
                # Tentative de forçage kill
                try:
                    import signal
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass
                break
        except OSError:
            # Processus n'existe plus
            log("Processus fermé.")
            break

    # Petite pause de sécurité pour libérer les verrous fichiers
    time.sleep(2)

    # 2. Remplacer le fichier
    log("Remplacement du fichier...")
    retries = 5
    success = False
    
    for i in range(retries):
        try:
            if os.path.exists(target_file):
                if os.path.isdir(target_file):
                    shutil.rmtree(target_file)
                else:
                    os.remove(target_file)
            shutil.move(new_file, target_file)
            
            # Rendre exécutable sur Linux/Mac
            if os.name != 'nt':
                try:
                    import stat
                    st = os.stat(target_file)
                    os.chmod(target_file, st.st_mode | stat.S_IEXEC)
                except Exception as e:
                    log(f"Erreur chmod: {e}")

            success = True
            log("Remplacement réussi.")
            break
        except Exception as e:
            log(f"Erreur remplacement ({i+1}/{retries}): {e}")
            time.sleep(1)

    if not success:
        log("Echec critique du remplacement.")
        sys.exit(1)

    # 3. Relancer l'application
    log("Redémarrage application...")
    try:
        if os.name == 'nt':
            subprocess.Popen([target_file])
        else:
            # Sur Linux/Mac, utiliser nohup ou double-fork idéalement, mais Popen suffit souvent
            subprocess.Popen([target_file], start_new_session=True)
            
    except Exception as e:
        log(f"Erreur redémarrage: {e}")

if __name__ == "__main__":
    main()
