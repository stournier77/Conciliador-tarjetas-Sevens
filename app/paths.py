"""Carpetas de resultados independientes de la instalación y de las actualizaciones."""
from datetime import datetime
from pathlib import Path
import os


def documents_folder() -> Path:
    if os.name == "nt":
        # Respeta Documentos incluso si Windows lo redirige a OneDrive u otra unidad.
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Documents"


def output_root() -> Path:
    return documents_folder() / "Conciliador Tarjetas" / "Archivos conciliados"


def output_destination(start, end, now: datetime, provider: str = "Brex") -> tuple[Path, str]:
    if provider != "Brex":
        raise ValueError("Proveedor de tarjetas aún no implementado")
    period = f"{start:%Y-%m-%d}_al_{end:%Y-%m-%d}"
    folder = output_root() / provider / now.strftime("%Y-%m-%d")
    filename = f"Conciliacion_Tarjetas_{provider}_{period}_{now:%Y-%m-%d_%H-%M-%S_%f}.xlsx"
    return folder, filename
