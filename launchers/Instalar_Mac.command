#!/bin/zsh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/launchers/Abrir_Conciliador_Tarjetas_Mac.command" --install
