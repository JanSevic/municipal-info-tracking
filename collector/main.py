"""Jeden běh sběru: stáhne zdroje, uloží nové záznamy, zařadí je do odběrů
a rozešle splatné e-maily.

  python -m collector.main --data ./data [--only desu,cenia_eia] [--no-email]
"""
import argparse
import json
import logging
import pathlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import matching, notify, textextract
from .sources import SOURCES
from .store import Store

log = logging.getLogger("collector")
ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Prague")
KNOWN_KEEP_DAYS = 400


def vocabulary(subs):
    """Klíčová slova, jejichž výskyt v textu předpočítáme pro web."""
    gr = json.loads((ROOT / "config" / "govradar_kd8.json").read_text("utf-8"))
    presets = json.loads((ROOT / "config" / "presets.json").read_text("utf-8"))
    words = set(gr["desu_klicova_slova"] + gr["cenia_klicova_slova"] + gr["sz_zakazky_klicova_slova"]
                + gr["stredocesky_kraj"]["klicova_slova"] + gr["ustecky_kraj"]["klicova_slova"])
    for p in presets:
        words.update(p["filter"].get("keywords") or [])
        for t in p["filter"].get("topics") or []:
            words.update(t["keywords"])
    for s in subs:
        words.update(s.get("filter", {}).get("keywords") or [])
        for t in s.get("filter", {}).get("topics") or []:
            words.update(t.get("keywords") or [])
    return sorted(w for w in words if w.strip())


def process(rec):
    if rec.docs:
        textextract.fill_text(rec)
    hay = f"{rec.title}\n{rec.category}\n{rec.text}"
    obce = sorted(set(rec.obce_struct) | set(matching.find_obce(hay)))
    return rec, obce


def run(data_dir, only=None, send_email=True):
    store = Store(data_dir)
    state = store.load_state()
    subs = notify.load_subscriptions()
    vocab = vocabulary(subs)
    now = datetime.now(TZ)
    new_total = []

    for src in SOURCES:
        sid = src["id"]
        sst = state["sources"].setdefault(sid, {"known": set()})
        if only and sid not in only:
            continue
        if not src.get("fetch") or src.get("status") != "ok":
            continue
        baseline = not sst["known"]   # první běh zdroje: zpětně doplníme, ale neposíláme e-mailem
        try:
            fetched = src["fetch"](sst)
        except Exception as e:  # noqa: BLE001 – výpadek jednoho zdroje nesmí zastavit ostatní
            log.exception("Zdroj %s selhal", sid)
            sst["last_error"] = f"{now.isoformat(timespec='minutes')}: {type(e).__name__}: {e}"[:400]
            continue
        fresh = [r for r in fetched if r.id not in sst["known"]]
        log.info("%s: staženo %d, nových %d", sid, len(fetched), len(fresh))
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(process, fresh))
        for rec, obce in results:
            sst["known"].add(rec.id)
            if not rec.published:          # výchozí stav (např. MMR) – jen zapamatovat
                continue
            idx = rec.to_index()
            idx["obce"] = obce
            idx["kw"] = matching.find_keywords(f"{rec.title}\n{rec.category}\n{rec.text}", vocab)
            idx["fetched"] = now.isoformat(timespec="minutes")
            idx["snippet"] = (rec.text or "")[:300]
            store.add(rec.published[:7], idx, rec.text)
            if not baseline:
                new_total.append((idx, rec.text))
        sst["last_ok"] = now.isoformat(timespec="minutes")
        sst["last_error"] = None
        sst["since"] = (date.today() - timedelta(days=3)).isoformat()
        sst["last_new"] = len(fresh)

    # zařazení nových záznamů do odběrů
    for sub in subs:
        st = state["subs"].setdefault(sub["id"], {"pending": [], "last_sent": None})
        have = {p["id"] for p in st["pending"]}
        for idx, text in new_total:
            if idx["id"] not in have and matching.matches(sub.get("filter", {}), idx, text):
                st["pending"].append({k: idx.get(k) for k in
                                      ("id", "source", "title", "url", "published", "category", "ref")})
    names = {s["id"]: s["name"] for s in SOURCES}
    if send_email:
        notify.deliver(state, names, now)

    state["last_run"] = now.isoformat(timespec="minutes")
    store.flush()
    store.save_state(state)
    store.write_meta({
        "last_run": state["last_run"],
        "months": store.months(),
        "sources": [{
            "id": s["id"], "name": s["name"], "group": s["group"], "url": s["url"],
            "govradar": s.get("govradar", False), "status": s["status"],
            "last_ok": state["sources"].get(s["id"], {}).get("last_ok"),
            "last_error": state["sources"].get(s["id"], {}).get("last_error"),
        } for s in SOURCES],
    })
    log.info("Hotovo: %d nových záznamů k odběrům", len(new_total))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-email", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    run(a.data, only=set(filter(None, a.only.split(","))), send_email=not a.no_email)


if __name__ == "__main__":
    main()
