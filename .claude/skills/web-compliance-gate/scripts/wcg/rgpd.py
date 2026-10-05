"""RGPD côté HTTP/code : pages légales (contenu vérifié), formulaires, e-commerce, Consent Mode."""
from __future__ import annotations

import re
from pathlib import Path

from .core import norm, parse
from .stack import iter_files

LEGAL_LINKS = {
    "mentions": re.compile(r"mentions[\s-]*l[eé]gales|legal[\s-]*notice|/mentions|impressum", re.I),
    "privacy": re.compile(r"(politique|charte).{0,25}(confidentialit|donn[ée]es|vie priv)|privacy|confidentialit|donnees-personnelles|rgpd", re.I),
    "cookies": re.compile(r"cookie", re.I),
    "cgv": re.compile(r"\bcgv\b|conditions g[ée]n[ée]rales de vente|conditions-generales-de-vente", re.I),
    "cgu": re.compile(r"\bcgu\b|conditions g[ée]n[ée]rales d.utilisation|conditions-generales-d-utilisation|terms", re.I),
}
FALLBACK_PATHS = {
    "mentions": ["mentions-legales", "mentions-legales.html", "mentions-legales.php", "legal", "mentions"],
    "privacy": ["politique-de-confidentialite", "politique-confidentialite", "confidentialite", "privacy", "privacy-policy", "rgpd", "donnees-personnelles"],
    "cookies": ["cookies", "politique-cookies", "gestion-des-cookies"],
    "cgv": ["cgv", "conditions-generales-de-vente"],
    "cgu": ["cgu", "conditions-generales-d-utilisation"],
}

PHONE = r"(\+33\s?|0)[1-9]([\s.-]?\d{2}){4}|\+\d{2,3}[\s\d]{8,14}"
EMAIL = r"[\w.+-]+@[\w-]+\.[\w.]+|\[at\]|\(at\)|formulaire de contact"

MENTIONS_REQ = {
    "Identité de l'éditeur (nom/raison sociale)": r"editeur|raison sociale|denomination|proprietaire du site|edite par|responsable du site",
    "Adresse postale": r"\b\d{5}\b",
    "Contact (email ou téléphone)": EMAIL + "|" + PHONE,
    "Immatriculation (SIREN/SIRET, RCS ou RM)": r"siret|siren|\brcs\b|registre du commerce|repertoire des metiers|\brm\b|\d{3}\s?\d{3}\s?\d{3}",
    "Directeur de la publication": r"direct(eur|rice) de (la )?publication|responsable de (la )?publication",
    "Hébergeur (nom et adresse)": r"heberg",
}
PRIVACY_REQ = {
    "Responsable du traitement": r"responsable (du|de) traitement|responsable des traitements|responsable du traitement",
    "Finalités": r"finalit",
    "Bases légales": r"base(s)? legale|fondement|interet legitime|execution (d.un|du) contrat|obligation legale|consentement",
    "Durées de conservation": r"duree(s)? de conservation|conserve(es|s)? (pendant|durant)|conservees? \d|pendant une duree",
    "Destinataires / sous-traitants": r"destinataire|sous-traitant|prestataire",
    "Transferts hors UE": r"hors (de l.)?(union europeenne|ue\b|l.ue|espace economique)|transfert|data privacy framework|clauses contractuelles",
    "Droit d'accès": r"droit d.acces|acceder a vos",
    "Droit de rectification": r"rectification",
    "Droit à l'effacement": r"effacement|droit a l.oubli|suppression de vos",
    "Droit à la limitation": r"limitation",
    "Droit à la portabilité": r"portabilite",
    "Droit d'opposition": r"opposition|vous opposer",
    "Retrait du consentement": r"retir(er|ez) (votre|son) consentement|retrait (de votre|du) consentement",
    "Réclamation auprès de la CNIL": r"cnil",
    "Contact pour exercer ses droits / DPO": r"dpo|delegue a la protection|exercer (vos|ces) droits|pour exercer",
}
COOKIE_REQ = {"Liste/finalités des cookies": r"cookie", "Durée des cookies": r"\d+\s*(mois|jours|ans|an\b)|duree"}

PERSONAL_FIELDS = re.compile(r"(e-?mail|courriel|nom|name|prenom|firstname|lastname|tel|phone|mobile|adresse|address|ville|city|cp|zip|postal|birth|naissance|message|societe|company)", re.I)
SENSITIVE_FIELDS = re.compile(r"(naissance|birth|\bage\b|\bsexe\b|gender|civilit|\bsecu\b|num.?secu|securite.?sociale|\bnir\b|social.?security|nationalit|religio|sante|health|pathologi|maladie|medic|traitement|mutuelle|handicap|orientation|syndic|casier|revenu|salaire|iban|carte.?vitale|ssn|passport|passeport|piece.?d.?identite)", re.I)
HEALTH_FIELDS = re.compile(r"(sante|health|pathologi|maladie|medic|allergi|antecedent|mutuelle|carte.?vitale|diagnos|ordonnance|groupe.?sanguin|patient)", re.I)
OPTIN = re.compile(r"(newsletter|consent|optin|opt-in|accept|partenaire|partner|marketing|offres|promo|cgu|cgv|rgpd|gdpr|terms)", re.I)
ECOM = re.compile(r"(panier|cart|checkout|commande|ajouter au panier|add to cart|paiement|€\s?\d|\d+[,.]\d{2}\s?€|stripe|paypal|woocommerce|shopify|prestashop)", re.I)
ACCOUNT = re.compile(r"(inscription|s.inscrire|register|sign ?up|creer (un|mon) compte|mon compte|se connecter|login|connexion)", re.I)


def _check_text(txt: str, reqs: dict) -> list:
    n = norm(txt)
    return [k for k, pat in reqs.items() if not re.search(pat, n)]


def run(ctx):
    R = ctx.results
    pages = ctx.pages
    root = ctx.base.rstrip("/") + "/"

    def legal():
        found = {k: None for k in LEGAL_LINKS}
        linked_on = {k: 0 for k in LEGAL_LINKS}
        for p in pages:
            seen_here = set()
            for a in p.doc.anchors:
                label = f"{a.get('_text', '')} {a.get('href', '')} {a.get('title', '')} {a.get('aria-label', '')}"
                for k, pat in LEGAL_LINKS.items():
                    if k == "cookies" and not re.search(r"(politique|gestion|parametr|preference|cookie)", label, re.I):
                        continue
                    href = (a.get("href") or "").strip()
                    if href.startswith(("#", "javascript:")) or not href:
                        continue
                    if pat.search(label) and (a.get("_abs") or "").startswith("http"):
                        if k == "privacy" and LEGAL_LINKS["mentions"].search(label):
                            continue
                        found[k] = found[k] or a["_abs"]
                        seen_here.add(k)
            for k in seen_here:
                linked_on[k] += 1
        for k, paths in FALLBACK_PATHS.items():
            if not found[k]:
                for path in paths:
                    r = ctx.http.get(root + path)
                    if r.status == 200 and r.is_html and len(r.body) > 500 and not ctx.is_ghost(r):
                        found[k] = r.url
                        break
        ctx.legal_pages = found
        n = len(pages)
        texts = {}
        for k, u in found.items():
            if u:
                r = ctx.http.get(u)
                texts[k] = parse(r.text, r.url).text if r.status == 200 else ""
        # mentions légales
        if not found["mentions"]:
            R.ko("RGPD-20", "Aucune page Mentions légales trouvée")
            R.ko("RGPD-21", "Page absente : aucun élément obligatoire publié")
        else:
            ratio = linked_on["mentions"] / n if n else 0
            R.check("RGPD-20", ratio >= 0.9, f"{found['mentions']} (liée sur {linked_on['mentions']}/{n} pages)",
                    f"{found['mentions']} liée seulement sur {linked_on['mentions']}/{n} pages", soft=ratio >= 0.5)
            missing = _check_text(texts.get("mentions", ""), MENTIONS_REQ)
            t = norm(texts.get("mentions", ""))
            m = re.search(r"heberg.{0,500}", t)
            if m and not re.search(PHONE, m.group(0)):
                missing.append("Téléphone de l'hébergeur (LCEN art. 6 III)")
            editeur = t.split("heberg", 1)[0]
            if re.search(r"\b(sas|sasu|sarl|eurl|sa|sci|sca|snc)\b", editeur) and "capital" not in t:
                missing.append("Capital social (société)")
            if re.search(r"\b(sas|sasu|sarl|eurl|sa)\b", editeur) and not re.search(r"tva|fr\s?\d{2}\s?\d{9}", t):
                missing.append("N° TVA intracommunautaire (si assujetti)")
            R.check("RGPD-21", not missing, "Tous les éléments LCEN trouvés", f"{len(missing)} élément(s) manquant(s)", missing,
                    note="Détection par mots-clés : relire la page pour confirmer l'exactitude des informations.")
        # politique
        if not found["privacy"]:
            R.ko("RGPD-22", "Aucune politique de confidentialité trouvée")
            R.ko("RGPD-23", "Politique absente")
        else:
            ratio = linked_on["privacy"] / n if n else 0
            R.check("RGPD-22", ratio >= 0.9, f"{found['privacy']} (liée sur {linked_on['privacy']}/{n} pages)",
                    f"Liée seulement sur {linked_on['privacy']}/{n} pages", soft=ratio >= 0.5)
            missing = _check_text(texts.get("privacy", ""), PRIVACY_REQ)
            R.check("RGPD-23", not missing, "Toutes les mentions art. 13 trouvées", f"{len(missing)} mention(s) manquante(s)", missing)
        ctext = texts.get("cookies") or texts.get("privacy", "")
        if not ctext:
            R.ko("RGPD-24", "Aucune information cookies trouvée")
        else:
            missing = _check_text(ctext, COOKIE_REQ)
            R.check("RGPD-24", not missing, "Information cookies présente", "Information cookies incomplète", missing, soft=True)
        # e-commerce / comptes
        alltext = " ".join(p.doc.text[:20000] for p in pages)
        is_ecom = len(ECOM.findall(alltext)) >= 3
        has_account = bool(ACCOUNT.search(alltext)) or any((i.get("type") or "") == "password" for p in pages for f in p.doc.forms for i in f["_inputs"])
        ctx.is_ecommerce = is_ecom
        if is_ecom:
            R.check("RGPD-25", bool(found["cgv"]), f"CGV : {found['cgv']}", "Site marchand détecté mais aucune CGV")
            med = norm(texts.get("cgv", "") + " " + texts.get("mentions", ""))
            R.check("RGPD-26", "mediat" in med, "Médiateur mentionné", "Médiateur de la consommation non mentionné")
        elif has_account:
            R.check("RGPD-25", bool(found["cgu"] or found["cgv"]), "CGU présentes", "Espace compte détecté sans CGU", soft=True)
            R.na("RGPD-26", "Pas de vente en ligne détectée")
        else:
            R.na("RGPD-25", "Ni vente en ligne ni compte utilisateur détecté")
            R.na("RGPD-26", "Pas de vente en ligne détectée")

    def forms():
        personal_forms, no_notice, prechecked, http_forms, sensitive, health = 0, [], [], [], [], []
        privacy = (ctx.legal_pages or {}).get("privacy") or ""
        for p in pages:
            for f in p.doc.forms:
                fields = [i for i in f["_inputs"] if i.get("_tag") in ("input", "textarea", "select") and (i.get("type") or "text").lower() not in ("hidden", "submit", "button", "search")]
                names = " ".join(f"{i.get('name', '')} {i.get('id', '')} {i.get('placeholder', '')} {i.get('autocomplete', '')}" for i in fields)
                is_search = (f.get("role") == "search") or all((i.get("type") or "") == "search" or re.search(r"search|q$|recherche", i.get("name", "") or "", re.I) for i in fields)
                if not fields or is_search:
                    continue
                label = f"{p.url} → form {f.get('id') or f.get('name') or f.get('action') or ''}".strip()
                if (f.get("_abs") or "").startswith("http://") and not ctx.is_local:
                    http_forms.append(label)
                if PERSONAL_FIELDS.search(names) or any((i.get("type") or "") in ("email", "tel", "password") for i in fields):
                    personal_forms += 1
                    txt = norm(f["_text"])
                    near = re.search(r"donnees|rgpd|confidentialit|vie privee|traitement|cnil|droit d.acces|privacy", txt)
                    link_in_form = any((privacy and a.get("_abs") == privacy) or LEGAL_LINKS["privacy"].search(f"{a.get('_text', '')} {a.get('href', '')}")
                                       for a in f.get("_links", []))
                    if not (near or link_in_form):
                        no_notice.append(label)
                for i in fields:
                    if (i.get("type") or "").lower() == "checkbox" and "checked" in i and OPTIN.search(f"{i.get('name', '')} {i.get('id', '')} {i.get('value', '')}"):
                        prechecked.append(f"{label} : case « {i.get('name') or i.get('id')} » pré-cochée")
                for i in fields:
                    key = norm(f"{i.get('name', '')} {i.get('id', '')} {i.get('placeholder', '')}")
                    if SENSITIVE_FIELDS.search(key):
                        sensitive.append(f"{label} : {i.get('name') or i.get('id')}")
                    if HEALTH_FIELDS.search(key):
                        health.append(f"{label} : {i.get('name') or i.get('id')}")
        if personal_forms == 0:
            spa_inputs = [p.url for p in pages if p.doc.inputs_outside_forms]
            if spa_inputs:
                R.manual("RGPD-30", "Champs hors <form> (formulaire JS)", note="Vérifier manuellement la mention d'information sous le formulaire : " + ", ".join(spa_inputs[:5]))
            else:
                R.na("RGPD-30", "Aucun formulaire de collecte trouvé")
        else:
            R.check("RGPD-30", not no_notice, f"{personal_forms} formulaire(s) avec mention d'information",
                    f"{len(no_notice)}/{personal_forms} formulaire(s) sans mention d'information", no_notice)
        R.check("RGPD-31", not prechecked, "Aucune case pré-cochée", "Cases d'opt-in pré-cochées", prechecked)
        if ctx.is_local and not ctx.base.startswith("https"):
            R.na("RGPD-32", "Site local en HTTP — vérifié en prod (TLS-10)")
        else:
            R.check("RGPD-32", not http_forms, "Formulaires en HTTPS", "Formulaires envoyés en HTTP", http_forms)
        if sensitive:
            R.warn("RGPD-33", f"{len(sensitive)} champ(s) sensible(s) à justifier", sensitive)
        elif personal_forms:
            R.ok("RGPD-33", "Aucun champ sensible détecté")
        else:
            R.na("RGPD-33", "Pas de formulaire")
        if health:
            R.manual("RGPD-34", f"Données de santé collectées ({len(health)} champ(s))",
                     note="Données sensibles (art. 9) : hébergeur certifié HDS, chiffrement, AIPD obligatoire, base légale explicite. " + "; ".join(health[:5]))
        else:
            R.na("RGPD-34", "Aucune donnée de santé détectée dans les formulaires")

    def consent_code():
        tag = re.compile(r"(gtag\(|googletagmanager\.com|google-analytics\.com|fbq\(|connect\.facebook\.net|hotjar|clarity\.ms|_paq\.push|mixpanel|posthog|plausible|umami)", re.I)
        consent = re.compile(r"(\bconsent\b|consentement|cookie.?banner|gtag\(\s*['\"]consent['\"]|ad_storage|analytics_storage|tarteaucitron|axeptio|didomi|cookiebot|onetrust|cookieconsent|klaro|complianz|cmplz|consentmanager|iubenda|type=['\"]text/plain['\"][^>]*data-(category|cookiecategory|type)|data-cookieconsent|hasConsent|consentGiven|requireConsent|disableCookies)", re.I)
        hits_tag, hits_consent = [], []
        own_js = sorted({s.get("_abs") for p in pages for s in p.doc.scripts if s.get("_abs") and s.get("_abs").startswith(ctx.base)})[:15]
        js_text = {u: ctx.http.get(u).text[:400_000] for u in own_js}
        for u, t in js_text.items():
            if tag.search(t):
                hits_tag.append(u)
            if consent.search(t):
                hits_consent.append(u)
        for p in pages:
            blob = " ".join(s.get("_abs", "") or "" for s in p.doc.scripts) + " ".join(p.doc.inline_scripts)
            if tag.search(blob):
                hits_tag.append(p.url)
            if consent.search(blob):
                hits_consent.append(p.url)
        if ctx.src:
            rootp = Path(ctx.src)
            for f in iter_files(rootp, (".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".php", ".html", ".twig", ".blade.php", ".erb", ".py", ".njk", ".hbs", ".liquid"), 5000):
                try:
                    t = f.read_text(errors="replace")[:400_000]
                except Exception:  # noqa: BLE001
                    continue
                rel = str(f.relative_to(rootp))
                if tag.search(t):
                    hits_tag.append(rel)
                if consent.search(t):
                    hits_consent.append(rel)
        if not hits_tag:
            R.na("RGPD-17", "Aucun outil de mesure/pub détecté")
        elif re.search(r"plausible|umami", " ".join(hits_tag), re.I) and not re.search(r"gtag|facebook|hotjar|clarity|fbq", " ".join(hits_tag), re.I):
            R.ok("RGPD-17", "Outil de mesure sans cookie (Plausible/Umami) — exemption possible", hits_tag[:5])
        else:
            R.check("RGPD-17", bool(hits_consent), "Mécanisme de consentement présent dans le code", "Traceurs présents sans mécanisme de consentement identifié",
                    sorted(set(hits_tag))[:10] + [f"consentement : {c}" for c in sorted(set(hits_consent))[:5]])

    ctx.legal_pages = {}
    R.guard(["RGPD-20", "RGPD-21", "RGPD-22", "RGPD-23", "RGPD-24", "RGPD-25", "RGPD-26"], legal)
    R.guard(["RGPD-30", "RGPD-31", "RGPD-32", "RGPD-33", "RGPD-34"], forms)
    R.guard(["RGPD-17"], consent_code)
