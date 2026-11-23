"""Obecní hlídače webů bez strukturovaných dat (typicky dotační výzvy).

make_links: seznam výzev – každý nový odkaz odpovídající vzoru (URL, případně
            i názvu odkazu) = nový záznam; text se doplní z detailu výzvy.

Při prvním spuštění se aktuální nabídka uloží s dnešním datem a kategorií
„vyhlášeno před začátkem sledování“ (e-mailem se nepošle).
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import net
from ..model import Record
from .util import today

FIRST_RUN_CAT = "vyhlášeno před začátkem sledování"


def _soup(url):
    r = net.get(url)
    return BeautifulSoup(r.text, "html.parser"), r.url


def _main_text(soup):
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.find(id=re.compile("content|obsah", re.I)) or soup.body or soup
    return re.sub(r"\s+", " ", main.get_text(" ", strip=True))[:20000]


def make_links(src_id, list_urls, pattern, category="", detail=True, skip_titles=(), title_pattern=None):
    rx = re.compile(pattern)
    trx = re.compile(title_pattern) if title_pattern else None
    if isinstance(list_urls, str):
        list_urls = [list_urls]

    def fetch(state):
        known = state.get("known", set())
        first_run = not known
        found = {}
        for lu in list_urls:
            soup, base = _soup(lu)
            for a in soup.find_all("a", href=True):
                h = urljoin(base, a["href"]).split("#")[0]
                title = a.get_text(" ", strip=True)
                if rx.search(h) and title and title not in skip_titles and (not trx or trx.search(title)):
                    if h not in found or len(title) > len(found[h]):
                        found[h] = title
        out = []
        for url, title in found.items():
            rid = f"{src_id}:{url}"
            if rid in known:
                continue
            text = ""
            if detail:
                try:
                    d, _ = _soup(url)
                    h1 = d.find("h1")
                    if h1 and len(h1.get_text(strip=True)) > 8:
                        title = h1.get_text(" ", strip=True)
                    text = _main_text(d)
                except Exception:  # noqa: BLE001 – detail je jen doplněk
                    pass
                net.polite_pause(0.3)
            out.append(Record(
                id=rid, source=src_id, title=title[:300], url=url, published=today(),
                category=FIRST_RUN_CAT if first_run else category, text=text,
            ))
        return out
    return fetch
