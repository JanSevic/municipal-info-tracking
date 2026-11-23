"""MěÚ Kralupy nad Vltavou (ORP pro Dřínov) – úřední deska vč. stavebního úřadu.

Otevřená data města neobsahují odkazy na přílohy, proto čteme webovou desku
(seznam + detail nových dokumentů s přílohami).
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import net
from ..model import Doc, Record
from .util import cz_date

BASE = "https://www.mestokralupy.cz"
SOURCE = {
    "id": "kralupy", "name": "MěÚ Kralupy n. Vlt. (ORP, stavební úřad)", "group": "Místní úřady",
    "url": BASE + "/mestsky-urad/uredni-deska/", "govradar": False,
}


def _field(text, label):
    m = re.search(re.escape(label) + r":\s*\|\s*([^|]+)", text)
    return m.group(1).strip() if m else ""


def fetch(state):
    soup = BeautifulSoup(net.get(SOURCE["url"]).text, "html.parser")
    out = []
    for a in soup.select("div.eud-document-title a[href]"):
        doc_id = a["href"].rstrip("/").split("/")[-1]
        rid = f"kralupy:{doc_id}"
        if rid in state.get("known", ()):
            continue
        url = urljoin(BASE, a["href"])
        d = BeautifulSoup(net.get(url).text, "html.parser")
        t = d.get_text(" | ", strip=True)
        t = t[t.find("Detail vyvěšeného dokumentu"):]
        docs = [Doc(x.get_text(" ", strip=True), urljoin(BASE, x["href"]))
                for x in d.find_all("a", href=re.compile(r"/files/eud/"))]
        out.append(Record(
            id=rid, source="kralupy", title=a.get_text(" ", strip=True), url=url,
            published=cz_date(_field(t, "Vyvěšeno dne")),
            valid_to=cz_date(_field(t, "Bude sejmuto dne")),
            category=" / ".join(x for x in (_field(t, "Vyvěsil"), _field(t, "Kategorie")) if x),
            ref=_field(t, "Číslo jednací"), docs=docs,
        ))
        net.polite_pause(0.3)
    return out
