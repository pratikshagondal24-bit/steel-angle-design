"""Unequal-angle catalogue transcribed from SP 6 (Part 1):1964, Table IV.

Areas are converted from cm² to mm². This historical catalogue is used only
for section lookup in the student prototype; verify section dimensions against
the applicable current product standard and supplier data before design.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AngleSection:
    designation: str
    long_leg_mm: float
    short_leg_mm: float
    thickness_mm: float
    gross_area_mm2: float
    table_page: int


# Table III (equal angles, printed pages 8 and 10) and Table IV (unequal
# angles, printed pages 12 and 14). Areas are the steel-book values.
_EQUAL_ROWS = {
    20: {3: 112, 4: 145},
    25: {3: 141, 4: 184, 5: 225},
    30: {3: 173, 4: 226, 5: 277},
    35: {3: 203, 4: 266, 5: 327, 6: 386},
    40: {3: 234, 4: 307, 5: 378, 6: 447},
    45: {3: 264, 4: 347, 5: 428, 6: 507},
    50: {3: 295, 4: 388, 5: 479, 6: 568},
    55: {5: 527, 6: 626, 8: 818, 10: 1002},
    60: {5: 575, 6: 684, 8: 896, 10: 1100},
    65: {5: 625, 6: 744, 8: 976, 10: 1200},
    70: {5: 677, 6: 806, 8: 1058, 10: 1302},
    75: {5: 727, 6: 866, 8: 1138, 10: 1402},
    80: {6: 929, 8: 1221, 10: 1505, 12: 1781},
    90: {6: 1047, 8: 1379, 10: 1703, 12: 2019},
    100: {6: 1167, 8: 1539, 10: 1903, 12: 2259},
    110: {8: 1702, 10: 2106, 12: 2502, 15: 3081},
    130: {8: 2022, 10: 2506, 12: 2982, 15: 3681},
    150: {10: 2903, 12: 3459, 15: 4278, 18: 5079},
    200: {12: 4661, 15: 5780, 18: 6881, 25: 9380},
}

_ROWS = {
    (30, 20): {3: 141, 4: 184, 5: 225},
    (40, 25): {3: 188, 4: 246, 5: 302, 6: 356},
    (45, 30): {3: 218, 4: 286, 5: 352, 6: 416},
    (50, 30): {3: 234, 4: 307, 5: 378, 6: 447},
    (60, 40): {5: 476, 6: 565, 8: 737},
    (65, 45): {5: 526, 6: 625, 8: 817},
    (70, 45): {5: 552, 6: 656, 8: 858, 10: 1052},
    (75, 50): {5: 602, 6: 716, 8: 938, 10: 1152},
    (80, 50): {5: 627, 6: 746, 8: 978, 10: 1202},
    (90, 60): {6: 865, 8: 1137, 10: 1401, 12: 1657},
    (100, 65): {6: 955, 8: 1257, 10: 1551},
    (100, 75): {6: 1014, 8: 1336, 10: 1650, 12: 1956},
    (125, 75): {6: 1166, 8: 1538, 10: 1902},
    (125, 95): {6: 1286, 8: 1698, 10: 2102, 12: 2498},
    (150, 75): {8: 1742, 10: 2156, 12: 2562},
    (150, 115): {8: 2058, 10: 2552, 12: 3038, 15: 3752},
    (200, 100): {10: 2903, 12: 3459, 15: 4278},
    (200, 150): {10: 3400, 12: 4056, 15: 5025, 18: 5976},
}

CATALOG: dict[str, AngleSection] = {}
for leg, thicknesses in _EQUAL_ROWS.items():
    for thickness, area in thicknesses.items():
        name = f"ISA {leg}x{leg}x{thickness}"
        CATALOG[name] = AngleSection(name, leg, leg, thickness, area, 8 if leg <= 65 else 10)
for (long_leg, short_leg), thicknesses in _ROWS.items():
    for thickness, area in thicknesses.items():
        name = f"ISA {long_leg}x{short_leg}x{thickness}"
        CATALOG[name] = AngleSection(name, long_leg, short_leg, thickness, area, 12 if long_leg < 90 else 14)


def normalize_designation(value: str) -> str:
    """Accept common spacing and multiplication-sign variations."""
    digits = re.findall(r"\d+(?:\.\d+)?", (value or "").replace("×", "x"))
    if len(digits) != 3:
        return ""
    return "ISA " + "x".join(str(int(float(number))) for number in digits)


def find_angle(value: str) -> AngleSection | None:
    parts = parse_angle(value)
    return parts[0] if parts else None


def parse_angle(value: str) -> tuple[AngleSection, int] | None:
    """Parse a single/double angle designation such as '2 ISA 55x55x10'."""
    text = (value or "").strip().upper().replace("×", "X")
    count = 1
    if text.startswith("2"):
        count = 2
        text = text[1:].strip()
    section = CATALOG.get(normalize_designation(text))
    return (section, count) if section else None
