#!/bin/zsh
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HOME/Documents/App Conciliador Tarjetas Maveric/Archivos APP/runtime_mac/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Primero instalá el conciliador de Tarjetas en esta Mac."
  exit 1
fi
# Reinicia exclusivamente la prueba de este proyecto. Nunca toca el puerto habitual 8783.
"$PYTHON" - "$ROOT" <<'PY'
from pathlib import Path
import os,signal,subprocess,sys,time
root=Path(sys.argv[1]).resolve()
p=subprocess.run(['/usr/sbin/lsof','-t','-iTCP:18783','-sTCP:LISTEN'],capture_output=True,text=True)
for value in set(p.stdout.split()):
    pid=int(value)
    cwd=subprocess.run(['/usr/sbin/lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
    if 'n'+str(root/'app') not in cwd.stdout.splitlines():
        raise SystemExit('El puerto de prueba está ocupado por otra aplicación. No se cerró ningún proceso.')
    os.kill(pid,signal.SIGTERM)
for _ in range(50):
    p=subprocess.run(['/usr/sbin/lsof','-t','-iTCP:18783','-sTCP:LISTEN'],capture_output=True,text=True)
    if not p.stdout.strip(): break
    time.sleep(.1)
else:
    raise SystemExit('La prueba anterior aún se está cerrando. Volvé a abrir este acceso.')
PY
# Abre el navegador solamente cuando la nueva prueba responde.
"$PYTHON" - <<'PY' &
import time,urllib.request,webbrowser
for _ in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:18783/_stcore/health',timeout=1) as r:
            if r.status==200:
                webbrowser.open('http://127.0.0.1:18783/?diseno=04-01')
                break
    except OSError: pass
    time.sleep(1)
PY
cd "$ROOT/app"
exec "$PYTHON" -m streamlit run main.py --server.port=18783 --server.address=127.0.0.1 --server.headless=true --browser.gatherUsageStats=false --server.fileWatcherType=poll --server.runOnSave=true --theme.base=light
