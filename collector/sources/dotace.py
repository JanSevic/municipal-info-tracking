"""Dotace pro obce – nové výzvy a programy SFŽP a MMR (národní dotace).

SFŽP: web běží na WordPressu, nové stránky v sekci „Dotace a půjčky“ čteme
přes jeho veřejné REST API.
MMR: v sekci Národní dotace sledujeme nové stránky programů a jejich výzev
(nový odkaz = nový záznam; při prvním spuštění se jen založí výchozí stav).
"""
import re
from datetime import date, timedelta
from html import unescape
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import net
from ..model import Record
from .util import iso_date, today

SFZP = {
    "id": "dotace_sfzp", "name": "SFŽP – dotační výzvy", "group": "Majetek a peníze",
    "url": "https://sfzp.gov.cz/dotace-a-pujcky/", "govradar": False,
}
MMR = {
    "id": "dotace_mmr", "name": "MMR – národní dotace", "group": "Majetek a peníze",
    "url": "https://mmr.gov.cz/cs/narodni-dotace", "govradar": False,
}


def _clean(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def fetch_sfzp(state):
    since = state.get("since") or (date.today() - timedelta(days=45)).isoformat()
    pages = net.get("https://sfzp.gov.cz/wp-json/wp/v2/pages", params={
        "orderby": "date", "order": "desc", "per_page": 50,
        "_fields": "id,date,modified,link,title,content",
    }).json()
    out = []
    for p in pages:
        if "/dotace-a-pujcky/" not in p.get("link", ""):
            continue
        published = iso_date(p.get("date"))
        if published < since:
            continue
        out.append(Record(
            id=f"dotace_sfzp:{p['id']}", source="dotace_sfzp",
            title=_clean(p["title"]["rendered"]), url=p["link"], published=published,
            category="SFŽP", ref=str(p["id"]),
            text=_clean(p.get("content", {}).get("rendered"))[:20000],
        ))
    return out


MMR_BASE = "https://mmr.gov.cz"


def _links(url, prefix):
    soup = BeautifulSoup(net.get(url).text, "html.parser")
    res = {}
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.lower().startswith(prefix.lower()) and h.rstrip("/").lower() != prefix.rstrip("/").lower() \
                and not h.lower().endswith("/archiv"):
            res.setdefault(h.split("?")[0], a.get_text(" ", strip=True))
    return res


def fetch_mmr(state):
    known = state.get("known", set())
    first_run = not known
    cats = _links(f"{MMR_BASE}/cs/narodni-dotace", "/cs/narodni-dotace/")
    found = {}
    for cat_url in cats:
        cat_page = urljoin(MMR_BASE, cat_url)
        slug = cat_url.rstrip("/").split("/")[-1]
        progs = _links(cat_page, f"/Narodni-dotace/{slug}/")
        for i, (prog_url, title) in enumerate(progs.items()):
            found[prog_url] = (title, cats[cat_url])
            if i < 4:  # výzvy jen u nejnovějších programů (nahoře v seznamu)
                for sub_url, sub_title in _links(urljoin(MMR_BASE, prog_url), prog_url + "/").items():
                    found[sub_url] = (f"{title} – {sub_title}", cats[cat_url])
                net.polite_pause(0.3)
    out = []
    for url, (title, cat) in found.items():
        out.append(Record(
            id=f"dotace_mmr:{url.lower()}", source="dotace_mmr", title=title,
            url=urljoin(MMR_BASE, url), published=today(), category=cat,
        ))
    if first_run:
        for r in out:
            r.published = ""  # výchozí stav – nejsou to novinky
    return out
