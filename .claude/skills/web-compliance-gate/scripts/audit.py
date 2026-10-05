#!/usr/bin/env python3
"""web-compliance-gate — audit complet RGPD · SEO · Sécurité · SSL/TLS · Performance · Accessibilité.

Exemples :
  python audit.py --url http://localhost:3000 --src .                      # fin de projet / audit local
  python audit.py --url https://client.fr --prod-url https://client.fr     # audit de prod complet (SSL inclus)
  python audit.py --url http://localhost:8000 --src . --only rgpd,secu     # re-test ciblé après corrections
  python audit.py --questions > answers.json                               # modèle des questions documentaires
  python audit.py --list-checks                                            # catalogue complet des contrôles

Sorties : <out>/report.md (lu par Claude), report.json (machine), report.html (client, jauges).
Code retour : 0 = VALIDÉ, 1 = autre verdict, 2 = site injoignable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wcg import browser, code, perf, rgpd, security_http, seo, stack, tls  # noqa: E402
from wcg.catalog import CATEGORIES, CHECKS, DOC_QUESTIONS, catalog_markdown  # noqa: E402
from wcg.core import Crawler, Http, Results, is_local_host  # noqa: E402
from wcg.report import score, write_all  # noqa: E402


class Ctx:
    pass


def seeds_from_sitemap(http, base, is_local, limit=25):
    root = base.rstrip("/")
    r = http.get(root + "/sitemap.xml")
    if r.status != 200:
        return []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
    if "<sitemapindex" in r.text and locs:
        sub = http.get(root + urllib.parse.urlsplit(locs[0]).path if is_local else locs[0])
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sub.text)
    if is_local:
        locs = [root + urllib.parse.urlsplit(u).path for u in locs]
    return locs[:limit]


def api_candidates(pages, base):
    out = set()
    for p in pages[:10]:
        blob = " ".join(p.doc.inline_scripts)
        for m in re.finditer(r"""(?:fetch|axios\.\w+|\$\.(?:get|post|ajax))\(\s*['"`](/[^'"`$]+)""", blob):
            out.add(urllib.parse.urljoin(base, m.group(1)))
    for guess in ("/api", "/api/", "/graphql", "/wp-json/"):
        out.add(urllib.parse.urljoin(base, guess))
    return sorted(out)[:6]


def doctor():
    import shutil
    rows = []

    def tool(name, cmd, why, install):
        path = shutil.which(cmd)
        rows.append((bool(path), name, why, install))

    rows.append((sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}", "moteur d'audit", "Python 3.9+"))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--no-sandbox"])
            b.close()
        rows.append((True, "Playwright + Chromium", "tests RGPD en navigateur, rendu, poids, axe", ""))
    except ImportError:
        rows.append((False, "Playwright", "tests RGPD en navigateur, rendu, poids, axe", "pip install playwright && python -m playwright install chromium"))
    except Exception:  # noqa: BLE001
        rows.append((False, "Chromium (Playwright)", "tests en navigateur", "python -m playwright install chromium  (Linux : --with-deps)"))
    tool("Node.js / npx", "npx", "Lighthouse, axe-core, npm audit", "https://nodejs.org (LTS)")
    tool("openssl", "openssl", "chaîne TLS, clé, signature, protocoles", "Linux/macOS : présent ; Windows : Git for Windows ou winget install ShiningLight.OpenSSL.Light")
    tool("Semgrep", "semgrep", "SAST OWASP Top 10 (SEC-C15)", "pipx install semgrep  (ou Docker semgrep/semgrep)")
    tool("Gitleaks", "gitleaks", "secrets dans l'historique git (SEC-C16)", "brew install gitleaks | winget install gitleaks | binaire GitHub")
    tool("pip-audit", "pip-audit", "CVE Python (si projet Python)", "pipx install pip-audit")
    tool("Composer", "composer", "CVE PHP (si projet PHP)", "https://getcomposer.org")
    tool("git", "git", ".env versionné ? historique", "https://git-scm.com")
    tool("dig", "dig", "CAA (facultatif, repli DNS-over-HTTPS)", "facultatif")
    ok_all = True
    for ok, name, why, inst in rows:
        print(f"  {'✔' if ok else '✘'} {name:<24} {why}" + ("" if ok else f"\n      → {inst}"))
        if not ok and name not in ("dig", "pip-audit", "Composer"):
            ok_all = False
    print("\nPrêt pour un audit complet." if ok_all else "\nInstaller les outils marqués ✘ : sinon les contrôles concernés sortent « Non exécuté » et le verdict reste INCOMPLET.")
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(description="Audit complet RGPD/SEO/Sécurité/SSL/Perf/Accessibilité")
    ap.add_argument("--url", help="URL du site à auditer (local ou en ligne)")
    ap.add_argument("--src", help="Dossier du code source (analyse statique, dépendances, secrets)")
    ap.add_argument("--prod-url", help="URL HTTPS de production pour les tests SSL/TLS, HTTP/2, variantes de domaine")
    ap.add_argument("--out", default="wcg-report", help="Dossier de sortie (défaut : ./wcg-report)")
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--only", help="Catégories à auditer : " + ",".join(CATEGORIES))
    ap.add_argument("--answers", help="JSON des réponses aux questions documentaires (voir --questions)")
    ap.add_argument("--threshold", type=int, default=90, help="Score minimal par catégorie pour valider (défaut 90)")
    ap.add_argument("--lh-pages", type=int, default=2, help="Nombre de pages passées dans Lighthouse (défaut 2)")
    ap.add_argument("--no-browser", action="store_true", help="Désactive les tests Chromium (déconseillé)")
    ap.add_argument("--no-lighthouse", action="store_true")
    ap.add_argument("--external-links", action="store_true", help="Teste aussi les liens sortants")
    ap.add_argument("--insecure", action="store_true", help="Accepte un certificat auto-signé (https local)")
    ap.add_argument("--list-checks", action="store_true")
    ap.add_argument("--questions", action="store_true", help="Affiche le modèle answers.json")
    ap.add_argument("--doctor", action="store_true", help="Vérifie les outils nécessaires à un audit complet")
    a = ap.parse_args()

    if a.doctor:
        return doctor()

    if a.list_checks:
        print(catalog_markdown())
        return 0
    if a.questions:
        print(json.dumps({k: {"question": v, "reponse": "oui | non | na", "commentaire": ""} for k, v in DOC_QUESTIONS.items()}, ensure_ascii=False, indent=2))
        return 0
    if not a.url and not a.src:
        ap.error("--url et/ou --src requis")

    t0 = time.time()
    cats = [c.strip() for c in (a.only or ",".join(CATEGORIES)).split(",") if c.strip() in CATEGORIES]
    ctx = Ctx()
    ctx.opts = a
    ctx.results = Results()
    ctx.src = str(Path(a.src).resolve()) if a.src else None
    ctx.prod_url = a.prod_url.rstrip("/") + "/" if a.prod_url else None
    ctx.out_dir = str(Path(a.out).resolve())
    Path(ctx.out_dir).mkdir(parents=True, exist_ok=True)
    ctx.http = Http(insecure=a.insecure or bool(a.url and is_local_host(urllib.parse.urlsplit(a.url).hostname or "")))
    ctx.pages, ctx.api_candidates, ctx.sitemap_urls = [], [], []
    ctx.is_ecommerce = False
    st = stack.detect(ctx.src)
    ctx.stack = st

    if a.url:
        base = a.url if a.url.endswith("/") or urllib.parse.urlsplit(a.url).path not in ("", "/") else a.url.rstrip("/") + "/"
        ctx.is_local = is_local_host(urllib.parse.urlsplit(base).hostname or "")
        home = ctx.http.get(base)
        if home.status == 0 or home.status >= 500:
            print(f"[wcg] Site injoignable : {base} ({home.status or home.error}). Démarrer le serveur (build de prod de préférence) puis relancer.", file=sys.stderr)
            return 2
        ctx.base = home.url if home.url.startswith(("http://", "https://")) else base
        ctx.home_resp = home
        # signature du « faux 200 » (catch-all / fallback SPA) pour ne pas confondre une page inexistante avec une vraie page
        ghost = ctx.http.get(ctx.base.rstrip("/") + "/wcg-page-fantome-5e8b1", use_cache=False)
        ctx.soft404 = (ghost.status == 200, len(ghost.body), home.body[:2000])

        def is_ghost(r, _g=ghost, _h=home):
            if r.status != 200 or ghost.status != 200:
                return False
            return abs(len(r.body) - len(_g.body)) < 80 or r.body[:3000] == _g.body[:3000] or r.body[:3000] == _h.body[:3000]
        ctx.is_ghost = is_ghost
        print(f"[wcg] Crawl de {ctx.base} (max {a.max_pages} pages)…", file=sys.stderr)
        crawler = Crawler(ctx.http, ctx.base, a.max_pages)
        crawler.run(seeds_from_sitemap(ctx.http, ctx.base, ctx.is_local))
        ctx.crawler = crawler
        ctx.pages = crawler.pages
        ctx.api_candidates = api_candidates(ctx.pages, ctx.base)
        print(f"[wcg] {len(ctx.pages)} page(s) HTML récupérée(s)", file=sys.stderr)
    else:
        ctx.base, ctx.is_local, ctx.home_resp = "", True, None
        ctx.is_ghost = lambda r: False

    steps = []
    if a.url:
        if "secu" in cats or "tls" in cats:
            steps.append(("Sécurité HTTP", security_http.run))
        if "rgpd" in cats:
            steps.append(("RGPD pages légales & formulaires", rgpd.run))
        if not a.no_browser and ({"rgpd", "seo", "perf", "a11y"} & set(cats)):
            steps.append(("Navigateur (consentement, rendu, poids, axe)", browser.run))
        if "seo" in cats:
            steps.append(("SEO", seo.run))
        if "tls" in cats:
            steps.append(("SSL/TLS", tls.run))
        if {"perf", "a11y", "seo"} & set(cats):
            steps.append(("Performance & accessibilité", perf.run))
    if "secu" in cats:
        steps.append(("Analyse du code & dépendances", code.run))
    for label, fn in steps:
        print(f"[wcg] {label}…", file=sys.stderr)
        try:
            fn(ctx)
        except Exception as e:  # noqa: BLE001
            print(f"[wcg] ! {label} : {type(e).__name__}: {e}", file=sys.stderr)

    # contrôles documentaires
    answers = {}
    if a.answers and Path(a.answers).exists():
        raw = json.loads(Path(a.answers).read_text(encoding="utf-8"))
        answers = {k: (v.get("reponse") if isinstance(v, dict) else v) for k, v in raw.items()}
    for fid, q in DOC_QUESTIONS.items():
        if CHECKS[fid]["cat"] not in cats:
            continue
        rep = str(answers.get(fid, "")).strip().lower()
        if rep in ("oui", "yes", "true", "ok"):
            ctx.results.ok(fid, "Confirmé par le client")
        elif rep in ("non", "no", "false"):
            ctx.results.ko(fid, "Non en place (réponse client)")
        elif rep in ("na", "n/a", "non applicable"):
            ctx.results.na(fid, "Non applicable (réponse client)")
        else:
            ctx.results.manual(fid, "Question à poser au client", note=q)

    # points « à vérifier » tranchés après revue (code relu par Claude, ou confirmation client)
    for fid, rep in answers.items():
        f = ctx.results.items.get(fid)
        if fid in DOC_QUESTIONS or not f or f.status != "manual":
            continue
        rep = str(rep).strip().lower()
        if rep in ("oui", "yes", "true", "ok"):
            f.status, f.evidence = "pass", f"Vérifié après revue — {f.evidence}"
        elif rep in ("non", "no", "false"):
            f.status, f.evidence = "fail", f"Revue : non conforme — {f.evidence}"
        elif rep in ("na", "n/a"):
            f.status = "na"

    # tout contrôle de la catégorie non renseigné = non exécuté (rien ne passe en silence)
    for fid, meta in CHECKS.items():
        if meta["cat"] in cats and fid not in ctx.results.items:
            why = "Aucune URL fournie (--url)" if not a.url and meta["method"] in ("http", "browser", "tool") else \
                  "Tests navigateur désactivés" if a.no_browser and meta["method"] == "browser" else "Contrôle non exécuté"
            ctx.results.err(fid, why)

    findings = [f.to_dict() for f in ctx.results.items.values() if CHECKS[f.id]["cat"] in cats]
    summary = score(findings, cats, a.threshold, tls_untested=bool(ctx.is_local and not ctx.prod_url and not ctx.base.startswith("https")))
    meta = {
        "target": ctx.base or ctx.src, "prod_url": ctx.prod_url, "mode": "local" if ctx.is_local else "production",
        "date": dt.datetime.now().strftime("%d/%m/%Y %H:%M"), "pages": len(ctx.pages), "requests": ctx.http.count,
        "stack": st["frameworks"] + st["cms"] + st["languages"] + st["servers"] + st["hosting"], "stack_refs": st["refs"],
        "categories": cats, "duration_s": round(time.time() - t0), "checks": len(findings),
        "crawled": [p.url for p in ctx.pages],
    }
    write_all(Path(ctx.out_dir), meta, findings, summary)
    print(f"\n=== VERDICT : {summary['verdict']} — global {summary['global']}/100 ({summary['grade']}) ===")
    for cat, v in summary["categories"].items():
        c = v["counts"]
        print(f"  {v['label']:<22} {(str(v['score']) if v['score'] is not None else '–'):>4}/100  KO {c['fail']:>2} · à améliorer {c['warn']:>2} · à vérifier {c['manual']:>2} · non exécutés {c['error']:>2}")
    print(f"Stack : {', '.join(meta['stack']) or 'non détectée'} → fiches : {', '.join('references/stacks/' + r for r in st['refs'])}")
    print(f"Rapports : {ctx.out_dir}/report.md · report.html · report.json  ({meta['duration_s']} s)")
    return 0 if summary["verdict"] == "VALIDÉ" else 1


if __name__ == "__main__":
    sys.exit(main())
