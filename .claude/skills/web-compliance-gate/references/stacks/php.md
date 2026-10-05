# Stack PHP — PHP natif, Laravel, Symfony, WordPress, Drupal, PrestaShop, Slim, CodeIgniter

## PHP natif (commun à tous)
**php.ini de production**
```ini
expose_php = Off
display_errors = Off
display_startup_errors = Off
log_errors = On
error_reporting = E_ALL
session.cookie_secure = 1
session.cookie_httponly = 1
session.cookie_samesite = "Lax"
session.use_strict_mode = 1
session.use_only_cookies = 1
opcache.enable = 1
allow_url_include = Off
```
**Base de données : PDO + requêtes préparées uniquement**
```php
$pdo = new PDO("mysql:host=$h;dbname=$db;charset=utf8mb4", $u, $p, [
  PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_EMULATE_PREPARES => false ]);
$st = $pdo->prepare('SELECT id, nom FROM clients WHERE id = :id AND user_id = :uid');
$st->execute(['id' => $_GET['id'] ?? 0, 'uid' => $_SESSION['uid']]);
```
**Échappement de sortie** : `htmlspecialchars($v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` pour toute donnée affichée (fonction `e()` utilitaire).
**Mots de passe** : `password_hash($pwd, PASSWORD_ARGON2ID)` (ou `PASSWORD_DEFAULT`) + `password_verify` + `password_needs_rehash`.
**Session** : `session_regenerate_id(true)` à la connexion ; jeton CSRF `bin2hex(random_bytes(32))` stocké en session, champ caché, comparaison `hash_equals`.
**Upload** : `finfo_file` pour le MIME réel, liste blanche, `move_uploaded_file` vers un dossier hors webroot, nom `bin2hex(random_bytes(16))`.
**Secrets** : `vlucas/phpdotenv` ou variables d'environnement du vhost ; `.env` hors du dossier public.
**Structure** : seul `public/` est le DocumentRoot (`index.php`, assets) ; le code, `vendor/`, `.env`, la config sont un niveau au-dessus.
**Audit** : `composer audit --locked --no-dev` ; Semgrep couvre PHP.
**Limitation de débit** : compteur en BDD/Redis par IP + identifiant sur le login, temporisation progressive.

## Laravel
- `.env` prod : `APP_ENV=production`, `APP_DEBUG=false`, `APP_URL=https://…`, `SESSION_SECURE_COOKIE=true`, `SESSION_SAME_SITE=lax`.
- En-têtes : middleware dédié (`php artisan make:middleware SecurityHeaders`) enregistré dans `bootstrap/app.php` (Laravel 11+) ou `Kernel.php` ; CSP avec nonce : `spatie/laravel-csp` (`@nonce` dans Blade, intégration Vite `Vite::useCspNonce()`).
- HTTPS : `URL::forceScheme('https')` en prod (AppServiceProvider) + `TrustProxies` configuré derrière un proxy ; redirection au niveau serveur.
- CSRF : `@csrf` dans chaque formulaire (middleware actif par défaut) ; exclusions minimales.
- Rate limit : `RateLimiter::for('login', …)` + `->middleware('throttle:login')` ; Fortify/Breeze l'incluent.
- Auth/Autorisation : Breeze/Fortify/Jetstream ; **Policies** et `$this->authorize()` / `Gate` sur chaque ressource (anti-IDOR) ; `Password::min(12)->mixedCase()->numbers()->symbols()->uncompromised()`.
- SQL : Eloquent/Query Builder ; `whereRaw`/`DB::select` avec bindings `?` uniquement.
- XSS : `{{ }}` échappe ; `{!! !!}` seulement sur du HTML assaini (`mews/purifier`).
- SEO : `artesaos/seotools` ou composant Blade `<x-seo>` ; `spatie/laravel-sitemap` ; `abort(404)`.
- Prod : `php artisan config:cache route:cache view:cache`, `composer install --no-dev --optimize-autoloader`, Telescope/Debugbar non installés en prod (`--dev`), `storage/` non accessible publiquement.
- RGPD : purge planifiée (`$schedule->command('model:prune')` avec `Prunable`), journal des consentements.

## Symfony
- `APP_ENV=prod`, `APP_DEBUG=0` ; `composer dump-env prod` ; profiler absent en prod (`symfony/web-profiler-bundle` en `require-dev`).
- `nelmio/security-bundle` : CSP (nonces Twig `csp_nonce()`), HSTS, clickjacking, content-type, referrer-policy, forced SSL.
- CSRF : Form component (actif par défaut), `csrf_token()` pour les formulaires manuels ; `login_throttling` dans `security.yaml` (requiert `symfony/rate-limiter`).
- Hachage : `password_hashers: auto` ; Voters pour l'autorisation ; `access_control` dans security.yaml.
- SEO : `presta/sitemap-bundle`, métas dans les templates Twig, `throw $this->createNotFoundException()`.

## WordPress
- Mises à jour du cœur, thèmes, extensions (auto-updates activées) ; supprimer extensions et thèmes inutilisés ; comptes admin avec MFA (Wordfence Login Security / Two Factor).
- `wp-config.php` : `define('WP_DEBUG', false); define('DISALLOW_FILE_EDIT', true); define('FORCE_SSL_ADMIN', true);` clés de salage uniques ; préfixe de table non standard ; `wp-config.php` protégé (hors webroot ou `<Files wp-config.php> Require all denied </Files>`).
- `.htaccess` : bloquer `xmlrpc.php` si inutilisé, désactiver l'exécution PHP dans `wp-content/uploads`, `Options -Indexes`, en-têtes de sécurité (voir serveurs-hebergement.md).
- Limiter les tentatives de connexion (Limit Login Attempts Reloaded, Wordfence) ; masquer l'énumération des auteurs (`/?author=1`) et l'API REST users si non nécessaire.
- RGPD : CMP (Complianz, CookieYes, tarteaucitron via extension) avec blocage automatique des scripts ; polices locales (OMGF ou thème) ; embeds YouTube en façade (WP YouTube Lyte) ; page de confidentialité native (Réglages → Confidentialité) à compléter ; outils d'export/effacement des données natifs.
- SEO : Yoast SEO ou Rank Math (sitemap, métas, schema, canonical) ; permaliens « Titre de la publication ».
- Perf : cache de page (WP Rocket, LiteSpeed Cache, W3TC), WebP natif, lazy-load natif, OPcache, CDN ; limiter les extensions lourdes (page builders).
- Audit : WPScan (API) pour les extensions vulnérables ; `wp core verify-checksums` (WP-CLI).

## Drupal / PrestaShop / Magento
- Drupal : module Security Kit (seckit) pour les en-têtes, `settings.php` protégé, `$settings['trusted_host_patterns']`, mises à jour de sécurité (drupal.org/security).
- PrestaShop/Magento : mode debug désactivé (`_PS_MODE_DEV_ false`), dossier admin renommé, modules à jour, CGV + médiateur + droit de rétractation (site marchand), CMP compatible (module officiel), hébergement conforme PCI si paiement non délégué (préférer un prestataire de paiement hébergé : Stripe Checkout, PayPlug, Stancer).

## Hébergement mutualisé / Plesk / cPanel
PHP-FPM version supportée (8.2+), extension Let's Encrypt avec renouvellement automatique, redirection HTTPS permanente cochée, HSTS dans les réglages Apache & nginx supplémentaires, DocumentRoot sur `public/` (Laravel/Symfony), tâches planifiées pour la purge des données et les sauvegardes.
