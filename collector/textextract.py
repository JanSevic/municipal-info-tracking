"""Stažení příloh a vytažení textu (PDF, DOCX, ODT, TXT/HTML).

Skeny bez textové vrstvy nepozná (stejně jako GovRadar) – záznam se pak
označí text_status="bez_textu".
"""
import io
import logging
import re
import zipfile

from . import net

log = logging.getLogger(__name__)

MAX_BYTES = 15 * 1024 * 1024   # větší přílohy (typicky celé dokumentace v ZIP) nestahujeme
MAX_TEXT = 60_000              # kolik znaků textu z jednoho záznamu nejvýš držíme
MAX_DOCS = 4                   # kolik příloh na záznam nejvýš čteme


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages[:60]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # poškozená stránka
            continue
    return "\n".join(parts)


def _zip_xml(data: bytes, member: str) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read(member).decode("utf-8", "replace")
    xml = re.sub(r"</(w:p|text:p|text:h)>", "\n", xml)
    return re.sub(r"<[^>]+>", " ", xml)


def extract(data: bytes, name: str = "", content_type: str = "") -> str:
    n = (name or "").lower()
    ct = (content_type or "").lower()
    if data[:4] == b"%PDF" or n.endswith(".pdf") or "pdf" in ct:
        return _pdf(data)
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
            if "word/document.xml" in names:
                return _zip_xml(data, "word/document.xml")
            if "content.xml" in names:
                return _zip_xml(data, "content.xml")
        except zipfile.BadZipFile:
            return ""
        return ""  # ZIP archivy (dokumentace EIA) nečteme
    if n.endswith((".txt", ".htm", ".html")) or ct.startswith("text/"):
        txt = data.decode("utf-8", "replace")
        return re.sub(r"<[^>]+>", " ", txt)
    return ""


def fetch_text(url: str, name: str = "", session=None) -> tuple[str, str]:
    """Vrátí (text, status). status: "" ok | "bez_textu" | "nestazeno" | "chyba"."""
    s = session or net.SESSION
    if name and name.lower().endswith((".zip", ".rar", ".7z", ".jpg", ".png", ".dwg", ".shp")):
        return "", "nestazeno"
    try:
        with s.get(url, timeout=net.TIMEOUT, stream=True) as r:
            r.raise_for_status()
            size = int(r.headers.get("Content-Length") or 0)
            if size > MAX_BYTES:
                return "", "nestazeno"
            buf = io.BytesIO()
            for chunk in r.iter_content(64 * 1024):
                buf.write(chunk)
                if buf.tell() > MAX_BYTES:
                    return "", "nestazeno"
            txt = extract(buf.getvalue(), name, r.headers.get("Content-Type", ""))
    except Exception as e:  # noqa: BLE001 – jedna vadná příloha nesmí shodit běh
        log.warning("Příloha %s: %s", url, e)
        return "", "chyba"
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt).strip()
    if len(txt) < 20:
        return "", "bez_textu"
    return txt[:MAX_TEXT], ""


def fill_text(record, session=None):
    """Doplní record.text z příloh (max MAX_DOCS)."""
    texts, statuses = [], []
    for d in record.docs[:MAX_DOCS]:
        if not d.url:
            continue
        t, st = fetch_text(d.url, d.name, session)
        if t:
            texts.append(t)
        statuses.append(st)
    if texts:
        record.text = ("\n\n".join([record.text] + texts) if record.text else "\n\n".join(texts))[:MAX_TEXT]
        record.text_status = ""
    elif statuses:
        record.text_status = next((s for s in ("bez_textu", "chyba", "nestazeno") if s in statuses), "")
