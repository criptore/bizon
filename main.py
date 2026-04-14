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

# Configuration du logging : fichier + terminal (stdout original)
log_file = "cassandre.log"
log_stream = open(log_file, "a", encoding="utf-8")

# On garde une référence au stdout original (terminal) pour les logs en direct
_original_stdout = sys.stdout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(log_stream),      # → cassandre.log
        logging.StreamHandler(_original_stdout) # → terminal (visible pendant debug)
    ]
)

# Redirige stdout/stderr vers le log pour capturer les print() et erreurs non loggées
# Note : on redirige APRÈS avoir configuré le handler terminal ci-dessus
sys.stdout = log_stream
sys.stderr = log_stream
logger = logging.getLogger("CassandreMain")

def launch_terminal_process():
    """
    Démarre le dashboard dans un processus complètement séparé.
    Indispensable sur macOS : Tkinter et pywebview utilisent tous deux NSApp.
    Les lancer dans le même processus provoque un crash (segfault).
    Le subprocess écrit dans cassandre.log pour que les erreurs soient traçables.
    """
    import subprocess
    import os
    project_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info("[PROCESS] Démarrage du Terminal de Trading (processus isolé)...")
    # ...
    # MPLBACKEND=Agg : empêche matplotlib de tenter TkAgg sur macOS (SIGABRT subprocess)
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    return subprocess.Popen(
        [sys.executable, "-c",
         "import sys, logging;"
         "sys.path.insert(0, '.');"
         "from src.ui.dashboard import launch_dashboard;"
         "launch_dashboard(standalone=True)"],
        cwd=project_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def stream_logs(proc):
    """Lit et affiche la sortie du subprocess en temps réel."""
    for line in proc.stdout:
        # On affiche dans le terminal original
        _original_stdout.write(line)
        _original_stdout.flush()

def main():
    """Lancement de l'application Cassandre Desktop."""
    dashboard_proc = None
    try:
        from src.ui.launcher_ui import LauncherUI

        def on_launch():
            nonlocal dashboard_proc
            logger.info("[UI] Signal de lancement du terminal reçu depuis LauncherUI.")
            dashboard_proc = launch_terminal_process()
            ui.close()

        logger.info("[SYSTEM] Démarrage de l'interface de contrôle...")
        ui = LauncherUI(on_launch_callback=on_launch)
        ui.run()

        # Garder le terminal ouvert tant que le dashboard tourne
        if dashboard_proc is not None:
            import threading
            threading.Thread(target=stream_logs, args=(dashboard_proc,), daemon=True).start()
            logger.info("[SYSTEM] Dashboard en cours — terminal maintenu ouvert (Ctrl+C pour quitter).")
            dashboard_proc.wait()
            logger.info("[SYSTEM] Dashboard fermé.")

    except Exception as e:
        logger.exception("Erreur au démarrage")
        # En cas d'erreur critique sans interface, on essaye d'afficher une boîte de dialogue
        try:
            import tkinter.messagebox as mbox
            mbox.showerror("Erreur Cassandre", f"Impossible de lancer l'application :\n{e}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
