#!/bin/zsh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GH="$ROOT/tools/gh"
if ! "$GH" auth status >/dev/null 2>&1; then
  echo 'Primera configuración: iniciá sesión en GitHub con tu cuenta.'
  "$GH" auth login --hostname github.com --git-protocol https --web
fi
export UV_CACHE_DIR="$ROOT/runtime_mac/cache" UV_PYTHON_INSTALL_DIR="$ROOT/runtime_mac/python"
PYTHON="$("$ROOT/runtime_mac/uv/uv" python find --managed-python 3.12)"
"$PYTHON" "$ROOT/launchers/Publicar_directo.py"
read '?Enter para cerrar...'
