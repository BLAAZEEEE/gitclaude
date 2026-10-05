"""Contrôles de sécurité observables en HTTP sur le site qui tourne (config défensive)."""
from __future__ import annotations

import re
import urllib.parse

from .core import registrable

TRACE_PATTERNS = [
    r"Traceback \(most recent call last\)", r"Whoops!? .*There was an error", r"Stack trace:", r"at [\w$.<>]+ \([^)]*:\d+:\d+\)",
    r"Fatal error</b>:", r"Warning</b>:.*on line", r"Notice</b>:.*on line", r"Symfony\\Component\\", r"Illuminate\\",
    r"django\.core\.exceptions", r"You're seeing this error because you have <code>DEBUG = True", r"Werkzeug Debugger",
    r"ActionController::RoutingError", r"java\.lang\.\w+Exception", r"System\.\w+Exception", r"Microsoft \.NET Framework Version",
    r"Exception in thread", r"SQLSTATE\[", r"PDOException", r"mysqli_", r"ORA-\d{5}", r"pg_query\(\)", r"at Object\.<anonymous>",
    r"webpack-internal:///", r"__NEXT_DATA__.*\"err\"", r"Laravel\s*v?\d", r"xdebug",
]

# Chemins bien connus dont l'exposition publique est une erreur de configuration classique.
SENSITIVE_PATHS = [
    (".env", "critical", lambda b: re.search(rb"^[A-Z_]{3,}=", b, re.M)),
    (".env.local", "critical", lambda b: re.search(rb"^[A-Z_]{3,}=", b, re.M)),
    (".env.production", "critical", lambda b: re.search(rb"^[A-Z_]{3,}=", b, re.M)),
    (".git/HEAD", "critical", lambda b: b.startswith(b"ref:") or re.match(rb"^[0-9a-f]{40}", b)),
    (".git/config", "critical", lambda b: b"[core]" in b),
    (".svn/entries", "high", lambda b: len(b) > 0 and b"<html" not in b.lower()),
    (".DS_Store", "medium", lambda b: b[:8] == b"\x00\x00\x00\x01Bud1"),
    ("wp-config.php.bak", "critical", lambda b: b"DB_PASSWORD" in b),
    ("wp-config.php~", "critical", lambda b: b"DB_PASSWORD" in b),
    ("config.php.bak", "critical", lambda b: b"<?php" in b),
    ("backup.sql", "critical", lambda b: re.search(rb"(CREATE TABLE|INSERT INTO)", b, re.I)),
    ("dump.sql", "critical", lambda b: re.search(rb"(CREATE TABLE|INSERT INTO)", b, re.I)),
    ("database.sql", "critical", lambda b: re.search(rb"(CREATE TABLE|INSERT INTO)", b, re.I)),
    ("db.sqlite", "critical", lambda b: b.startswith(b"SQLite format 3")),
    ("database.sqlite", "critical", lambda b: b.startswith(b"SQLite format 3")),
    ("phpinfo.php", "high", lambda b: b"phpinfo()" in b or b"PHP Version" in b),
    ("info.php", "high", lambda b: b"PHP Version" in b),
    ("composer.json", "low", lambda b: b'"require"' in b),
    ("package.json", "low", lambda b: b'"dependencies"' in b or b'"name"' in b),
    ("docker-compose.yml", "high", lambda b: b"services:" in b),
    ("id_rsa", "critical", lambda b: b"PRIVATE KEY" in b),
    ("storage/logs/laravel.log", "critical", lambda b: b"local.ERROR" in b or b"production.ERROR" in b),
    ("debug.log", "high", lambda b: len(b) > 50 and b"<html" not in b[:500].lower()),
    ("wp-content/debug.log", "high", lambda b: b"PHP " in b),
    ("npm-debug.log", "medium", lambda b: b"npm" in b),
    (".htpasswd", "critical", lambda b: re.search(rb"^\w+:\$?", b, re.M)),
    ("web.config.bak", "high", lambda b: b"<configuration" in b),
    ("server-status", "medium", lambda b: b"Apache Server Status" in b),
    ("server-info", "medium", lambda b: b"Apache Server Information" in b),
    ("actuator/env", "critical", lambda b: b"propertySources" in b),
    ("actuator/heapdump", "critical", lambda b: len(b) > 1000 and b"<html" not in b[:200].lower()),
    ("_profiler/", "high", lambda b: b"Symfony Profiler" in b),
    ("telescope", "high", lambda b: b"Telescope" in b),
    ("elmah.axd", "high", lambda b: b"Error Log" in b),
    ("Dockerfile", "low", lambda b: b"FROM " in b),
    ("backup.zip", "high", lambda b: b[:2] == b"PK"),
    ("site.zip", "high", lambda b: b[:2] == b"PK"),
    ("www.zip", "high", lambda b: b[:2] == b"PK"),
]

ADMIN_PATHS = [
    ("phpmyadmin/", lambda b: b"phpMyAdmin" in b), ("pma/", lambda b: b"phpMyAdmin" in b),
    ("adminer.php", lambda b: b"Adminer" in b), ("adminer/", lambda b: b"Adminer" in b),
    ("_debugbar/", lambda b: b"debugbar" in b.lower()), ("graphiql", lambda b: b"graphiql" in b.lower()),
    ("swagger-ui.html", lambda b: b"swagger" in b.lower()), ("api/docs", lambda b: b"swagger" in b.lower() or b"redoc" in b.lower()),
]

SESSION_NAMES = re.compile(r"(sess|sid|auth|token|jwt|remember|login|connect\.sid|laravel_session|phpsessid|jsessionid|asp\.net_sessionid|_session|csrftoken|xsrf)", re.I)
CSRF_FIELDS = re.compile(r"(csrf|xsrf|_token|authenticity_token|csrfmiddlewaretoken|__requestverificationtoken|nonce|_wpnonce|form_key)", re.I)


def parse_set_cookie(raw: str) -> dict:
    parts = [p.strip() for p in raw.split(";")]
    name, _, value = parts[0].partition("=")
    attrs = {}
    for p in parts[1:]:
        k, _, v = p.partition("=")
        attrs[k.strip().lower()] = v.strip()
    return {"name": name.strip(), "value": value, "attrs": attrs, "raw": raw}


def run(ctx):
    R = ctx.results
    home = ctx.home_resp
    pages = ctx.pages
    https = ctx.base.startswith("https://")

    # ------------------------------------------------------------ en-têtes
    def headers_checks():
        csp = home.h("content-security-policy")
        csp_ro = home.h("content-security-policy-report-only")
        meta_csp = next((m.get("content") for p in pages[:1] for m in p.doc.metas if m.get("http-equiv", "").lower() == "content-security-policy"), None) if pages else None
        eff = csp or meta_csp or ""
        if eff:
            R.ok("SEC-01", "CSP présente" + (" (via <meta>)" if not csp else ""), [eff[:300]],
                 note="frame-ancestors est ignoré dans une CSP en <meta> : le mettre en en-tête HTTP." if not csp else "")
        elif csp_ro:
            R.warn("SEC-01", "Seulement Content-Security-Policy-Report-Only (pas appliquée)", [csp_ro[:300]])
        else:
            R.ko("SEC-01", "Aucun en-tête Content-Security-Policy")
        if eff:
            dirs = {d.strip().split(" ")[0].lower(): d.strip() for d in eff.split(";") if d.strip()}
            script = dirs.get("script-src") or dirs.get("default-src") or ""
            probs = []
            if "'unsafe-inline'" in script and not re.search(r"'nonce-|'sha(256|384|512)-|'strict-dynamic'", script):
                probs.append("'unsafe-inline' dans script-src")
            if "'unsafe-eval'" in script:
                probs.append("'unsafe-eval' dans script-src")
            if re.search(r"(^|\s)(\*|https?:|data:)(\s|$)", script.partition(" ")[2]):
                probs.append("source trop large (*, https:, data:) dans script-src")
            if "object-src" not in dirs and "'none'" not in dirs.get("default-src", ""):
                probs.append("object-src 'none' absent")
            if "base-uri" not in dirs:
                probs.append("base-uri absent")
            R.check("SEC-02", not probs, "CSP stricte", "CSP permissive", probs, soft=len(probs) <= 1 and "unsafe" not in " ".join(probs))
        else:
            R.ko("SEC-02", "Pas de CSP à évaluer")
        xfo = home.h("x-frame-options")
        fa = re.search(r"frame-ancestors\s+([^;]+)", csp or "")
        if fa and "*" not in fa.group(1):
            R.ok("SEC-03", f"frame-ancestors {fa.group(1).strip()}")
        elif xfo.upper() in ("DENY", "SAMEORIGIN"):
            R.ok("SEC-03", f"X-Frame-Options: {xfo}")
        else:
            R.ko("SEC-03", "Ni frame-ancestors ni X-Frame-Options")
        R.check("SEC-04", home.h("x-content-type-options").lower() == "nosniff", "nosniff présent", "X-Content-Type-Options absent")
        rp = home.h("referrer-policy").lower()
        R.check("SEC-05", bool(rp) and "unsafe-url" not in rp, f"Referrer-Policy: {rp}", f"Referrer-Policy {'absente' if not rp else 'trop permissive: ' + rp}")
        R.check("SEC-06", bool(home.h("permissions-policy")), "Permissions-Policy présente", "Permissions-Policy absente")
        R.check("SEC-07", bool(home.h("cross-origin-opener-policy")), "COOP présente", "Cross-Origin-Opener-Policy absente")
        leaks = []
        srv = home.h("server")
        if re.search(r"\d", srv):
            leaks.append(f"Server: {srv}")
        for h in ("x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator", "x-drupal-cache", "x-runtime"):
            if home.h(h):
                leaks.append(f"{h}: {home.h(h)}")
        R.check("SEC-08", not leaks, "Aucune version divulguée", "Versions/technos divulguées", leaks)

        cc = home.h("cache-control").lower()
        forms_with_pw = any(i.get("type", "").lower() == "password" for p in pages for f in p.doc.forms for i in f["_inputs"])
        if forms_with_pw:
            pw_pages = [p for p in pages if any(i.get("type", "").lower() == "password" for f in p.doc.forms for i in f["_inputs"])]
            bad = [p.url for p in pw_pages if not re.search(r"no-store|private", p.resp.h("cache-control").lower())]
            R.check("SEC-24", not bad, "Pages de connexion non mises en cache partagé", "Pages avec mot de passe sans Cache-Control no-store/private", bad, soft=True)
        else:
            R.na("SEC-24", "Aucune page avec formulaire d'authentification trouvée", note=f"Accueil : Cache-Control: {cc or '(absent)'}")

    # ------------------------------------------------------------ cookies
    def cookies_checks():
        cookies = {}
        for p in pages:
            for raw in p.resp.hs("set-cookie"):
                c = parse_set_cookie(raw)
                cookies.setdefault(c["name"], (c, p.url))
        for raw in home.hs("set-cookie"):
            c = parse_set_cookie(raw)
            cookies.setdefault(c["name"], (c, ctx.base))
        if not cookies:
            for fid in ("SEC-09", "SEC-10", "SEC-11"):
                R.na(fid, "Aucun cookie posé par le serveur sur les pages visitées")
            return
        no_secure = [f"{n} ({u})" for n, (c, u) in cookies.items() if "secure" not in c["attrs"]]
        sess = {n: c for n, (c, u) in cookies.items() if SESSION_NAMES.search(n)}
        no_http = [n for n, c in sess.items() if "httponly" not in c["attrs"] and not re.search(r"csrf|xsrf", n, re.I)]
        no_ss = [n for n, (c, u) in cookies.items() if c["attrs"].get("samesite", "").lower() not in ("lax", "strict") and
                 not (c["attrs"].get("samesite", "").lower() == "none" and "secure" in c["attrs"])]
        note = "Site testé en HTTP local : vérifier que la config de prod force Secure." if ctx.is_local and not https else ""
        if no_secure:
            (R.warn if ctx.is_local and not https else R.ko)("SEC-09", f"{len(no_secure)} cookie(s) sans Secure", no_secure, note=note)
        else:
            R.ok("SEC-09", f"{len(cookies)} cookie(s), tous Secure")
        if sess:
            R.check("SEC-10", not no_http, "Cookies de session HttpOnly", "Cookies de session sans HttpOnly", no_http)
        else:
            R.na("SEC-10", "Aucun cookie de session identifié")
        R.check("SEC-11", not no_ss, "SameSite défini", "Cookies sans SameSite=Lax/Strict", no_ss, soft=True)

    # ------------------------------------------------------------ CORS
    def cors_checks():
        probe_origin = "https://wcg-origin-check.example"
        targets = [ctx.base] + [u for u in ctx.api_candidates][:4]
        bad = []
        for t in targets:
            r = ctx.http.get(t, headers={"Origin": probe_origin}, use_cache=False)
            acao = r.h("access-control-allow-origin")
            acac = r.h("access-control-allow-credentials").lower() == "true"
            if acao == probe_origin:
                bad.append(f"{t} → renvoie l'Origin reçu{' avec credentials' if acac else ''}")
            elif acao == "*" and acac:
                bad.append(f"{t} → * avec credentials")
            elif acao == "*" and t != ctx.base:
                bad.append(f"{t} → ACAO * sur une API (à vérifier si données privées)")
        if bad:
            sev_soft = all("à vérifier" in b for b in bad)
            (R.warn if sev_soft else R.ko)("SEC-12", "Politique CORS permissive", bad)
        else:
            R.ok("SEC-12", f"Aucune origine arbitraire acceptée ({len(targets)} URL testées)")

    # ------------------------------------------------------------ exposition
    def exposure_checks():
        root = ctx.base.rstrip("/") + "/"
        # référence : réponse à un chemin inexistant, pour écarter les « catch-all » en 200
        ref = ctx.http.get(root + "wcg-inexistant-7f3a9c/", use_cache=False)
        ref_len = len(ref.body)
        found, found_low = [], []
        for path, sev, sig in SENSITIVE_PATHS:
            r = ctx.http.get(root + path, follow=False, use_cache=False)
            if r.status == 200 and r.body and sig(r.body[:200_000]) and not (ref.status == 200 and abs(len(r.body) - ref_len) < 50):
                (found if sev in ("critical", "high") else found_low).append(f"/{path} ({sev})")
        if found:
            R.ko("SEC-13", f"{len(found)} fichier(s) sensible(s) accessible(s)", found + found_low)
        elif found_low:
            R.warn("SEC-13", "Fichiers de projet accessibles (faible gravité)", found_low)
        else:
            R.ok("SEC-13", f"{len(SENSITIVE_PATHS)} chemins sensibles testés, aucun exposé")
        # listing de répertoires
        dirs = set()
        for p in pages:
            for u in [s.get("_abs") for s in p.doc.scripts] + [l.get("_abs") for l in p.doc.links] + [i.get("_abs") for i in p.doc.imgs]:
                if u and u.startswith(root):
                    d = u[: u.rfind("/") + 1]
                    if d != root:
                        dirs.add(d)
        for d in ("uploads/", "images/", "img/", "assets/", "static/", "files/", "wp-content/uploads/", "storage/"):
            dirs.add(root + d)
        listed = []
        for d in sorted(dirs)[:25]:
            r = ctx.http.get(d, follow=False, use_cache=False)
            if r.status == 200 and re.search(r"<title>Index of /|Directory listing for|<h1>Index of", r.text[:3000], re.I):
                listed.append(d)
        R.check("SEC-14", not listed, f"{min(len(dirs), 25)} répertoires testés, aucun listing", "Listing de répertoire actif", listed)
        # interfaces d'admin
        admins = []
        for path, sig in ADMIN_PATHS:
            r = ctx.http.get(root + path, follow=True, use_cache=False)
            if r.status == 200 and sig(r.body[:100_000]):
                admins.append(f"/{path}")
        if admins:
            (R.warn if ctx.is_local else R.ko)("SEC-22", "Interfaces d'admin/debug accessibles sans restriction", admins,
                                             note="En local c'est normal ; s'assurer qu'elles ne sont pas déployées en prod." if ctx.is_local else "")
        else:
            R.ok("SEC-22", "Aucune interface d'admin/debug connue exposée")

    # ------------------------------------------------------------ erreurs & méthodes
    def error_checks():
        root = ctx.base.rstrip("/") + "/"
        probes = [root + "wcg-page-inexistante-9b1e", root + "api/wcg-inexistant", root + "wcg-inexistant.php"]
        leaks = []
        for u in probes:
            r = ctx.http.get(u, use_cache=False)
            body = r.text[:200_000]
            for pat in TRACE_PATTERNS:
                if re.search(pat, body):
                    leaks.append(f"{u} → {pat[:40]}")
                    break
        R.check("SEC-15", not leaks, "Pages d'erreur génériques", "Traces techniques visibles", leaks)
        r = ctx.http.get(ctx.base, method="TRACE", use_cache=False)
        R.check("SEC-16", r.status in (0, 400, 403, 404, 405, 501) or r.status >= 400, f"TRACE → {r.status or 'refusé'}", f"TRACE accepté ({r.status})", soft=True)
        st = ctx.http.get(root + ".well-known/security.txt", use_cache=False)
        R.check("SEC-20", st.status == 200 and "contact:" in st.text.lower(), "security.txt présent", "security.txt absent ou sans Contact")

    # ------------------------------------------------------------ contenu des pages
    def page_checks():
        host = urllib.parse.urlsplit(ctx.base).hostname or ""
        third, no_sri, mixed = set(), [], []
        for p in pages:
            for s in p.doc.scripts:
                u = s.get("_abs")
                if u and urllib.parse.urlsplit(u).hostname and registrable(urllib.parse.urlsplit(u).hostname) != registrable(host):
                    third.add(urllib.parse.urlsplit(u).hostname)
                    if not s.get("integrity"):
                        no_sri.append(u)
            for l in p.doc.links:
                u = l.get("_abs") or ""
                if "stylesheet" in l.get("rel", "") and u.startswith("http") and registrable(urllib.parse.urlsplit(u).hostname or "") != registrable(host):
                    if not l.get("integrity") and "fonts.googleapis.com" not in u:
                        no_sri.append(u)
            if p.url.startswith("https://"):
                for u in ([s.get("_abs") for s in p.doc.scripts] + [l.get("_abs") for l in p.doc.links if "stylesheet" in l.get("rel", "") or "icon" in l.get("rel", "")]
                          + [i.get("_abs") for i in p.doc.imgs] + [f.get("_abs") for f in p.doc.iframes]):
                    if u and u.startswith("http://"):
                        mixed.append(f"{p.url} → {u}")
        no_sri = sorted(set(no_sri))
        R.check("SEC-17", not no_sri, "Ressources tierces avec SRI ou aucune", "Scripts/CSS tiers sans integrity", no_sri, soft=True)
        R.check("SEC-18", not mixed, "Aucun contenu mixte", "Ressources HTTP sur pages HTTPS", mixed)
        R.add("SEC-23", "pass" if not third else "warn", f"{len(third)} domaine(s) de scripts tiers", sorted(third))
        # CSRF + mots de passe
        post_forms, no_token, pw_issues = 0, [], []
        for p in pages:
            for f in p.doc.forms:
                method = (f.get("method") or "get").lower()
                inputs = f["_inputs"]
                if method == "post":
                    post_forms += 1
                    if not any(CSRF_FIELDS.search(i.get("name", "") or "") for i in inputs):
                        no_token.append(f"{p.url} → form action={f.get('action') or '(même page)'}")
                for i in inputs:
                    if (i.get("type") or "").lower() == "password":
                        ac = (i.get("autocomplete") or "").lower()
                        if ac not in ("current-password", "new-password"):
                            pw_issues.append(f"{p.url} → champ {i.get('name') or i.get('id') or '?'} autocomplete='{ac or '(absent)'}'")
                        if (f.get("_abs") or "").startswith("http://") and not ctx.is_local:
                            pw_issues.append(f"{p.url} → mot de passe envoyé en HTTP")
        if post_forms == 0:
            spa = any(re.search(r"fetch\(|axios|XMLHttpRequest", s) for p in pages for s in p.doc.inline_scripts)
            if ctx.pages and (spa or any(p.doc.inputs_outside_forms for p in pages)):
                R.manual("SEC-19", "Pas de <form method=post> : formulaires en JS/API",
                         note="Vérifier côté API : token CSRF (double-submit / en-tête) ou cookies SameSite=Strict + vérification Origin.")
            else:
                R.na("SEC-19", "Aucun formulaire POST trouvé")
        else:
            samesite_ok = all("samesite=lax" in c.lower() or "samesite=strict" in c.lower() for c in home.hs("set-cookie")) and home.hs("set-cookie")
            if no_token:
                (R.warn if samesite_ok else R.ko)("SEC-19", f"{len(no_token)}/{post_forms} formulaire(s) POST sans jeton CSRF visible", no_token,
                                                  note="Cookies SameSite présents : risque réduit mais jeton recommandé." if samesite_ok else "")
            else:
                R.ok("SEC-19", f"{post_forms} formulaire(s) POST avec jeton")
        has_pw = any((i.get("type") or "").lower() == "password" for p in pages for f in p.doc.forms for i in f["_inputs"])
        if has_pw:
            R.check("SEC-21", not pw_issues, "Champs mot de passe corrects", "Champs mot de passe à corriger", pw_issues, soft=True)
        else:
            R.na("SEC-21", "Aucun champ mot de passe trouvé")

    R.guard(["SEC-01", "SEC-02", "SEC-03", "SEC-04", "SEC-05", "SEC-06", "SEC-07", "SEC-08", "SEC-24"], headers_checks)
    R.guard(["SEC-09", "SEC-10", "SEC-11"], cookies_checks)
    R.guard(["SEC-12"], cors_checks)
    R.guard(["SEC-13", "SEC-14", "SEC-22"], exposure_checks)
    R.guard(["SEC-15", "SEC-16", "SEC-20"], error_checks)
    R.guard(["SEC-17", "SEC-18", "SEC-19", "SEC-21", "SEC-23"], page_checks)
