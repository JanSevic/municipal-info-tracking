"""HTTP klient s opakováním pokusů a slušnou identifikací."""
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = "Mozilla/5.0 (compatible; ObecniRadar/1.0; monitoring urednich desek pro samospravu)"
TIMEOUT = 45


def session() -> requests.Session:
    s = requests.Session()
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
    r = SESSION.get(url, **kw)
    r.raise_for_status()
    return r


def post(url, **kw):
    kw.setdefault("timeout", TIMEOUT)
    r = SESSION.post(url, **kw)
    r.raise_for_status()
    return r


def polite_pause(seconds=0.5):
    time.sleep(seconds)
