"""Catalogue de tous les contrôles. Source de vérité : id, catégorie, gravité, titre, correction, référence.

Gravités : critical (10) · high (6) · medium (3) · low (1) · info (0, non noté)
Méthodes : http (requêtes réelles) · browser (Chromium réel) · code (analyse du dépôt)
           tool (outil externe : Lighthouse, npm audit…) · doc (question au client, non visible dans le code)
"""

CATEGORIES = {
    "rgpd": "RGPD & cookies",
    "seo": "SEO",
    "secu": "Sécurité",
    "tls": "SSL / TLS & HTTPS",
    "perf": "Performance",
    "a11y": "Accessibilité",
}

SEVERITY_WEIGHT = {"critical": 10, "high": 6, "medium": 3, "low": 1, "info": 0}

_R = "references/"
_C = [
    # ======================================================================= RGPD — consentement (navigateur)
    ("RGPD-01", "rgpd", "critical", "browser", "Aucun cookie/traceur non exempté déposé avant consentement",
     "Bloquer tout script de mesure/pub/réseaux sociaux tant que l'utilisateur n'a pas accepté (CMP ou chargement conditionnel). Seuls les cookies strictement nécessaires (session, panier, CSRF, choix de consentement) sont permis avant.", _R + "rgpd.md#consentement"),
    ("RGPD-02", "rgpd", "critical", "browser", "Aucune requête vers un domaine de tracking avant consentement",
     "Ne charger Google Analytics/Tag Manager, Meta Pixel, Hotjar, Clarity, LinkedIn, TikTok… qu'après un clic sur « Accepter ». Avec GTM : Consent Mode v2 en « denied » par défaut ET balises conditionnées.", _R + "rgpd.md#consentement"),
    ("RGPD-03", "rgpd", "high", "browser", "Aucun identifiant de traceur en localStorage/sessionStorage avant consentement",
     "Même règle que pour les cookies (art. 82 loi Informatique et Libertés) : le stockage local d'identifiants de suivi exige le consentement.", _R + "rgpd.md#consentement"),
    ("RGPD-04", "rgpd", "high", "browser", "Bandeau de consentement présent si des traceurs soumis à consentement existent",
     "Ajouter une CMP (tarteaucitron.js, Axeptio, Didomi, orestbida/cookieconsent…) ou supprimer les traceurs. Sans traceur soumis à consentement, aucun bandeau n'est requis.", _R + "rgpd.md#bandeau"),
    ("RGPD-05", "rgpd", "critical", "browser", "Bouton « Refuser » disponible au premier niveau du bandeau",
     "Ajouter « Tout refuser » (ou « Continuer sans accepter ») sur le premier écran, sans passer par « Paramétrer ».", _R + "rgpd.md#bandeau"),
    ("RGPD-06", "rgpd", "high", "browser", "Refuser aussi visible et simple qu'Accepter (taille, style, un clic)",
     "Même composant, même taille, même contraste pour Accepter et Refuser. Pas de lien gris minuscule pour refuser.", _R + "rgpd.md#bandeau"),
    ("RGPD-07", "rgpd", "critical", "browser", "Après « Refuser » : aucun traceur chargé ni cookie non exempté",
     "Vérifier que le refus est bien propagé à tous les scripts (catégories de la CMP, Consent Mode, iframes).", _R + "rgpd.md#consentement"),
    ("RGPD-08", "rgpd", "high", "browser", "Le refus est respecté sur les pages suivantes (navigation)",
     "Le choix doit être mémorisé (cookie de choix) et relu sur chaque page avant tout chargement de traceur.", _R + "rgpd.md#consentement"),
    ("RGPD-09", "rgpd", "medium", "browser", "Durée de vie des cookies traceurs ≤ 13 mois",
     "Configurer la durée des cookies analytics/pub à 13 mois maximum (ex. GA4 : cookie_expires ≤ 34186669 s).", _R + "rgpd.md#durees"),
    ("RGPD-10", "rgpd", "low", "browser", "Choix de consentement conservé ~6 mois (bonne pratique CNIL)",
     "Régler la durée du cookie de choix de la CMP autour de 6 mois, puis redemander.", _R + "rgpd.md#durees"),
    ("RGPD-11", "rgpd", "medium", "browser", "Lien permanent pour modifier/retirer son consentement",
     "Ajouter un lien « Gestion des cookies » dans le pied de page de toutes les pages, qui rouvre la CMP.", _R + "rgpd.md#bandeau"),
    ("RGPD-12", "rgpd", "medium", "browser", "Pas de cookie wall (contenu accessible sans accepter)",
     "Le bandeau ne doit pas bloquer l'accès au site ni le défilement. Un cookie wall n'est admis qu'au cas par cas avec alternative réelle.", _R + "rgpd.md#bandeau"),
    ("RGPD-13", "rgpd", "high", "browser", "Polices hébergées localement (pas de Google Fonts distant)",
     "Télécharger les polices (google-webfonts-helper, fontsource) et les servir depuis le site : l'appel à fonts.googleapis.com transmet l'IP du visiteur à Google.", _R + "rgpd.md#tiers"),
    ("RGPD-14", "rgpd", "high", "browser", "Contenus tiers (YouTube, Maps, Vimeo, réseaux sociaux) bloqués avant consentement",
     "Remplacer l'iframe par une vignette « Cliquer pour charger » (façade) ou la conditionner au consentement de la CMP.", _R + "rgpd.md#tiers"),
    ("RGPD-15", "rgpd", "medium", "browser", "reCAPTCHA / widgets de chat : information et base légale",
     "Préférer une alternative sans traceur (Friendly Captcha, hCaptcha configuré, honeypot, Cloudflare Turnstile) ou informer + conditionner.", _R + "rgpd.md#tiers"),
    ("RGPD-16", "rgpd", "low", "browser", "Scripts/CDN tiers inventoriés (transfert d'IP)",
     "Auto-héberger les librairies (jQuery, Bootstrap, icônes…) ou les mentionner comme destinataires dans la politique.", _R + "rgpd.md#tiers"),
    ("RGPD-17", "rgpd", "medium", "code", "Consent Mode / chargement conditionnel des traceurs dans le code",
     "Si gtag/GTM est présent : gtag('consent','default',{…:'denied'}) avant la balise, et mise à jour sur consentement.", _R + "rgpd.md#consentement"),
    # ======================================================================= RGPD — pages légales
    ("RGPD-20", "rgpd", "high", "http", "Page « Mentions légales » présente et accessible depuis toutes les pages",
     "Créer /mentions-legales et la lier dans le footer (LCEN art. 6 III). Modèle : references/rgpd.md#modele-mentions.", _R + "rgpd.md#mentions-legales"),
    ("RGPD-21", "rgpd", "high", "http", "Mentions légales complètes (éditeur, adresse, contact, SIRET/RCS, directeur de publication, hébergeur + téléphone)",
     "Compléter les éléments manquants listés dans le détail.", _R + "rgpd.md#mentions-legales"),
    ("RGPD-22", "rgpd", "high", "http", "Politique de confidentialité présente et accessible depuis toutes les pages",
     "Créer /politique-de-confidentialite et la lier dans le footer et près de chaque formulaire.", _R + "rgpd.md#politique"),
    ("RGPD-23", "rgpd", "high", "http", "Politique de confidentialité complète (art. 13 RGPD)",
     "Ajouter : responsable, finalités, bases légales, durées, destinataires, transferts hors UE, les 6 droits, retrait du consentement, réclamation CNIL, contact/DPO.", _R + "rgpd.md#politique"),
    ("RGPD-24", "rgpd", "medium", "http", "Information cookies (liste des traceurs, finalités, durées)",
     "Ajouter une section ou page cookies listant chaque traceur, son émetteur, sa finalité et sa durée.", _R + "rgpd.md#politique"),
    ("RGPD-25", "rgpd", "medium", "http", "CGV (site marchand) / CGU (comptes utilisateurs) présentes",
     "Site e-commerce : CGV obligatoires (Code de la consommation). Espace membre : CGU recommandées.", _R + "rgpd.md#cgv"),
    ("RGPD-26", "rgpd", "medium", "http", "Médiateur de la consommation mentionné (site marchand B2C)",
     "Indiquer le médiateur de la consommation et ses coordonnées (art. L612-1 C. conso) dans les CGV.", _R + "rgpd.md#cgv"),
    # ======================================================================= RGPD — formulaires
    ("RGPD-30", "rgpd", "high", "http", "Information RGPD à côté de chaque formulaire collectant des données",
     "Sous le formulaire : finalité, base légale, destinataires, durée, droits + lien vers la politique (mention d'information courte).", _R + "rgpd.md#formulaires"),
    ("RGPD-31", "rgpd", "high", "http", "Aucune case de consentement/newsletter pré-cochée",
     "Retirer l'attribut checked des cases d'opt-in (newsletter, partenaires, CGU).", _R + "rgpd.md#formulaires"),
    ("RGPD-32", "rgpd", "critical", "http", "Formulaires envoyés en HTTPS",
     "Action du formulaire en https:// (ou relative sur un site 100 % HTTPS).", _R + "rgpd.md#formulaires"),
    ("RGPD-33", "rgpd", "medium", "http", "Minimisation : champs sensibles ou superflus à justifier",
     "Supprimer les champs non indispensables (date de naissance, civilité, n° de sécu…) ou justifier leur finalité.", _R + "rgpd.md#formulaires"),
    ("RGPD-34", "rgpd", "medium", "code", "Données sensibles/health : stockage et accès protégés",
     "Données de santé ou sensibles : chiffrement, contrôle d'accès, HDS si santé en France. À confirmer.", _R + "rgpd.md#documentaire"),
    # ======================================================================= RGPD — documentaire (hors code)
    ("RGPD-D01", "rgpd", "high", "doc", "Registre des activités de traitement tenu à jour (art. 30)", "Créer le registre (modèle CNIL).", _R + "rgpd.md#documentaire"),
    ("RGPD-D02", "rgpd", "high", "doc", "Contrats de sous-traitance art. 28 signés (hébergeur, emailing, analytics, CRM…)", "Récupérer/accepter les DPA de chaque prestataire.", _R + "rgpd.md#documentaire"),
    ("RGPD-D03", "rgpd", "high", "doc", "Données hébergées dans l'UE ou transferts encadrés (DPF, CCT)", "Vérifier la localisation et les garanties de chaque prestataire.", _R + "rgpd.md#documentaire"),
    ("RGPD-D04", "rgpd", "medium", "doc", "Durées de conservation définies ET appliquées (purge/archivage)", "Mettre en place une purge automatique (cron, TTL).", _R + "rgpd.md#documentaire"),
    ("RGPD-D05", "rgpd", "medium", "doc", "Procédure de réponse aux demandes de droits sous 1 mois", "Adresse dédiée + procédure écrite.", _R + "rgpd.md#documentaire"),
    ("RGPD-D06", "rgpd", "medium", "doc", "Procédure de violation de données (notification CNIL sous 72 h)", "Procédure + registre des violations.", _R + "rgpd.md#documentaire"),
    ("RGPD-D07", "rgpd", "medium", "doc", "AIPD réalisée si traitement à risque (santé, profilage, grande échelle…)", "Réaliser l'AIPD (outil PIA de la CNIL).", _R + "rgpd.md#documentaire"),
    ("RGPD-D08", "rgpd", "medium", "doc", "Preuve des consentements conservée (journal CMP / formulaires)", "Activer la journalisation des consentements.", _R + "rgpd.md#documentaire"),
    ("RGPD-D09", "rgpd", "low", "doc", "DPO désigné si obligatoire, sinon référent identifié", "Désigner un DPO (organisme public, suivi à grande échelle, données sensibles à grande échelle).", _R + "rgpd.md#documentaire"),

    # ======================================================================= SEO
    ("SEO-01", "seo", "high", "http", "Balise <title> présente sur chaque page", "Ajouter un title unique et descriptif.", _R + "seo.md#balises"),
    ("SEO-02", "seo", "low", "http", "Longueur du title entre 30 et 60 caractères", "Viser 50-60 caractères avec le mot-clé principal au début.", _R + "seo.md#balises"),
    ("SEO-03", "seo", "medium", "http", "Titles uniques entre les pages", "Chaque page doit avoir un title distinct.", _R + "seo.md#balises"),
    ("SEO-04", "seo", "medium", "http", "Meta description présente", "Ajouter une meta description incitative.", _R + "seo.md#balises"),
    ("SEO-05", "seo", "low", "http", "Longueur de la meta description entre 70 et 160 caractères", "Viser 120-155 caractères.", _R + "seo.md#balises"),
    ("SEO-06", "seo", "low", "http", "Meta descriptions uniques", "Rédiger une description par page.", _R + "seo.md#balises"),
    ("SEO-07", "seo", "medium", "http", "Un seul H1 par page", "Une page = un H1 qui résume le sujet.", _R + "seo.md#structure"),
    ("SEO-08", "seo", "low", "http", "Hiérarchie des titres sans saut (H2 → H4 interdit)", "Respecter l'ordre H1 > H2 > H3.", _R + "seo.md#structure"),
    ("SEO-09", "seo", "medium", "http", "Attribut lang sur <html>", "<html lang=\"fr\">.", _R + "seo.md#balises"),
    ("SEO-10", "seo", "high", "http", "Meta viewport (mobile-first)", "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.", _R + "seo.md#balises"),
    ("SEO-11", "seo", "medium", "http", "Balise canonical absolue et valide", "<link rel=\"canonical\" href=\"https://domaine/page\"> pointant vers une URL 200.", _R + "seo.md#indexation"),
    ("SEO-12", "seo", "critical", "http", "Aucun noindex involontaire (meta robots / X-Robots-Tag)", "Retirer noindex des pages à indexer (souvent oublié depuis la préprod).", _R + "seo.md#indexation"),
    ("SEO-13", "seo", "high", "http", "robots.txt présent, ne bloque pas le site, référence le sitemap", "Créer robots.txt avec « Sitemap: https://…/sitemap.xml » et sans « Disallow: / » en prod.", _R + "seo.md#indexation"),
    ("SEO-14", "seo", "high", "http", "sitemap.xml présent et XML valide", "Générer un sitemap (plugin du framework ou script de build).", _R + "seo.md#indexation"),
    ("SEO-15", "seo", "medium", "http", "URLs du sitemap en 200 et canoniques", "Retirer du sitemap les URLs redirigées, en erreur ou non canoniques.", _R + "seo.md#indexation"),
    ("SEO-16", "seo", "low", "http", "Pages découvertes présentes dans le sitemap", "Ajouter les pages manquantes au sitemap.", _R + "seo.md#indexation"),
    ("SEO-17", "seo", "medium", "http", "Images avec attribut alt", "alt descriptif sur les images informatives, alt=\"\" sur les décoratives.", _R + "seo.md#contenu"),
    ("SEO-18", "seo", "high", "http", "Aucun lien interne cassé (4xx/5xx)", "Corriger ou rediriger (301) les liens listés.", _R + "seo.md#liens"),
    ("SEO-19", "seo", "low", "http", "Aucun lien externe cassé", "Mettre à jour ou retirer les liens sortants morts.", _R + "seo.md#liens"),
    ("SEO-20", "seo", "low", "http", "Pas de chaînes de redirection (plus d'un saut)", "Faire pointer les liens directement vers l'URL finale.", _R + "seo.md#liens"),
    ("SEO-21", "seo", "medium", "http", "Page inexistante = vrai statut 404 (pas de soft-404)", "Renvoyer le code HTTP 404 sur les routes inconnues (attention aux SPA et fallback index.html).", _R + "seo.md#indexation"),
    ("SEO-22", "seo", "low", "http", "Balises Open Graph (og:title, og:description, og:image, og:url)", "Ajouter les balises OG pour les partages.", _R + "seo.md#social"),
    ("SEO-23", "seo", "low", "http", "Twitter/X card", "<meta name=\"twitter:card\" content=\"summary_large_image\">.", _R + "seo.md#social"),
    ("SEO-24", "seo", "medium", "http", "Données structurées JSON-LD présentes et valides", "Ajouter Organization/LocalBusiness + WebSite (+ Product, Article, BreadcrumbList selon la page).", _R + "seo.md#donnees-structurees"),
    ("SEO-25", "seo", "low", "http", "Favicon déclaré", "<link rel=\"icon\" href=\"/favicon.ico\"> (+ apple-touch-icon).", _R + "seo.md#balises"),
    ("SEO-26", "seo", "low", "http", "Contenu suffisant (pas de page « mince » < 250 mots)", "Enrichir les pages de contenu principal.", _R + "seo.md#contenu"),
    ("SEO-27", "seo", "medium", "http", "Pas de contenu dupliqué entre URLs", "Canonical, redirection 301 ou fusion des pages dupliquées.", _R + "seo.md#contenu"),
    ("SEO-28", "seo", "low", "http", "URLs propres (minuscules, tirets, sans espaces ni paramètres inutiles)", "Réécrire les routes en slugs lisibles.", _R + "seo.md#liens"),
    ("SEO-29", "seo", "low", "http", "hreflang cohérent (si multilingue)", "Chaque version liste toutes les autres + x-default, URLs absolues.", _R + "seo.md#international"),
    ("SEO-30", "seo", "medium", "http", "Une seule version du site (http→https, www↔non-www consolidés)", "Rediriger en 301 toutes les variantes vers l'URL canonique.", _R + "seo.md#indexation"),
    ("SEO-31", "seo", "medium", "browser", "Contenu principal présent dans le HTML sans JavaScript (SSR/SSG)", "SPA : passer en SSR/SSG (Next, Nuxt, Astro, prerender) pour que le contenu soit dans le HTML initial.", _R + "seo.md#rendu"),
    ("SEO-32", "seo", "low", "http", "Liens de navigation en <a href> crawlables", "Remplacer les onclick/router.push sans href par de vrais liens.", _R + "seo.md#liens"),
    ("SEO-33", "seo", "low", "http", "Encodage déclaré (UTF-8)", "<meta charset=\"utf-8\"> en premier dans le <head>.", _R + "seo.md#balises"),
    ("SEO-34", "seo", "medium", "tool", "Score SEO Lighthouse ≥ 90", "Corriger les audits Lighthouse SEO listés.", _R + "seo.md#balises"),

    # ======================================================================= Sécurité — en-têtes & config (HTTP)
    ("SEC-01", "secu", "high", "http", "Content-Security-Policy présente", "Définir une CSP (default-src 'self' ; script-src avec nonce ; object-src 'none' ; base-uri 'self' ; frame-ancestors 'self').", _R + "securite.md#csp"),
    ("SEC-02", "secu", "medium", "http", "CSP stricte (pas de 'unsafe-inline'/'unsafe-eval'/* dans script-src)", "Passer les scripts inline en fichiers ou nonces/hashes ; retirer unsafe-eval.", _R + "securite.md#csp"),
    ("SEC-03", "secu", "high", "http", "Protection anti-clickjacking (frame-ancestors ou X-Frame-Options)", "CSP frame-ancestors 'self' (+ X-Frame-Options: SAMEORIGIN).", _R + "securite.md#entetes"),
    ("SEC-04", "secu", "medium", "http", "X-Content-Type-Options: nosniff", "Ajouter l'en-tête sur toutes les réponses.", _R + "securite.md#entetes"),
    ("SEC-05", "secu", "low", "http", "Referrer-Policy définie", "Referrer-Policy: strict-origin-when-cross-origin.", _R + "securite.md#entetes"),
    ("SEC-06", "secu", "low", "http", "Permissions-Policy définie", "Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=().", _R + "securite.md#entetes"),
    ("SEC-07", "secu", "low", "http", "Cross-Origin-Opener-Policy définie", "Cross-Origin-Opener-Policy: same-origin.", _R + "securite.md#entetes"),
    ("SEC-08", "secu", "low", "http", "Pas de divulgation de version (Server, X-Powered-By)", "Masquer ServerTokens/expose_php/x-powered-by.", _R + "securite.md#entetes"),
    ("SEC-09", "secu", "high", "http", "Cookies avec attribut Secure", "Secure sur tous les cookies en production.", _R + "securite.md#cookies"),
    ("SEC-10", "secu", "high", "http", "Cookies de session HttpOnly", "HttpOnly sur les cookies de session/auth.", _R + "securite.md#cookies"),
    ("SEC-11", "secu", "medium", "http", "Cookies avec SameSite (Lax ou Strict)", "SameSite=Lax par défaut, Strict pour l'admin.", _R + "securite.md#cookies"),
    ("SEC-12", "secu", "high", "http", "CORS non permissif (pas d'origine arbitraire acceptée avec credentials)", "Liste blanche d'origines ; jamais « * » avec credentials ni reflet de l'Origin reçu.", _R + "securite.md#cors"),
    ("SEC-13", "secu", "critical", "http", "Aucun fichier sensible exposé (.env, .git, sauvegardes, dumps SQL, config)", "Bloquer l'accès côté serveur et sortir ces fichiers du webroot.", _R + "securite.md#exposition"),
    ("SEC-14", "secu", "medium", "http", "Listing de répertoires désactivé", "Apache : Options -Indexes ; Nginx : autoindex off.", _R + "securite.md#exposition"),
    ("SEC-15", "secu", "high", "http", "Pages d'erreur sans trace technique (stack trace, debug)", "Désactiver le mode debug en prod et servir des pages d'erreur génériques.", _R + "securite.md#erreurs"),
    ("SEC-16", "secu", "low", "http", "Méthode TRACE désactivée", "Apache : TraceEnable Off.", _R + "securite.md#entetes"),
    ("SEC-17", "secu", "medium", "http", "Intégrité SRI sur les scripts/CSS tiers", "Ajouter integrity=\"sha384-…\" crossorigin=\"anonymous\" ou auto-héberger.", _R + "securite.md#supply-chain"),
    ("SEC-18", "secu", "high", "http", "Aucun contenu mixte (http:// sur page https)", "Passer toutes les ressources en https:// ou relatives.", _R + "securite.md#entetes"),
    ("SEC-19", "secu", "high", "http", "Jeton anti-CSRF dans les formulaires POST", "Ajouter le token CSRF du framework (+ SameSite).", _R + "securite.md#csrf"),
    ("SEC-20", "secu", "low", "http", "/.well-known/security.txt présent", "Créer security.txt (Contact, Expires).", _R + "securite.md#entetes"),
    ("SEC-21", "secu", "medium", "http", "Champs mot de passe correctement configurés (autocomplete, HTTPS)", "autocomplete=\"current-password\"/\"new-password\", formulaire en HTTPS.", _R + "securite.md#auth"),
    ("SEC-22", "secu", "medium", "http", "Interfaces d'administration non exposées publiquement (phpMyAdmin, /server-status…)", "Restreindre par IP/VPN/auth, ou retirer.", _R + "securite.md#exposition"),
    ("SEC-23", "secu", "info", "http", "Inventaire des scripts tiers", "Vérifier que chaque script tiers est nécessaire et maintenu.", _R + "securite.md#supply-chain"),
    ("SEC-24", "secu", "low", "http", "Pages authentifiées/formulaires non mis en cache partagé", "Cache-Control: no-store sur les réponses personnelles.", _R + "securite.md#entetes"),
    # ======================================================================= Sécurité — code
    ("SEC-C01", "secu", "critical", "code", "Aucun secret en dur dans le code (clés API, mots de passe, clés privées)", "Déplacer en variables d'environnement, révoquer/régénérer les secrets exposés, purger l'historique git.", _R + "securite.md#secrets"),
    ("SEC-C02", "secu", "high", "code", "Fichiers .env ignorés par git et non versionnés", "Ajouter .env* au .gitignore, git rm --cached, fournir un .env.example.", _R + "securite.md#secrets"),
    ("SEC-C03", "secu", "high", "code", "Mode debug désactivé pour la production", "APP_DEBUG=false, DEBUG=False, display_errors=Off, NODE_ENV=production.", _R + "securite.md#erreurs"),
    ("SEC-C04", "secu", "high", "code", "Requêtes SQL paramétrées (pas de concaténation de variables)", "Requêtes préparées / ORM avec paramètres liés.", _R + "securite.md#injection"),
    ("SEC-C05", "secu", "medium", "code", "Pas d'insertion HTML non échappée (innerHTML, v-html, dangerouslySetInnerHTML, {!! !!}, |safe)", "Échapper ou assainir (DOMPurify) toute donnée injectée en HTML.", _R + "securite.md#xss"),
    ("SEC-C06", "secu", "medium", "code", "Pas d'évaluation dynamique de code / commandes shell avec données externes", "Supprimer eval/exec/shell=True ; utiliser des API sûres avec liste blanche.", _R + "securite.md#injection"),
    ("SEC-C07", "secu", "critical", "code", "Mots de passe hachés avec un algorithme adapté (bcrypt/argon2/scrypt/PBKDF2)", "Remplacer md5/sha1/sha256 simples par password_hash/bcrypt/argon2id.", _R + "securite.md#auth"),
    ("SEC-C08", "secu", "high", "code", "Vérification TLS jamais désactivée dans le code", "Retirer verify=False / rejectUnauthorized:false / InsecureSkipVerify.", _R + "securite.md#entetes"),
    ("SEC-C09", "secu", "medium", "code", "CORS non ouvert à « * » dans la config applicative", "Liste blanche explicite d'origines.", _R + "securite.md#cors"),
    ("SEC-C10", "secu", "critical", "tool", "Aucune dépendance avec vulnérabilité connue (critique/haute)", "Mettre à jour les paquets listés (npm audit fix, composer update…).", _R + "securite.md#supply-chain"),
    ("SEC-C11", "secu", "medium", "code", "Fichier de verrouillage des dépendances versionné", "Committer package-lock.json / composer.lock / poetry.lock…", _R + "securite.md#supply-chain"),
    ("SEC-C12", "secu", "medium", "code", "Limitation de débit (rate limiting) sur l'authentification", "express-rate-limit, throttle Laravel, django-axes, slowapi, rack-attack…", _R + "securite.md#auth"),
    ("SEC-C13", "secu", "medium", "code", "Politique de mot de passe conforme CNIL (≥ 12 caractères avec complexité, ou ≥ 14)", "minlength 12 + 4 types de caractères, ou 14 sans caractères spéciaux, ou passphrase.", _R + "securite.md#auth"),
    ("SEC-C14", "secu", "medium", "code", "Upload de fichiers contrôlé (type, taille, stockage hors webroot)", "Vérifier MIME réel + extension, taille max, renommage, stockage hors webroot.", _R + "securite.md#upload"),
    ("SEC-C15", "secu", "high", "tool", "Analyse statique SAST (Semgrep) sans alerte bloquante", "Corriger les alertes ERROR de Semgrep.", _R + "securite.md#outils"),
    ("SEC-C16", "secu", "critical", "tool", "Aucun secret dans l'historique git (Gitleaks)", "Révoquer les secrets trouvés puis réécrire l'historique (git filter-repo).", _R + "securite.md#secrets"),
    ("SEC-C17", "secu", "high", "code", "Contrôle d'accès côté serveur sur les routes protégées", "Middleware d'auth + vérification d'appartenance des ressources (IDOR) sur chaque route sensible.", _R + "securite.md#acces"),
    ("SEC-C18", "secu", "medium", "code", "Journalisation des événements de sécurité (connexions, échecs, actions admin)", "Logger sans données sensibles, avec alerte sur anomalies.", _R + "securite.md#logs"),
    # ======================================================================= Sécurité — documentaire
    ("SEC-D01", "secu", "high", "doc", "Sauvegardes automatiques, chiffrées, externalisées et restauration testée", "Mettre en place 3-2-1 + test de restauration.", _R + "securite.md#organisationnel"),
    ("SEC-D02", "secu", "high", "doc", "MFA sur les comptes admin (hébergeur, registrar, CMS, dépôt git)", "Activer la double authentification partout.", _R + "securite.md#organisationnel"),
    ("SEC-D03", "secu", "medium", "doc", "Mises à jour de sécurité appliquées régulièrement (OS, serveur, CMS, dépendances)", "Planifier (unattended-upgrades, Dependabot/Renovate).", _R + "securite.md#organisationnel"),
    ("SEC-D04", "secu", "medium", "doc", "Moindre privilège (utilisateur BDD dédié sans droits admin, pare-feu, SSH par clé)", "Compte BDD applicatif limité, ufw, PasswordAuthentication no.", _R + "securite.md#organisationnel"),

    # ======================================================================= SSL / TLS
    ("TLS-01", "tls", "critical", "http", "Certificat valide et chaîne de confiance reconnue", "Installer un certificat reconnu (Let's Encrypt via Certbot/Caddy) avec la chaîne complète.", _R + "ssl-tls.md#certificat"),
    ("TLS-02", "tls", "critical", "http", "Le certificat couvre le nom de domaine (et www)", "Émettre le certificat pour domaine.fr ET www.domaine.fr.", _R + "ssl-tls.md#certificat"),
    ("TLS-03", "tls", "high", "http", "Expiration du certificat > 30 jours (et renouvellement automatique)", "Automatiser le renouvellement (certbot renew timer, Caddy, ACME de l'hébergeur).", _R + "ssl-tls.md#renouvellement"),
    ("TLS-04", "tls", "high", "http", "TLS 1.0 et 1.1 désactivés", "Protocoles autorisés : TLSv1.2 TLSv1.3 uniquement.", _R + "ssl-tls.md#protocoles"),
    ("TLS-05", "tls", "medium", "http", "TLS 1.3 supporté", "Activer TLSv1.3 (OpenSSL ≥ 1.1.1).", _R + "ssl-tls.md#protocoles"),
    ("TLS-06", "tls", "high", "http", "Clé robuste (RSA ≥ 2048 bits ou ECDSA ≥ 256 bits)", "Régénérer la clé (ECDSA P-256 recommandé).", _R + "ssl-tls.md#certificat"),
    ("TLS-07", "tls", "high", "http", "Signature du certificat SHA-256 ou supérieure", "Réémettre le certificat.", _R + "ssl-tls.md#certificat"),
    ("TLS-08", "tls", "high", "http", "Aucune suite de chiffrement faible acceptée (RC4, 3DES, NULL, EXPORT, anonymes)", "Appliquer la config Mozilla « Intermediate ».", _R + "ssl-tls.md#protocoles"),
    ("TLS-09", "tls", "high", "http", "Chaîne complète servie (certificats intermédiaires)", "Utiliser fullchain.pem et non cert.pem.", _R + "ssl-tls.md#certificat"),
    ("TLS-10", "tls", "critical", "http", "HTTP redirige vers HTTPS en 301/308", "Redirection permanente de toutes les URLs http:// vers https://.", _R + "ssl-tls.md#redirection"),
    ("TLS-11", "tls", "high", "http", "HSTS actif (max-age ≥ 1 an, includeSubDomains)", "Strict-Transport-Security: max-age=31536000; includeSubDomains (preload quand tout est prêt).", _R + "ssl-tls.md#hsts"),
    ("TLS-12", "tls", "low", "http", "Enregistrement DNS CAA", "Ajouter CAA 0 issue \"letsencrypt.org\" (ou votre AC).", _R + "ssl-tls.md#dns"),
    ("TLS-13", "tls", "medium", "code", "Config serveur du dépôt : redirection HTTPS + HSTS prévus (mode local)", "Ajouter la redirection et HSTS dans la config serveur/app versionnée.", _R + "ssl-tls.md#redirection"),
    ("TLS-14", "tls", "info", "http", "OCSP stapling (informatif)", "Optionnel ; certaines AC (dont Let's Encrypt) ont abandonné OCSP.", _R + "ssl-tls.md#protocoles"),
    ("TLS-15", "tls", "high", "http", "Aucune ressource de la page servie en HTTP (voir aussi SEC-18)", "Tout charger en HTTPS.", _R + "ssl-tls.md#redirection"),

    # ======================================================================= Performance
    ("PERF-01", "perf", "high", "tool", "Score Performance Lighthouse (mobile) ≥ 90", "Traiter les opportunités Lighthouse listées.", _R + "performance.md#lighthouse"),
    ("PERF-02", "perf", "high", "tool", "LCP ≤ 2,5 s", "Précharger l'image LCP (fetchpriority=high), SSR, CDN, image optimisée.", _R + "performance.md#cwv"),
    ("PERF-03", "perf", "high", "tool", "CLS ≤ 0,1", "width/height sur images/iframes, réserver l'espace des bannières, font-display.", _R + "performance.md#cwv"),
    ("PERF-04", "perf", "medium", "tool", "TBT ≤ 200 ms (proxy labo de l'INP)", "Découper le JS, différer les scripts tiers, code splitting.", _R + "performance.md#cwv"),
    ("PERF-05", "perf", "medium", "tool", "FCP ≤ 1,8 s", "Réduire le CSS/JS bloquant, CSS critique inline.", _R + "performance.md#cwv"),
    ("PERF-06", "perf", "medium", "http", "TTFB ≤ 800 ms", "Cache serveur/page, requêtes BDD indexées, CDN, OPcache.", _R + "performance.md#serveur"),
    ("PERF-07", "perf", "high", "http", "Compression gzip/Brotli des ressources texte", "Activer brotli/gzip (mod_deflate, gzip on, compression middleware).", _R + "performance.md#serveur"),
    ("PERF-08", "perf", "medium", "http", "Cache long sur les ressources statiques versionnées", "Cache-Control: public, max-age=31536000, immutable sur les assets hashés.", _R + "performance.md#cache"),
    ("PERF-09", "perf", "medium", "browser", "Poids total de la page ≤ 1,6 Mo", "Compresser images, supprimer le JS inutile, lazy-load.", _R + "performance.md#poids"),
    ("PERF-10", "perf", "low", "browser", "Nombre de requêtes ≤ 70", "Regrouper, supprimer les scripts tiers superflus.", _R + "performance.md#poids"),
    ("PERF-11", "perf", "medium", "http", "Images en formats modernes (WebP/AVIF)", "Convertir (sharp, squoosh, <picture>).", _R + "performance.md#images"),
    ("PERF-12", "perf", "medium", "http", "Dimensions (width/height) sur les images", "Ajouter width et height pour éviter le CLS.", _R + "performance.md#images"),
    ("PERF-13", "perf", "low", "http", "Lazy-loading des images hors écran", "loading=\"lazy\" sauf pour l'image LCP.", _R + "performance.md#images"),
    ("PERF-14", "perf", "medium", "http", "Pas de script bloquant dans le <head> (defer/async/module)", "Ajouter defer ou déplacer en fin de body.", _R + "performance.md#js"),
    ("PERF-15", "perf", "low", "http", "Polices : font-display et préchargement", "font-display: swap ; <link rel=preload as=font crossorigin>.", _R + "performance.md#polices"),
    ("PERF-16", "perf", "medium", "http", "HTTP/2 ou HTTP/3 activé", "Activer HTTP/2 (Protocols h2 http/1.1 ; listen 443 ssl http2).", _R + "performance.md#serveur"),
    ("PERF-17", "perf", "medium", "browser", "JavaScript total ≤ 350 Ko transférés", "Code splitting, tree-shaking, supprimer librairies lourdes.", _R + "performance.md#js"),
    ("PERF-18", "perf", "low", "http", "CSS/JS minifiés", "Build de production (Vite/Webpack) ou minification serveur.", _R + "performance.md#js"),
    ("PERF-19", "perf", "low", "tool", "Score Best Practices Lighthouse ≥ 90", "Corriger les audits Best Practices listés.", _R + "performance.md#lighthouse"),
    ("PERF-20", "perf", "low", "http", "Images pas surdimensionnées (poids unitaire ≤ 300 Ko)", "Redimensionner, srcset/sizes.", _R + "performance.md#images"),

    # ======================================================================= Accessibilité
    ("A11Y-01", "a11y", "high", "tool", "Score Accessibilité Lighthouse ≥ 90", "Corriger les audits listés.", _R + "accessibilite.md"),
    ("A11Y-02", "a11y", "high", "tool", "Aucune violation axe-core critique/sérieuse", "Corriger les violations listées (règle, élément).", _R + "accessibilite.md"),
    ("A11Y-03", "a11y", "high", "http", "Champs de formulaire avec label", "<label for> ou aria-label sur chaque champ.", _R + "accessibilite.md#formulaires"),
    ("A11Y-04", "a11y", "medium", "http", "Boutons et liens avec un nom accessible", "Texte visible ou aria-label sur les boutons icônes.", _R + "accessibilite.md"),
    ("A11Y-05", "a11y", "medium", "http", "Zoom non bloqué (pas de user-scalable=no / maximum-scale=1)", "Retirer ces paramètres du viewport.", _R + "accessibilite.md"),
    ("A11Y-06", "a11y", "low", "http", "Repères de structure (main, nav) et lien d'évitement", "<main>, <nav>, lien « Aller au contenu ».", _R + "accessibilite.md"),
    ("A11Y-07", "a11y", "medium", "doc", "Déclaration d'accessibilité si le site y est soumis (RGAA / EAA)", "Publier la déclaration + mention « Accessibilité : non/partiellement/totalement conforme ».", _R + "accessibilite.md#obligations"),
]

CHECKS = {
    cid: {"cat": cat, "sev": sev, "method": meth, "title": title, "fix": fix, "ref": ref}
    for cid, cat, sev, meth, title, fix, ref in _C
}

# questions posées au client pour les contrôles documentaires
DOC_QUESTIONS = {cid: v["title"] for cid, v in CHECKS.items() if v["method"] == "doc"}


def catalog_markdown() -> str:
    lines = ["# Catalogue des contrôles", "",
             f"{len(CHECKS)} contrôles. Gravité → poids : critical 10, high 6, medium 3, low 1, info 0.",
             "Méthode : http = requêtes réelles, browser = Chromium réel, code = analyse du dépôt, tool = outil externe, doc = question au client.", ""]
    for cat, label in CATEGORIES.items():
        items = [(k, v) for k, v in CHECKS.items() if v["cat"] == cat]
        lines += [f"## {label} ({len(items)})", "", "| ID | Gravité | Méthode | Contrôle | Correction |", "|---|---|---|---|---|"]
        for k, v in items:
            lines.append(f"| {k} | {v['sev']} | {v['method']} | {v['title']} | {v['fix'].replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)
