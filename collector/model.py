"""Datový model záznamu."""
from dataclasses import dataclass, field, asdict


@dataclass
class Doc:
    name: str
    url: str


@dataclass
class Record:
    id: str                      # globálně unikátní, např. "desu:11646"
    source: str                  # id zdroje (viz sources/__init__.py)
    title: str
    url: str                     # odkaz na detail záznamu
    published: str               # YYYY-MM-DD (vyvěšeno / změněno)
    valid_to: str = ""           # YYYY-MM-DD (svěšení), pokud je známé
    category: str = ""           # rubrika / typ / stav
    ref: str = ""                # číslo jednací / kód
    docs: list = field(default_factory=list)      # [Doc]
    obce_struct: list = field(default_factory=list)  # kódy obcí ze strukturovaných dat (CENIA)
    text: str = ""               # vytažený text (popis + přílohy), neukládá se do indexu celý
    text_status: str = ""        # "" | "bez_textu" | "nestazeno" | "chyba"

    def to_index(self):
        d = asdict(self)
        d.pop("text")
        d.pop("obce_struct")
        return d
