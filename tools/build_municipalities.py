"""Sestaví číselník obcí (config/obce.json) z RÚIAN (ČÚZK ArcGIS REST).

Obsahuje: všechny obce Středočeského kraje + obce Ústeckého kraje uvedené
v monitoringu GovRadar/KD8 (Podřipsko). Pro každou obec: kód, název, okres,
ORP a seznam sousedních obcí (sdílí hranici).

Spouští se ručně (data se mění zřídka):  python tools/build_municipalities.py
"""
import json
import pathlib
import time

import requests

B = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer"
ROOT = pathlib.Path(__file__).resolve().parent.parent
S = requests.Session()


def q(layer, where, fields="*", geometry=None, extra=None):
    params = {"where": where, "outFields": fields, "returnGeometry": "false", "f": "json"}
    if geometry:
        params.update(geometry)
    if extra:
        params.update(extra)
    out, offset = [], 0
    while True:
        params["resultOffset"] = offset
        for attempt in range(4):
            try:
                r = S.post(f"{B}/{layer}/query", data=params, timeout=60)
                r.raise_for_status()
                d = r.json()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(3)
        feats = d.get("features", [])
        out += [f["attributes"] for f in feats]
        if not d.get("exceededTransferLimit"):
            return out
        offset += len(feats)


def main():
    kd8 = json.loads((ROOT / "config" / "govradar_kd8.json").read_text("utf-8"))
    ustecke_jmena = {a.split(" / ", 1)[1] for a in kd8["cenia_oblasti"] if a.startswith("Litoměřice /")}

    okresy = {o["kod"]: o for o in q(15, "vusc IN (27, 60)", "kod,nazev,vusc")}
    orp = {o["kod"]: o["nazev"] for o in q(14, "1=1", "kod,nazev")}
    pou = {p["kod"]: p for p in q(13, "1=1", "kod,orp")}
    obce = q(12, "okres IN (%s)" % ",".join(map(str, okresy)), "kod,nazev,okres,pou")

    result = []
    for o in obce:
        ok = okresy[o["okres"]]
        if ok["vusc"] == 60 and o["nazev"] not in ustecke_jmena:
            continue
        p = pou.get(o["pou"])
        result.append({
            "kod": o["kod"],
            "nazev": o["nazev"],
            "okres": ok["nazev"],
            "kraj": "Středočeský" if ok["vusc"] == 27 else "Ústecký",
            "orp": orp.get(p["orp"]) if p else None,
        })
    result.sort(key=lambda x: (x["kraj"], x["okres"], x["nazev"]))

    # Sousedé Dřínova (okres Mělník): obce, jejichž hranice se dotýká
    drinov = next(o for o in result if o["nazev"] == "Dřínov" and o["okres"] == "Mělník")
    geom = S.post(f"{B}/12/query", data={"where": f"kod={drinov['kod']}", "returnGeometry": "true",
                                          "outFields": "kod", "f": "json"}, timeout=60).json()
    g = geom["features"][0]["geometry"]
    sr = geom.get("spatialReference", {})
    g["spatialReference"] = sr
    sousede = q(12, f"kod<>{drinov['kod']}", "kod,nazev", geometry={
        "geometry": json.dumps(g), "geometryType": "esriGeometryPolygon",
        "spatialRel": "esriSpatialRelIntersects", "inSR": json.dumps(sr)})
    drinov["sousede"] = sorted(s["nazev"] for s in sousede)

    (ROOT / "config" / "obce.json").write_text(json.dumps(result, ensure_ascii=False, indent=0), "utf-8")
    print(len(result), "obcí; sousedé Dřínova:", drinov["sousede"], "ORP:", drinov["orp"])


if __name__ == "__main__":
    main()
