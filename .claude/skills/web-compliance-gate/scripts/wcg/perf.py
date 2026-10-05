"""Performance (Lighthouse + mesures HTTP) et accessibilité (Lighthouse + contrôles HTML)."""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import ssl
import statistics
import subprocess
import tempfile
import urllib.parse
from pathlib import Path


LH_IDS = ["PERF-01", "PERF-02", "PERF-03", "PERF-04", "PERF-05", "PERF-19", "SEO-34", "A11Y-01"]


def _lighthouse(ctx, url):
    npx = shutil.which("npx")
    if not npx:
        return None, "Node.js/npx introuvable"
    env = dict(os.environ)
    if not env.get("CHROME_PATH") and getattr(ctx, "chromium_path", None):
        env["CHROME_PATH"] = ctx.chromium_path
    out = Path(tempfile.mkdtemp()) / "lh.json"
    flags = "--headless=new --no-sandbox --disable-gpu" + (" --ignore-certificate-errors" if ctx.is_local and url.startswith("https") else "")
    cmd = [npx, "-y", "lighthouse@12", url, "--output=json", f"--output-path={out}", "--quiet",
           f"--chrome-flags={flags}", "--only-categories=performance,accessibility,best-practices,seo",
           "--max-wait-for-load=45000"]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=240, env=env, shell=os.name == "nt")
    except subprocess.TimeoutExpired:
        return None, "Lighthouse : délai dépassé"
    if not out.exists():
        return None, f"Lighthouse a échoué : {p.stderr.decode('utf-8', 'replace')[-300:]}"
    try:
        return json.loads(out.read_text()), ""
    except Exception as e:  # noqa: BLE001
        return None, f"Rapport Lighthouse illisible ({e})"


def run(ctx):
    R = ctx.results
    R.guard(LH_IDS, _lh_all, ctx)
    R.guard(["PERF-06", "PERF-07", "PERF-08", "PERF-11", "PERF-12", "PERF-13", "PERF-14", "PERF-15", "PERF-16", "PERF-18", "PERF-20"], _http_perf, ctx)
    R.guard(["A11Y-03", "A11Y-04", "A11Y-05", "A11Y-06"], _a11y_html, ctx)


def _lh_all(ctx):
    R = ctx.results
    if ctx.opts.no_lighthouse:
        for fid in LH_IDS:
            R.err(fid, "Lighthouse désactivé (--no-lighthouse)")
        return
    urls = [ctx.base]
    others = [p.url for p in ctx.pages[1:] if p.url.rstrip("/") != ctx.base.rstrip("/")]
    urls += others[: max(0, ctx.opts.lh_pages - 1)]
    reports = []
    err = ""
    for u in urls:
        rep, err = _lighthouse(ctx, u)
        if rep:
            reports.append((u, rep))
    if not reports:
        for fid in LH_IDS:
            R.err(fid, err or "Lighthouse indisponible", note="Nécessite Node.js + Chrome/Chromium (CHROME_PATH).")
        return
    ctx.lighthouse = reports

    def worst(cat):
        vals = [(r["categories"].get(cat, {}).get("score"), u) for u, r in reports if r["categories"].get(cat, {}).get("score") is not None]
        return min(vals) if vals else (None, None)

    def failing_audits(cat, limit=12):
        out = []
        for u, r in reports:
            refs = r["categories"].get(cat, {}).get("auditRefs", [])
            for ref in refs:
                a = r["audits"].get(ref["id"], {})
                if a.get("score") is not None and a["score"] < 0.9 and ref.get("weight", 0) > 0 or (a.get("details", {}).get("type") == "opportunity" and a.get("score", 1) < 0.9):
                    dv = a.get("displayValue", "")
                    out.append(f"{u} — {a.get('title', ref['id'])}{' : ' + dv if dv else ''}")
        return list(dict.fromkeys(out))[:limit]

    for fid, cat, label in (("PERF-01", "performance", "Performance"), ("PERF-19", "best-practices", "Best Practices"),
                            ("SEO-34", "seo", "SEO"), ("A11Y-01", "accessibility", "Accessibilité")):
        sc, u = worst(cat)
        if sc is None:
            R.err(fid, f"Score {label} indisponible")
            continue
        s100 = round(sc * 100)
        det = failing_audits(cat)
        if s100 >= 90:
            R.ok(fid, f"{label} {s100}/100 (pire page : {u})", det)
        elif s100 >= 75 and fid != "PERF-01":
            R.warn(fid, f"{label} {s100}/100", det)
        elif s100 >= 80 and fid == "PERF-01":
            R.warn(fid, f"{label} {s100}/100 (mobile, throttling 4G lente)", det)
        else:
            R.ko(fid, f"{label} {s100}/100", det)

    def metric(aid):
        vals = [r["audits"].get(aid, {}).get("numericValue") for _, r in reports]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None
    for fid, aid, good, poor, fmt in (("PERF-02", "largest-contentful-paint", 2500, 4000, lambda v: f"{v / 1000:.2f} s"),
                                      ("PERF-03", "cumulative-layout-shift", 0.1, 0.25, lambda v: f"{v:.3f}"),
                                      ("PERF-04", "total-blocking-time", 200, 600, lambda v: f"{v:.0f} ms"),
                                      ("PERF-05", "first-contentful-paint", 1800, 3000, lambda v: f"{v / 1000:.2f} s")):
        v = metric(aid)
        if v is None:
            R.err(fid, "Mesure indisponible")
        elif v <= good:
            R.ok(fid, fmt(v))
        elif v <= poor:
            R.warn(fid, f"{fmt(v)} (à améliorer)")
        else:
            R.ko(fid, f"{fmt(v)} (mauvais)")
    ttfb = metric("server-response-time")
    if ttfb is not None:
        ctx.lh_ttfb = ttfb


def _head(ctx, url):
    r = ctx.http.get(url, method="HEAD")
    if r.status in (405, 501, 0) or not r.h("content-length"):
        r = ctx.http.get(url)
        return r, len(r.body) if r.body else int(r.h("content-length") or 0)
    return r, int(r.h("content-length") or 0)


def _http_perf(ctx):
    R = ctx.results
    pages = ctx.pages
    host = urllib.parse.urlsplit(ctx.base).hostname or ""
    # TTFB
    times = []
    for _ in range(3):
        r = ctx.http.get(ctx.base, use_cache=False)
        if r.status:
            times.append(r.elapsed * 1000)
    ttfb = getattr(ctx, "lh_ttfb", None) or (statistics.median(times) if times else None)
    if ttfb is None:
        R.err("PERF-06", "Mesure impossible")
    else:
        R.check("PERF-06", ttfb <= 800, f"{ttfb:.0f} ms", f"{ttfb:.0f} ms (> 800 ms)", soft=ttfb <= 1800,
                note="Mesuré depuis la machine d'audit ; en local la latence réseau est quasi nulle." if ctx.is_local else "")
    # inventaire des assets même origine
    assets = {"css": set(), "js": set(), "img": set(), "font": set()}
    for p in pages[:10]:
        for s in p.doc.scripts:
            u = s.get("_abs")
            if u and urllib.parse.urlsplit(u).hostname == host:
                assets["js"].add(u)
        for l in p.doc.links:
            u = l.get("_abs") or ""
            if urllib.parse.urlsplit(u).hostname != host:
                continue
            rel = l.get("rel", "").lower()
            if "stylesheet" in rel:
                assets["css"].add(u)
            elif "preload" in rel and l.get("as") == "font":
                assets["font"].add(u)
        for i in p.doc.imgs:
            u = i.get("_abs")
            if u and urllib.parse.urlsplit(u).hostname == host and not u.startswith("data:"):
                assets["img"].add(u)
    # compression
    uncompressed = []
    for u in [ctx.base] + sorted(assets["css"])[:8] + sorted(assets["js"])[:12]:
        r = ctx.http.get(u, headers={"Accept-Encoding": "br, gzip"}, use_cache=False)
        size = len(r.body)
        if r.status == 200 and size > 1400 and r.h("content-encoding").lower() not in ("gzip", "br", "zstd", "deflate"):
            uncompressed.append(f"{u} ({size / 1024:.0f} Ko)")
    R.check("PERF-07", not uncompressed, "Ressources texte compressées", f"{len(uncompressed)} ressource(s) non compressée(s)", uncompressed)
    # cache
    short = []
    statics = sorted(assets["css"])[:8] + sorted(assets["js"])[:12] + sorted(assets["img"])[:12] + sorted(assets["font"])[:4]
    for u in statics:
        r = ctx.http.get(u, method="HEAD")
        if r.status in (405, 501):
            r = ctx.http.get(u)
        cc = r.h("cache-control").lower()
        m = re.search(r"max-age=(\d+)", cc)
        age = int(m.group(1)) if m else 0
        if "immutable" in cc or age >= 2592000:
            continue
        if not cc and r.h("expires"):
            continue
        short.append(f"{u} → Cache-Control: {cc or '(absent)'}")
    if statics:
        R.check("PERF-08", not short, f"{len(statics)} asset(s) avec cache long", f"{len(short)}/{len(statics)} asset(s) sans cache long", short,
                soft=len(short) <= len(statics) // 2, note="En dev (vite/webpack dev server) le cache est désactivé : tester le build de production." if ctx.is_local else "")
    else:
        R.na("PERF-08", "Aucun asset statique même origine")
    # images
    legacy, no_dim, heavy, not_lazy = [], [], [], []
    for p in pages[:10]:
        for i in p.doc.imgs:
            u = i.get("_abs") or ""
            if u.startswith("data:"):
                continue
            if "width" not in i or "height" not in i:
                if not re.search(r"aspect-ratio", i.get("style", "") + i.get("class", "")):
                    no_dim.append(f"{p.url} → {i.get('src', '')[:80]}")
            if i["_index"] >= 3 and i.get("loading", "").lower() != "lazy":
                not_lazy.append(f"{p.url} → {i.get('src', '')[:80]}")
    for u in sorted(assets["img"])[:30]:
        r, size = _head(ctx, u)
        ext = urllib.parse.urlsplit(u).path.lower().rsplit(".", 1)[-1]
        ct = r.h("content-type").lower()
        if (ext in ("jpg", "jpeg", "png", "gif", "bmp") or ct in ("image/jpeg", "image/png", "image/gif")) and size > 15_000:
            legacy.append(f"{u} ({size / 1024:.0f} Ko, {ct or ext})")
        if size > 300_000:
            heavy.append(f"{u} ({size / 1024:.0f} Ko)")
    if assets["img"]:
        R.check("PERF-11", not legacy, "Images en WebP/AVIF ou légères", f"{len(legacy)} image(s) JPEG/PNG à convertir", legacy, soft=len(legacy) <= 2)
        R.check("PERF-20", not heavy, "Aucune image > 300 Ko", f"{len(heavy)} image(s) > 300 Ko", heavy)
    else:
        R.na("PERF-11", "Aucune image même origine")
        R.na("PERF-20", "Aucune image même origine")
    total_imgs = sum(len(p.doc.imgs) for p in pages[:10])
    if total_imgs:
        R.check("PERF-12", not no_dim, "width/height présents", f"{len(no_dim)} image(s) sans dimensions", no_dim, soft=len(no_dim) <= 2)
        R.check("PERF-13", not not_lazy, "Lazy-loading en place", f"{len(not_lazy)} image(s) hors écran sans loading=lazy", not_lazy, soft=True)
    else:
        R.na("PERF-12", "Aucune image")
        R.na("PERF-13", "Aucune image")
    # scripts bloquants
    blocking = []
    for p in pages[:10]:
        for s in p.doc.scripts:
            if s["_in_head"] and s.get("src") and "async" not in s and "defer" not in s and (s.get("type") or "").lower() not in ("module", "application/ld+json", "text/plain"):
                blocking.append(f"{p.url} → {s.get('src')[:90]}")
    blocking = list(dict.fromkeys(blocking))
    R.check("PERF-14", not blocking, "Aucun script bloquant dans le <head>", f"{len(blocking)} script(s) bloquant(s)", blocking)
    # polices
    css_text = " ".join(" ".join(p.doc.inline_styles) for p in pages[:5])
    for u in sorted(assets["css"])[:8]:
        css_text += ctx.http.get(u).text[:500_000]
    faces = re.findall(r"@font-face\s*\{[^}]*\}", css_text, re.I)
    no_display = [f[:90] for f in faces if "font-display" not in f.lower()]
    if faces:
        R.check("PERF-15", not no_display, f"{len(faces)} @font-face avec font-display", f"{len(no_display)} @font-face sans font-display", no_display, soft=True)
    else:
        R.na("PERF-15", "Aucune police web auto-hébergée détectée")
    # minification
    notmin = []
    for u in sorted(assets["css"])[:8] + sorted(assets["js"])[:12]:
        t = ctx.http.get(u).text
        if len(t) > 6000:
            lines = t.count("\n") + 1
            if len(t) / lines < 60 and not re.search(r"\.min\.(js|css)", u):
                notmin.append(f"{u} ({len(t) / 1024:.0f} Ko, {lines} lignes)")
    if assets["css"] or assets["js"]:
        R.check("PERF-18", not notmin, "CSS/JS minifiés", f"{len(notmin)} fichier(s) non minifié(s)", notmin, soft=True,
                note="Serveur de dev détecté ? Tester le build de production." if ctx.is_local and notmin else "")
    else:
        R.na("PERF-18", "Aucun CSS/JS externe même origine")
    # HTTP/2
    target = ctx.prod_url or (ctx.base if ctx.base.startswith("https") else None)
    if not target:
        R.na("PERF-16", "Site local en HTTP : tester en prod (--prod-url)")
    else:
        u = urllib.parse.urlsplit(target)
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        c.set_alpn_protocols(["h2", "http/1.1"])
        with socket.create_connection((u.hostname, u.port or 443), timeout=10) as sock:
            with c.wrap_socket(sock, server_hostname=u.hostname) as s:
                proto = s.selected_alpn_protocol()
        alt = ctx.http.get(target).h("alt-svc")
        R.check("PERF-16", proto == "h2", f"ALPN : {proto}{' + HTTP/3 annoncé' if 'h3' in alt else ''}", f"HTTP/2 non négocié (ALPN : {proto or 'aucun'})")


def _a11y_html(ctx):
    R = ctx.results
    pages = ctx.pages
    unlabeled, unnamed, zoom = [], [], []
    main_missing, skip_missing = [], []
    for p in pages:
        d = p.doc
        fields = [i for f in d.forms for i in f["_inputs"]] + d.inputs_outside_forms
        for i in fields:
            t = (i.get("type") or "text").lower()
            if i.get("_tag") == "button" or t in ("hidden", "submit", "button", "reset", "image"):
                continue
            if not (i.get("id") in d.labels_for or i.get("_wrapped_label") or i.get("aria-label") or i.get("aria-labelledby") or i.get("title")):
                unlabeled.append(f"{p.url} → {i.get('_tag')} name={i.get('name') or '?'}")
        for b in d.buttons:
            if not ((b.get("_text") or "").strip() or b.get("aria-label") or b.get("aria-labelledby") or b.get("title") or b.get("_img_alt")):
                unnamed.append(f"{p.url} → <button class='{b.get('class', '')[:40]}'>")
        for a in d.anchors:
            if a.get("href") and not ((a.get("_text") or "").strip() or a.get("aria-label") or a.get("aria-labelledby") or a.get("title") or a.get("_img_alt")):
                unnamed.append(f"{p.url} → <a href='{a.get('href', '')[:60]}'>")
        vp = (d.meta(name="viewport") or "").lower().replace(" ", "")
        if "user-scalable=no" in vp or "user-scalable=0" in vp or re.search(r"maximum-scale=(1(\.0)?|0\.\d)(,|$)", vp):
            zoom.append(f"{p.url} : {vp}")
        if not d.has_main:
            main_missing.append(p.url)
        if not any((a.get("href") or "").startswith("#") and re.search(r"(contenu|content|skip|aller au|passer)", a.get("_text", ""), re.I) for a in d.anchors):
            skip_missing.append(p.url)
    unlabeled = list(dict.fromkeys(unlabeled))
    unnamed = list(dict.fromkeys(unnamed))
    if any(f for p in pages for f in p.doc.forms) or any(p.doc.inputs_outside_forms for p in pages):
        R.check("A11Y-03", not unlabeled, "Tous les champs ont un label", f"{len(unlabeled)} champ(s) sans label", unlabeled)
    else:
        R.na("A11Y-03", "Aucun champ de formulaire")
    R.check("A11Y-04", not unnamed, "Boutons et liens nommés", f"{len(unnamed)} bouton(s)/lien(s) sans nom accessible", unnamed)
    R.check("A11Y-05", not zoom, "Zoom autorisé", "Zoom bloqué", zoom)
    probs = [f"<main> absent : {u}" for u in main_missing[:10]] + ([f"Lien d'évitement absent ({len(skip_missing)} page(s))"] if skip_missing else [])
    R.check("A11Y-06", not probs, "Repères et lien d'évitement présents", "Structure à compléter", probs, soft=True)
