"""Úložiště dat (adresář DATA_DIR, v GitHubu větev `data`).

  records/YYYY-MM.json   – lehký index záznamů pro web (bez celého textu)
  fulltext/YYYY-MM.json  – {id: text} pro fulltextové hledání (web načítá jen při hledání)
  state.json             – stav sběru a fronty e-mailů
  meta.json              – přehled pro web (zdroje, poslední běh, dostupné měsíce)
"""
import json
import pathlib


class Store:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        (self.root / "records").mkdir(parents=True, exist_ok=True)
        (self.root / "fulltext").mkdir(parents=True, exist_ok=True)
        self._records = {}
        self._fulltext = {}

    # --- obecné ---
    def _read(self, rel, default):
        p = self.root / rel
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        return default

    def _write(self, rel, data, compact=False):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        txt = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact \
            else json.dumps(data, ensure_ascii=False, indent=1)
        p.write_text(txt, "utf-8")

    # --- stav ---
    def load_state(self):
        st = self._read("state.json", {"sources": {}, "subs": {}})
        for s in st["sources"].values():
            s["known"] = set(s.get("known", []))
        return st

    def save_state(self, st):
        out = {"sources": {}, "subs": st["subs"], "last_run": st.get("last_run")}
        for k, s in st["sources"].items():
            out["sources"][k] = {**s, "known": sorted(s.get("known", []))}
        self._write("state.json", out)

    # --- záznamy ---
    def _month(self, m):
        if m not in self._records:
            self._records[m] = self._read(f"records/{m}.json", [])
            self._fulltext[m] = self._read(f"fulltext/{m}.json", {})
        return self._records[m], self._fulltext[m]

    def add(self, month, index_rec, text):
        recs, ft = self._month(month)
        recs.append(index_rec)
        if text:
            ft[index_rec["id"]] = text

    def months(self):
        return sorted(p.stem for p in (self.root / "records").glob("*.json"))

    def flush(self):
        for m, recs in self._records.items():
            recs.sort(key=lambda r: (r.get("published") or "", r["id"]), reverse=True)
            self._write(f"records/{m}.json", recs, compact=True)
            self._write(f"fulltext/{m}.json", self._fulltext[m], compact=True)

    def write_meta(self, meta):
        self._write("meta.json", meta)
