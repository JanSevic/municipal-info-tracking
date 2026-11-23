"""Registr sledovaných zdrojů.

status:
  "ok"         – sbírá se automaticky
  "blokovano"  – web blokuje servery mimo ČR (GitHub Actions); viz README
  "pripravuje" – parser se připravuje
"""
from . import cenia, desu, dotace, kralupy, ofn, sz_zakazky, uzsvm

SOURCES = [
    # --- zdroje GovRadaru (PDF) ---
    {**desu.SOURCE, "fetch": desu.fetch, "status": "ok"},
    {**cenia.EIA, "fetch": cenia.fetch_eia, "status": "ok"},
    {"id": "kraj_stc", "name": "Středočeský kraj – úřední deska", "group": "Kraje",
     "url": "https://stredoceskykraj.cz/web/urad/uredni-deska", "govradar": True,
     "fetch": None, "status": "blokovano"},
    {**ofn.UST, "fetch": ofn.fetch_ust, "status": "ok"},
    {**sz_zakazky.SOURCE, "fetch": sz_zakazky.fetch, "status": "ok"},
    # --- zdroje zmíněné v e-mailu GovRadaru, schválené navíc ---
    {"id": "rsd", "name": "ŘSD – úřední deska", "group": "Stavby a záměry",
     "url": "https://www.rsd.cz/uredni-deska", "govradar": False, "fetch": None, "status": "blokovano"},
    {"id": "sz_deska", "name": "Správa železnic – úřední deska", "group": "Stavby a záměry",
     "url": "https://www.spravazeleznic.cz/o-nas/uredni-deska", "govradar": False,
     "fetch": None, "status": "pripravuje"},
    {"id": "md", "name": "Ministerstvo dopravy – úřední deska", "group": "Stavby a záměry",
     "url": "https://md.gov.cz/O-nas/Uredni-deska", "govradar": False, "fetch": None, "status": "pripravuje"},
    {**cenia.SEA, "fetch": cenia.fetch_sea, "status": "ok"},
    # --- místní, pozemky, peníze ---
    {**kralupy.SOURCE, "fetch": kralupy.fetch, "status": "ok"},
    {"id": "spu", "name": "Státní pozemkový úřad – úřední deska", "group": "Místní úřady",
     "url": "https://spu.gov.cz/", "govradar": False, "fetch": None, "status": "pripravuje"},
    {**dotace.SFZP, "fetch": dotace.fetch_sfzp, "status": "ok"},
    {**dotace.MMR, "fetch": dotace.fetch_mmr, "status": "ok"},
    {**uzsvm.SOURCE, "fetch": uzsvm.fetch, "status": "ok"},
]

BY_ID = {s["id"]: s for s in SOURCES}
