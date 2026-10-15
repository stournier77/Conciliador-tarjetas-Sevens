"""Genera únicamente los tres archivos de distribución sin históricos ni runtimes."""
from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import zipfile
from arranque import ROOT, MANAGED

def build(destination):
    date=datetime.now(ZoneInfo('America/Montevideo')).strftime('%d/%m/%Y')
    version=(ROOT/'version.txt').read_text().strip()
    config=(ROOT/'app/config.py').read_text()
    if f'APP_VERSION = "{version}"' not in config:
        raise ValueError('La versión de config.py no coincide con version.txt')
    config=re.sub(r'APP_DATE = "[^"]*"', f'APP_DATE = "{date}"', config)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for platform in ('mac','pc'):
        with zipfile.ZipFile(destination / f'latest_{platform}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for name in MANAGED:
                path = ROOT / name
                candidates = path.rglob('*') if path.is_dir() else [path]
                for file in candidates:
                    if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                        if file.relative_to(ROOT).as_posix() == 'app/config.py':
                            z.writestr('app/config.py',config)
                        else:
                            z.write(file, file.relative_to(ROOT))
    (destination / 'version.txt').write_bytes((ROOT / 'version.txt').read_bytes())
    print('Paquete GitHub:', destination)

if __name__ == '__main__': build(sys.argv[1] if len(sys.argv)>1 else ROOT / 'Publicacion GitHub')
