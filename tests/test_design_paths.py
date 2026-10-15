import io
from datetime import date, datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from paths import output_destination
from engine import MavericFile, reconcile
import pandas as pd


def fixture_bytes():
    brex = pd.DataFrame([{"Swipe Time (UTC)": "2026-10-01T12:00:00Z", "Amount": 123.45, "Statement Descriptor": "IBERIA", "Merchant Name": "IBERIA", "Brex Category": "Airline expenses", "Type": "TRANSACTION", "Last 4": "4210", "Id": "PRUEBA-DISENO"}])
    maveric = pd.DataFrame([[datetime(2026, 10, 1), "075-1234567890", None, None, None, "PASAJERO DE PRUEBA", "+CC1:5495610076204210/ABC123", 123.45, None, 12345]])
    b, m = io.BytesIO(), io.BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w:
        brex.to_excel(w, sheet_name="Transactions", index=False)
    maveric.to_excel(m, index=False, header=False, engine="openpyxl")
    return b.getvalue(), m.getvalue()


class DesignPathsTests(unittest.TestCase):
    def test_dated_paths_and_unique_runs(self):
        with tempfile.TemporaryDirectory() as d, patch("paths.documents_folder", return_value=Path(d)):
            now = datetime(2026, 10, 15, 10, 20, 30, 123456)
            folder, name = output_destination(date(2026, 10, 1), date(2026, 10, 14), now)
            self.assertEqual(folder, Path(d) / "Conciliador Tarjetas/Archivos conciliados/Brex/2026-10-15")
            self.assertIn("2026-10-01_al_2026-10-14", name)
            self.assertNotEqual(name, output_destination(date(2026, 10, 1), date(2026, 10, 14), now.replace(microsecond=123457))[1])
            folder.mkdir(parents=True)
            (folder / name).write_bytes(b"old")
            self.assertEqual((folder / name).read_bytes(), b"old")

    def test_reconciliation_still_matches_and_separates_accounts(self):
        brex, mav = fixture_bytes()
        result, stats = reconcile(brex, [MavericFile("Maveric Lefitur.xlsx", mav, "LEFITUR")])
        sheets = pd.read_excel(io.BytesIO(result), sheet_name=None)
        self.assertTrue({"LEFITUR", "DANARSIN", "PARAGUAY", "Resumen", "Tarjetas"}.issubset(sheets))
        self.assertEqual(sheets["LEFITUR"].iloc[0]["Estado"], "OK")
        self.assertEqual(sheets["LEFITUR"].iloc[0]["Importe Brex"], 123.45)
        self.assertEqual(sum(stats.values()), 1)

    def test_full_interface_generates_file_in_new_folder(self):
        from streamlit.testing.v1 import AppTest
        b, m = fixture_bytes()
        brex, mav = io.BytesIO(b), io.BytesIO(m)
        brex.name = "Brex_PRUEBA.xlsx"
        mav.name = "Maveric_Lefitur_PRUEBA.xlsx"
        with tempfile.TemporaryDirectory() as d, patch("paths.documents_folder", return_value=Path(d)), patch("authorized_devices.authorization", return_value=(True, "TEST", {"name":"Equipo de prueba","role":"user"})), patch("streamlit.file_uploader", side_effect=lambda label, **kw: brex if kw.get("key") == "archivo_brex" else mav):
            app = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=15).run()
            button = next(b for b in app.button if b.label == "GENERAR CONCILIACIÓN")
            self.assertFalse(button.disabled)
            button.click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            outputs = list(Path(d).rglob("*.xlsx"))
            self.assertEqual(len(outputs), 1)
            self.assertIn("Archivos conciliados/Brex", outputs[0].as_posix())
            self.assertEqual(pd.read_excel(outputs[0], sheet_name="LEFITUR").iloc[0]["Estado"], "OK")

    def test_interface_loads_with_required_controls(self):
        from streamlit.testing.v1 import AppTest
        with patch("authorized_devices.authorization", return_value=(True, "TEST", {"name":"Equipo de prueba","role":"user"})):
            app = AppTest.from_file(str(ROOT / "app/main.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        self.assertTrue(next(b for b in app.button if b.label == "GENERAR CONCILIACIÓN").disabled)
        self.assertEqual([b.label for b in app.sidebar.button], ["Abrir carpeta de conciliaciones", "Cerrar aplicación"])

if __name__ == "__main__":
    unittest.main()
