from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass

AUTHORIZED_DEVICES = {
    "00000000-0000-0000-0000-309C230BAEF1": {"name": "Tuki PC", "role": "admin"},
    "D4157452-1745-11EC-B699-67F9496C3500": {"name": "Laura Techera PC", "role": "user"},
    "86FE5326-6706-53D3-97C4-442452FDC186": {"name": "Tuki Mac", "role": "admin"},
    "0C8703A9-3F15-54CD-A977-B4D2B4CFE266": {"name": "Federico Mac", "role": "user"},
    "C1C28570-D1CF-0000-0000-000000000000": {"name": "Federico PC", "role": "user"},
    "60658200-1690-11EC-8AD9-C282CD8C3500": {"name": "Karen PC", "role": "user"},
    "CFB42280-DF54-11EE-AE55-C374CD633000": {"name": "PC adicional", "role": "user"},
}


def _normalize(value: str) -> str:
    return value.strip().upper()


def get_device_uuid() -> str:
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True, stderr=subprocess.DEVNULL
            )
            match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            return _normalize(match.group(1)) if match else "NO-DETECTADO"
        if system == "Windows":
            cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if out:
                return _normalize(out.splitlines()[-1])
            out = subprocess.check_output(["wmic", "csproduct", "get", "uuid"], text=True).splitlines()
            return _normalize(next(x for x in out if "UUID" not in x and x.strip()))
    except Exception:
        pass
    return "NO-DETECTADO"


def authorization() -> tuple[bool, str, dict[str, str] | None]:
    uuid = get_device_uuid()
    device = AUTHORIZED_DEVICES.get(uuid)
    return device is not None, uuid, device
