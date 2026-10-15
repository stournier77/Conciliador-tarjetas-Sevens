@echo off
setlocal
set "SEVENS_REPAIR_SELF=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$source=[IO.File]::ReadAllText($env:SEVENS_REPAIR_SELF); & ([scriptblock]::Create(($source -split '(?m)^#SEVENS_POWERSHELL\r?$',2)[1]))"
if errorlevel 1 pause
exit /b
#SEVENS_POWERSHELL
$ErrorActionPreference='Stop'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$documents=[Environment]::GetFolderPath('MyDocuments')
$root=Join-Path $documents 'App Conciliador Tarjetas Maveric\Archivos APP'
if (-not (Test-Path (Join-Path $root 'launchers\Abrir_Conciliador_Tarjetas_PC.bat'))) {
    throw "No se encontró la instalación de Tarjetas en: $root"
}
$headers=@{'User-Agent'='Sevens-Tarjetas-Repair';'Accept'='application/vnd.github+json'}
$release=Invoke-RestMethod 'https://api.github.com/repos/stournier77/Conciliador-tarjetas-Sevens/releases/latest' -Headers $headers -TimeoutSec 30
if ([version]($release.tag_name.TrimStart('v')) -lt [version]'0.4.2') { throw 'La reparación todavía no está publicada. Volvé a intentarlo en unos minutos.' }
$asset=$release.assets | Where-Object { $_.name -eq 'latest_pc.zip' } | Select-Object -First 1
if (-not $asset -or -not $asset.browser_download_url.StartsWith('https://github.com/stournier77/Conciliador-tarjetas-Sevens/releases/download/')) { throw 'Paquete de actualización inválido' }
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('Sevens-Tarjetas-'+[Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $temporary | Out-Null
$backup=Join-Path $root ('backups\reparacion_pc_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
$replaced=New-Object System.Collections.Generic.List[string]
try {
    $zipPath=Join-Path $temporary 'latest_pc.zip'
    Write-Host 'Descargando la reparación oficial de Sevens...'
    Invoke-WebRequest $asset.browser_download_url -OutFile $zipPath -UseBasicParsing -TimeoutSec 120
    if (-not $asset.digest -or -not $asset.digest.StartsWith('sha256:')) { throw 'GitHub no proporcionó la verificación del paquete' }
    if ((Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLower() -ne $asset.digest.Substring(7)) { throw 'La verificación del paquete falló' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $names=@('Abrir_Conciliador_Tarjetas_PC.ps1','python_pc.ps1')
        foreach ($name in $names) {
            $entry=$archive.GetEntry('launchers/'+$name)
            if (-not $entry) { throw "Falta un archivo de reparación: $name" }
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,(Join-Path $temporary $name),$true)
        }
    } finally { $archive.Dispose() }
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    foreach ($name in $names) {
        $target=Join-Path $root ('launchers\'+$name)
        if (Test-Path $target) { Copy-Item $target (Join-Path $backup $name) }
        $replaced.Add($name)
        Copy-Item (Join-Path $temporary $name) $target -Force
    }
    Write-Host 'Inicio reparado. Abriendo Tarjetas; se actualizará automáticamente.'
    Start-Process -FilePath (Join-Path $root 'launchers\Abrir_Conciliador_Tarjetas_PC.bat') -WorkingDirectory $root
} catch {
    foreach ($name in $replaced) {
        $saved=Join-Path $backup $name
        if (Test-Path $saved) { Copy-Item $saved (Join-Path $root ('launchers\'+$name)) -Force }
    }
    throw
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
