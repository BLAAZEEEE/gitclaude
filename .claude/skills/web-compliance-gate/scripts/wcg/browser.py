"""Tests dans un vrai Chromium (Playwright) : consentement cookies, rendu JS, poids réel, axe-core."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path

from .core import registrable
from .trackers import CONSENT_COOKIES, LS_TRACKER_KEYS, TRACKER_COOKIES, classify

BROWSER_IDS = ["RGPD-01", "RGPD-02", "RGPD-03", "RGPD-04", "RGPD-05", "RGPD-06", "RGPD-07", "RGPD-08", "RGPD-09", "RGPD-10",
               "RGPD-11", "RGPD-12", "RGPD-13", "RGPD-14", "RGPD-15", "RGPD-16", "SEO-31", "PERF-09", "PERF-10", "PERF-17", "A11Y-02"]

CLICKABLE = "button, a, [role=button], input[type=button], input[type=submit], [onclick]"
ACCEPT = re.compile(r"(tout accepter|accepter tout|accepter et fermer|accepter les cookies|^\s*accepter\s*$|j.accepte|^\s*accept( all)?( cookies)?\s*$|allow all|^\s*allow\s*$|autoriser|ok pour moi|^\s*d.accord\s*$|accepter et continuer|j.ai compris|^\s*ok\s*$|agree)", re.I)
REFUSE = re.compile(r"(tout refuser|refuser tout|^\s*refuser\s*$|je refuse|refuser les cookies|continuer sans accepter|reject( all)?|decline|deny|non merci|interdire|n.accepter que|uniquement (les )?(cookies )?(essentiels|n[ée]cessaires|strictement)|necessary only|only necessary|essentials only|refuser et fermer)", re.I)
SETTINGS = re.compile(r"(param[eè]tr|personnalis|g[ée]rer|pr[ée]f[ée]rences|customi[sz]e|settings|choisir|options)", re.I)
SAVE = re.compile(r"(enregistrer|sauvegarder|valider|confirmer|save|confirm)", re.I)
WITHDRAW = re.compile(r"((g[ée]rer|param[eè]tr\w*|pr[ée]f[ée]rences|modifier|gestion)\s*(des|les|mes)?\s*(choix\s*)?(de\s*)?cookies|cookies?\s*(settings|preferences|param)|manage cookies|cookie settings|gestion des cookies|panneau de gestion|consentement)", re.I)
CMP_SELECTORS = ["#tarteaucitronRoot", "#tarteaucitronAlertBig", "#axeptio_overlay", "#didomi-host", "#CybotCookiebotDialog", "#onetrust-banner-sdk",
                 ".cc-window", "#cc-main", "#cc--main", ".klaro", "#cmplz-cookiebanner-container", "#iubenda-cs-banner", "#usercentrics-root",
                 "#cookie-law-info-bar", "#moove_gdpr_cookie_info_bar", "#BorlabsCookieBox", "[id*=cookie-banner]", "[class*=cookie-banner]",
                 "[id*=cookieconsent]", "[class*=cookie-consent]", "[aria-label*=cookie i]"]
CMP_FLOATING = ["#tarteaucitronIcon", "#tarteaucitronManager", "#axeptio_main_button", ".axeptio_widget", "#didomi-notice", "#CookiebotWidget",
                "#ot-sdk-btn-floating", ".cc-revoke", "[data-cc=show-preferencesModal]", "[data-cc=c-settings]", "#cmplz-manage-consent"]
MAX_13_MONTHS = 396 * 86400
SIX_MONTHS_PLUS = 213 * 86400


def _axe_path():
    cache = Path(os.environ.get("WCG_CACHE", Path.home() / ".cache" / "wcg"))
    p = cache / "node_modules" / "axe-core" / "axe.min.js"
    if p.exists():
        return p
    if shutil.which("npm"):
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(["npm", "install", "--prefix", str(cache), "axe-core@4", "--silent", "--no-audit", "--no-fund"],
                       capture_output=True, timeout=180, shell=os.name == "nt")
    return p if p.exists() else None


class Session:
    """Un contexte navigateur vierge + enregistrement réseau."""

    def __init__(self, browser, site_host, locale="fr-FR"):
        self.ctx = browser.new_context(locale=locale, viewport={"width": 1366, "height": 850}, ignore_https_errors=True,
                                       user_agent=None)
        self.page = self.ctx.new_page()
        self.site_host = site_host
        self.requests = []          # (t, url, resource_type)
        self.bytes = 0
        self.js_bytes = 0
        self.nreq = 0
        self._types = {}
        self.page.on("request", lambda r: self.requests.append((time.time(), r.url, r.resource_type)))
        try:
            cdp = self.ctx.new_cdp_session(self.page)
            cdp.send("Network.enable")
            cdp.on("Network.responseReceived", lambda e: self._types.__setitem__(e["requestId"], e.get("type", "")))
            cdp.on("Network.loadingFinished", self._fin)
        except Exception:  # noqa: BLE001
            pass

    def _fin(self, e):
        size = e.get("encodedDataLength", 0) or 0
        self.bytes += size
        self.nreq += 1
        if self._types.get(e["requestId"]) == "Script":
            self.js_bytes += size

    def goto(self, url, settle=2.5):
        try:
            self.page.goto(url, wait_until="networkidle", timeout=35000)
        except Exception:  # noqa: BLE001
            try:
                self.page.goto(url, wait_until="load", timeout=35000)
            except Exception:  # noqa: BLE001
                pass
        self.page.wait_for_timeout(int(settle * 1000))

    def since(self, t0=0.0):
        return [u for t, u, _ in self.requests if t >= t0]

    def cookies(self):
        return self.ctx.cookies()

    def storage_keys(self):
        try:
            return self.page.evaluate("() => { const k=[]; try{for(let i=0;i<localStorage.length;i++)k.push(localStorage.key(i))}catch(e){}; try{for(let i=0;i<sessionStorage.length;i++)k.push(sessionStorage.key(i))}catch(e){}; return k }")
        except Exception:  # noqa: BLE001
            return []

    def find(self, pattern, max_len=60):
        """Éléments cliquables visibles dont le texte correspond, dans toutes les frames (shadow DOM ouvert inclus)."""
        out = []
        for fr in self.page.frames:
            try:
                loc = fr.locator(CLICKABLE).filter(has_text=pattern)
                for el in loc.all()[:15]:
                    try:
                        if not el.is_visible():
                            continue
                        txt = (el.inner_text(timeout=1500) or el.get_attribute("value") or "").strip()
                        if txt and len(txt) <= max_len and pattern.search(txt):
                            out.append((el, txt))
                    except Exception:  # noqa: BLE001
                        continue
            except Exception:  # noqa: BLE001
                continue
            # aria-label / value des input sans texte
            try:
                for el in fr.locator("input[type=button], input[type=submit], button[aria-label], a[aria-label]").all()[:40]:
                    lab = (el.get_attribute("value") or el.get_attribute("aria-label") or "").strip()
                    if lab and pattern.search(lab) and el.is_visible():
                        out.append((el, lab))
            except Exception:  # noqa: BLE001
                pass
        return out

    def style(self, el):
        try:
            return el.evaluate("""e => { const s=getComputedStyle(e), r=e.getBoundingClientRect();
                return {w:r.width,h:r.height,fs:parseFloat(s.fontSize),bg:s.backgroundColor,border:s.borderStyle+' '+s.borderWidth,color:s.color,opacity:s.opacity,td:s.textDecorationLine} }""")
        except Exception:  # noqa: BLE001
            return None

    def cmp_present(self):
        for sel in CMP_SELECTORS:
            try:
                if self.page.locator(sel).first.is_visible(timeout=300):
                    return sel
            except Exception:  # noqa: BLE001
                continue
        return None

    def close(self):
        try:
            self.ctx.close()
        except Exception:  # noqa: BLE001
            pass


def _classify_all(urls, site):
    trackers, embeds, fonts, captcha, cdn, exempt = {}, {}, {}, {}, set(), {}
    for u in urls:
        c = classify(u)
        if not c:
            continue
        kind, name, cat = c
        if kind == "tracker":
            (exempt if cat == "mesure-exemptable" else trackers).setdefault(name, u)
        elif kind == "embed":
            embeds.setdefault(name, u)
        elif kind == "font":
            fonts.setdefault(name, u)
        elif kind == "captcha":
            captcha.setdefault(name, u)
        elif kind == "cdn":
            cdn.add(name)
    return trackers, embeds, fonts, captcha, cdn, exempt


def _bad_cookies(cookies, site_host):
    site_reg = registrable(site_host)
    bad, other = [], []
    for c in cookies:
        dom = c["domain"].lstrip(".")
        third = registrable(dom) != site_reg and not dom.endswith(site_host)
        if third or TRACKER_COOKIES.search(c["name"]):
            bad.append(f"{c['name']} ({dom})")
        elif not CONSENT_COOKIES.search(c["name"]):
            other.append(f"{c['name']} ({dom})")
    return bad, other


def run(ctx):
    R = ctx.results
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        for fid in BROWSER_IDS:
            R.err(fid, "Playwright non installé", note="pip install playwright && python -m playwright install chromium")
        return
    site_host = urllib.parse.urlsplit(ctx.base).hostname or ""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as e:  # noqa: BLE001
            for fid in BROWSER_IDS:
                R.err(fid, f"Chromium non lancé : {str(e)[:120]}", note="python -m playwright install chromium")
            return
        ctx.chromium_path = p.chromium.executable_path
        try:
            R.guard(BROWSER_IDS[:16] + ["PERF-09", "PERF-10", "PERF-17"], _consent_flows, ctx, browser, site_host)
            R.guard(["SEO-31"], _render_check, ctx, browser, site_host)
            R.guard(["A11Y-02"], _axe, ctx, browser, site_host)
        finally:
            browser.close()


def _consent_flows(ctx, browser, site_host):
    R = ctx.results
    second = next((p.url for p in ctx.pages[1:] if p.url.rstrip("/") != ctx.base.rstrip("/")), None)

    # ---------------------------------------------------- 1. arrivée sans interaction
    s = Session(browser, site_host)
    s.goto(ctx.base)
    base_urls = s.since()
    trk, emb, fonts, cap, cdn, exempt = _classify_all(base_urls, site_host)
    base_cookies = s.cookies()
    bad_c, other_c = _bad_cookies(base_cookies, site_host)
    ls_bad = [k for k in s.storage_keys() if LS_TRACKER_KEYS.search(k or "")]
    accept_btns = s.find(ACCEPT)
    refuse_btns = s.find(REFUSE)
    settings_btns = s.find(SETTINGS, 40)
    cmp_sel = s.cmp_present()
    banner = bool(accept_btns or cmp_sel)
    # poids réel de la page d'accueil (avant consentement)
    PERF_BUDGET = 1.6 * 1024 * 1024
    R.check("PERF-09", s.bytes <= PERF_BUDGET, f"{s.bytes / 1024:.0f} Ko transférés", f"{s.bytes / 1024:.0f} Ko transférés (> 1 600 Ko)", soft=s.bytes <= 2.5 * 1024 * 1024)
    R.check("PERF-10", s.nreq <= 70, f"{s.nreq} requêtes", f"{s.nreq} requêtes (> 70)", soft=True)
    R.check("PERF-17", s.js_bytes <= 350 * 1024, f"JS : {s.js_bytes / 1024:.0f} Ko", f"JS : {s.js_bytes / 1024:.0f} Ko (> 350 Ko)", soft=s.js_bytes <= 600 * 1024)

    pre_note = "Cookies posés avant consentement à justifier comme strictement nécessaires : " + ", ".join(other_c[:10]) if other_c else ""
    R.check("RGPD-01", not bad_c, f"Aucun cookie traceur avant consentement ({len(other_c)} cookie(s) technique(s))",
            f"{len(bad_c)} cookie(s) traceur(s) déposé(s) avant consentement", bad_c, note=pre_note)
    ev = [f"{n} : {u[:110]}" for n, u in trk.items()]
    if exempt:
        ev += [f"{n} (exemptable si configuré sans cookie tiers / IP anonymisée) : {u[:90]}" for n, u in exempt.items()]
    if trk:
        R.ko("RGPD-02", f"{len(trk)} service(s) de tracking chargé(s) avant consentement", ev)
    elif exempt:
        R.warn("RGPD-02", "Outil de mesure potentiellement exempté chargé avant consentement", ev,
               note="Matomo : exemption CNIL possible si configuré selon le guide CNIL (pas de recoupement, IP tronquée, cookies ≤ 13 mois).")
    else:
        R.ok("RGPD-02", f"{len(set(base_urls))} requêtes analysées, aucun traceur")
    R.check("RGPD-03", not ls_bad, "Aucun identifiant traceur en stockage local", "Identifiants de traceurs en storage avant consentement", ls_bad)
    if fonts:
        google = {k: v for k, v in fonts.items() if "Google" in k or "Adobe" in k}
        (R.ko if google else R.warn)("RGPD-13", "Polices chargées depuis un serveur tiers", [f"{k} : {v[:100]}" for k, v in fonts.items()])
    else:
        R.ok("RGPD-13", "Polices servies localement")
    if emb:
        R.ko("RGPD-14", f"{len(emb)} contenu(s) tiers chargé(s) avant consentement", [f"{k} : {v[:100]}" for k, v in emb.items()],
             note="youtube-nocookie.com dépose quand même des identifiants (localStorage) : façade « cliquer pour charger » recommandée.")
    else:
        R.ok("RGPD-14", "Aucun contenu tiers chargé avant consentement")
    if cap:
        rc = {k: v for k, v in cap.items() if k == "reCAPTCHA"}
        if rc:
            R.warn("RGPD-15", "reCAPTCHA (Google) chargé dès l'arrivée", [f"{k} : {v[:100]}" for k, v in cap.items()],
                   note="Informer dans la politique ; idéalement charger uniquement sur la page du formulaire, ou alternative sans traceur.")
        else:
            R.ok("RGPD-15", f"Captcha : {', '.join(cap)}", note="Mentionner le service dans la politique de confidentialité.")
    else:
        R.na("RGPD-15", "Aucun captcha/chat tiers détecté au chargement")
    R.check("RGPD-16", not cdn, "Aucun CDN public tiers", f"{len(cdn)} CDN tiers (transfert d'IP)", sorted(cdn), soft=True)

    # cookie wall
    if banner:
        try:
            blocked = s.page.evaluate("""() => { const b=getComputedStyle(document.body).overflow+getComputedStyle(document.documentElement).overflow;
                const el=document.elementFromPoint(innerWidth/2, innerHeight/2); let n=el, fixed=false;
                while(n && n!==document.body){ const st=getComputedStyle(n); if(st.position==='fixed' && n.getBoundingClientRect().height>innerHeight*0.8){fixed=true;break}; n=n.parentElement }
                return {overflowHidden: /hidden/.test(b), overlay: fixed} }""")
        except Exception:  # noqa: BLE001
            blocked = {"overflowHidden": False, "overlay": False}
        if blocked.get("overlay") and blocked.get("overflowHidden"):
            R.warn("RGPD-12", "Le bandeau recouvre la page et bloque le défilement (cookie wall possible)",
                   note="Admis seulement avec une alternative réelle ; sinon laisser le site consultable (bandeau non bloquant).")
        else:
            R.ok("RGPD-12", "Le site reste consultable avec le bandeau affiché")
    s.close()

    # ---------------------------------------------------- 2. acceptation (révèle les traceurs conditionnés)
    a = Session(browser, site_host)
    a.goto(ctx.base, settle=1.5)
    acc = a.find(ACCEPT)
    accepted_trk, accepted_cookies = {}, []
    if acc:
        t0 = time.time()
        try:
            acc[0][0].click(timeout=5000)
        except Exception:  # noqa: BLE001
            pass
        a.page.wait_for_timeout(3500)
        accepted_trk, *_ = _classify_all(a.since(t0), site_host)
        accepted_cookies = a.cookies()
        if second:
            a.goto(second, settle=2)
            accepted_cookies = a.cookies()
            more, *_ = _classify_all(a.since(t0), site_host)
            accepted_trk.update(more)
    needs_consent = bool(trk or accepted_trk or emb or bad_c)
    if accepted_trk and not trk:
        # preuve dynamique : les traceurs n'apparaissent qu'après « Accepter » → chargement conditionnel vérifié
        R.items.pop("RGPD-17", None)
        R.ok("RGPD-17", "Chargement conditionnel vérifié en navigateur : " + ", ".join(accepted_trk) + " uniquement après acceptation")

    # durées (après acceptation)
    now = time.time()
    long_trk, consent_long = [], []
    for c in {(c["name"], c["domain"]): c for c in base_cookies + accepted_cookies}.values():
        exp = c.get("expires", -1)
        if exp and exp > 0:
            life = exp - now
            if TRACKER_COOKIES.search(c["name"]) and life > MAX_13_MONTHS:
                long_trk.append(f"{c['name']} : {life / 86400:.0f} j")
            if CONSENT_COOKIES.search(c["name"]) and life > SIX_MONTHS_PLUS:
                consent_long.append(f"{c['name']} : {life / 86400:.0f} j")
    trk_cookies_after = [c for c in base_cookies + accepted_cookies if TRACKER_COOKIES.search(c["name"])]
    if trk_cookies_after:
        R.check("RGPD-09", not long_trk, f"{len(trk_cookies_after)} cookie(s) traceur(s) ≤ 13 mois", "Cookies traceurs > 13 mois", long_trk)
    else:
        R.na("RGPD-09", "Aucun cookie traceur observé après acceptation")
    consent_cookies = [c for c in accepted_cookies if CONSENT_COOKIES.search(c["name"])]
    if consent_cookies:
        R.check("RGPD-10", not consent_long, "Choix conservé ≤ ~7 mois", "Choix conservé plus de 6 mois", consent_long, soft=True)
    elif banner:
        R.manual("RGPD-10", "Cookie de choix non identifié (stocké en localStorage ?)", note="Vérifier la durée de conservation du choix dans la config de la CMP (6 mois recommandés).")
    else:
        R.na("RGPD-10", "Pas de bandeau")

    # lien de retrait
    withdraw_pages = 0
    checked = 0
    for pg in ctx.pages[:6]:
        checked += 1
        if any(WITHDRAW.search(f"{x.get('_text', '')} {x.get('href', '')} {x.get('aria-label', '')}") for x in pg.doc.anchors + pg.doc.buttons):
            withdraw_pages += 1
    floating = None
    if acc:
        for sel in CMP_FLOATING:
            try:
                if a.page.locator(sel).first.is_visible(timeout=300):
                    floating = sel
                    break
            except Exception:  # noqa: BLE001
                continue
        if not floating and a.find(WITHDRAW, 60):
            floating = "lien rendu en JS"
    a.close()

    # ---------------------------------------------------- 3. décision bandeau
    if not needs_consent and not banner:
        R.ok("RGPD-04", "Aucun traceur soumis à consentement détecté : bandeau non requis")
        for fid in ("RGPD-05", "RGPD-06", "RGPD-07", "RGPD-08", "RGPD-11"):
            R.na(fid, "Pas de traceur soumis à consentement")
        R.na("RGPD-12", "Pas de bandeau")
        return
    if not banner:
        R.ko("RGPD-04", "Traceurs présents mais aucun bandeau de consentement détecté",
             [*trk.keys(), *accepted_trk.keys(), *emb.keys()])
        for fid in ("RGPD-05", "RGPD-06", "RGPD-07", "RGPD-08"):
            R.ko(fid, "Aucun bandeau : impossible de refuser")
        R.ko("RGPD-11", "Aucun moyen de gérer le consentement")
        R.na("RGPD-12", "Pas de bandeau")
        return
    R.ok("RGPD-04", f"Bandeau détecté ({cmp_sel or 'bouton « ' + accept_btns[0][1][:30] + ' »'})",
         [f"Traceurs conditionnés à l'acceptation : {', '.join(accepted_trk) or 'aucun observé'}"])

    # ---------------------------------------------------- 4. refus
    if refuse_btns:
        R.ok("RGPD-05", f"Bouton « {refuse_btns[0][1][:40]} » au premier niveau")
    else:
        R.ko("RGPD-05", "Pas de bouton Refuser au premier niveau", [f"Boutons visibles : {', '.join(t for _, t in accept_btns + settings_btns)[:200]}"])
    rs = Session(browser, site_host)
    rs.goto(ctx.base, settle=1.5)
    r_btns = rs.find(REFUSE)
    a_btns = rs.find(ACCEPT)
    if r_btns and a_btns:
        sa, sr = rs.style(a_btns[0][0]), rs.style(r_btns[0][0])
        issues = []
        if sa and sr:
            area_a, area_r = sa["w"] * sa["h"], sr["w"] * sr["h"]
            if area_a and area_r / area_a < 0.6:
                issues.append(f"Refuser {area_r:.0f}px² vs Accepter {area_a:.0f}px²")
            if sa["fs"] and sr["fs"] / sa["fs"] < 0.9:
                issues.append(f"police Refuser {sr['fs']}px vs Accepter {sa['fs']}px")
            transparent = lambda c: c in ("rgba(0, 0, 0, 0)", "transparent")  # noqa: E731
            if not transparent(sa["bg"]) and transparent(sr["bg"]) and "none" in sr["border"]:
                issues.append("Accepter est un bouton plein, Refuser un simple lien")
            if float(sr.get("opacity", 1)) < 0.8:
                issues.append("Refuser semi-transparent")
        R.check("RGPD-06", not issues, "Refuser et Accepter ont un poids visuel équivalent", "Refuser moins visible qu'Accepter", issues)
    elif not r_btns:
        R.ko("RGPD-06", "Refus non disponible en un clic")
    t0 = time.time()
    clicked = False
    path = []
    if r_btns:
        try:
            r_btns[0][0].click(timeout=5000)
            clicked = True
            path.append(f"clic « {r_btns[0][1][:30]} »")
        except Exception:  # noqa: BLE001
            pass
    else:
        st = rs.find(SETTINGS, 40)
        if st:
            try:
                st[0][0].click(timeout=5000)
                rs.page.wait_for_timeout(1200)
                path.append(f"clic « {st[0][1][:30]} »")
                nxt = rs.find(REFUSE) or rs.find(SAVE, 40)
                if nxt:
                    nxt[0][0].click(timeout=5000)
                    clicked = True
                    path.append(f"clic « {nxt[0][1][:30]} »")
            except Exception:  # noqa: BLE001
                pass
    if not clicked:
        R.ko("RGPD-07", "Impossible d'effectuer un refus automatiquement", path)
        R.manual("RGPD-08", "Refus non testable automatiquement")
    else:
        rs.page.wait_for_timeout(3500)
        after = rs.since(t0)
        trk_after, emb_after, *_ = _classify_all(after, site_host)
        bad_after, _ = _bad_cookies(rs.cookies(), site_host)
        items = [f"traceur : {k}" for k in trk_after] + [f"contenu tiers : {k}" for k in emb_after] + [f"cookie : {c}" for c in bad_after]
        R.check("RGPD-07", not items, f"Refus respecté ({' → '.join(path)})", "Des traceurs se chargent malgré le refus", items)
        if second:
            t1 = time.time()
            rs.goto(second, settle=2.5)
            trk2, emb2, *_ = _classify_all(rs.since(t1), site_host)
            bad2, _ = _bad_cookies(rs.cookies(), site_host)
            again = rs.find(ACCEPT)
            items2 = [f"traceur : {k}" for k in trk2] + [f"contenu tiers : {k}" for k in emb2] + [f"cookie : {c}" for c in bad2]
            if again:
                items2.append("le bandeau réapparaît (choix non mémorisé)")
            R.check("RGPD-08", not items2, f"Refus conservé sur {second}", "Refus non conservé en navigation", items2)
        else:
            R.na("RGPD-08", "Une seule page crawlée")
    rs.close()
    if withdraw_pages >= max(1, checked - 1) or floating:
        R.ok("RGPD-11", "Gestion des cookies accessible (" + (f"lien sur {withdraw_pages}/{checked} pages" if withdraw_pages else f"bouton flottant {floating}") + ")")
    elif withdraw_pages:
        R.warn("RGPD-11", f"Lien de gestion des cookies sur {withdraw_pages}/{checked} pages seulement")
    else:
        R.ko("RGPD-11", "Aucun lien « Gestion des cookies » pour retirer son consentement")


def _render_check(ctx, browser, site_host):
    R = ctx.results
    bad, tested = [], 0
    for pg in ctx.pages[:3]:
        raw_words = len(re.findall(r"\w{2,}", pg.doc.text))
        s = Session(browser, site_host)
        s.goto(pg.url, settle=1.5)
        try:
            rendered = s.page.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception:  # noqa: BLE001
            rendered = ""
        s.close()
        rw = len(re.findall(r"\w{2,}", rendered))
        tested += 1
        if rw > 80 and raw_words < rw * 0.35:
            bad.append(f"{pg.url} : {raw_words} mots dans le HTML initial vs {rw} après JavaScript")
    R.check("SEO-31", not bad, f"Contenu présent dans le HTML initial ({tested} page(s))", "Contenu rendu uniquement côté client (CSR)", bad)


def _axe(ctx, browser, site_host):
    R = ctx.results
    axe = _axe_path()
    if not axe:
        R.err("A11Y-02", "axe-core indisponible", note="npm install axe-core (nécessite Node.js/npm)")
        return
    src = axe.read_text(encoding="utf-8")
    viol = {}
    for pg in ctx.pages[:5]:
        s = Session(browser, site_host)
        s.goto(pg.url, settle=1)
        try:
            s.page.add_script_tag(content=src)
            res = s.page.evaluate("""async () => (await axe.run(document, {resultTypes:['violations']})).violations
                .map(v => ({id:v.id, impact:v.impact, help:v.help, n:v.nodes.length, target:(v.nodes[0]||{}).target}))""")
        except Exception as e:  # noqa: BLE001
            res = []
            viol.setdefault("_errors", []).append(f"{pg.url}: {str(e)[:80]}")
        s.close()
        for v in res:
            key = v["id"]
            cur = viol.setdefault(key, {"impact": v["impact"], "help": v["help"], "n": 0, "pages": [], "target": v.get("target")})
            cur["n"] += v["n"]
            cur["pages"].append(pg.url)
    viol.pop("_errors", None)
    serious = {k: v for k, v in viol.items() if v["impact"] in ("critical", "serious")}
    details = [f"[{v['impact']}] {k} — {v['help']} ({v['n']} élément(s), ex. {v['target']}) sur {len(v['pages'])} page(s)" for k, v in
               sorted(viol.items(), key=lambda kv: ("critical", "serious", "moderate", "minor").index(kv[1]["impact"] or "minor"))]
    if serious:
        R.ko("A11Y-02", f"{len(serious)} règle(s) critique(s)/sérieuse(s) en échec", details)
    elif viol:
        R.warn("A11Y-02", f"{len(viol)} violation(s) modérée(s)/mineure(s)", details)
    else:
        R.ok("A11Y-02", f"Aucune violation axe-core ({min(len(ctx.pages), 5)} page(s))")
