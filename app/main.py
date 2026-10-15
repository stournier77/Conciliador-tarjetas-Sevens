from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

from authorized_devices import authorization
from config import APP_DATE, APP_NAME, APP_VERSION
from engine import MavericFile, ReconciliationError, infer_maveric_group, read_brex, reconcile
from paths import output_destination, output_root
from ui import ASSETS, apply_design, file_heading, footer, header, sidebar_brand, sidebar_info

st.set_page_config(page_title=APP_NAME, page_icon=str(ASSETS / "conciliador_tarjetas.png"), layout="wide", initial_sidebar_state="expanded")
apply_design()
allowed, device_uuid, device = authorization()
if not allowed:
    st.error("Esta computadora no está habilitada para usar el conciliador.")
    st.code(device_uuid)
    st.caption("Enviá este ID al administrador para solicitar la habilitación.")
    st.stop()


def _open_output_folder() -> None:
    folder = output_root()
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    elif os.name == "nt":
        os.startfile(str(folder))
    else:
        subprocess.Popen(["xdg-open", str(folder)])


with st.sidebar:
    sidebar_brand()
    if st.button("Abrir carpeta de conciliaciones", icon=":material/folder_open:", use_container_width=True, key="abrir_carpeta"):
        try:
            _open_output_folder()
        except Exception as exc:
            st.error(f"No se pudo abrir la carpeta: {exc}")
    sidebar_info(device["name"], APP_VERSION, APP_DATE)
    if st.button("Cerrar aplicación", icon=":material/power_settings_new:", use_container_width=True, key="cerrar_aplicacion"):
        st.info("Cerrando aplicación… Podés cerrar esta pestaña.")
        os._exit(0)

header()
st.markdown('<h2 class="sevens-section-title">Cargar archivos</h2>', unsafe_allow_html=True)
left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True, key="upload_brex"):
        file_heading("Subir Excel de la Tarjeta")
        brex_file = st.file_uploader("Subir Excel de la Tarjeta", type=["xlsx"], accept_multiple_files=False, label_visibility="collapsed", key="archivo_brex")
with right:
    with st.container(border=True, key="upload_maveric"):
        file_heading("Subir Excel de Maveric")
        maveric_file = st.file_uploader("Subir Excel de Maveric", type=["xls", "xlsx"], accept_multiple_files=False, label_visibility="collapsed", key="archivo_maveric")

# Conserva la detección y el valor inicial que usaba el selector anterior.
primary_group = infer_maveric_group(maveric_file.name) if maveric_file else "LEFITUR"
if primary_group not in {"LEFITUR", "DANARSIN", "PARAGUAY"}:
    primary_group = "LEFITUR"

conciliar = st.button("GENERAR CONCILIACIÓN", icon=":material/fact_check:", type="primary", disabled=not (brex_file and maveric_file), use_container_width=True, key="generar_conciliacion")
if conciliar:
    try:
        brex_bytes = brex_file.getvalue()
        with st.spinner("Leyendo archivos y conciliando…"):
            brex_df = read_brex(brex_bytes)
            if brex_df.empty:
                raise ReconciliationError("El archivo Brex no contiene transacciones válidas")
            start_date = min(brex_df["_date"])
            end_date = max(brex_df["_date"])
            result, stats = reconcile(brex_bytes, [MavericFile(maveric_file.name, maveric_file.getvalue(), primary_group)], primary_group=primary_group)
        base, filename = output_destination(start_date, end_date, datetime.now())
        base.mkdir(parents=True, exist_ok=True)
        output_path = base / filename
        output_path.write_bytes(result)
        st.success("Conciliación terminada y guardada automáticamente")
        st.caption(f"Guardado en: {output_path}")
        cols = st.columns(min(4, max(1, len(stats))))
        for index, (name, value) in enumerate(sorted(stats.items())):
            cols[index % len(cols)].metric(name, value)
        st.download_button("Descargar también una copia", data=result, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ReconciliationError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.exception(exc)
footer()
