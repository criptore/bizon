import logging
import sys
import os

# Compatibilité Python 3.13+ (audioop removal)
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
        sys.modules["pyaudioop"] = audioop
    except ImportError:
        pass

# Configuration du logging sécurisée
log_file = "bizon.log"
log_stream = open(log_file, "a", encoding="utf-8")

# Redirection totale pour éviter Errno 5 (Input/Output error) 
# quand le terminal qui a lancé le script se ferme.
sys.stdout = log_stream
sys.stderr = log_stream

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(log_stream)
    ]
)
logger = logging.getLogger("BizonMain")

def launch_terminal_process():
    """
    Démarre le dashboard dans un processus complètement séparé.
    Indispensable sur macOS : Tkinter et pywebview utilisent tous deux NSApp.
    Les lancer dans le même processus provoque un crash (segfault).
    """
    import subprocess
    import os
    project_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info("Démarrage du Terminal de Trading (processus isolé)...")
    subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from src.ui.dashboard import launch_dashboard; "
         "launch_dashboard(standalone=True)"],
        cwd=project_dir
    )

def main():
    """Lancement de l'application Bizon Desktop."""
    try:
        from src.ui.launcher_ui import LauncherUI
        
        # Callback pour passer de l'analyse au terminal
        def on_launch():
            logger.info("Signal de lancement du terminal reçu.")
            # On lance le dashboard dans un nouveau thread pour ne pas bloquer Tkinter 
            # (ou on ferme Tkinter)
            ui.close()
            launch_terminal_process()

        logger.info("Démarrage de l'interface de contrôle...")
        ui = LauncherUI(on_launch_callback=on_launch)
        ui.run()
        
    except Exception as e:
        logger.exception("Erreur au démarrage")
        # En cas d'erreur critique sans interface, on essaye d'afficher une boîte de dialogue
        try:
            import tkinter.messagebox as mbox
            mbox.showerror("Erreur Bizon", f"Impossible de lancer l'application :\n{e}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
