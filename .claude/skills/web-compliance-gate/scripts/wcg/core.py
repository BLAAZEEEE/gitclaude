"""Noyau commun : modèle de résultat, client HTTP, parseur HTML, crawler."""
from __future__ import annotations

import gzip
import ipaddress
import re
import socket
import ssl
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable

from .catalog import CHECKS

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 web-compliance-gate/1.0"
MAX_BODY = 6 * 1024 * 1024

# --------------------------------------------------------------------------- résultats

STATUSES = ("pass", "fail", "warn", "manual", "na", "error")


@dataclass
class Finding:
    id: str
    status: str                      # pass | fail | warn | manual | na | error
    evidence: str = ""               # ce qui a été observé (court)
    details: list = field(default_factory=list)   # éléments précis : urls, fichiers:ligne…
    note: str = ""                   # précision contextuelle

    def to_dict(self):
        meta = CHECKS.get(self.id, {})
        return {
            "id": self.id,
            "category": meta.get("cat", "?"),
            "severity": meta.get("sev", "low"),
            "title": meta.get("title", self.id),
            "status": self.status,
            "evidence": self.evidence,
            "details": self.details[:60],
            "details_total": len(self.details),
            "note": self.note,
            "fix": meta.get("fix", ""),
            "ref": meta.get("ref", ""),
        }


class Results:
    def __init__(self):
        self.items: dict[str, Finding] = {}

    def add(self, fid: str, status: str, evidence: str = "", details: Iterable | None = None, note: str = ""):
        if fid not in CHECKS:
            raise KeyError(f"Check inconnu : {fid}")
        assert status in STATUSES, status
        details = list(details or [])
        prev = self.items.get(fid)
        # si un test est rejoué (ex : plusieurs pages), on garde le pire résultat
        order = {"fail": 5, "error": 4, "warn": 3, "manual": 2, "pass": 1, "na": 0}
        if prev and order[prev.status] > order[status]:
            prev.details.extend(details)
            return prev
        if prev:
            details = prev.details + details
        f = Finding(fid, status, evidence, details, note)
        self.items[fid] = f
        return f

    def ok(self, fid, evidence="", details=None, note=""):
        return self.add(fid, "pass", evidence, details, note)

    def ko(self, fid, evidence="", details=None, note=""):
        return self.add(fid, "fail", evidence, details, note)

    def warn(self, fid, evidence="", details=None, note=""):
        return self.add(fid, "warn", evidence, details, note)

    def na(self, fid, evidence="", note=""):
        return self.add(fid, "na", evidence, None, note)

    def err(self, fid, evidence="", note=""):
        return self.add(fid, "error", evidence, None, note)

    def manual(self, fid, evidence="", note=""):
        return self.add(fid, "manual", evidence, None, note)

    def check(self, fid, condition: bool, ok_ev="", ko_ev="", details=None, soft=False, note=""):
        """Raccourci : pass si condition, sinon fail (ou warn si soft)."""
        if condition:
            return self.ok(fid, ok_ev, details, note)
        return (self.warn if soft else self.ko)(fid, ko_ev, details, note)

    def guard(self, fids: Iterable[str], fn, *a, **kw):
        """Exécute fn ; en cas d'exception, marque les checks non encore renseignés en 'error'."""
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            msg = f"{type(e).__name__}: {e}"[:300]
            for fid in fids:
                if fid not in self.items:
                    self.err(fid, f"Le test n'a pas pu s'exécuter ({msg})")
            return None


# --------------------------------------------------------------------------- utilitaires texte

def norm(s: str) -> str:
    """minuscules, sans accents, espaces compactés — pour les recherches par mots-clés."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s.lower()).strip()


def is_local_host(host: str) -> bool:
    host = (host or "").strip("[]").lower()
    if host in ("localhost", "0.0.0.0") or host.endswith((".localhost", ".local", ".test", ".internal", ".lan")):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        pass
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return ip.is_loopback or ip.is_private
    except Exception:  # noqa: BLE001
        return False


def same_site(u1: str, u2: str) -> bool:
    h1 = urllib.parse.urlsplit(u1).hostname or ""
    h2 = urllib.parse.urlsplit(u2).hostname or ""
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    return strip(h1) == strip(h2)


def registrable(host: str) -> str:
    parts = (host or "").split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "gouv", "org", "net", "ac") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


# --------------------------------------------------------------------------- HTTP

@dataclass
class Resp:
    url: str
    status: int
    headers: list          # liste de (nom_minuscule, valeur) — garde les Set-Cookie multiples
    body: bytes
    elapsed: float
    chain: list            # [(url, status)] des redirections suivies
    error: str = ""
    http_version: str = ""

    def h(self, name: str, default: str = "") -> str:
        name = name.lower()
        for k, v in self.headers:
            if k == name:
                return v
        return default

    def hs(self, name: str) -> list:
        name = name.lower()
        return [v for k, v in self.headers if k == name]

    @property
    def ctype(self) -> str:
        return self.h("content-type").split(";")[0].strip().lower()

    @property
    def is_html(self) -> bool:
        return "html" in self.ctype

    @property
    def text(self) -> str:
        m = re.search(r"charset=([\w-]+)", self.h("content-type"), re.I)
        enc = m.group(1) if m else "utf-8"
        try:
            return self.body.decode(enc, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # noqa: D401
        return None


class Http:
    def __init__(self, insecure: bool = False, timeout: float = 20.0):
        self.timeout = timeout
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.ctx = ctx
        self.opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ctx))
        self.cache: dict = {}
        self.count = 0

    def _one(self, url, method="GET", headers=None, data=None):
        req = urllib.request.Request(url, method=method, data=data)
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        req.add_header("Accept-Encoding", "gzip, deflate")
        req.add_header("Accept-Language", "fr-FR,fr;q=0.9,en;q=0.5")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        t0 = time.perf_counter()
        self.count += 1
        try:
            r = self.opener.open(req, timeout=self.timeout)
            status = r.status
        except urllib.error.HTTPError as e:
            r = e
            status = e.code
        raw = r.read(MAX_BODY) if method != "HEAD" else b""
        elapsed = time.perf_counter() - t0
        hdrs = [(k.lower(), v) for k, v in r.headers.items()]
        enc = r.headers.get("Content-Encoding", "").lower()
        body = raw
        try:
            if enc == "gzip":
                body = gzip.decompress(raw)
            elif enc == "deflate":
                body = zlib.decompress(raw)
        except Exception:  # noqa: BLE001
            body = raw
        return status, hdrs, body, elapsed, len(raw)

    def get(self, url, method="GET", headers=None, follow=True, data=None, use_cache=True) -> Resp:
        key = (url, method, tuple(sorted((headers or {}).items())), follow)
        if use_cache and key in self.cache and data is None:
            return self.cache[key]
        chain = []
        cur = url
        total = 0.0
        for _ in range(10):
            try:
                status, hdrs, body, el, wire = self._one(cur, method, headers, data)
            except Exception as e:  # noqa: BLE001
                resp = Resp(cur, 0, [], b"", total, chain, error=f"{type(e).__name__}: {e}")
                self.cache[key] = resp
                return resp
            total += el
            loc = next((v for k, v in hdrs if k == "location"), None)
            if follow and status in (301, 302, 303, 307, 308) and loc:
                chain.append((cur, status))
                cur = urllib.parse.urljoin(cur, loc)
                if method == "POST" and status in (301, 302, 303):
                    method, data = "GET", None
                continue
            resp = Resp(cur, status, hdrs, body, total, chain)
            resp.wire_size = wire  # type: ignore[attr-defined]
            if use_cache and data is None:
                self.cache[key] = resp
            return resp
        resp = Resp(cur, 0, [], b"", total, chain, error="Trop de redirections")
        self.cache[key] = resp
        return resp


# --------------------------------------------------------------------------- parseur HTML

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Doc(HTMLParser):
    """Extraction ciblée de tout ce dont les tests ont besoin, sans dépendance externe."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.lang = None
        self.title = None
        self.titles = 0
        self.metas: list[dict] = []
        self.links: list[dict] = []          # <link>
        self.anchors: list[dict] = []        # <a>
        self.imgs: list[dict] = []
        self.scripts: list[dict] = []
        self.iframes: list[dict] = []
        self.forms: list[dict] = []
        self.inputs_outside_forms: list[dict] = []
        self.labels_for: set = set()
        self.headings: list[tuple] = []
        self.buttons: list[dict] = []
        self.jsonld: list[str] = []
        self.inline_scripts: list[str] = []
        self.inline_styles: list[str] = []
        self.text_parts: list[str] = []
        self.has_main = False
        self.has_nav = False
        self.charset = None
        self.pictures = 0
        self._stack: list[str] = []
        self._cur_script = None
        self._cur_style = False
        self._cur_title = False
        self._cur_heading = None
        self._cur_a = None
        self._cur_button = None
        self._cur_label = None
        self._cur_form = None
        self._in_head = False
        self._skip = 0

    # --- helpers
    def abs(self, u):
        if not u:
            return u
        return urllib.parse.urljoin(self.base, u.strip())

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        if tag not in VOID:
            self._stack.append(tag)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "head":
            self._in_head = True
        elif tag == "body":
            self._in_head = False
        elif tag == "title":
            self._cur_title = True
            self.titles += 1
            self.title = self.title or ""
        elif tag == "meta":
            self.metas.append(a)
            if "charset" in a:
                self.charset = a["charset"]
        elif tag == "link":
            a["_abs"] = self.abs(a.get("href"))
            self.links.append(a)
        elif tag == "a":
            a["_abs"] = self.abs(a.get("href")) if a.get("href") else ""
            a["_text"] = ""
            self._cur_a = a
            self.anchors.append(a)
            if self._cur_form is not None:
                self._cur_form["_links"].append(a)
        elif tag == "img":
            a["_abs"] = self.abs(a.get("src"))
            a["_in_picture"] = "picture" in self._stack
            a["_index"] = len(self.imgs)
            self.imgs.append(a)
            for holder in (self._cur_a, self._cur_button):
                if holder is not None:
                    holder["_img_alt"] = (holder.get("_img_alt") or "") + (a.get("alt") or "")
        elif tag == "picture":
            self.pictures += 1
        elif tag == "script":
            a["_abs"] = self.abs(a.get("src")) if a.get("src") else ""
            a["_in_head"] = self._in_head
            self.scripts.append(a)
            self._cur_script = a
            a["_content"] = ""
            self._skip += 1
        elif tag == "style":
            self._cur_style = True
            self._skip += 1
        elif tag in ("noscript", "template", "svg"):
            self._skip += 1
        elif tag == "iframe":
            a["_abs"] = self.abs(a.get("src"))
            self.iframes.append(a)
        elif tag == "form":
            a["_abs"] = self.abs(a.get("action") or self.base)
            a["_inputs"] = []
            a["_text"] = ""
            a["_links"] = []
            self._cur_form = a
            self.forms.append(a)
        elif tag in ("input", "textarea", "select"):
            a["_tag"] = tag
            a["_wrapped_label"] = self._cur_label is not None
            (self._cur_form["_inputs"] if self._cur_form else self.inputs_outside_forms).append(a)
        elif tag == "label":
            if a.get("for"):
                self.labels_for.add(a["for"])
            self._cur_label = a
        elif tag == "button":
            a["_text"] = ""
            self._cur_button = a
            self.buttons.append(a)
            if self._cur_form is not None:
                self._cur_form["_inputs"].append({"_tag": "button", **a})
        elif re.fullmatch(r"h[1-6]", tag):
            self._cur_heading = [int(tag[1]), ""]
        elif tag == "main" or a.get("role") == "main":
            self.has_main = True
        elif tag == "nav":
            self.has_nav = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self._stack and self._stack[-1] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
        if tag == "title":
            self._cur_title = False
        elif tag == "script":
            if self._cur_script is not None:
                c = self._cur_script["_content"]
                t = (self._cur_script.get("type") or "").lower()
                if t == "application/ld+json":
                    self.jsonld.append(c)
                elif c.strip():
                    self.inline_scripts.append(c)
            self._cur_script = None
            self._skip = max(0, self._skip - 1)
        elif tag == "style":
            self._cur_style = False
            self._skip = max(0, self._skip - 1)
        elif tag in ("noscript", "template", "svg"):
            self._skip = max(0, self._skip - 1)
        elif tag == "a":
            self._cur_a = None
        elif tag == "button":
            self._cur_button = None
        elif tag == "label":
            self._cur_label = None
        elif tag == "form":
            self._cur_form = None
        elif re.fullmatch(r"h[1-6]", tag) and self._cur_heading:
            self.headings.append((self._cur_heading[0], self._cur_heading[1].strip()))
            self._cur_heading = None
        elif tag == "head":
            self._in_head = False

    def handle_data(self, data):
        if self._cur_script is not None:
            self._cur_script["_content"] += data
            return
        if self._cur_style:
            self.inline_styles.append(data)
            return
        if self._cur_title:
            self.title += data
            return
        if self._skip:
            return
        if self._cur_heading is not None:
            self._cur_heading[1] += data
        if self._cur_a is not None:
            self._cur_a["_text"] += data
        if self._cur_button is not None:
            self._cur_button["_text"] += data
        if self._cur_form is not None:
            self._cur_form["_text"] += data
        self.text_parts.append(data)

    # --- accès pratiques
    def meta(self, name=None, prop=None, http_equiv=None):
        for m in self.metas:
            if name and m.get("name", "").lower() == name:
                return m.get("content", "")
            if prop and m.get("property", "").lower() == prop:
                return m.get("content", "")
            if http_equiv and m.get("http-equiv", "").lower() == http_equiv:
                return m.get("content", "")
        return None

    def link_rel(self, rel):
        return [l for l in self.links if rel in (l.get("rel", "").lower().split())]

    @property
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()


def parse(html: str, url: str) -> Doc:
    d = Doc(url)
    try:
        d.feed(html)
        d.close()
    except Exception:  # noqa: BLE001
        pass
    # les ancres à l'intérieur des formulaires servent à détecter un lien vers la politique
    return d


# --------------------------------------------------------------------------- crawler

SKIP_EXT = re.compile(r"\.(png|jpe?g|gif|webp|avif|svg|ico|pdf|zip|rar|7z|gz|mp4|webm|mp3|wav|woff2?|ttf|eot|css|js|json|xml|txt|docx?|xlsx?|pptx?)(\?|$)", re.I)


@dataclass
class Page:
    url: str
    resp: Resp
    doc: Doc | None
    depth: int


class Crawler:
    def __init__(self, http: Http, start: str, max_pages: int = 40):
        self.http = http
        self.start = start
        self.max_pages = max_pages
        self.pages: list[Page] = []
        self.broken: list[tuple] = []     # (url cible, statut, page source)
        self.seen: set = set()
        self.link_status: dict = {}

    @staticmethod
    def clean(u):
        u, _ = urllib.parse.urldefrag(u)
        return u

    def run(self, seeds: list[str] | None = None):
        queue = [(self.clean(self.start), 0, None)] + [(self.clean(s), 1, "sitemap") for s in (seeds or [])]
        while queue and len(self.pages) < self.max_pages:
            url, depth, src = queue.pop(0)
            if url in self.seen:
                continue
            self.seen.add(url)
            r = self.http.get(url)
            self.link_status[url] = r.status
            if r.status >= 400 or r.status == 0:
                self.broken.append((url, r.status or r.error, src))
                continue
            if not same_site(r.url, self.start):
                continue
            if not r.is_html:
                continue
            doc = parse(r.text, r.url)
            self.pages.append(Page(r.url, r, doc, depth))
            self.seen.add(self.clean(r.url))
            for a in doc.anchors:
                href = a.get("_abs") or ""
                if not href.startswith(("http://", "https://")):
                    continue
                href = self.clean(href)
                if not same_site(href, self.start) or SKIP_EXT.search(href):
                    continue
                if href not in self.seen:
                    queue.append((href, depth + 1, r.url))
        return self.pages
