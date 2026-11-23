"""HTTP klient s opakováním pokusů a slušnou identifikací."""
import os
import pathlib
import tempfile
import time

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = "Mozilla/5.0 (compatible; ObecniRadar/1.0; monitoring urednich desek pro samospravu)"
TIMEOUT = 45


def _ca_bundle() -> str:
    """Standardní sada kořenových certifikátů + mezilehlé certifikáty z config/.

    Některé servery (např. spravazeleznic.cz) neposílají mezilehlý certifikát
    svého vydavatele. Prohlížeče si ho dohledají, Python ne. Ověřování TLS
    zůstává plně zapnuté – jen doplníme chybějící článek řetězce.
    """
    base = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or certifi.where()
    extra = sorted((pathlib.Path(__file__).resolve().parent.parent / "config").glob("*_ca_*.pem"))
    if not extra:
        return base
    out = pathlib.Path(tempfile.gettempdir()) / "obecni-radar-ca.pem"
    out.write_text(pathlib.Path(base).read_text() + "\n" + "\n".join(p.read_text() for p in extra))
    return str(out)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = _ca_bundle()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET", "POST"))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = UA
    s.headers["Accept-Language"] = "cs,en;q=0.5"
    return s


SESSION = session()


def get(url, **kw):
    kw.setdefault("timeout", TIMEOUT)
    kw.setdefault("verify", SESSION.verify)   # jinak má přednost proměnná REQUESTS_CA_BUNDLE
    r = SESSION.get(url, **kw)
    r.raise_for_status()
    return r


def post(url, **kw):
    kw.setdefault("timeout", TIMEOUT)
    kw.setdefault("verify", SESSION.verify)
    r = SESSION.post(url, **kw)
    r.raise_for_status()
    return r


def polite_pause(seconds=0.5):
    time.sleep(seconds)
