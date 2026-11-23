"""Registr sledovaných zdrojů.

status:
  "ok"         – sbírá se automaticky
  "blokovano"  – web blokuje servery mimo ČR (GitHub Actions); viz README
  "pripravuje" – parser se připravuje
"""
from . import cenia, desu, dotace, kralupy, ofn, sz_zakazky, uzsvm, watch

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
    # --- dotace pro obce ---
    {"id": "dotace_opzp", "name": "OPŽP – výzvy (odpady, voda, energie)", "group": "Dotace",
     "url": "https://opzp.cz/nabidka-dotaci/", "govradar": False, "status": "ok",
     "fetch": watch.make_links("dotace_opzp", "https://opzp.cz/nabidka-dotaci/", r"opzp\.cz/dotace/\d+-vyzva", "OPŽP")},
    {"id": "dotace_npzp", "name": "Národní program Životní prostředí – výzvy", "group": "Dotace",
     "url": "https://www.narodniprogramzp.cz/nabidka-dotaci/", "govradar": False, "status": "ok",
     "fetch": watch.make_links("dotace_npzp", "https://www.narodniprogramzp.cz/nabidka-dotaci/",
                               r"detail-vyzvy/\?id=\d+", "NPŽP")},
    {"id": "dotace_irop", "name": "IROP – výzvy", "group": "Dotace",
     "url": "https://irop.gov.cz/cs/vyzvy-2021-2027", "govradar": False, "status": "ok",
     "fetch": watch.make_links("dotace_irop", "https://irop.gov.cz/cs/vyzvy-2021-2027",
                               r"/Vyzvy-2021-2027/Vyzvy/.+", "IROP")},
    {"id": "dotace_nsa", "name": "Národní sportovní agentura – výzvy", "group": "Dotace",
     "url": "https://nsa.gov.cz/dotace-investicni/", "govradar": False, "status": "ok",
     "fetch": watch.make_links("dotace_nsa", ["https://nsa.gov.cz/dotace-investicni/", "https://nsa.gov.cz/dotace-neinvesticni/"],
                               r"nsa\.gov\.cz/dotace/.*vyzva", "NSA")},
    {"id": "dotace_hzs", "name": "MV/HZS – dotace pro jednotky hasičů obcí", "group": "Dotace",
     "url": "https://hzscr.gov.cz/dotace", "govradar": False, "status": "ok",
     "fetch": watch.make_links("dotace_hzs", ["https://hzscr.gov.cz/ucelove-investicni-dotace",
                                              "https://hzscr.gov.cz/neinvesticni-dotace-2"],
                               r"hzscr\.gov\.cz/", "HZS ČR", title_pattern=r"^Výzv")},
    {"id": "dotace_szif", "name": "SZIF – zemědělské a venkovské dotace", "group": "Dotace",
     "url": "https://szif.gov.cz/cs", "govradar": False, "fetch": None, "status": "pripravuje"},
    {"id": "dotace_sfdi", "name": "SFDI – chodníky, cyklostezky, bezpečnost", "group": "Dotace",
     "url": "https://sfdi.gov.cz/", "govradar": False, "fetch": None, "status": "pripravuje"},
]

BY_ID = {s["id"]: s for s in SOURCES}
