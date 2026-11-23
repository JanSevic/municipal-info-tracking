"""ÚZSVM – Nabídka majetku pro obce a kraje (nabidkamajetku.gov.cz).

Jde o nabídky státního majetku, u kterých mají územní samosprávné celky
přednost (bezúplatné/úplatné převody před veřejnou nabídkou).
"""
from datetime import date, timedelta

from .. import net
from ..model import Record
from .util import cz_date

BASE = "https://nabidkamajetku.gov.cz"
SOURCE = {
    "id": "uzsvm", "name": "ÚZSVM – nabídka majetku pro obce", "group": "Majetek",
    "url": BASE + "/Home/OffersUsc?ListType=offer-usc", "govradar": False,
}


def fetch(state):
    since = state.get("since") or (date.today() - timedelta(days=45)).isoformat()
    out = []
    for page in range(1, 60):
        d = net.post(f"{BASE}/api/Property/List",
                     json={"PageSize": 100, "Page": page, "ListType": "offer-usc"}).json()
        props = d.get("Properties") or []
        for p in props:
            updated = cz_date(p.get("UpdatedDate") or "")
            if updated and updated < since:
                continue
            status = p.get("StatusName") or ""
            out.append(Record(
                id=f"uzsvm:{p['Id']}", source="uzsvm",
                title=p.get("Name") or "",
                url=f"{BASE}/Home/Detail/{p['Id']}",
                published=updated,
                valid_to=cz_date(status.split(" - ")[-1]) if " - " in status else "",
                category=" / ".join(x for x in (p.get("CategoryName"), "okres " + (p.get("DistrictName") or "")) if x),
                ref=str(p["Id"]),
                text=f"{p.get('Description') or ''}\nOkres: {p.get('DistrictName') or ''}\n{status}",
            ))
        if page >= (d.get("PageCount") or 0) or not props:
            break
    return out
