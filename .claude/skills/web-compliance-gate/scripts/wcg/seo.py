"""Contrôles SEO technique et on-page sur toutes les pages crawlées."""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict

from .core import norm, same_site


def run(ctx):
    R = ctx.results
    pages = ctx.pages
    if not pages:
        from .catalog import CHECKS
        for fid in [k for k in CHECKS if k.startswith("SEO-") and k not in ("SEO-31", "SEO-34")]:
            R.err(fid, "Aucune page HTML récupérée")
        return
    content_pages = [p for p in pages if not re.search(r"(mentions|legal|confidentialit|privacy|cookies|cgv|cgu|conditions|plan-du-site|contact|login|connexion|inscription|panier|cart|checkout|compte|account|404)", p.url, re.I)]

    def onpage():
        no_title, bad_len_t, titles = [], [], defaultdict(list)
        no_desc, bad_len_d, descs = [], [], defaultdict(list)
        h1_issues, hier, no_lang, no_vp, canon_issues, noindex, no_charset = [], [], [], [], [], [], []
        og_missing, tw_missing, favicon_missing, thin, no_alt = [], [], [], [], []
        jsonld_ok, jsonld_bad, dup_hash = [], [], defaultdict(list)
        imgs_total = 0
        for p in pages:
            d = p.doc
            t = (d.title or "").strip()
            if not t:
                no_title.append(p.url)
            else:
                titles[t].append(p.url)
                if not 30 <= len(t) <= 60:
                    bad_len_t.append(f"{p.url} ({len(t)} car.) « {t[:70]} »")
            desc = (d.meta(name="description") or "").strip()
            if not desc:
                no_desc.append(p.url)
            else:
                descs[desc].append(p.url)
                if not 70 <= len(desc) <= 160:
                    bad_len_d.append(f"{p.url} ({len(desc)} car.)")
            h1 = [h for h in d.headings if h[0] == 1]
            if len(h1) != 1:
                h1_issues.append(f"{p.url} ({len(h1)} H1)")
            prev = 0
            for lvl, txt in d.headings:
                if prev and lvl > prev + 1:
                    hier.append(f"{p.url} : H{prev} → H{lvl} « {txt[:40]} »")
                    break
                prev = lvl
            if not d.lang:
                no_lang.append(p.url)
            if not d.meta(name="viewport"):
                no_vp.append(p.url)
            if not d.charset and "charset" not in (d.meta(http_equiv="content-type") or "").lower() and "charset" not in p.resp.h("content-type").lower():
                no_charset.append(p.url)
            can = d.link_rel("canonical")
            if not can:
                canon_issues.append(f"{p.url} : absente")
            elif len(can) > 1:
                canon_issues.append(f"{p.url} : {len(can)} canonical")
            else:
                href = can[0].get("href", "")
                if not href.startswith("http"):
                    canon_issues.append(f"{p.url} : canonical relative « {href} »")
                elif not same_site(href, ctx.base) and not ctx.prod_url:
                    canon_issues.append(f"{p.url} : canonical vers autre domaine {href}")
            robots = " ".join(filter(None, [d.meta(name="robots") or "", d.meta(name="googlebot") or "", p.resp.h("x-robots-tag")])).lower()
            if "noindex" in robots:
                noindex.append(f"{p.url} ({robots})")
            if not all(d.meta(prop=k) for k in ("og:title", "og:description", "og:image")):
                og_missing.append(p.url)
            if not d.meta(name="twitter:card"):
                tw_missing.append(p.url)
            if not (d.link_rel("icon") or d.link_rel("shortcut")):
                favicon_missing.append(p.url)
            words = len(re.findall(r"\w{2,}", d.text))
            if p in content_pages and words < 250:
                thin.append(f"{p.url} ({words} mots)")
            for img in d.imgs:
                imgs_total += 1
                if "alt" not in img:
                    no_alt.append(f"{p.url} → {img.get('src', '')[:90]}")
            for block in d.jsonld:
                try:
                    data = json.loads(block)
                    items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
                    types = [i.get("@type") for i in items if isinstance(i, dict)]
                    ctx_ok = isinstance(data, list) or "schema.org" in str(data.get("@context", "")) if isinstance(data, dict) else True
                    (jsonld_ok if ctx_ok and any(types) else jsonld_bad).append(f"{p.url} : {types or 'sans @type'}")
                except Exception as e:  # noqa: BLE001
                    jsonld_bad.append(f"{p.url} : JSON invalide ({e})")
            body_sig = hashlib.md5(norm(d.text).encode()).hexdigest()
            if len(d.text) > 200:
                dup_hash[body_sig].append(p.url)
        n = len(pages)
        R.check("SEO-01", not no_title, f"{n} pages avec title", f"{len(no_title)} page(s) sans title", no_title)
        R.check("SEO-02", not bad_len_t, "Longueurs de title correctes", f"{len(bad_len_t)} title(s) hors 30-60 car.", bad_len_t, soft=True)
        dup_t = [f"« {t[:60]} » ×{len(u)} : {', '.join(u[:4])}" for t, u in titles.items() if len(u) > 1]
        R.check("SEO-03", not dup_t, "Titles uniques", f"{len(dup_t)} title(s) dupliqué(s)", dup_t)
        R.check("SEO-04", not no_desc, "Meta descriptions présentes", f"{len(no_desc)} page(s) sans meta description", no_desc)
        R.check("SEO-05", not bad_len_d, "Longueurs de description correctes", f"{len(bad_len_d)} description(s) hors 70-160 car.", bad_len_d, soft=True)
        dup_d = [f"×{len(u)} : {', '.join(u[:4])}" for t, u in descs.items() if len(u) > 1]
        R.check("SEO-06", not dup_d, "Descriptions uniques", f"{len(dup_d)} description(s) dupliquée(s)", dup_d, soft=True)
        R.check("SEO-07", not h1_issues, "Un H1 par page", f"{len(h1_issues)} page(s) sans H1 unique", h1_issues)
        R.check("SEO-08", not hier, "Hiérarchie Hn correcte", f"{len(hier)} saut(s) de niveau", hier, soft=True)
        R.check("SEO-09", not no_lang, "lang présent", f"{len(no_lang)} page(s) sans lang", no_lang)
        R.check("SEO-10", not no_vp, "viewport présent", f"{len(no_vp)} page(s) sans viewport", no_vp)
        R.check("SEO-11", not canon_issues, "Canonicals valides", f"{len(canon_issues)} problème(s) de canonical", canon_issues)
        if noindex:
            if ctx.is_local:
                R.warn("SEO-12", f"{len(noindex)} page(s) en noindex (local)", noindex, note="Normal en préprod si voulu : vérifier que la prod n'a PAS ce noindex.")
            else:
                R.ko("SEO-12", f"{len(noindex)} page(s) en noindex", noindex)
        else:
            R.ok("SEO-12", "Aucun noindex")
        R.check("SEO-17", not no_alt, f"{imgs_total} image(s), toutes avec alt", f"{len(no_alt)} image(s) sans alt", no_alt)
        R.check("SEO-22", not og_missing, "Open Graph complet", f"{len(og_missing)} page(s) sans OG complet", og_missing, soft=True)
        R.check("SEO-23", not tw_missing, "Twitter card présente", f"{len(tw_missing)} page(s) sans twitter:card", tw_missing, soft=True)
        if jsonld_bad:
            R.ko("SEO-24", "JSON-LD invalide", jsonld_bad + jsonld_ok)
        elif jsonld_ok:
            R.ok("SEO-24", f"JSON-LD présent sur {len(jsonld_ok)} page(s)", jsonld_ok)
        else:
            R.ko("SEO-24", "Aucune donnée structurée JSON-LD")
        R.check("SEO-25", not favicon_missing, "Favicon déclaré", "Favicon non déclaré", favicon_missing[:5], soft=True)
        R.check("SEO-26", not thin, "Contenu suffisant", f"{len(thin)} page(s) à contenu mince", thin, soft=True)
        dups = [", ".join(u) for u in dup_hash.values() if len(u) > 1]
        R.check("SEO-27", not dups, "Pas de contenu dupliqué", f"{len(dups)} groupe(s) de pages identiques", dups)
        R.check("SEO-33", not no_charset, "Encodage déclaré", "Encodage non déclaré", no_charset, soft=True)
        # hreflang
        hl = [(p.url, l) for p in pages for l in p.doc.links if "alternate" in l.get("rel", "") and l.get("hreflang")]
        if not hl:
            R.na("SEO-29", "Site monolingue (pas de hreflang)")
        else:
            bad = [f"{u} → {l.get('href')}" for u, l in hl if not (l.get("href") or "").startswith("http")]
            has_xdef = any(l.get("hreflang") == "x-default" for _, l in hl)
            if not has_xdef:
                bad.append("x-default absent")
            R.check("SEO-29", not bad, f"{len(hl)} hreflang", "hreflang incomplet", bad, soft=True)
        # URLs propres
        ugly = [p.url for p in pages if re.search(r"[A-Z]|_|%20|\.php\?|\?.*=.*&.*=|/index\.(php|html)$", urllib.parse.urlsplit(p.url).path + ("?" + urllib.parse.urlsplit(p.url).query if urllib.parse.urlsplit(p.url).query else ""))]
        R.check("SEO-28", not ugly, "URLs propres", f"{len(ugly)} URL(s) peu lisible(s)", ugly, soft=True)
        # liens crawlables
        js_links = []
        for p in pages:
            for a in p.doc.anchors:
                href = (a.get("href") or "").strip()
                if a.get("role") == "button" or re.search(r"cookie|consent|menu|fermer|close|ouvrir", a.get("_text", "") + a.get("id", ""), re.I):
                    continue
                if (not href or href.startswith("javascript:") or href == "#") and (a.get("onclick") or a.get("_text", "").strip()):
                    js_links.append(f"{p.url} → « {a.get('_text', '').strip()[:40]} »")
        R.check("SEO-32", not js_links, "Liens en <a href>", f"{len(js_links)} lien(s) sans href réel", js_links, soft=True)

    def indexation():
        root = ctx.base.rstrip("/")
        rob = ctx.http.get(root + "/robots.txt")
        sitemaps = []
        if rob.status == 200 and "html" not in rob.ctype and not ctx.is_ghost(rob):
            txt = rob.text
            sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", txt)
            block_all = False
            ua = None
            for line in txt.splitlines():
                line = line.split("#")[0].strip()
                if line.lower().startswith("user-agent:"):
                    ua = line.split(":", 1)[1].strip()
                elif line.lower().startswith("disallow:") and ua in ("*", "Googlebot") and line.split(":", 1)[1].strip() == "/":
                    block_all = True
            probs = []
            if block_all:
                probs.append("Disallow: / pour tous les robots")
            if not sitemaps:
                probs.append("Aucune ligne Sitemap:")
            if block_all and not ctx.is_local:
                R.ko("SEO-13", "robots.txt bloque tout le site", probs)
            else:
                R.check("SEO-13", not probs, "robots.txt correct", "robots.txt incomplet", probs, soft=not block_all or ctx.is_local)
        else:
            R.ko("SEO-13", "robots.txt absent" + (" (le serveur renvoie une page HTML à la place)" if rob.status == 200 else f" (statut {rob.status})"))
        sm_urls, sm_candidates = [], sitemaps or [root + "/sitemap.xml", root + "/sitemap_index.xml", root + "/wp-sitemap.xml"]
        found = None
        for sm in sm_candidates:
            if ctx.is_local and sitemaps:
                # un sitemap déclaré avec le domaine de prod : on le relit sur l'hôte local
                sm = root + urllib.parse.urlsplit(sm).path
            r = ctx.http.get(sm)
            if r.status == 200 and not ctx.is_ghost(r) and ("xml" in r.ctype or r.text.lstrip().startswith("<?xml") or "<urlset" in r.text[:500]):
                found = (sm, r)
                break
        if not found:
            R.ko("SEO-14", "Aucun sitemap XML trouvé", sm_candidates)
            R.na("SEO-15", "Pas de sitemap")
            R.na("SEO-16", "Pas de sitemap")
            ctx.sitemap_urls = []
            return
        sm, r = found
        try:
            tree = ET.fromstring(r.body)
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = [e.text.strip() for e in tree.findall(".//s:loc", ns) if e.text]
            if tree.tag.endswith("sitemapindex"):
                for child in locs[:10]:
                    cr = ctx.http.get(root + urllib.parse.urlsplit(child).path if ctx.is_local else child)
                    try:
                        sm_urls += [e.text.strip() for e in ET.fromstring(cr.body).findall(".//s:loc", ns) if e.text]
                    except ET.ParseError:
                        pass
            else:
                sm_urls = locs
            R.check("SEO-14", bool(sm_urls), f"{sm} valide ({len(sm_urls)} URL)", f"{sm} vide")
        except ET.ParseError as e:
            R.ko("SEO-14", f"{sm} : XML invalide ({e})")
            ctx.sitemap_urls = []
            return
        ctx.sitemap_urls = sm_urls
        bad = []
        for u in sm_urls[:60]:
            test = root + urllib.parse.urlsplit(u).path if ctx.is_local else u
            rr = ctx.http.get(test, follow=False)
            if rr.status != 200:
                bad.append(f"{u} → {rr.status}")
        R.check("SEO-15", not bad, f"{min(len(sm_urls), 60)} URL du sitemap en 200", f"{len(bad)} URL du sitemap non-200", bad)
        paths = {urllib.parse.urlsplit(u).path.rstrip("/") for u in sm_urls}
        missing = [p.url for p in pages if urllib.parse.urlsplit(p.url).path.rstrip("/") not in paths and p.resp.status == 200]
        R.check("SEO-16", not missing, "Pages crawlées présentes dans le sitemap", f"{len(missing)} page(s) absente(s) du sitemap", missing, soft=True)

    def links():
        internal_broken = [f"{u} ({s}) ← {src}" for u, s, src in ctx.crawler.broken if src != "sitemap"]
        R.check("SEO-18", not internal_broken, f"{len(ctx.crawler.seen)} URL internes testées, aucune cassée", f"{len(internal_broken)} lien(s) interne(s) cassé(s)", internal_broken)
        # redirections
        chains = []
        for u, s in ctx.crawler.link_status.items():
            r = ctx.http.cache.get((u, "GET", (), True))
            if r and len(r.chain) > 1:
                chains.append(" → ".join([c[0] for c in r.chain] + [r.url]))
        R.check("SEO-20", not chains, "Aucune chaîne de redirection", f"{len(chains)} chaîne(s)", chains, soft=True)
        # externes
        if ctx.opts.external_links:
            ext = {a.get("_abs") for p in pages for a in p.doc.anchors if (a.get("_abs") or "").startswith("http") and not same_site(a.get("_abs"), ctx.base)}
            dead = []
            for u in sorted(ext)[:80]:
                r = ctx.http.get(u, method="HEAD")
                if r.status in (405, 403, 0):
                    r = ctx.http.get(u)
                if r.status >= 400 and r.status not in (401, 403, 429, 999) or r.status == 0:
                    dead.append(f"{u} → {r.status or r.error[:60]}")
            R.check("SEO-19", not dead, f"{min(len(ext), 80)} lien(s) externe(s) OK", f"{len(dead)} lien(s) externe(s) cassé(s)", dead, soft=True)
        else:
            R.na("SEO-19", "Désactivé (ajouter --external-links)")
        # soft 404
        r = ctx.http.get(ctx.base.rstrip("/") + "/wcg-cette-page-nexiste-pas-4d2c", use_cache=False)
        R.check("SEO-21", r.status == 404 or r.status == 410, f"Route inconnue → {r.status}", f"Route inconnue → {r.status} (soft-404)")

    def consolidation():
        if ctx.is_local and not ctx.prod_url:
            R.na("SEO-30", "Test des variantes de domaine réservé à la prod (--prod-url)")
            return
        u = urllib.parse.urlsplit(ctx.prod_url or ctx.base)
        host = u.hostname
        alt = host[4:] if host.startswith("www.") else "www." + host
        final = {}
        for scheme in ("http", "https"):
            for h in (host, alt):
                r = ctx.http.get(f"{scheme}://{h}/")
                if r.status:
                    final[f"{scheme}://{h}/"] = (r.status, r.url)
        dest = {v[1].rstrip("/") for v in final.values() if v[0] == 200}
        R.check("SEO-30", len(dest) <= 1, f"Toutes les variantes → {', '.join(dest)}", "Plusieurs versions du site accessibles",
                [f"{k} → {v[0]} {v[1]}" for k, v in final.items()])

    R.guard(["SEO-01", "SEO-02", "SEO-03", "SEO-04", "SEO-05", "SEO-06", "SEO-07", "SEO-08", "SEO-09", "SEO-10", "SEO-11", "SEO-12",
             "SEO-17", "SEO-22", "SEO-23", "SEO-24", "SEO-25", "SEO-26", "SEO-27", "SEO-28", "SEO-29", "SEO-32", "SEO-33"], onpage)
    R.guard(["SEO-13", "SEO-14", "SEO-15", "SEO-16"], indexation)
    R.guard(["SEO-18", "SEO-19", "SEO-20", "SEO-21"], links)
    R.guard(["SEO-30"], consolidation)
