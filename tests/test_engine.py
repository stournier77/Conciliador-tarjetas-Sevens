from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from engine import PREFIX_COMPANY, _last4, infer_maveric_group


def test_last4():
    assert _last4("+CC1:5495610076204210") == "4210"


def test_group_detection():
    assert infer_maveric_group("Maveric Lefitur.xls") == "LEFITUR"
    assert infer_maveric_group("Maveric Danarsin.xls") == "DANARSIN"


def test_easyjet_prefix():
    assert PREFIX_COMPANY["888"] == "EASYJET"
