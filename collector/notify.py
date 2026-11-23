"""E-mailové odběry.

Odběry jsou v config/subscriptions.json. E-mailová adresa je v něm zašifrovaná
veřejným klíčem (RSA-OAEP/SHA-256, šifruje web při ukládání filtru);
soukromý klíč je jen v GitHub Secrets (SUBSCRIPTIONS_PRIVATE_KEY).

SMTP se nastavuje přes GitHub Secrets:
  SMTP_HOST, SMTP_PORT (výchozí 587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
  SMTP_SECURITY = starttls (výchozí) | ssl | none
"""
import base64
import html
import json
import logging
import os
import pathlib
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Prague")
SEND_HOUR = 0          # sběr běží jednou denně ve 3:00, souhrny jdou hned po něm
SITE_URL = os.environ.get("SITE_URL", "")


def load_subscriptions():
    p = ROOT / "config" / "subscriptions.json"
    if not p.exists():
        return []
    return json.loads(p.read_text("utf-8")).get("subscriptions", [])


def decrypt_email(enc: str) -> str | None:
    if not enc.startswith("enc:"):
        return enc  # nešifrovaná adresa (nedoporučeno ve veřejném repozitáři)
    pem = os.environ.get("SUBSCRIPTIONS_PRIVATE_KEY")
    if not pem:
        log.warning("Chybí SUBSCRIPTIONS_PRIVATE_KEY – e-mail nelze dešifrovat")
        return None
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    return key.decrypt(base64.b64decode(enc[4:]), padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)).decode()


def is_due(frequency: str, last_sent: str | None, now: datetime) -> bool:
    if frequency == "ihned":
        return True
    if now.hour < SEND_HOUR:
        return False
    last = datetime.fromisoformat(last_sent).astimezone(TZ) if last_sent else None
    if frequency == "denne":
        return last is None or last.date() < now.date()
    if frequency == "tydne":
        return now.weekday() == 0 and (last is None or (now.date() - last.date()).days >= 6)
    return False


def _smtp_send(to: str, subject: str, text: str, html_body: str):
    host = os.environ.get("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP není nastaveno (chybí SMTP_HOST)")
    port = int(os.environ.get("SMTP_PORT") or 587)
    security = (os.environ.get("SMTP_SECURITY") or "starttls").lower()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER")
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    ctx = ssl.create_default_context()
    if security == "ssl":
        srv = smtplib.SMTP_SSL(host, port, context=ctx, timeout=60)
    else:
        srv = smtplib.SMTP(host, port, timeout=60)
        if security == "starttls":
            srv.starttls(context=ctx)
    with srv:
        if os.environ.get("SMTP_USER"):
            srv.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        srv.send_message(msg)


def _cz(iso):
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return f"{int(d)}. {int(m)}. {y}"


def render(sub, records, source_names):
    n = len(records)
    subject = f"Obecní radar – {sub.get('name', 'odběr')}: {n} {'nový záznam' if n == 1 else 'nové záznamy' if n < 5 else 'nových záznamů'}"
    by_src = {}
    for r in records:
        by_src.setdefault(r["source"], []).append(r)
    lines, parts = [], []
    for src, recs in by_src.items():
        name = source_names.get(src, src)
        lines.append(f"\n== {name} ({len(recs)}) ==")
        parts.append(f"<h3 style='margin:18px 0 6px;font:600 15px sans-serif'>{html.escape(name)} ({len(recs)})</h3><ul style='padding-left:18px;margin:0'>")
        for r in recs:
            meta = " · ".join(x for x in (_cz(r.get("published")), r.get("category"), r.get("ref")) if x)
            lines.append(f"- {r['title']}\n  {meta}\n  {r['url']}")
            parts.append(f"<li style='margin:0 0 8px;font:14px/1.4 sans-serif'><a href='{html.escape(r['url'])}'>{html.escape(r['title'])}</a>"
                         f"<br><span style='color:#666;font-size:12px'>{html.escape(meta)}</span></li>")
        parts.append("</ul>")
    footer = f"\n\nFiltr a všechny záznamy: {SITE_URL}" if SITE_URL else ""
    text = f"Nové záznamy pro odběr „{sub.get('name')}“:\n" + "\n".join(lines) + footer
    html_body = (f"<div style='max-width:680px'><p style='font:14px sans-serif'>Nové záznamy pro odběr "
                 f"<b>{html.escape(sub.get('name', ''))}</b>:</p>{''.join(parts)}"
                 + (f"<p style='font:12px sans-serif;color:#666;margin-top:24px'><a href='{html.escape(SITE_URL)}'>Otevřít přehled</a></p>" if SITE_URL else "")
                 + "</div>")
    return subject, text, html_body


def deliver(state, source_names, now=None):
    """Odešle splatné odběry. Fronta (pending) se vyprázdní jen po úspěšném odeslání."""
    now = now or datetime.now(TZ)
    for sub in load_subscriptions():
        sid = sub["id"]
        st = state["subs"].setdefault(sid, {"pending": [], "last_sent": None})
        if not st["pending"] or not is_due(sub.get("frequency", "denne"), st["last_sent"], now):
            continue
        recs = st["pending"]   # uložené zkrácené záznamy (id, název, odkaz, ...)
        try:
            to = decrypt_email(sub["email"])
            if not to:
                continue
            _smtp_send(to, *render(sub, recs, source_names))
            st["pending"] = []
            st["last_sent"] = now.isoformat()
            log.info("Odběr %s: odesláno %d záznamů", sid, len(recs))
        except Exception as e:  # noqa: BLE001
            log.error("Odběr %s: odeslání selhalo: %s", sid, e)
