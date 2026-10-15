from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests
from packaging.version import Version, InvalidVersion

from config import APP_VERSION, GITHUB_OWNER, GITHUB_REPO


@dataclass(slots=True)
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str | None = None
    release_url: str | None = None
    asset_url: str | None = None
    message: str = ""


def _configured() -> bool:
    return GITHUB_OWNER not in {"", "TU_USUARIO_O_ORGANIZACION"} and bool(GITHUB_REPO)


def check_for_update(platform_key: str, timeout: int = 8) -> UpdateInfo:
    if not _configured():
        return UpdateInfo(False, APP_VERSION, message="GitHub todavía no está configurado en app/config.py")

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    try:
        response = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
        response.raise_for_status()
        data = response.json()
        tag = str(data.get("tag_name", "")).lstrip("v")
        try:
            available = Version(tag) > Version(APP_VERSION)
        except InvalidVersion:
            available = tag != APP_VERSION

        wanted = {
            "mac": ["latest_mac.zip", "mac.zip", ".dmg"],
            "windows": ["latest_pc.zip", "windows.zip", ".exe"],
        }.get(platform_key, [])
        asset_url = None
        for asset in data.get("assets", []):
            name = str(asset.get("name", "")).lower()
            if any(token in name for token in wanted):
                asset_url = asset.get("browser_download_url")
                break

        return UpdateInfo(
            available=available,
            current_version=APP_VERSION,
            latest_version=tag or None,
            release_url=data.get("html_url"),
            asset_url=asset_url,
            message="Actualización disponible" if available else "La aplicación está actualizada",
        )
    except Exception as exc:
        return UpdateInfo(False, APP_VERSION, message=f"No se pudo comprobar la actualización: {exc}")


def save_update_metadata(path: Path, info: UpdateInfo) -> None:
    path.write_text(json.dumps(info.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")
