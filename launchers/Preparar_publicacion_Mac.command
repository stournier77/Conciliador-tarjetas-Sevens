#!/bin/zsh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export UV_PYTHON_INSTALL_DIR="$ROOT/runtime_mac/python"
export UV_CACHE_DIR="$ROOT/runtime_mac/cache"
UV="$ROOT/runtime_mac/uv/uv"
if [[ ! -x "$UV" ]]; then echo 'Ejecutá primero el instalador.'; exit 1; fi
PYTHON="$("$UV" python find --managed-python 3.12)"
"$PYTHON" "$ROOT/launchers/Preparar_publicacion.py"
open "$ROOT/Publicacion GitHub"
open 'https://github.com/stournier77/Conciliador-tarjetas-Sevens/releases/new'
