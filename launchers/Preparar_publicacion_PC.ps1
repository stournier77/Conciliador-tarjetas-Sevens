$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Root 'runtime_pc\python'
$env:UV_CACHE_DIR = Join-Path $Root 'runtime_pc\cache'
$Uv = Join-Path $Root 'runtime_pc\uv\uv.exe'
$Python = (& $Uv python find --managed-python 3.12).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Ejecutá primero el instalador.' }
& $Python (Join-Path $PSScriptRoot 'Preparar_publicacion.py')
if ($LASTEXITCODE -ne 0) { throw 'No se generó el paquete.' }
Start-Process (Join-Path $Root 'Publicacion GitHub')
Start-Process 'https://github.com/stournier77/Conciliador-tarjetas-Sevens/releases/new'
