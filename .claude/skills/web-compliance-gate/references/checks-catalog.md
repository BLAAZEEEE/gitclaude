# Catalogue des contrôles

160 contrôles. Gravité → poids : critical 10, high 6, medium 3, low 1, info 0.
Méthode : http = requêtes réelles, browser = Chromium réel, code = analyse du dépôt, tool = outil externe, doc = question au client.

## RGPD & cookies (38)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| RGPD-01 | critical | browser | Aucun cookie/traceur non exempté déposé avant consentement | Bloquer tout script de mesure/pub/réseaux sociaux tant que l'utilisateur n'a pas accepté (CMP ou chargement conditionnel). Seuls les cookies strictement nécessaires (session, panier, CSRF, choix de consentement) sont permis avant. |
| RGPD-02 | critical | browser | Aucune requête vers un domaine de tracking avant consentement | Ne charger Google Analytics/Tag Manager, Meta Pixel, Hotjar, Clarity, LinkedIn, TikTok… qu'après un clic sur « Accepter ». Avec GTM : Consent Mode v2 en « denied » par défaut ET balises conditionnées. |
| RGPD-03 | high | browser | Aucun identifiant de traceur en localStorage/sessionStorage avant consentement | Même règle que pour les cookies (art. 82 loi Informatique et Libertés) : le stockage local d'identifiants de suivi exige le consentement. |
| RGPD-04 | high | browser | Bandeau de consentement présent si des traceurs soumis à consentement existent | Ajouter une CMP (tarteaucitron.js, Axeptio, Didomi, orestbida/cookieconsent…) ou supprimer les traceurs. Sans traceur soumis à consentement, aucun bandeau n'est requis. |
| RGPD-05 | critical | browser | Bouton « Refuser » disponible au premier niveau du bandeau | Ajouter « Tout refuser » (ou « Continuer sans accepter ») sur le premier écran, sans passer par « Paramétrer ». |
| RGPD-06 | high | browser | Refuser aussi visible et simple qu'Accepter (taille, style, un clic) | Même composant, même taille, même contraste pour Accepter et Refuser. Pas de lien gris minuscule pour refuser. |
| RGPD-07 | critical | browser | Après « Refuser » : aucun traceur chargé ni cookie non exempté | Vérifier que le refus est bien propagé à tous les scripts (catégories de la CMP, Consent Mode, iframes). |
| RGPD-08 | high | browser | Le refus est respecté sur les pages suivantes (navigation) | Le choix doit être mémorisé (cookie de choix) et relu sur chaque page avant tout chargement de traceur. |
| RGPD-09 | medium | browser | Durée de vie des cookies traceurs ≤ 13 mois | Configurer la durée des cookies analytics/pub à 13 mois maximum (ex. GA4 : cookie_expires ≤ 34186669 s). |
| RGPD-10 | low | browser | Choix de consentement conservé ~6 mois (bonne pratique CNIL) | Régler la durée du cookie de choix de la CMP autour de 6 mois, puis redemander. |
| RGPD-11 | medium | browser | Lien permanent pour modifier/retirer son consentement | Ajouter un lien « Gestion des cookies » dans le pied de page de toutes les pages, qui rouvre la CMP. |
| RGPD-12 | medium | browser | Pas de cookie wall (contenu accessible sans accepter) | Le bandeau ne doit pas bloquer l'accès au site ni le défilement. Un cookie wall n'est admis qu'au cas par cas avec alternative réelle. |
| RGPD-13 | high | browser | Polices hébergées localement (pas de Google Fonts distant) | Télécharger les polices (google-webfonts-helper, fontsource) et les servir depuis le site : l'appel à fonts.googleapis.com transmet l'IP du visiteur à Google. |
| RGPD-14 | high | browser | Contenus tiers (YouTube, Maps, Vimeo, réseaux sociaux) bloqués avant consentement | Remplacer l'iframe par une vignette « Cliquer pour charger » (façade) ou la conditionner au consentement de la CMP. |
| RGPD-15 | medium | browser | reCAPTCHA / widgets de chat : information et base légale | Préférer une alternative sans traceur (Friendly Captcha, hCaptcha configuré, honeypot, Cloudflare Turnstile) ou informer + conditionner. |
| RGPD-16 | low | browser | Scripts/CDN tiers inventoriés (transfert d'IP) | Auto-héberger les librairies (jQuery, Bootstrap, icônes…) ou les mentionner comme destinataires dans la politique. |
| RGPD-17 | medium | code | Consent Mode / chargement conditionnel des traceurs dans le code | Si gtag/GTM est présent : gtag('consent','default',{…:'denied'}) avant la balise, et mise à jour sur consentement. |
| RGPD-20 | high | http | Page « Mentions légales » présente et accessible depuis toutes les pages | Créer /mentions-legales et la lier dans le footer (LCEN art. 6 III). Modèle : references/rgpd.md#modele-mentions. |
| RGPD-21 | high | http | Mentions légales complètes (éditeur, adresse, contact, SIRET/RCS, directeur de publication, hébergeur + téléphone) | Compléter les éléments manquants listés dans le détail. |
| RGPD-22 | high | http | Politique de confidentialité présente et accessible depuis toutes les pages | Créer /politique-de-confidentialite et la lier dans le footer et près de chaque formulaire. |
| RGPD-23 | high | http | Politique de confidentialité complète (art. 13 RGPD) | Ajouter : responsable, finalités, bases légales, durées, destinataires, transferts hors UE, les 6 droits, retrait du consentement, réclamation CNIL, contact/DPO. |
| RGPD-24 | medium | http | Information cookies (liste des traceurs, finalités, durées) | Ajouter une section ou page cookies listant chaque traceur, son émetteur, sa finalité et sa durée. |
| RGPD-25 | medium | http | CGV (site marchand) / CGU (comptes utilisateurs) présentes | Site e-commerce : CGV obligatoires (Code de la consommation). Espace membre : CGU recommandées. |
| RGPD-26 | medium | http | Médiateur de la consommation mentionné (site marchand B2C) | Indiquer le médiateur de la consommation et ses coordonnées (art. L612-1 C. conso) dans les CGV. |
| RGPD-30 | high | http | Information RGPD à côté de chaque formulaire collectant des données | Sous le formulaire : finalité, base légale, destinataires, durée, droits + lien vers la politique (mention d'information courte). |
| RGPD-31 | high | http | Aucune case de consentement/newsletter pré-cochée | Retirer l'attribut checked des cases d'opt-in (newsletter, partenaires, CGU). |
| RGPD-32 | critical | http | Formulaires envoyés en HTTPS | Action du formulaire en https:// (ou relative sur un site 100 % HTTPS). |
| RGPD-33 | medium | http | Minimisation : champs sensibles ou superflus à justifier | Supprimer les champs non indispensables (date de naissance, civilité, n° de sécu…) ou justifier leur finalité. |
| RGPD-34 | medium | code | Données sensibles/health : stockage et accès protégés | Données de santé ou sensibles : chiffrement, contrôle d'accès, HDS si santé en France. À confirmer. |
| RGPD-D01 | high | doc | Registre des activités de traitement tenu à jour (art. 30) | Créer le registre (modèle CNIL). |
| RGPD-D02 | high | doc | Contrats de sous-traitance art. 28 signés (hébergeur, emailing, analytics, CRM…) | Récupérer/accepter les DPA de chaque prestataire. |
| RGPD-D03 | high | doc | Données hébergées dans l'UE ou transferts encadrés (DPF, CCT) | Vérifier la localisation et les garanties de chaque prestataire. |
| RGPD-D04 | medium | doc | Durées de conservation définies ET appliquées (purge/archivage) | Mettre en place une purge automatique (cron, TTL). |
| RGPD-D05 | medium | doc | Procédure de réponse aux demandes de droits sous 1 mois | Adresse dédiée + procédure écrite. |
| RGPD-D06 | medium | doc | Procédure de violation de données (notification CNIL sous 72 h) | Procédure + registre des violations. |
| RGPD-D07 | medium | doc | AIPD réalisée si traitement à risque (santé, profilage, grande échelle…) | Réaliser l'AIPD (outil PIA de la CNIL). |
| RGPD-D08 | medium | doc | Preuve des consentements conservée (journal CMP / formulaires) | Activer la journalisation des consentements. |
| RGPD-D09 | low | doc | DPO désigné si obligatoire, sinon référent identifié | Désigner un DPO (organisme public, suivi à grande échelle, données sensibles à grande échelle). |

## SEO (34)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| SEO-01 | high | http | Balise <title> présente sur chaque page | Ajouter un title unique et descriptif. |
| SEO-02 | low | http | Longueur du title entre 30 et 60 caractères | Viser 50-60 caractères avec le mot-clé principal au début. |
| SEO-03 | medium | http | Titles uniques entre les pages | Chaque page doit avoir un title distinct. |
| SEO-04 | medium | http | Meta description présente | Ajouter une meta description incitative. |
| SEO-05 | low | http | Longueur de la meta description entre 70 et 160 caractères | Viser 120-155 caractères. |
| SEO-06 | low | http | Meta descriptions uniques | Rédiger une description par page. |
| SEO-07 | medium | http | Un seul H1 par page | Une page = un H1 qui résume le sujet. |
| SEO-08 | low | http | Hiérarchie des titres sans saut (H2 → H4 interdit) | Respecter l'ordre H1 > H2 > H3. |
| SEO-09 | medium | http | Attribut lang sur <html> | <html lang="fr">. |
| SEO-10 | high | http | Meta viewport (mobile-first) | <meta name="viewport" content="width=device-width, initial-scale=1">. |
| SEO-11 | medium | http | Balise canonical absolue et valide | <link rel="canonical" href="https://domaine/page"> pointant vers une URL 200. |
| SEO-12 | critical | http | Aucun noindex involontaire (meta robots / X-Robots-Tag) | Retirer noindex des pages à indexer (souvent oublié depuis la préprod). |
| SEO-13 | high | http | robots.txt présent, ne bloque pas le site, référence le sitemap | Créer robots.txt avec « Sitemap: https://…/sitemap.xml » et sans « Disallow: / » en prod. |
| SEO-14 | high | http | sitemap.xml présent et XML valide | Générer un sitemap (plugin du framework ou script de build). |
| SEO-15 | medium | http | URLs du sitemap en 200 et canoniques | Retirer du sitemap les URLs redirigées, en erreur ou non canoniques. |
| SEO-16 | low | http | Pages découvertes présentes dans le sitemap | Ajouter les pages manquantes au sitemap. |
| SEO-17 | medium | http | Images avec attribut alt | alt descriptif sur les images informatives, alt="" sur les décoratives. |
| SEO-18 | high | http | Aucun lien interne cassé (4xx/5xx) | Corriger ou rediriger (301) les liens listés. |
| SEO-19 | low | http | Aucun lien externe cassé | Mettre à jour ou retirer les liens sortants morts. |
| SEO-20 | low | http | Pas de chaînes de redirection (plus d'un saut) | Faire pointer les liens directement vers l'URL finale. |
| SEO-21 | medium | http | Page inexistante = vrai statut 404 (pas de soft-404) | Renvoyer le code HTTP 404 sur les routes inconnues (attention aux SPA et fallback index.html). |
| SEO-22 | low | http | Balises Open Graph (og:title, og:description, og:image, og:url) | Ajouter les balises OG pour les partages. |
| SEO-23 | low | http | Twitter/X card | <meta name="twitter:card" content="summary_large_image">. |
| SEO-24 | medium | http | Données structurées JSON-LD présentes et valides | Ajouter Organization/LocalBusiness + WebSite (+ Product, Article, BreadcrumbList selon la page). |
| SEO-25 | low | http | Favicon déclaré | <link rel="icon" href="/favicon.ico"> (+ apple-touch-icon). |
| SEO-26 | low | http | Contenu suffisant (pas de page « mince » < 250 mots) | Enrichir les pages de contenu principal. |
| SEO-27 | medium | http | Pas de contenu dupliqué entre URLs | Canonical, redirection 301 ou fusion des pages dupliquées. |
| SEO-28 | low | http | URLs propres (minuscules, tirets, sans espaces ni paramètres inutiles) | Réécrire les routes en slugs lisibles. |
| SEO-29 | low | http | hreflang cohérent (si multilingue) | Chaque version liste toutes les autres + x-default, URLs absolues. |
| SEO-30 | medium | http | Une seule version du site (http→https, www↔non-www consolidés) | Rediriger en 301 toutes les variantes vers l'URL canonique. |
| SEO-31 | medium | browser | Contenu principal présent dans le HTML sans JavaScript (SSR/SSG) | SPA : passer en SSR/SSG (Next, Nuxt, Astro, prerender) pour que le contenu soit dans le HTML initial. |
| SEO-32 | low | http | Liens de navigation en <a href> crawlables | Remplacer les onclick/router.push sans href par de vrais liens. |
| SEO-33 | low | http | Encodage déclaré (UTF-8) | <meta charset="utf-8"> en premier dans le <head>. |
| SEO-34 | medium | tool | Score SEO Lighthouse ≥ 90 | Corriger les audits Lighthouse SEO listés. |

## Sécurité (46)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| SEC-01 | high | http | Content-Security-Policy présente | Définir une CSP (default-src 'self' ; script-src avec nonce ; object-src 'none' ; base-uri 'self' ; frame-ancestors 'self'). |
| SEC-02 | medium | http | CSP stricte (pas de 'unsafe-inline'/'unsafe-eval'/* dans script-src) | Passer les scripts inline en fichiers ou nonces/hashes ; retirer unsafe-eval. |
| SEC-03 | high | http | Protection anti-clickjacking (frame-ancestors ou X-Frame-Options) | CSP frame-ancestors 'self' (+ X-Frame-Options: SAMEORIGIN). |
| SEC-04 | medium | http | X-Content-Type-Options: nosniff | Ajouter l'en-tête sur toutes les réponses. |
| SEC-05 | low | http | Referrer-Policy définie | Referrer-Policy: strict-origin-when-cross-origin. |
| SEC-06 | low | http | Permissions-Policy définie | Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=(). |
| SEC-07 | low | http | Cross-Origin-Opener-Policy définie | Cross-Origin-Opener-Policy: same-origin. |
| SEC-08 | low | http | Pas de divulgation de version (Server, X-Powered-By) | Masquer ServerTokens/expose_php/x-powered-by. |
| SEC-09 | high | http | Cookies avec attribut Secure | Secure sur tous les cookies en production. |
| SEC-10 | high | http | Cookies de session HttpOnly | HttpOnly sur les cookies de session/auth. |
| SEC-11 | medium | http | Cookies avec SameSite (Lax ou Strict) | SameSite=Lax par défaut, Strict pour l'admin. |
| SEC-12 | high | http | CORS non permissif (pas d'origine arbitraire acceptée avec credentials) | Liste blanche d'origines ; jamais « * » avec credentials ni reflet de l'Origin reçu. |
| SEC-13 | critical | http | Aucun fichier sensible exposé (.env, .git, sauvegardes, dumps SQL, config) | Bloquer l'accès côté serveur et sortir ces fichiers du webroot. |
| SEC-14 | medium | http | Listing de répertoires désactivé | Apache : Options -Indexes ; Nginx : autoindex off. |
| SEC-15 | high | http | Pages d'erreur sans trace technique (stack trace, debug) | Désactiver le mode debug en prod et servir des pages d'erreur génériques. |
| SEC-16 | low | http | Méthode TRACE désactivée | Apache : TraceEnable Off. |
| SEC-17 | medium | http | Intégrité SRI sur les scripts/CSS tiers | Ajouter integrity="sha384-…" crossorigin="anonymous" ou auto-héberger. |
| SEC-18 | high | http | Aucun contenu mixte (http:// sur page https) | Passer toutes les ressources en https:// ou relatives. |
| SEC-19 | high | http | Jeton anti-CSRF dans les formulaires POST | Ajouter le token CSRF du framework (+ SameSite). |
| SEC-20 | low | http | /.well-known/security.txt présent | Créer security.txt (Contact, Expires). |
| SEC-21 | medium | http | Champs mot de passe correctement configurés (autocomplete, HTTPS) | autocomplete="current-password"/"new-password", formulaire en HTTPS. |
| SEC-22 | medium | http | Interfaces d'administration non exposées publiquement (phpMyAdmin, /server-status…) | Restreindre par IP/VPN/auth, ou retirer. |
| SEC-23 | info | http | Inventaire des scripts tiers | Vérifier que chaque script tiers est nécessaire et maintenu. |
| SEC-24 | low | http | Pages authentifiées/formulaires non mis en cache partagé | Cache-Control: no-store sur les réponses personnelles. |
| SEC-C01 | critical | code | Aucun secret en dur dans le code (clés API, mots de passe, clés privées) | Déplacer en variables d'environnement, révoquer/régénérer les secrets exposés, purger l'historique git. |
| SEC-C02 | high | code | Fichiers .env ignorés par git et non versionnés | Ajouter .env* au .gitignore, git rm --cached, fournir un .env.example. |
| SEC-C03 | high | code | Mode debug désactivé pour la production | APP_DEBUG=false, DEBUG=False, display_errors=Off, NODE_ENV=production. |
| SEC-C04 | high | code | Requêtes SQL paramétrées (pas de concaténation de variables) | Requêtes préparées / ORM avec paramètres liés. |
| SEC-C05 | medium | code | Pas d'insertion HTML non échappée (innerHTML, v-html, dangerouslySetInnerHTML, {!! !!}, |safe) | Échapper ou assainir (DOMPurify) toute donnée injectée en HTML. |
| SEC-C06 | medium | code | Pas d'évaluation dynamique de code / commandes shell avec données externes | Supprimer eval/exec/shell=True ; utiliser des API sûres avec liste blanche. |
| SEC-C07 | critical | code | Mots de passe hachés avec un algorithme adapté (bcrypt/argon2/scrypt/PBKDF2) | Remplacer md5/sha1/sha256 simples par password_hash/bcrypt/argon2id. |
| SEC-C08 | high | code | Vérification TLS jamais désactivée dans le code | Retirer verify=False / rejectUnauthorized:false / InsecureSkipVerify. |
| SEC-C09 | medium | code | CORS non ouvert à « * » dans la config applicative | Liste blanche explicite d'origines. |
| SEC-C10 | critical | tool | Aucune dépendance avec vulnérabilité connue (critique/haute) | Mettre à jour les paquets listés (npm audit fix, composer update…). |
| SEC-C11 | medium | code | Fichier de verrouillage des dépendances versionné | Committer package-lock.json / composer.lock / poetry.lock… |
| SEC-C12 | medium | code | Limitation de débit (rate limiting) sur l'authentification | express-rate-limit, throttle Laravel, django-axes, slowapi, rack-attack… |
| SEC-C13 | medium | code | Politique de mot de passe conforme CNIL (≥ 12 caractères avec complexité, ou ≥ 14) | minlength 12 + 4 types de caractères, ou 14 sans caractères spéciaux, ou passphrase. |
| SEC-C14 | medium | code | Upload de fichiers contrôlé (type, taille, stockage hors webroot) | Vérifier MIME réel + extension, taille max, renommage, stockage hors webroot. |
| SEC-C15 | high | tool | Analyse statique SAST (Semgrep) sans alerte bloquante | Corriger les alertes ERROR de Semgrep. |
| SEC-C16 | critical | tool | Aucun secret dans l'historique git (Gitleaks) | Révoquer les secrets trouvés puis réécrire l'historique (git filter-repo). |
| SEC-C17 | high | code | Contrôle d'accès côté serveur sur les routes protégées | Middleware d'auth + vérification d'appartenance des ressources (IDOR) sur chaque route sensible. |
| SEC-C18 | medium | code | Journalisation des événements de sécurité (connexions, échecs, actions admin) | Logger sans données sensibles, avec alerte sur anomalies. |
| SEC-D01 | high | doc | Sauvegardes automatiques, chiffrées, externalisées et restauration testée | Mettre en place 3-2-1 + test de restauration. |
| SEC-D02 | high | doc | MFA sur les comptes admin (hébergeur, registrar, CMS, dépôt git) | Activer la double authentification partout. |
| SEC-D03 | medium | doc | Mises à jour de sécurité appliquées régulièrement (OS, serveur, CMS, dépendances) | Planifier (unattended-upgrades, Dependabot/Renovate). |
| SEC-D04 | medium | doc | Moindre privilège (utilisateur BDD dédié sans droits admin, pare-feu, SSH par clé) | Compte BDD applicatif limité, ufw, PasswordAuthentication no. |

## SSL / TLS & HTTPS (15)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| TLS-01 | critical | http | Certificat valide et chaîne de confiance reconnue | Installer un certificat reconnu (Let's Encrypt via Certbot/Caddy) avec la chaîne complète. |
| TLS-02 | critical | http | Le certificat couvre le nom de domaine (et www) | Émettre le certificat pour domaine.fr ET www.domaine.fr. |
| TLS-03 | high | http | Expiration du certificat > 30 jours (et renouvellement automatique) | Automatiser le renouvellement (certbot renew timer, Caddy, ACME de l'hébergeur). |
| TLS-04 | high | http | TLS 1.0 et 1.1 désactivés | Protocoles autorisés : TLSv1.2 TLSv1.3 uniquement. |
| TLS-05 | medium | http | TLS 1.3 supporté | Activer TLSv1.3 (OpenSSL ≥ 1.1.1). |
| TLS-06 | high | http | Clé robuste (RSA ≥ 2048 bits ou ECDSA ≥ 256 bits) | Régénérer la clé (ECDSA P-256 recommandé). |
| TLS-07 | high | http | Signature du certificat SHA-256 ou supérieure | Réémettre le certificat. |
| TLS-08 | high | http | Aucune suite de chiffrement faible acceptée (RC4, 3DES, NULL, EXPORT, anonymes) | Appliquer la config Mozilla « Intermediate ». |
| TLS-09 | high | http | Chaîne complète servie (certificats intermédiaires) | Utiliser fullchain.pem et non cert.pem. |
| TLS-10 | critical | http | HTTP redirige vers HTTPS en 301/308 | Redirection permanente de toutes les URLs http:// vers https://. |
| TLS-11 | high | http | HSTS actif (max-age ≥ 1 an, includeSubDomains) | Strict-Transport-Security: max-age=31536000; includeSubDomains (preload quand tout est prêt). |
| TLS-12 | low | http | Enregistrement DNS CAA | Ajouter CAA 0 issue "letsencrypt.org" (ou votre AC). |
| TLS-13 | medium | code | Config serveur du dépôt : redirection HTTPS + HSTS prévus (mode local) | Ajouter la redirection et HSTS dans la config serveur/app versionnée. |
| TLS-14 | info | http | OCSP stapling (informatif) | Optionnel ; certaines AC (dont Let's Encrypt) ont abandonné OCSP. |
| TLS-15 | high | http | Aucune ressource de la page servie en HTTP (voir aussi SEC-18) | Tout charger en HTTPS. |

## Performance (20)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| PERF-01 | high | tool | Score Performance Lighthouse (mobile) ≥ 90 | Traiter les opportunités Lighthouse listées. |
| PERF-02 | high | tool | LCP ≤ 2,5 s | Précharger l'image LCP (fetchpriority=high), SSR, CDN, image optimisée. |
| PERF-03 | high | tool | CLS ≤ 0,1 | width/height sur images/iframes, réserver l'espace des bannières, font-display. |
| PERF-04 | medium | tool | TBT ≤ 200 ms (proxy labo de l'INP) | Découper le JS, différer les scripts tiers, code splitting. |
| PERF-05 | medium | tool | FCP ≤ 1,8 s | Réduire le CSS/JS bloquant, CSS critique inline. |
| PERF-06 | medium | http | TTFB ≤ 800 ms | Cache serveur/page, requêtes BDD indexées, CDN, OPcache. |
| PERF-07 | high | http | Compression gzip/Brotli des ressources texte | Activer brotli/gzip (mod_deflate, gzip on, compression middleware). |
| PERF-08 | medium | http | Cache long sur les ressources statiques versionnées | Cache-Control: public, max-age=31536000, immutable sur les assets hashés. |
| PERF-09 | medium | browser | Poids total de la page ≤ 1,6 Mo | Compresser images, supprimer le JS inutile, lazy-load. |
| PERF-10 | low | browser | Nombre de requêtes ≤ 70 | Regrouper, supprimer les scripts tiers superflus. |
| PERF-11 | medium | http | Images en formats modernes (WebP/AVIF) | Convertir (sharp, squoosh, <picture>). |
| PERF-12 | medium | http | Dimensions (width/height) sur les images | Ajouter width et height pour éviter le CLS. |
| PERF-13 | low | http | Lazy-loading des images hors écran | loading="lazy" sauf pour l'image LCP. |
| PERF-14 | medium | http | Pas de script bloquant dans le <head> (defer/async/module) | Ajouter defer ou déplacer en fin de body. |
| PERF-15 | low | http | Polices : font-display et préchargement | font-display: swap ; <link rel=preload as=font crossorigin>. |
| PERF-16 | medium | http | HTTP/2 ou HTTP/3 activé | Activer HTTP/2 (Protocols h2 http/1.1 ; listen 443 ssl http2). |
| PERF-17 | medium | browser | JavaScript total ≤ 350 Ko transférés | Code splitting, tree-shaking, supprimer librairies lourdes. |
| PERF-18 | low | http | CSS/JS minifiés | Build de production (Vite/Webpack) ou minification serveur. |
| PERF-19 | low | tool | Score Best Practices Lighthouse ≥ 90 | Corriger les audits Best Practices listés. |
| PERF-20 | low | http | Images pas surdimensionnées (poids unitaire ≤ 300 Ko) | Redimensionner, srcset/sizes. |

## Accessibilité (7)

| ID | Gravité | Méthode | Contrôle | Correction |
|---|---|---|---|---|
| A11Y-01 | high | tool | Score Accessibilité Lighthouse ≥ 90 | Corriger les audits listés. |
| A11Y-02 | high | tool | Aucune violation axe-core critique/sérieuse | Corriger les violations listées (règle, élément). |
| A11Y-03 | high | http | Champs de formulaire avec label | <label for> ou aria-label sur chaque champ. |
| A11Y-04 | medium | http | Boutons et liens avec un nom accessible | Texte visible ou aria-label sur les boutons icônes. |
| A11Y-05 | medium | http | Zoom non bloqué (pas de user-scalable=no / maximum-scale=1) | Retirer ces paramètres du viewport. |
| A11Y-06 | low | http | Repères de structure (main, nav) et lien d'évitement | <main>, <nav>, lien « Aller au contenu ». |
| A11Y-07 | medium | doc | Déclaration d'accessibilité si le site y est soumis (RGAA / EAA) | Publier la déclaration + mention « Accessibilité : non/partiellement/totalement conforme ». |

