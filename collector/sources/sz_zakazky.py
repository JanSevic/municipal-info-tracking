"""Správa železnic – veřejné zakázky (profil zadavatele E-ZAK, XML export
podle vyhlášky o profilu zadavatele).

Nový záznam = zakázka, kterou jsme ještě neviděli. Zadávací dokumentace
(často stovky MB) nestahujeme – hledá se v názvu a předmětu zakázky.
"""
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from .. import net
from ..model import Record
from .util import iso_date

BASE = "https://zakazky.spravazeleznic.cz"
NS = "{urn:cz:isvz:mmr:schemas:vz-z-profilu-zadavatele:v100}"
SOURCE = {
    "id": "sz_zakazky", "name": "Správa železnic – veřejné zakázky", "group": "Stavby a záměry",
    "url": BASE + "/contract_index.html?type=all&state=all", "govradar": True,
}


def _t(el, tag):
    x = el.find(NS + tag)
    return (x.text or "").strip() if x is not None and x.text else ""


def fetch(state):
    since = state.get("since") or (date.today() - timedelta(days=14)).isoformat()
    od = date.fromisoformat(since) - timedelta(days=1)
    do = date.today()
    xml = net.get(f"{BASE}/XMLdataVZ", params={"od": od.strftime("%d%m%Y"), "do": do.strftime("%d%m%Y")},
                  timeout=120).content
    root = ET.fromstring(xml)
    out = []
    for z in root.findall(NS + "zakazka"):
        vz = _t(z, "id_objektu")                      # VZ-16975
        num = vz.split("-")[-1]
        dates = sorted(iso_date(e.text or "") for e in z.iter(NS + "datum_uverejneni") if e.text)
        dates += sorted(iso_date(e.text or "") for e in z.iter(NS + "cas_vlozeni_na_profil") if e.text)
        published = min(d for d in dates if d) if any(dates) else do.isoformat()
        stav = next((e.text for e in z.iter(NS + "stav_zadavaciho_postupu") if e.text), "")
        parts = [_t(c, "nazev_casti_vz") + ": " + _t(c, "predmet_casti_vz") for c in z.iter(NS + "cast_zakazky")]
        out.append(Record(
            id=f"sz_zakazky:{vz}", source="sz_zakazky",
            title=_t(z, "nazev_vz"),
            url=f"{BASE}/contract_display_{num}.html",
            published=published,
            category=" / ".join(x for x in (_t(z, "rezim_vz"), _t(z, "druh_vz"), stav) if x),
            ref=vz,
            text=_t(z, "predmet_vz") + "\n" + "\n".join(parts),
        ))
    return out
