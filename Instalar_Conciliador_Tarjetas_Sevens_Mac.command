#!/bin/zsh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$SCRIPT_DIR/launchers/Instalar_Mac.command" 2>/dev/null || true
exec "$SCRIPT_DIR/launchers/Instalar_Mac.command"
