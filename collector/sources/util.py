import re
from datetime import datetime

MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
          "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def cz_date(s: str) -> str:
    """'22.11.2026' / '22. 11. 2026' -> '2026-11-22'"""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    if not m:
        return ""
    d, mo, y = map(int, m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"


def java_date(s: str) -> str:
    """'Mon Nov 23 12:49:27 CET 2026' nebo '23.11.2026 12:49' -> '2026-11-23'"""
    if re.search(r"\d{1,2}\.\s*\d{1,2}\.\s*\d{4}", s or ""):
        return cz_date(s)
    m = re.search(r"\w{3} (\w{3}) (\d{1,2}) [\d:]+ \w+ (\d{4})", s or "")
    if not m:
        return ""
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"


def iso_date(s: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s or "")
    return m.group(1) if m else ""


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")
