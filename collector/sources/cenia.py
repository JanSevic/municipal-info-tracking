"""CENIA – Informační systém EIA (záměry) a SEA (koncepce).

Záměr se v seznamu objeví znovu při každé změně stavu. Jako nový záznam
bereme kombinaci kód + stav + den změny; do textu stahujeme jen přílohy
přidané v den poslední změny (celé dokumentace v ZIP nestahujeme).
"""
import re
from datetime import date, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import net
from ..matching import obce
from ..model import Doc, Record
from .util import cz_date, java_date

BASE = "https://portal.cenia.cz"


def _list_page(view, page):
    html = net.get(f"{BASE}/eiasea/view/{view}", params={"p": page, "lang": "cs"}).text
    soup = BeautifulSoup(html, "html.parser")
    tbl = soup.find("table", class_="view")
    items = []
    if not tbl:
        return items
    for a in tbl.find_all("a", href=re.compile(r"/eiasea/detail/")):
        block = a.find_parent("tr")
        fields = {}
        row = block
        for _ in range(3):  # pod řádkem s názvem následují řádky „štítek: hodnota“
            row = row.find_next_sibling("tr")
            if row is None:
                break
            tds = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            for i, t in enumerate(tds[:-1]):
                if t.endswith(":"):
                    fields[t[:-1]] = tds[i + 1]
        items.append({
            "code": block.find("td").get_text(strip=True),
            "name": a.get_text(" ", strip=True), "href": urljoin(BASE, a["href"]),
            "changed": java_date(fields.get("Změněno", "")),
            "state": fields.get("Stav", ""),
            "office": fields.get("Příslušný úřad", ""),
        })
    return items


def _detail(url, changed):
    soup = BeautifulSoup(net.get(url).text, "html.parser")
    by_name_okres = {(o["nazev"], o["okres"]): o["kod"] for o in obce()}
    kody = []
    for tbl in soup.find_all("table", class_="umisteni"):
        for tr in tbl.find_all("tr")[1:]:
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) >= 3 and (tds[2], tds[1]) in by_name_okres:
                kody.append(by_name_okres[(tds[2], tds[1])])
    places = soup.find_all("table", class_="umisteni")
    place_txt = " ; ".join(t.get_text(" ", strip=True) for t in places)
    docs = []
    for a in soup.find_all("a", class_="entity_field"):
        tail = a.next_sibling or ""
        d = cz_date(str(tail))
        if d and changed and d >= changed:
            docs.append(Doc(a.get_text(strip=True), urljoin(BASE, a["href"])))
    return sorted(set(kody)), place_txt, docs


def make_fetch(view, src_id, kind):
    def fetch(state):
        since = state.get("since") or (date.today() - timedelta(days=30)).isoformat()
        out = []
        for page in range(1, 40):
            items = _list_page(view, page)
            if not items:
                break
            for it in items:
                if it["changed"] and it["changed"] < since:
                    return out
                rid = f"{src_id}:{it['code']}:{it['state']}:{it['changed']}"
                if rid in state.get("known", ()):
                    continue
                kody, place_txt, docs = _detail(it["href"], it["changed"])
                out.append(Record(
                    id=rid, source=src_id,
                    title=f"{it['name']} – {it['state']}",
                    url=it["href"], published=it["changed"], category=it["state"],
                    ref=it["code"], docs=docs, obce_struct=kody,
                    text=f"{kind} {it['code']}: {it['name']}\nStav: {it['state']}\n"
                         f"Příslušný úřad: {it['office']}\nUmístění: {place_txt}",
                ))
                net.polite_pause(0.3)
        return out
    return fetch


EIA = {
    "id": "cenia_eia", "name": "CENIA – EIA záměry", "group": "Stavby a záměry",
    "url": f"{BASE}/eiasea/view/eia100_cr?lang=cs", "govradar": True,
}
SEA = {
    "id": "cenia_sea", "name": "CENIA – SEA koncepce", "group": "Stavby a záměry",
    "url": f"{BASE}/eiasea/view/sea100_koncepce?lang=cs", "govradar": False,
}
fetch_eia = make_fetch("eia100_cr", "cenia_eia", "Záměr EIA")
fetch_sea = make_fetch("sea100_koncepce", "cenia_sea", "Koncepce SEA")
