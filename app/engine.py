from __future__ import annotations

import io
import itertools
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from card_map import CARD_OWNERS, owner_family

PREFIX_COMPANY = {
    "001":"AMERICAN AIRLINES","006":"DELTA AIR LINES","014":"AIR CANADA","016":"UNITED AIRLINES",
    "044":"AEROLINEAS ARGENTINAS","045":"LATAM","057":"AIR FRANCE","074":"KLM","075":"IBERIA",
    "081":"QANTAS","105":"FINNAIR","117":"SAS","127":"GOL","134":"AVIANCA","157":"QATAR AIRWAYS",
    "160":"CATHAY PACIFIC","176":"EMIRATES","217":"THAI AIRWAYS","220":"LUFTHANSA",
    "230":"COPA AIRLINES","235":"TURKISH AIRLINES","260":"FIJI AIRWAYS","279":"JETBLUE AIRWAYS",
    "328":"NORWEGIAN AIR","333":"VIVA AEROBUS","445":"PARANAIR","526":"SOUTHWEST",
    "577":"AZUL","605":"SKY AIRLINE","618":"SINGAPORE AIRLINES","781":"CHINA EASTERN AIRLINES",
    "784":"CHINA SOUTHERN AIRLINES","888":"EASYJET","890":"SERVICE FEE","973":"JETSMART","996":"AIR EUROPA","999":"AIR CHINA",
}


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _upper(value: object) -> str:
    return _text(value).upper()


def _last4(value: object) -> str:
    if isinstance(value, (int, float)) and not pd.isna(value):
        digits = str(int(value))
    else:
        digits = re.sub(r"\D", "", str(value or ""))
    return digits[-4:].zfill(4) if digits else ""


def _auth(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", _upper(value))


def _amount(value: object) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _company_from_ticket(ticket: str) -> str | None:
    match = re.match(r"^(\d{3})[- ]?\d{6,}", _upper(ticket))
    return PREFIX_COMPANY.get(match.group(1)) if match else None


def _normal_company(value: object) -> str:
    text = _upper(value)
    aliases = [
        (["AEROLINEAS"],"AEROLINEAS ARGENTINAS"),(["AMERICAN"],"AMERICAN AIRLINES"),
        (["DELTA"],"DELTA AIR LINES"),(["AIR CANADA"],"AIR CANADA"),(["UNITED"],"UNITED AIRLINES"),
        (["AIR FRANCE"],"AIR FRANCE"),(["KLM"],"KLM"),(["IBERIA"],"IBERIA"),
        (["LATAM","LAN AIR"],"LATAM"),(["AIR EUROPA"],"AIR EUROPA"),(["COPA"],"COPA AIRLINES"),
        (["QATAR"],"QATAR AIRWAYS"),(["EMIRATES"],"EMIRATES"),(["LUFTHANSA"],"LUFTHANSA"),
        (["THAI"],"THAI AIRWAYS"),(["SINGAPORE"],"SINGAPORE AIRLINES"),
        (["CHINA EAST"],"CHINA EASTERN AIRLINES"),(["CHINA SOUTH"],"CHINA SOUTHERN AIRLINES"),
        (["AIR CHINA"],"AIR CHINA"),(["VIVA"],"VIVA AEROBUS"),(["GOL"],"GOL"),
        (["SKY"],"SKY AIRLINE"),(["JETSMART"],"JETSMART"),(["AZUL"],"AZUL"),
        (["FINNAIR"],"FINNAIR"),(["AVIANCA"],"AVIANCA"),(["TURKISH","THY"],"TURKISH AIRLINES"),
        (["CATHAY"],"CATHAY PACIFIC"),(["PARANAIR"],"PARANAIR"),(["JETBLUE"],"JETBLUE AIRWAYS"),
        (["SOUTHWEST"],"SOUTHWEST"),(["QANTAS"],"QANTAS"),(["SAS"],"SAS"),
        (["EASYJET"],"EASYJET"),(["FRONTIER"],"FRONTIER AIRLINES"),
    ]
    for tokens, company in aliases:
        if any(token in text for token in tokens):
            return company
    return text


def infer_maveric_group(filename: str) -> str:
    name = _upper(filename)
    if "DANARSIN" in name:
        return "DANARSIN"
    if "PARAGUAY" in name:
        return "PARAGUAY"
    if "LEFITUR" in name or "BREX" in name:
        return "LEFITUR"
    return "DESCONOCIDO"


@dataclass(slots=True)
class MavericFile:
    name: str
    content: bytes
    forced_group: str | None = None


class ReconciliationError(RuntimeError):
    pass


def read_brex(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content), sheet_name="Transactions", engine="openpyxl")
    required = {"Swipe Time (UTC)", "Amount", "Statement Descriptor", "Merchant Name", "Brex Category", "Type", "Last 4", "Id"}
    missing = required - set(df.columns)
    if missing:
        raise ReconciliationError(f"Faltan columnas en Brex: {', '.join(sorted(missing))}")

    df = df[df["Type"].astype(str).str.upper().eq("TRANSACTION")].copy()
    df["_dt"] = pd.to_datetime(df["Swipe Time (UTC)"], utc=True, errors="coerce", format="mixed")
    df = df[df["_dt"].notna()].copy()
    df["_date"] = df["_dt"].dt.date
    df["_time"] = df["_dt"].dt.strftime("%H:%M:%S")
    df["_amount"] = pd.to_numeric(df["Amount"], errors="coerce").round(2)
    df["_last4"] = df["Last 4"].map(_last4)
    df["_owner"] = df["_last4"].map(CARD_OWNERS).fillna("SIN CLASIFICAR")
    df["_owner_family"] = df["_owner"].map(owner_family)
    df["_company"] = (df["Merchant Name"].fillna(df["Statement Descriptor"])).map(_normal_company)
    df["_is_air"] = df["Brex Category"].astype(str).str.upper().eq("AIRLINE EXPENSES")
    df["_is_fee"] = df["Statement Descriptor"].astype(str).str.upper().eq("AGENT FEE")
    return df.reset_index(drop=True)


def _read_maveric_table(content: bytes, name: str) -> pd.DataFrame:
    if name.lower().endswith(".xls"):
        return pd.read_excel(io.BytesIO(content), header=None, engine="xlrd")
    return pd.read_excel(io.BytesIO(content), header=None, engine="openpyxl")


def read_maveric(file: MavericFile) -> pd.DataFrame:
    raw = _read_maveric_table(file.content, file.name)
    source_group = file.forced_group or infer_maveric_group(file.name)
    provider = ""
    records: list[dict[str, object]] = []

    for idx, row in raw.iterrows():
        values = list(row.values) + [None] * 13
        a = values[0]
        if isinstance(a, str) and a.strip():
            a_text, b_text = _upper(a), _upper(values[1])
            if ((b_text and a_text == b_text) or (
                a_text not in {"FECHA","DOLARES","BOLETO","PASAJERO","F. DE PAGO"}
                and not a_text.startswith("TOTALES") and "TOTAL" not in a_text
                and a_text not in {"EMITIDO CON TARJETA","CASH"}
            )):
                provider = a_text

        if isinstance(a, (int, float)) and not pd.isna(a) and float(a) > 30000:
            dt = pd.Timestamp("1899-12-30") + pd.to_timedelta(float(a), unit="D")
        else:
            dt = pd.to_datetime(a, errors="coerce")
        payment = _text(values[6])
        amount = _amount(values[7])
        # CASH and rows without a real card authorization are excluded completely.
        if pd.isna(dt) or "CC" not in _upper(payment) or amount in {None, 0}:
            continue
        before, sep, after = payment.partition("/")
        card = _last4(before)
        authorization = _auth(after) if sep else ""
        if not card or not authorization:
            continue

        ticket = _text(values[1])
        records.append({
            "mav_id": f"{file.name}:{idx+1}",
            "source_file": file.name,
            "source_group": source_group,
            "row_number": idx + 1,
            "date": dt.date(),
            "ticket": ticket,
            "company": _company_from_ticket(ticket),
            "last4": card,
            "auth": authorization,
            "amount": amount,
            "reservation": _amount(values[9]),
            "provider": provider,
            "passenger": _upper(values[5]),
        })
    return pd.DataFrame(records)


def _authorization_parts(maveric: pd.DataFrame) -> list[dict[str, object]]:
    air = maveric[maveric["company"].notna() & maveric["company"].ne("SERVICE FEE")].copy()
    cols = ["source_file", "source_group", "date", "last4", "auth", "company"]
    parts: list[dict[str, object]] = []
    for key, part in air.groupby(cols, dropna=False, sort=False):
        parts.append({"key": key, "records": part.to_dict("records")})
    return parts


def _candidate_subsets(records: list[dict[str, object]]) -> Iterable[tuple[int, ...]]:
    n = len(records)
    if n <= 12:
        for size in range(1, n + 1):
            yield from itertools.combinations(range(n), size)
        return
    # Very large authorization groups are rare on the target cards. Avoid exponential blow-up.
    for i in range(n):
        yield (i,)
    yield tuple(range(n))


def _match_air(brex: pd.DataFrame, maveric: pd.DataFrame) -> tuple[dict[int, dict], set[str]]:
    """Global non-reuse allocation inside authorization groups.

    A Maveric authorization may contain several tickets and may represent several separate
    Brex charges when the tickets are individually charged. Candidate subsets are generated
    inside the authorization, and grouped exact matches are reserved before individual ones.
    """
    brex_by_key: dict[tuple[str, str, float], list[int]] = defaultdict(list)
    for bi, b in brex.iterrows():
        if bool(b["_is_air"]) and float(b["_amount"]) >= 0:
            brex_by_key[(b["_last4"], b["_company"], round(float(b["_amount"]), 2))].append(bi)

    candidates: list[tuple[tuple, int, dict]] = []
    for auth_part in _authorization_parts(maveric):
        source_file, source_group, mav_date, card, authorization, company = auth_part["key"]
        records = auth_part["records"]
        seen: set[tuple[float, tuple[str, ...]]] = set()
        for indices in _candidate_subsets(records):
            total = round(sum(float(records[i]["amount"]) for i in indices), 2)
            ids = tuple(str(records[i]["mav_id"]) for i in indices)
            signature = (total, ids)
            if signature in seen:
                continue
            seen.add(signature)
            for bi in brex_by_key.get((card, company, total), []):
                b = brex.loc[bi]
                same_date = mav_date == b["_date"]
                grouped = len(indices) > 1
                # Priority: grouped same date, individual same date, grouped other date,
                # individual other date. Tickets are never reused.
                phase = 0 if same_date and grouped else 1 if same_date else 2 if grouped else 3
                distance = abs((mav_date - b["_date"]).days)
                sort_key = (
                    phase,
                    distance,
                    -len(indices),
                    source_file,
                    min(int(records[i]["row_number"]) for i in indices),
                )
                payload = {
                    "source_file": source_file,
                    "source_group": source_group,
                    "date": mav_date,
                    "last4": card,
                    "auth": authorization,
                    "company": company,
                    "amount": total,
                    "records": [records[i] for i in indices],
                }
                candidates.append((sort_key, bi, payload))

    candidates.sort(key=lambda item: item[0])
    matches: dict[int, dict] = {}
    used: set[str] = set()
    for _, bi, group in candidates:
        ids = [str(r["mav_id"]) for r in group["records"]]
        if bi in matches or any(mid in used for mid in ids):
            continue
        used.update(ids)
        count = len(group["records"])
        same_date = group["date"] == brex.loc[bi, "_date"]
        alternate = False
        match_type = "OK agrupado" if count > 1 else "OK individual"
        if not same_date:
            match_type += " (otra fecha)"
        matches[bi] = {"type": match_type, "group": group, "alternate": alternate}
    return matches, used


def _agent_fee_matches(brex: pd.DataFrame, maveric: pd.DataFrame, air_matches: dict[int, dict], used: set[str]) -> dict[int, dict]:
    results: dict[int, dict] = {}
    fee_mav = maveric[
        maveric["ticket"].astype(str).str.startswith("890-")
        & maveric["provider"].astype(str).str.upper().str.contains("CTC", na=False)
    ].copy()

    air_by_key: dict[tuple[str, object], list[int]] = defaultdict(list)
    for bi, b in brex.iterrows():
        if bool(b["_is_air"]):
            air_by_key[(b["_last4"], b["_date"])].append(bi)

    linked: dict[int, list[int]] = {}
    for bi, b in brex.iterrows():
        if not bool(b["_is_fee"]) or float(b["_amount"]) < 0:
            continue
        distances = []
        for ai in air_by_key.get((b["_last4"], b["_date"]), []):
            seconds = abs((brex.loc[ai, "_dt"] - b["_dt"]).total_seconds())
            if seconds <= 300:
                distances.append((seconds, ai))
        distances.sort()
        if distances:
            best = distances[0][0]
            linked[bi] = [ai for seconds, ai in distances if seconds <= best + 2]
        else:
            linked[bi] = []

    buckets: dict[tuple, list[int]] = defaultdict(list)
    for bi, air_ids in linked.items():
        b = brex.loc[bi]
        signature = tuple(sorted(air_ids)) if air_ids else (b["_time"],)
        buckets[(b["_last4"], b["_date"], signature)].append(bi)

    for _, fee_indices in buckets.items():
        total = round(float(brex.loc[fee_indices, "_amount"].sum()), 2)
        first = brex.loc[fee_indices[0]]
        candidates = fee_mav[
            fee_mav["last4"].eq(first["_last4"])
            & fee_mav["date"].eq(first["_date"])
            & fee_mav["amount"].round(2).eq(total)
            & ~fee_mav["mav_id"].isin(used)
        ].copy()

        linked_air_groups = [air_matches[ai]["group"] for ai in linked[fee_indices[0]] if ai in air_matches]
        linked_res = [r.get("reservation") for group in linked_air_groups for r in group["records"] if pd.notna(r.get("reservation"))]
        linked_rows = [r["row_number"] for group in linked_air_groups for r in group["records"]]

        chosen = None
        if not candidates.empty:
            def score(row: pd.Series) -> tuple[float, float, int]:
                res_distance = min((abs(float(row["reservation"]) - float(r)) for r in linked_res), default=999999)
                row_distance = min((abs(int(row["row_number"]) - int(r)) for r in linked_rows), default=999999)
                return res_distance, row_distance, int(row["row_number"])
            candidates = candidates.assign(_score=candidates.apply(score, axis=1)).sort_values("_score")
            chosen = candidates.iloc[0]
            used.add(str(chosen["mav_id"]))

        for position, bi in enumerate(fee_indices):
            associated = [brex.loc[ai] for ai in linked[bi]]
            association_text = " || ".join(
                f"{a['Statement Descriptor']} | {a['_dt'].strftime('%d/%m/%Y %H:%M:%S')} | {a['Id']}"
                for a in associated
            )
            if chosen is not None:
                results[bi] = {
                    "type": "OK AGENT FEE AGRUPADO" if len(fee_indices) > 1 else "OK AGENT FEE",
                    "chosen": chosen.to_dict(),
                    "count": len(fee_indices),
                    "association": association_text,
                    "included": position > 0,
                }
            elif linked_air_groups:
                results[bi] = {
                    "type": "OK AGENT FEE ASOCIADO",
                    "air_groups": linked_air_groups,
                    "count": len(linked_air_groups),
                    "association": association_text,
                    "included": False,
                }
    return results


def _style_output(writer: pd.ExcelWriter, sheet_name: str, frame: pd.DataFrame) -> None:
    workbook = writer.book
    ws = writer.sheets[sheet_name]
    header = workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78", "align": "center"})
    amount_fmt = workbook.add_format({"num_format": "0.00"})
    red_amount = workbook.add_format({"num_format": "0.00", "font_color": "#C00000", "bold": True})
    green = workbook.add_format({"bg_color":"#C6EFCE","font_color":"#006100","bold":True})
    red = workbook.add_format({"bg_color":"#FFC7CE","font_color":"#9C0006","bold":True})
    orange = workbook.add_format({"bg_color":"#FCE5CD","font_color":"#7F6000","bold":True})
    blue = workbook.add_format({"bg_color":"#D9EAF7","font_color":"#1F4E78","bold":True})
    gray = workbook.add_format({"bg_color":"#D9E1F2","font_color":"#44546A","bold":True})
    pink = workbook.add_format({"bg_color":"#F4CCCC","font_color":"#9C0006","bold":True})

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(frame), 1), max(len(frame.columns)-1, 0))
    ws.set_row(0, 22, header)
    widths = [13,12,34,13,22,28,24,20,11,28,14,24,35,58,12,20,22,28,38,62,35]
    for col, width in enumerate(widths[:len(frame.columns)]):
        ws.set_column(col, col, width)
    if "Importe Brex" in frame.columns:
        c = frame.columns.get_loc("Importe Brex")
        ws.set_column(c, c, 14, amount_fmt)
        ws.conditional_format(1, c, max(len(frame),1), c, {"type":"cell","criteria":"<","value":0,"format":red_amount})
    if "Estado" in frame.columns:
        c = frame.columns.get_loc("Estado")
        last = max(len(frame), 1)
        ws.conditional_format(1,c,last,c,{"type":"text","criteria":"containing","value":"OK","format":green})
        ws.conditional_format(1,c,last,c,{"type":"text","criteria":"containing","value":"Con diferencia","format":red})
        ws.conditional_format(1,c,last,c,{"type":"text","criteria":"containing","value":"AGENT FEE","format":orange})
        ws.conditional_format(1,c,last,c,{"type":"text","criteria":"containing","value":"NO ES AÉREO","format":gray})
        ws.conditional_format(1,c,last,c,{"type":"text","criteria":"containing","value":"REFUND","format":pink})


def reconcile(brex_content: bytes, maveric_files: Iterable[MavericFile], primary_group: str = "LEFITUR") -> tuple[bytes, dict[str, int]]:
    # Siempre se conservan todos los cargos Brex. El archivo Maveric cargado se
    # utiliza como única base de conciliación y se prueba contra todos los cargos,
    # independientemente de la hoja/grupo donde luego se presenten en el Excel.
    brex = read_brex(brex_content).copy().reset_index(drop=True)

    mav_frames = [read_maveric(file) for file in maveric_files]
    if not mav_frames:
        raise ReconciliationError("Debe cargar al menos un archivo Maveric")
    maveric = pd.concat(mav_frames, ignore_index=True)
    air_matches, used = _match_air(brex, maveric)
    fee_matches = _agent_fee_matches(brex, maveric, air_matches, used)

    rows: list[dict[str, object]] = []
    status_counter: Counter[str] = Counter()
    for bi, b in brex.iterrows():
        status = match_type = detail = ""
        count = 0
        authorization = reservations = provider = tickets = association = source_file = ""
        amount = float(b["_amount"])

        if amount < 0:
            status = match_type = "REFUND"
            detail = "Importe Brex negativo - no se concilia"
        elif bool(b["_is_fee"]):
            fm = fee_matches.get(bi)
            if fm:
                status = "OK"
                match_type = fm["type"]
                association = fm.get("association", "")
                count = int(fm.get("count", 1))
                if "chosen" in fm:
                    chosen = fm["chosen"]
                    authorization = chosen["auth"]
                    reservations = str(int(chosen["reservation"])) if pd.notna(chosen["reservation"]) else ""
                    provider = chosen["provider"]
                    tickets = chosen["ticket"]
                    source_file = chosen["source_file"]
                    detail = f"USD {amount:.2f} conciliado con {tickets}"
                else:
                    groups = fm["air_groups"]
                    records = [r for g in groups for r in g["records"]]
                    authorization = " | ".join(dict.fromkeys(str(g["auth"]) for g in groups))
                    reservations = " | ".join(str(int(r["reservation"])) for r in records if pd.notna(r.get("reservation")))
                    provider = " | ".join(dict.fromkeys(str(r["provider"]) for r in records))
                    tickets = " | ".join(str(r["ticket"]) for r in records)
                    source_file = " | ".join(dict.fromkeys(str(g["source_file"]) for g in groups))
                    detail = "Service fee identificado por el/los aéreo(s) CTC asociado(s)"
            else:
                status = "AGENT FEE"
                match_type = "AGENT FEE SIN MATCH"
                detail = "No se encontró asociación confiable"
        elif not bool(b["_is_air"]):
            status = match_type = "NO ES AÉREO"
            detail = "Categoría distinta de Airline expenses"
        elif bi in air_matches:
            gm = air_matches[bi]
            group = gm["group"]
            records = group["records"]
            status = "OK"
            match_type = gm["type"]
            count = len(records)
            authorization = group["auth"]
            reservations = " | ".join(str(int(r["reservation"])) for r in records if pd.notna(r.get("reservation")))
            provider = " | ".join(dict.fromkeys(str(r["provider"]) for r in records))
            tickets = " | ".join(str(r["ticket"]) for r in records)
            source_file = group["source_file"]
            detail = f"{' + '.join(str(r['ticket']) for r in records)} = USD {group['amount']:.2f}"
        else:
            status = match_type = "Con diferencia"
            detail = "No se encontró coincidencia disponible en el archivo Maveric cargado"

        status_counter[match_type] += 1
        rows.append({
            "Fecha Brex": b["_date"], "Horario Brex": b["_time"], "ID Brex": b["Id"],
            "Type": b["Type"], "User": b.get("User", ""),
            "Statement Descriptor": b["Statement Descriptor"], "Merchant Name": b["Merchant Name"],
            "Brex Category": b["Brex Category"], "Last 4": b["_last4"], "Corresponde a:": b["_owner"],
            "Importe Brex": amount, "Estado": status, "Tipo conciliación": match_type,
            "Detalle": detail, "Cantidad": count, "Autorización Maveric": authorization,
            "Reservas Maveric": reservations, "Proveedor Maveric": provider,
            "Boletos Maveric": tickets, "Service Fee asociado a movimiento Brex": association,
            "Archivo Maveric encontrado": source_file,
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter", datetime_format="dd/mm/yyyy") as writer:
        frame = pd.DataFrame(rows)

        # Mantener la separación original por empresa/cuenta en hojas distintas.
        # La separación es solamente visual: todas las filas ya fueron conciliadas
        # contra el único archivo Maveric cargado.
        sheet_groups = ["LEFITUR", "DANARSIN", "PARAGUAY"]
        for group_name in sheet_groups:
            group_frame = frame[frame["Corresponde a:"].map(owner_family).eq(group_name)].copy()
            group_frame.to_excel(writer, sheet_name=group_name, index=False)
            _style_output(writer, group_name, group_frame)

        unclassified = frame[~frame["Corresponde a:"].map(owner_family).isin(sheet_groups)].copy()
        if not unclassified.empty:
            unclassified.to_excel(writer, sheet_name="SIN CLASIFICAR", index=False)
            _style_output(writer, "SIN CLASIFICAR", unclassified)

        summary = pd.DataFrame(sorted(status_counter.items()), columns=["Estado / Tipo", "Cantidad"])
        summary.to_excel(writer, sheet_name="Resumen", index=False)
        _style_output(writer, "Resumen", summary)

        cards = pd.DataFrame(sorted(CARD_OWNERS.items()), columns=["Last 4","Grupo"])
        cards.to_excel(writer, sheet_name="Tarjetas", index=False)
        _style_output(writer, "Tarjetas", cards)

    return output.getvalue(), dict(status_counter)
