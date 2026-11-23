"""Dopravní a energetický stavební úřad (DESÚ) – eDeska."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import net
from ..model import Doc, Record
from .util import cz_date

BASE = "https://espis.desu.gov.cz/eDeska/"
SOURCE = {
    "id": "desu",
    "name": "DESÚ – úřední deska",
    "group": "Stavby a záměry",
    "url": BASE + "eDeskaAktualni.jsp",
    "govradar": True,
}


def fetch(state):
    out, first = [], 0
    while True:
        html = net.post(BASE + "eDeskaAktualni.jsp", data={
            "order": "vyveseno", "desc": "true", "first": str(first), "count": "100",
            "oblast": "", "kategorie": "", "nazev": "",
        }).text
        soup = BeautifulSoup(html, "html.parser")
        rows = [a.find_parent("tr") for a in soup.select("a.detail")]
        for tr in rows:
            cells = {(" ".join(td.get("class") or [])): td for td in tr.find_all("td", recursive=False)}
            a = tr.select_one("a.detail")
            detail_id = a["href"].split("detailId=")[-1]
            dates = [td.get_text(strip=True) for td in tr.select("td.edeska-sloupec-zverejnit")]
            docs = [Doc(d.get_text(" ", strip=True).split(" (")[0], urljoin(BASE, d["href"]))
                    for d in tr.select("a.download")]
            kat = cells.get("content edeska-sloupec-kategorie")
            zn = cells.get("content edeska-sloupec-znacka")
            out.append(Record(
                id=f"desu:{detail_id}", source="desu",
                title=a.get_text(" ", strip=True),
                url=urljoin(BASE, a["href"]),
                published=cz_date(dates[0]) if dates else "",
                valid_to=cz_date(dates[1]) if len(dates) > 1 else "",
                category=kat.get_text(" ", strip=True) if kat else "",
                ref=zn.get_text(" ", strip=True) if zn else "",
                docs=docs,
            ))
        if len(rows) < 100 or first > 2000:
            return out
        first += 100
