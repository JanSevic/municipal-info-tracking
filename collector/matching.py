"""Rozpoznávání obcí v textu a vyhodnocení filtrů.

Stejná pravidla implementuje web (web/app.js), aby filtr na webu a v e-mailu
vracel totéž:
  * klíčové slovo musí začínat na začátku slova (stejně jako GovRadar:
    "transevropsk" najde "transevropské"). Slovo psané malými písmeny se
    hledá bez ohledu na velikost písmen; obsahuje-li velké písmeno (zkratky
    VRT, ZÚR, D8), rozlišuje se velikost. Krátké zkratky (do 4 znaků) se
    hledají jen jako celé slovo – "VRT" nenajde "vrtaček", "D8" nenajde "D80".
  * obec: název s velkým počátečním písmenem; u jednoslovných názvů s
    kmenem >= 4 znaky se toleruje skloňování (Dřínov, Dřínově, Dřínovem).
"""
import json
import pathlib
import re
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
VOWELS = "aeiouyáéíóúůýě"
WORD = re.compile(r"[\w-]+", re.UNICODE)


@lru_cache(maxsize=1)
def obce():
    return json.loads((ROOT / "config" / "obce.json").read_text("utf-8"))


def _stem(word: str) -> str:
    w = word
    if w[-1].lower() in VOWELS:
        w = w[:-1]
    if w.endswith("ec") and len(w) > 4:   # Kostelec -> Kostelc(e), Sedlec -> Sedlc(i)
        w = w[:-2] + "c"
    return w


@lru_cache(maxsize=1)
def _index():
    """stem prvního slova -> [(regex, [kódy])]"""
    by_name = {}
    for o in obce():
        by_name.setdefault(o["nazev"], []).append(o["kod"])
    idx = {}
    for name, kody in by_name.items():
        words = name.split(" ")
        first = words[0]
        if "-" in first or len(_stem(first)) < 4:
            pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
            stems = {first}
        else:
            stems = set()
            st = _stem(first)
            alt = {re.escape(first), re.escape(st) + r"\w{0,3}"}
            if first.endswith("ves"):           # Nelahozeves -> Nelahozevsi
                alt.add(re.escape(first[:-3]) + r"vs\w{0,2}")
                stems.add(first[:-3] + "vs")
            if first.endswith("ec") and len(first) > 5:
                alt.add(re.escape(first[:-2]) + r"c\w{0,3}")
            rest = "".join(r"\s+" + re.escape(w) for w in words[1:])
            pattern = r"(?<!\w)(?:" + "|".join(sorted(alt)) + r")" + rest + r"(?!\w)"
            stems |= {st, first}
        rx = re.compile(pattern)
        for s in stems:
            idx.setdefault(s, []).append((rx, kody))
    return idx


def find_obce(text: str) -> list[int]:
    """Kódy obcí zmíněných v textu."""
    if not text:
        return []
    idx = _index()
    candidates = []
    seen_tokens = set()
    for m in WORD.finditer(text):
        tok = m.group(0)
        if not tok[:1].isupper() or tok in seen_tokens:
            continue
        seen_tokens.add(tok)
        for cut in range(0, 4):
            if cut and len(tok) - cut < 4:
                break
            key = tok[:len(tok) - cut] if cut else tok
            if key in idx:
                candidates.extend(idx[key])
    found = set()
    checked = set()
    for rx, kody in candidates:
        if rx.pattern in checked:
            continue
        checked.add(rx.pattern)
        if rx.search(text):
            found.update(kody)
    return sorted(found)


@lru_cache(maxsize=4096)
def _kw_rx(kw: str):
    kw = kw.strip()
    case_sensitive = kw != kw.lower()
    whole = case_sensitive and len(kw) <= 4
    pattern = r"(?<!\w)" + re.escape(kw) + (r"(?!\w)" if whole else "")
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


def find_keywords(text: str, keywords) -> list[str]:
    return [k for k in keywords if k.strip() and _kw_rx(k).search(text or "")]


def matches(filter_: dict, rec_index: dict, text: str) -> bool:
    """Vyhodnotí filtr nad záznamem.

    filter_ = {"sources": [..] | None, "obce": [kód..], "keywords": [..],
               "topics": [{"keywords": [..], "sources": [..]}],
               "mode": "or" | "and"}

    keywords platí ve všech zdrojích, topics jen ve svých zdrojích
    (např. ZÚR jen na deskách krajů). Obojí se počítá jako „klíčové slovo“.
    """
    srcs = filter_.get("sources")
    if srcs and rec_index["source"] not in srcs:
        return False
    obce_f = set(filter_.get("obce") or [])
    kws = list(filter_.get("keywords") or [])
    topics = filter_.get("topics") or []
    if not obce_f and not kws and not topics:
        return True
    for t in topics:
        if rec_index["source"] in (t.get("sources") or []):
            kws += t.get("keywords") or []
    hit_obec = bool(obce_f & set(rec_index.get("obce") or []))
    hay = rec_index["title"] + "\n" + rec_index.get("category", "") + "\n" + (text or "")
    hit_kw = bool(find_keywords(hay, kws)) if kws else False
    has_kw_side = bool(filter_.get("keywords") or topics)
    if filter_.get("mode") == "and" and obce_f and has_kw_side:
        return hit_obec and hit_kw
    return hit_obec or hit_kw
