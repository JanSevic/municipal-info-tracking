"""Obecný parser úředních desek publikovaných jako otevřená data
podle OFN „Úřední desky“ (https://ofn.gov.cz/úřední-desky/2021-07-20/).

Použito pro Ústecký kraj a MěÚ Kralupy nad Vltavou; ve fázi 3 stejným
způsobem půjdou napojit desky obcí, které OFN publikují.
"""
from datetime import date, timedelta

from .. import net
from ..model import Doc, Record
from .util import iso_date


def _cs(v):
    if isinstance(v, dict):
        return v.get("cs") or next(iter(v.values()), "")
    return v or ""


def _date(v):
    if isinstance(v, dict):
        return iso_date(v.get("datum") or v.get("datum_a_čas") or "")
    return iso_date(v or "")


def make_fetch(src_id, url, backfill_days=45, timeout=60):
    def fetch(state):
        data = net.get(url, headers={"Accept": "application/ld+json, application/json"}, timeout=timeout).json()
        since = state.get("since") or (date.today() - timedelta(days=backfill_days)).isoformat()
        out = []
        for it in data.get("informace", []):
            published = _date(it.get("vyvěšení"))
            iri = it.get("iri") or it.get("url")
            if not iri:
                continue
            # starší položky, které jsme už zpracovali (nebo před začátkem sledování), přeskočíme
            if published and published < since and iri not in state.get("pending", ()):
                continue
            docs = []
            for d in it.get("dokument") or []:
                docs.append(Doc(_cs(d.get("název")), d.get("url") or ""))
            folder = _cs((it.get("složka") or {}).get("název")) if isinstance(it.get("složka"), dict) else ""
            agenda = ", ".join(_cs(a.get("název")) for a in it.get("agenda") or [] if isinstance(a, dict))
            category = it.get("zdroj") or folder or agenda
            popis = _cs(it.get("popis"))
            out.append(Record(
                id=f"{src_id}:{iri}", source=src_id,
                title=_cs(it.get("název")).replace("\\", '"'),
                url=it.get("url") or "",
                published=published,
                valid_to=_date(it.get("relevantní_do")),
                category=category,
                ref=it.get("číslo_jednací") or "",
                docs=docs,
                text=popis,
            ))
        return out
    return fetch


UST = {
    "id": "kraj_ust", "name": "Ústecký kraj – úřední deska", "group": "Kraje",
    "url": "https://www.kr-ustecky.cz/uredni-deska-prehled", "govradar": True,
}
fetch_ust = make_fetch("kraj_ust", "https://www.kr-ustecky.cz/opendata-uredni-deska", timeout=180)
