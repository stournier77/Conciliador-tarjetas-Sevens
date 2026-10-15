from __future__ import annotations

CARD_OWNERS: dict[str, str] = {}


def _assign(cards: list[int], owner: str) -> None:
    for card in cards:
        CARD_OWNERS[str(card).zfill(4)] = owner


# LEFITUR - tarjetas generales
_assign([
    152,273,377,679,795,1032,1224,1377,1591,1813,1822,1981,2137,2238,
    2473,2499,2596,2717,2749,2813,2908,3278,3485,3629,3926,3962,4151,
    4210,4609,4677,4874,4917,5136,5205,5786,5856,5940,5976,5990,6226,
    7062,7126,7295,7308,7486,7782,8146,8289,8708,8720,9388,9521,9591,
    9686,9731,
], "LEFITUR")

# LEFITUR - subgrupos / usos
_assign([485,509,1977,2989,3591,3790,4102,4606,5072,5255,7631,7748,8379,9880], "LEFITUR LOZADA")
_assign([7893], "LEFITUR BN USO SEVENS")
_assign([5996], "LEFITUR CTC")
_assign([252,4559], "LEFITUR ANDAMOS USO PROPIO")
_assign([9236], "LEFITUR TRAVELLER USO PROPIO")
_assign([3209], "LEFITUR TRAVELLER USO SEVENS")

# DANARSIN
_assign([646,856,1112,2106,2640,4154,6770,6985,7214,7764,7927,8110,9307,9605,9742], "DANARSIN LOZADA")
_assign([2807,3082,3316,4450], "DANARSIN")
_assign([61], "DANARSIN TUCANO")

# PARAGUAY
_assign([2151,5682,7261], "PARAGUAY")


def owner_family(owner: str) -> str:
    upper = (owner or "").upper()
    if upper.startswith("LEFITUR"):
        return "LEFITUR"
    if upper.startswith("DANARSIN"):
        return "DANARSIN"
    if upper.startswith("PARAGUAY"):
        return "PARAGUAY"
    return "OTROS"
