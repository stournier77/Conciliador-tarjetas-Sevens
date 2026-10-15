"""Mismo flujo de publicación para Tarjetas, IATA y Bancos; conserva sus formatos."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from zoneinfo import ZoneInfo
import Publicar_directo as service
import Preparar_publicacion as tarjetas

HOME=Path.home()/'Documents'
PROFILES={
 'tarjetas':('App Conciliador Tarjetas Maveric','Conciliador-tarjetas-Sevens'),
 'iata':('App Conciliador IATA Maveric','conciliador-tuki-updates'),
 'bancos':('App Conciliador Bancos Maveric','conciliador-bancos-maveric-sevens'),
}
def number(v):
 if not re.fullmatch(r'\d+\.\d+\.\d+',v): raise ValueError('Usá una versión como 0.3.6')
 return tuple(map(int,v.split('.')))

def read_version(kind,root):
 path={'tarjetas':'version.txt','iata':'installed_version.txt','bancos':'APP/version.txt'}[kind]
 return (root/path).read_text().strip()

def stamp(source,version,date,kind):
 key='VERSION' if kind=='iata' else 'APP_VERSION'
 source=re.sub(r'^'+key+r' = "[^"]*"',f'{key} = "{version}"',source,flags=re.M)
 if kind=='iata':
  source=re.sub(r'^CREATED_LABEL = "[^"]*"',f'CREATED_LABEL = "{date}"',source,flags=re.M)
 else:
  source=re.sub(r'^APP_DATE = "[^"]*"',f'APP_DATE = "{date}"',source,flags=re.M)
 compile(source,'app','exec')
 return source

def pack(kind,root,out,version,date):
 out.mkdir(parents=True,exist_ok=True)
 if kind=='tarjetas':
  from arranque import MANAGED
  with tempfile.TemporaryDirectory() as t:
   stage=Path(t)
   for name in MANAGED:
    p=root/name
    if p.is_dir(): shutil.copytree(p,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    elif p.exists(): shutil.copy2(p,stage/name)
   (stage/'version.txt').write_text(version+'\n')
   p=stage/'app/config.py'; p.write_text(stamp(p.read_text(),version,date,kind))
   previous=tarjetas.ROOT; tarjetas.ROOT=stage
   try: tarjetas.build(out)
   finally: tarjetas.ROOT=previous
 elif kind=='iata':
  source=stamp((root/'APP_MAC/app.py').read_text(),version,date,kind)
  for platform in ('mac','pc'):
   template=service.ROOT/'tools/templates'/f'iata_{platform}.zip'
   with zipfile.ZipFile(template) as old, zipfile.ZipFile(out/f'latest_{platform}.zip','w',zipfile.ZIP_DEFLATED) as new:
    for info in old.infolist():
     if info.is_dir(): continue
     name=re.sub(r' v3\.6\.2/',f' v{version}/',info.filename,count=1)
     data=old.read(info.filename)
     if name.endswith('/APP_MAC/app.py') or name.endswith('/APP_PC/app.py'): data=source.encode()
     elif name.endswith('/installed_version.txt'): data=(version+'\n').encode()
     new.writestr(name,data)
 else:
  # Bancos tiene un actualizador común a Mac/PC que requiere latest_app.zip en updates/.
  with zipfile.ZipFile(out/'latest_app.zip','w',zipfile.ZIP_DEFLATED) as new:
   for p in (root/'APP').rglob('*'):
    if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc': continue
    name=p.relative_to(root).as_posix(); data=p.read_bytes()
    if name=='APP/app.py': data=stamp(data.decode(),version,date,kind).encode()
    elif name=='APP/version.txt': data=(version+'\n').encode()
    new.writestr(name,data)
  for platform in ('mac','pc'): shutil.copy2(out/'latest_app.zip',out/f'latest_{platform}.zip')
 (out/'version.txt').write_text(version+'\n')
 return ['latest_mac.zip','latest_pc.zip','version.txt']+(['latest_app.zip'] if kind=='bancos' else [])

def publish(kind):
 folder,repo=PROFILES[kind]; root=HOME/folder/'Archivos APP'; service.REPO='stournier77/'+repo
 service.gh('auth','status')
 releases=service.api(f'repos/{service.REPO}/releases')
 installed=read_version(kind,root)
 latest=max((r['tag_name'].lstrip('v') for r in releases if not r['draft'] and not r['prerelease']),key=number,default='0.0.0')
 base=max((installed,latest),key=number)
 default=installed if number(installed)>number(latest) else '.'.join(map(str,(*number(base)[:2],number(base)[2]+1)))
 version=input(f'Versión a publicar [{default}]: ').strip() or default
 if number(version)<=number(latest): raise ValueError('La versión debe ser superior a la publicada')
 date=datetime.now(ZoneInfo('America/Montevideo')).strftime('%d/%m/%Y')
 out=root/'Publicacion GitHub'/('v'+version)
 names=pack(kind,root,out,version,date)
 title=f'{version} · {date} — Conciliador {kind.title()} Maveric Sevens'
 print('Paquetes preparados:',out,'\nPublicación:',title)
 if input('Escribí PUBLICAR para subir: ').strip()!='PUBLICAR': print('No publicado.'); return
 ref=service.api(f'repos/{service.REPO}/git/ref/heads/main'); parent=ref['object']['sha']
 commit=service.api(f'repos/{service.REPO}/git/commits/{parent}')
 import base64
 entries=[]
 targets={n:n for n in names} if kind!='bancos' else {'latest_app.zip':'updates/latest_app.zip','version.txt':'updates/version.txt'}
 for name,path in targets.items():
  blob=service.api(f'repos/{service.REPO}/git/blobs','POST',{'encoding':'base64','content':base64.b64encode((out/name).read_bytes()).decode()})
  entries.append({'path':path,'mode':'100644','type':'blob','sha':blob['sha']})
 tree=service.api(f'repos/{service.REPO}/git/trees','POST',{'base_tree':commit['tree']['sha'],'tree':entries})
 new=service.api(f'repos/{service.REPO}/git/commits','POST',{'message':title,'tree':tree['sha'],'parents':[parent]})
 service.api(f'repos/{service.REPO}/git/refs/heads/main','PATCH',{'sha':new['sha'],'force':False})
 notes=f'Versión: {version}\nFecha: {date}\n\nPaquetes para Mac y PC con la misma versión y fecha. Se conservan los históricos. Verificar los cambios del proyecto antes de distribuir.\n'
 with tempfile.TemporaryDirectory() as t:
  f=Path(t)/'notes.txt'; f.write_text(notes)
  service.gh('release','create','v'+version,'--repo',service.REPO,'--target',new['sha'],'--title',title,'--notes-file',str(f),'--draft',*[str(out/n) for n in names])
 release=next(r for r in service.api(f'repos/{service.REPO}/releases') if r['tag_name']=='v'+version)
 if {a['name'] for a in release['assets']}!=set(names): raise RuntimeError('Borrador incompleto; no se publicó')
 for asset in release['assets']:
  digest=asset.get('digest')
  if digest and digest!='sha256:'+hashlib.sha256((out/asset['name']).read_bytes()).hexdigest(): raise RuntimeError('Checksum incorrecto; no se publicó')
 service.gh('release','edit','v'+version,'--repo',service.REPO,'--draft=false','--latest')
 print('Publicado:',release['html_url'])

if __name__=='__main__':
 try: publish(sys.argv[1])
 except Exception as exc: print('ERROR:',exc); sys.exit(1)
