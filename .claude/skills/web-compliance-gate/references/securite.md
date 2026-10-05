# Sécurité — exigences et corrections (OWASP Top 10:2025, CNIL, ANSSI)

Sommaire : [en-têtes](#entetes) · [CSP](#csp) · [cookies](#cookies) · [CORS](#cors) · [exposition](#exposition) · [erreurs & debug](#erreurs) · [CSRF](#csrf) · [authentification](#auth) · [contrôle d'accès](#acces) · [injection](#injection) · [XSS](#xss) · [upload](#upload) · [secrets](#secrets) · [dépendances](#supply-chain) · [journalisation](#logs) · [outils](#outils) · [organisationnel](#organisationnel)

Correspondance OWASP Top 10:2025 : A01 Broken Access Control → [acces](#acces), [cors](#cors) · A02 Security Misconfiguration → [entetes](#entetes), [exposition](#exposition), [erreurs](#erreurs) · A03 Software Supply Chain Failures → [supply-chain](#supply-chain) · A04 Cryptographic Failures → [auth](#auth), ssl-tls.md · A05 Injection → [injection](#injection), [xss](#xss) · A06 Insecure Design → [upload](#upload), [csrf](#csrf) · A07 Authentication Failures → [auth](#auth) · A08 Software or Data Integrity Failures → [supply-chain](#supply-chain) (SRI) · A09 Security Logging & Alerting Failures → [logs](#logs) · A10 Mishandling of Exceptional Conditions → [erreurs](#erreurs).

Règle de conduite : les tests de l'audit sont **défensifs** (configuration, en-têtes, code, dépendances). Ils se lancent sur un site dont le client est propriétaire ou pour lequel il a donné son accord écrit.

<a id="entetes"></a>
## 1. En-têtes HTTP (SEC-03 à SEC-08, SEC-16, SEC-18, SEC-20, SEC-24)

Jeu de référence pour toute réponse HTML :
```
Content-Security-Policy: (voir §2)
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
Cross-Origin-Opener-Policy: same-origin
```
- Supprimer les bannières de version : Apache `ServerTokens Prod` + `ServerSignature Off` ; PHP `expose_php = Off` ; Nginx `server_tokens off` ; Express `app.disable('x-powered-by')` (Helmet le fait) ; ASP.NET `removeServerHeader` + retirer `X-Powered-By` dans web.config.
- `TraceEnable Off` (Apache).
- `/.well-known/security.txt` : `Contact: mailto:…` + `Expires: <date ISO>` (RFC 9116).
- Pages authentifiées ou avec données personnelles : `Cache-Control: no-store`.
- Contenu mixte : aucune ressource en `http://` sur une page HTTPS (`upgrade-insecure-requests` dans la CSP en filet de sécurité).
- Où les poser : voir la fiche de la stack (references/stacks/) — middleware applicatif ou config serveur, **une seule source** pour éviter les doublons contradictoires.

<a id="csp"></a>
## 2. Content-Security-Policy (SEC-01/02)

Politique de départ stricte, à assouplir au strict nécessaire :
```
default-src 'self';
script-src 'self' 'nonce-{NONCE}' 'strict-dynamic';
style-src 'self';
img-src 'self' data:;
font-src 'self';
connect-src 'self';
frame-src 'none';
object-src 'none';
base-uri 'self';
form-action 'self';
frame-ancestors 'self';
upgrade-insecure-requests
```
- **Pas de `'unsafe-inline'` ni `'unsafe-eval'` dans `script-src`.** Les scripts inline passent par un nonce aléatoire par requête (SSR) ou un hash `'sha256-…'` (sites statiques), ou deviennent des fichiers.
- Styles inline : si une librairie l'impose, `style-src 'self' 'unsafe-inline'` est un compromis acceptable (bien moins risqué que pour les scripts).
- Services tiers : ajouter uniquement leurs domaines exacts (ex. `https://www.googletagmanager.com` dans script-src et `https://*.google-analytics.com` dans connect-src).
- Déployer d'abord en `Content-Security-Policy-Report-Only` avec `report-to`, corriger les violations, puis passer en mode bloquant.
- `frame-ancestors` n'est pas pris en compte dans une CSP en `<meta>` : il faut l'en-tête HTTP.

<a id="cookies"></a>
## 3. Cookies (SEC-09/10/11)
Tout cookie : `Secure; SameSite=Lax` (ou `Strict` pour l'admin). Cookies de session/authentification : `HttpOnly` en plus, préfixe `__Host-` quand c'est possible (`__Host-sid=…; Path=/; Secure; HttpOnly; SameSite=Lax`). Régénérer l'identifiant de session à la connexion. Expiration de session raisonnable (ex. 30 min d'inactivité pour un back-office).

<a id="cors"></a>
## 4. CORS (SEC-12, SEC-C09)
Liste blanche explicite d'origines ; jamais `Access-Control-Allow-Origin: *` sur une API qui utilise des cookies ou renvoie des données privées ; ne jamais renvoyer l'`Origin` reçu sans le comparer à la liste. `Access-Control-Allow-Credentials: true` seulement avec une origine précise.

<a id="exposition"></a>
## 5. Fichiers et interfaces exposés (SEC-13/14/22)
- Le **webroot** ne contient que ce qui doit être public (`public/`, `dist/`, `web/`). `.env`, `.git/`, `composer.json`, dumps SQL, sauvegardes, logs : hors webroot, ou bloqués.
- Apache : `Options -Indexes` ; bloquer les fichiers cachés (`RedirectMatch 404 /\..*$`) ; Nginx : `location ~ /\. { deny all; }`, `autoindex off`.
- phpMyAdmin, Adminer, `/server-status`, Symfony Profiler, Laravel Telescope/Debugbar, Swagger, GraphiQL, Spring Actuator : absents en production, ou restreints par IP/VPN + authentification.
- Supprimer `phpinfo.php`, `info.php`, fichiers de test et de sauvegarde (`.bak`, `~`, `.old`, `.zip`).

<a id="erreurs"></a>
## 6. Erreurs & mode debug (SEC-15, SEC-C03) — OWASP A10
- Production : `APP_DEBUG=false` (Laravel), `APP_ENV=prod` (Symfony), `DEBUG=False` + `ALLOWED_HOSTS` (Django), `NODE_ENV=production` (Node), `display_errors=Off` + `log_errors=On` (PHP), `ASPNETCORE_ENVIRONMENT=Production`, `WP_DEBUG=false`.
- Pages d'erreur génériques (404/500) sans pile d'appels, requête SQL, chemin de fichier ni version. Détail complet dans les logs uniquement.
- Gérer chaque exception : `try/catch` autour des appels externes, gestionnaire d'erreurs global, pas d'état incohérent (transactions), échec **fermé** (en cas d'erreur d'autorisation → refuser).

<a id="csrf"></a>
## 7. CSRF (SEC-19)
Jeton CSRF sur tout formulaire/requête qui modifie un état (POST/PUT/PATCH/DELETE) : `@csrf` (Laravel), `{{ csrf_token('form') }}`/Form component (Symfony), `{% csrf_token %}` (Django), `protect_from_forgery` (Rails), `[ValidateAntiForgeryToken]` (ASP.NET), `csrf-csrf`/`csrf-sync` (Express, `csurf` est déprécié), Server Actions Next.js (vérification d'Origin intégrée). API en JSON + cookies : cookies `SameSite=Lax/Strict` + vérification de l'en-tête `Origin` + jeton double-submit.

<a id="auth"></a>
## 8. Authentification & mots de passe (SEC-21, SEC-C07, SEC-C12, SEC-C13) — OWASP A07, CNIL délibération 2022-100
- **Hachage** : Argon2id (recommandé), bcrypt (coût ≥ 12) ou scrypt/PBKDF2 avec sel. Jamais MD5, SHA-1, SHA-256 simple, ni chiffrement réversible. PHP `password_hash($p, PASSWORD_ARGON2ID)`, Node `argon2`/`bcrypt`, Python `argon2-cffi`/`passlib`, Django `Argon2PasswordHasher`, .NET `PasswordHasher`, Spring `Argon2PasswordEncoder`.
- **Politique CNIL (80 bits d'entropie)** si le mot de passe est le seul facteur : ≥ 12 caractères avec majuscules, minuscules, chiffres et caractères spéciaux, **ou** ≥ 14 caractères avec majuscules, minuscules et chiffres, **ou** phrase de passe d'au moins 7 mots. Avec restrictions d'accès (blocage/temporisation), des seuils plus bas sont admis par la CNIL, mais viser 12+.
- Pas de renouvellement périodique imposé aux utilisateurs standards ; renouvellement + **MFA** pour les comptes administrateurs.
- **Limitation des tentatives** : temporisation exponentielle ou blocage temporaire après N échecs, par compte ET par IP ; captcha possible après échecs.
- Vérifier le mot de passe contre les listes de mots de passe compromis (API Have I Been Pwned en k-anonymity).
- Messages d'erreur identiques pour « email inconnu » et « mot de passe faux » ; réinitialisation par lien à usage unique, expirant (≤ 1 h).
- Champs : `autocomplete="current-password"` / `"new-password"`, `type="password"`, formulaire en HTTPS.

<a id="acces"></a>
## 9. Contrôle d'accès (SEC-C17) — OWASP A01 (revue manuelle obligatoire)
Pour **chaque** route/endpoint qui touche des données non publiques, Claude vérifie en lisant le code :
1. authentification exigée côté serveur (le masquage côté front ne protège rien) ;
2. autorisation : la ressource demandée appartient à l'utilisateur ou son rôle l'autorise (anti-IDOR : `WHERE id = ? AND user_id = ?`, policies Laravel, voters Symfony, permissions DRF, `authorize` Pundit/CanCan) ;
3. refus par défaut (deny by default), y compris pour les nouvelles routes ;
4. identifiants non devinables pour les ressources partagées par lien (UUID v4) ;
5. actions d'admin journalisées.
Consigner le résultat de la revue dans `wcg-answers.json` (`"SEC-C17": {"reponse": "oui", "commentaire": "routes vérifiées : …"}`).

<a id="injection"></a>
## 10. Injection (SEC-C04, SEC-C06) — OWASP A05
- SQL : **requêtes préparées/paramétrées** partout (PDO `prepare` + `execute`, `mysqli` + `bind_param`, Eloquent/Doctrine/Prisma/Sequelize/SQLAlchemy/Django ORM, `pg` avec `$1`). Les noms de tables/colonnes dynamiques passent par une liste blanche.
- Pas de `eval`, `new Function`, `exec`/`system`/`shell_exec`, `subprocess(..., shell=True)` avec une donnée externe ; utiliser des API sans shell avec liste d'arguments.
- Désérialisation : pas de `unserialize`/`pickle.loads`/`yaml.load` non sûr sur une entrée utilisateur (JSON + validation de schéma).
- Valider toutes les entrées côté serveur (Zod, Joi, class-validator, FormRequest Laravel, Symfony Validator, Pydantic, DRF serializers).

<a id="xss"></a>
## 11. XSS (SEC-C05)
- S'appuyer sur l'échappement automatique des templates (JSX, Blade `{{ }}`, Twig, Jinja, Razor) ; chaque contournement (`dangerouslySetInnerHTML`, `v-html`, `{!! !!}`, `|safe`, `|raw`, `innerHTML`, `Html.Raw`) exige une donnée assainie avec **DOMPurify** (client) ou `sanitize-html`/HTML Purifier/`bleach`/`nh3` (serveur).
- `textContent` au lieu de `innerHTML` pour du texte.
- CSP stricte en seconde ligne de défense.

<a id="upload"></a>
## 12. Upload de fichiers (SEC-C14)
Liste blanche d'extensions **et** de types MIME réels (lecture des magic bytes), taille maximale, renommage aléatoire, stockage **hors webroot** ou sur un stockage objet sans exécution, service avec `Content-Disposition: attachment` pour les types non image, pas d'exécution PHP dans le dossier d'upload (`php_admin_flag engine off`), images ré-encodées (sharp/Intervention/Pillow) pour retirer les métadonnées EXIF.

<a id="secrets"></a>
## 13. Secrets (SEC-C01, SEC-C02, SEC-C16)
- Secrets uniquement dans des variables d'environnement ou un gestionnaire de secrets (Vault, Doppler, secrets de l'hébergeur, GitHub Actions secrets).
- `.gitignore` : `.env`, `.env.*` sauf `.env.example` (valeurs factices).
- Secret déjà commité : **le révoquer et le régénérer d'abord** (il est compromis), puis purger l'historique (`git filter-repo --path .env --invert-paths`), puis forcer la mise à jour du dépôt distant.
- Hook pre-commit : gitleaks (`gitleaks protect --staged`).

<a id="supply-chain"></a>
## 14. Dépendances & intégrité (SEC-17, SEC-23, SEC-C10, SEC-C11) — OWASP A03/A08
- Lockfile versionné ; installation reproductible (`npm ci`, `composer install --no-dev`, `pip install -r requirements.txt --require-hashes`).
- Audit : `npm audit --omit=dev` · `pnpm audit --prod` · `yarn npm audit` · `composer audit` · `pip-audit` · `bundle-audit` · `govulncheck ./...` · `cargo audit` · `dotnet list package --vulnerable --include-transitive` · OWASP dependency-check (JVM). Corriger toute vulnérabilité **critique/haute** avant livraison.
- Mises à jour automatisées : Dependabot ou Renovate.
- Scripts tiers : auto-héberger via le bundler ; sinon `integrity="sha384-…" crossorigin="anonymous"` (générer : `openssl dgst -sha384 -binary f.js | openssl base64 -A`). Les scripts qui changent en permanence (GTM, widgets) ne peuvent pas avoir de SRI : les limiter et les encadrer par la CSP.
- Pas de dépendances abandonnées ou inconnues pour des fonctions triviales.

<a id="logs"></a>
## 15. Journalisation & alertes (SEC-C18) — OWASP A09
Journaliser : connexions réussies/échouées, réinitialisations de mot de passe, changements de droits, actions admin, erreurs 5xx. Jamais de mot de passe, de jeton ni de donnée sensible dans les logs. Horodatage + IP + identifiant utilisateur. Conservation 6 mois à 1 an (CNIL). Alertes sur pics d'échecs de connexion ou de 5xx (Sentry, Uptime Kuma, fail2ban, alertes de l'hébergeur).

<a id="outils"></a>
## 16. Outils de l'audit (SEC-C15, SEC-C16)
| Outil | Rôle | Installation |
|---|---|---|
| Semgrep | SAST multi-langage (règles OWASP Top 10 + secrets) | `pipx install semgrep` (ou `pip install semgrep`) |
| Gitleaks | secrets dans tout l'historique git | `brew install gitleaks`, `winget install gitleaks`, binaire GitHub, ou Docker |
| pip-audit | CVE des dépendances Python | `pipx install pip-audit` |
| OWASP ZAP (baseline, passif) | scan passif complémentaire des en-têtes/cookies | `docker run --rm -t zaproxy/zap-stable zap-baseline.py -t https://site.fr` |
| SSL Labs / testssl.sh | contre-vérification TLS | ssllabs.com/ssltest ou `testssl.sh domaine.fr` |

<a id="organisationnel"></a>
## 17. Contrôles organisationnels (SEC-D01 à D04) — questions au client
- Sauvegardes : automatiques, chiffrées, hors du serveur (règle 3-2-1), **restauration testée** et datée.
- MFA partout : hébergeur, registrar/DNS, CMS admin, dépôt git, email pro.
- Mises à jour : OS (unattended-upgrades), serveur web, PHP/Node, CMS + extensions, dépendances — calendrier défini.
- Moindre privilège : utilisateur BDD applicatif sans droits DDL/admin, SSH par clé uniquement (`PasswordAuthentication no`, `PermitRootLogin no`), pare-feu (ufw : 22/80/443 seulement), fail2ban.
