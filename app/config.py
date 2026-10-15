from __future__ import annotations

from pathlib import Path

APP_NAME = "Conciliador de Tarjetas - Maveric"
APP_VERSION = "0.4.2"
APP_DATE = "15/10/2026"
INSTALL_FOLDER_NAME = "App Conciliador Tarjetas Maveric"
OUTPUT_FOLDER_NAME = "Archivos conciliados"

_repo_file = Path(__file__).resolve().parents[1] / "github_repo.txt"
_repo_value = _repo_file.read_text(encoding="utf-8").strip() if _repo_file.exists() else "stournier77/Conciliador-tarjetas-Sevens"
GITHUB_OWNER, _, GITHUB_REPO = _repo_value.partition("/")
