import os
import plistlib
import json
import shlex
import tempfile
from pathlib import Path
import shutil
import subprocess
import sys
from arranque import ROOT, deploy
sys.path.insert(0, str(ROOT / "app"))
from paths import documents_folder, output_root

def install():
    target = documents_folder() / 'App Conciliador Tarjetas Maveric'
    files = target / 'Archivos APP'
    output = output_root()
    output.mkdir(parents=True, exist_ok=True)
    deploy(ROOT, files)
    old = documents_folder() / 'Conciliador Tarjetas Maveric' / 'Conciliaciones Tarjetas Maveric'
    if old.exists():
        # Copia completa en subcarpeta separada para conservar colisiones.
        imported = output / 'Historicos_instalacion_anterior'
        if not imported.exists(): shutil.copytree(old, imported)
    shortcuts = target / 'Accesos'
    shortcuts.mkdir(exist_ok=True)
    if os.name == 'nt':
        # El escritorio real puede estar redirigido por Windows/OneDrive.
        shortcut_script = '''param([string]$Launcher,[string]$Icon,[string]$WorkDir)
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
$desktop = $shell.SpecialFolders.Item('Desktop')
$link = $shell.CreateShortcut((Join-Path $desktop 'Conciliador de Tarjetas - Maveric.lnk'))
$link.TargetPath = $Launcher
$link.WorkingDirectory = $WorkDir
$link.IconLocation = $Icon
$link.Description = 'Conciliador de Tarjetas - Maveric Sevens'
$link.Save()
'''
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'acceso.ps1'
            script.write_text(shortcut_script, encoding='utf-8-sig')
            subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Launcher', str(files/'launchers/Abrir_Conciliador_Tarjetas_PC.bat'), '-Icon', str(files/'assets/conciliador_tarjetas.ico'), '-WorkDir', str(files)], check=True)
        (shortcuts / 'Abrir Conciliador.bat').write_text('@echo off\r\ncall "%~dp0..\\Archivos APP\\launchers\\Abrir_Conciliador_Tarjetas_PC.bat"\r\n')
        (shortcuts / 'Editar proyecto.bat').write_text('@echo off\r\nstart "" "%~dp0..\\Archivos APP"\r\n')
        (shortcuts / 'Publicar GitHub.bat').write_text('@echo off\r\ncall "%~dp0..\\Archivos APP\\launchers\\Preparar_publicacion_PC.bat"\r\n')
    else:
        actions = {
            'Abrir Conciliador.command': 'exec "$BASE/Archivos APP/launchers/Abrir_Conciliador_Tarjetas_Mac.command"',
            'Editar proyecto.command': 'open "$BASE/Archivos APP"; open "https://github.com/stournier77/Conciliador-tarjetas-Sevens"',
            'Publicar GitHub.command': 'exec "$BASE/Archivos APP/launchers/Preparar_publicacion_Mac.command"',
        }
        for name, command in actions.items():
            f = shortcuts / name
            f.write_text('#!/bin/zsh\nBASE="$(cd "$(dirname "$0")/.." && pwd)"\n' + command + '\n')
            f.chmod(0o755)
    if os.name != 'nt':
        # Aplicación nativa: arranque inline, sin abrir un .command desde Terminal.
        desktop = Path.home() / 'Desktop'
        app = desktop / 'Conciliador de Tarjetas - Maveric.app'
        uv_target = files / 'runtime_mac/uv/uv'
        uv_source = ROOT / 'runtime_mac/uv/uv'
        if not uv_target.exists() and uv_source.exists():
            uv_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(uv_source, uv_target)
        env = 'export UV_CACHE_DIR=' + shlex.quote(str(files/'runtime_mac/cache')) + '; export UV_PYTHON_INSTALL_DIR=' + shlex.quote(str(files/'runtime_mac/python')) + '; export UV_NO_MODIFY_PATH=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1; '
        command = env + shlex.quote(str(uv_target)) + ' python install --no-bin --no-registry 3.12 && PYTHON=$(' + shlex.quote(str(uv_target)) + ' python find --managed-python 3.12) && "$PYTHON" ' + shlex.quote(str(files/'launchers/arranque.py'))
        background = 'nohup /bin/zsh -c ' + shlex.quote(command) + ' >> ' + shlex.quote(str(files/'logs/acceso_escritorio.log')) + ' 2>&1 < /dev/null &'
        (files/'logs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            source = temp/'inicio.applescript'
            source.write_text('on run\n do shell script ' + json.dumps(background) + '\nend run\n')
            built = temp/'Tarjetas.app'
            subprocess.run(['osacompile','-o',str(built),str(source)], check=True)
            shutil.copytree(built, app, dirs_exist_ok=True)
        icon = files/'assets/AppIcon.icns'
        if icon.exists(): shutil.copy2(icon, app/'Contents/Resources/AppIcon.icns')
        info_path = app/'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleName='Conciliador de Tarjetas - Maveric', CFBundleIdentifier='uy.sevens.conciliador.tarjetas', CFBundleIconFile='AppIcon', CFBundleVersion=(files/'version.txt').read_text().strip())
        info_path.write_bytes(plistlib.dumps(info))
        subprocess.run(['xattr','-d','com.apple.FinderInfo',str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['codesign','--force','--deep','--sign','-',str(app)], check=True)
    print('Instalación completa:', target)
    print('Accesos para abrir, editar y publicar:', shortcuts)
    print('Los archivos y carpetas ajenos al programa no se eliminaron.')

if __name__ == '__main__': install()
