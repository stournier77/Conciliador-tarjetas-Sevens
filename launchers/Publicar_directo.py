"""Publicación de los tres archivos mediante GitHub CLI, sin depender de Git/Xcode."""
import base64
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo
from arranque import ROOT, REPO
from Preparar_publicacion import build

GH = ROOT/'tools/gh'
def gh(*args, data=None):
    cmd=[str(GH),*args]
    if data is not None: cmd += ['--input','-']
    result=subprocess.run(cmd,input=json.dumps(data) if data is not None else None,text=True,capture_output=True,timeout=120)
    if result.returncode: raise RuntimeError(result.stderr.strip())
    return result.stdout

def api(path, method='GET', data=None):
    return json.loads(gh('api',path,'--method',method,data=data))

def identity():
    version=(ROOT/'version.txt').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Versión inválida')
    config=(ROOT/'app/config.py').read_text()
    if f'APP_VERSION = "{version}"' not in config: raise ValueError('version.txt y app/config.py no coinciden')
    date=datetime.now(ZoneInfo('America/Montevideo')).strftime('%d/%m/%Y')
    return version,date

def publish():
    if not GH.exists(): raise RuntimeError('No está instalada la herramienta GitHub CLI en Archivos APP/tools/gh')
    gh('auth','status')
    version,date=identity(); tag='v'+version
    releases=api(f'repos/{REPO}/releases')
    if any(r['tag_name']==tag for r in releases): raise ValueError('Esta versión ya existe en GitHub. Incrementá version.txt y app/config.py primero.')
    destination=ROOT/'Publicacion GitHub'; build(destination)
    title=f'{version} · {date} — Conciliador Tarjetas Maveric Sevens'
    print('Publicación:',title)
    if input('Escribí PUBLICAR para subir esta versión: ').strip()!='PUBLICAR':
        print('Paquetes preparados; publicación cancelada.'); return
    ref=api(f'repos/{REPO}/git/ref/heads/main'); parent=ref['object']['sha']
    commit=api(f'repos/{REPO}/git/commits/{parent}')
    entries=[]
    for name in ('latest_mac.zip','latest_pc.zip','version.txt'):
        blob=api(f'repos/{REPO}/git/blobs','POST',{'encoding':'base64','content':base64.b64encode((destination/name).read_bytes()).decode()})
        entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
    tree=api(f'repos/{REPO}/git/trees','POST',{'base_tree':commit['tree']['sha'],'tree':entries})
    new=api(f'repos/{REPO}/git/commits','POST',{'message':title,'tree':tree['sha'],'parents':[parent]})
    api(f'repos/{REPO}/git/refs/heads/main','PATCH',{'sha':new['sha'],'force':False})
    notes=f'Versión {version}\nFecha de publicación: {date}\n\nPaquetes Mac y Windows. Se conservan los históricos y la estructura Archivos APP / Conciliaciones Tarjetas Maveric. Consultar README incluido para instalación y pruebas.\n'
    with tempfile.TemporaryDirectory() as t:
        note=Path(t)/'notas.txt'; note.write_text(notes)
        gh('release','create',tag,'--repo',REPO,'--target',new['sha'],'--title',title,'--notes-file',str(note),'--draft',*[str(destination/n) for n in ('latest_mac.zip','latest_pc.zip','version.txt')])
    # Sólo publicar cuando los tres adjuntos estén presentes.
    release=next(r for r in api(f'repos/{REPO}/releases') if r['tag_name']==tag)
    if {a['name'] for a in release['assets']} != {'latest_mac.zip','latest_pc.zip','version.txt'}: raise RuntimeError('Release borrador incompleto; revisar antes de publicar')
    gh('release','edit',tag,'--repo',REPO,'--draft=false','--latest')
    print('Publicado:',f'https://github.com/{REPO}/releases/tag/{tag}')

if __name__=='__main__':
    try: publish()
    except Exception as exc: print('ERROR:',exc); sys.exit(1)
