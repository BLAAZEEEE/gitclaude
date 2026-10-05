# Serveurs & hébergement — Apache/.htaccess, Nginx, Caddy, IIS, Vercel, Netlify, Cloudflare, Firebase, Docker, Plesk/cPanel

Toujours lu : c'est ici que se posent la plupart des en-têtes, la redirection HTTPS, la compression, le cache et les vraies 404. Valeurs des en-têtes : securite.md#entetes et #csp.

## Apache (vhost ou .htaccess)
```apache
# --- HTTPS + domaine canonique (voir ssl-tls.md#redirection pour la variante proxy)
RewriteEngine On
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^ https://www.domaine.fr%{REQUEST_URI} [L,R=301]

# --- Sécurité
Options -Indexes
ServerSignature Off
RedirectMatch 404 /\.(?!well-known)
<FilesMatch "\.(env|ini|log|sql|bak|old|orig|sh|lock|yml|yaml|md|dist)$|^composer\.(json|lock)$|^package(-lock)?\.json$">
  Require all denied
</FilesMatch>
<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  Header always set Cross-Origin-Opener-Policy "same-origin"
  Header always set Content-Security-Policy "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; upgrade-insecure-requests"
  Header always unset X-Powered-By
  Header unset X-Powered-By
</IfModule>

# --- Compression
<IfModule mod_brotli.c>
  AddOutputFilterByType BROTLI_COMPRESS text/html text/plain text/css text/xml application/javascript application/json application/xml image/svg+xml
</IfModule>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/plain text/css text/xml application/javascript application/json application/xml image/svg+xml
</IfModule>

# --- Cache (assets versionnés)
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html "access plus 0 seconds"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType application/javascript "access plus 1 year"
  ExpiresByType image/webp "access plus 1 year"
  ExpiresByType image/avif "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
</IfModule>

# --- Vraie 404
ErrorDocument 404 /404.html
```
Dans le **vhost** (pas en .htaccess) : `ServerTokens Prod`, `TraceEnable Off`, `Protocols h2 http/1.1`, config TLS (ssl-tls.md#protocoles). Modules : `a2enmod headers rewrite expires deflate brotli http2 ssl`. SPA : `FallbackResource /index.html` renvoie 200 partout → préférer le prérendu (frontend-static.md).
Uploads (PHP) : `.htaccess` dans le dossier d'upload → `php_admin_flag engine off` (vhost) ou `<FilesMatch "\.ph(p[0-9]?|tml|ar)$"> Require all denied </FilesMatch>`.
Multi-sites sur un VPS : un vhost par site, un certificat par domaine (`certbot --apache -d site.fr -d www.site.fr`), les enregistrements DNS A de chaque (sous-)domaine doivent pointer vers l'IP du VPS **avant** l'émission du certificat.

## Nginx
```nginx
server_tokens off;
server {
  listen 443 ssl; http2 on;
  server_name www.domaine.fr;
  root /var/www/site/public;
  # TLS : ssl-tls.md#protocoles
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  add_header Cross-Origin-Opener-Policy "same-origin" always;
  add_header Content-Security-Policy "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'" always;
  gzip on; gzip_types text/css application/javascript application/json image/svg+xml application/xml;
  location ~ /\.(?!well-known) { deny all; }
  location ~* \.(env|ini|log|sql|bak|lock|md)$ { deny all; }
  location ~* \.(css|js|woff2|webp|avif|svg|png|jpg)$ { expires 1y; add_header Cache-Control "public, immutable"; add_header X-Content-Type-Options "nosniff" always; }
  error_page 404 /404.html;
  autoindex off;
}
```
Attention : un `add_header` dans un bloc `location` **annule** ceux du bloc parent → répéter les en-têtes ou utiliser un `include` commun. Reverse proxy vers Node/Python : `proxy_set_header X-Forwarded-Proto $scheme;` + `Host`, `X-Forwarded-For`.

## Caddy
```caddyfile
www.domaine.fr {
  encode zstd gzip
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options nosniff
    X-Frame-Options SAMEORIGIN
    Referrer-Policy strict-origin-when-cross-origin
    Permissions-Policy "camera=(), microphone=(), geolocation=()"
    -Server
  }
  @static path *.css *.js *.woff2 *.webp *.avif *.svg
  header @static Cache-Control "public, max-age=31536000, immutable"
  root * /var/www/site
  file_server
  handle_errors { rewrite * /404.html; file_server }
}
domaine.fr { redir https://www.domaine.fr{uri} permanent }
```
HTTPS, certificats et renouvellement automatiques.

## IIS (web.config)
`<httpProtocol><customHeaders>` pour les en-têtes (et `<remove name="X-Powered-By" />`), `<security><requestFiltering removeServerHeader="true">`, règle URL Rewrite HTTP→HTTPS (301), `<httpErrors>` avec 404 personnalisée, `<urlCompression doStaticCompression="true" doDynamicCompression="true" />`, `<staticContent><clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="365.00:00:00" />`.

## Vercel (`vercel.json`)
```json
{ "headers": [ { "source": "/(.*)", "headers": [
    { "key": "Content-Security-Policy", "value": "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'" },
    { "key": "X-Content-Type-Options", "value": "nosniff" },
    { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
    { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
    { "key": "X-Frame-Options", "value": "SAMEORIGIN" },
    { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains" } ] } ],
  "redirects": [ { "source": "/:path*", "has": [{ "type": "host", "value": "domaine.fr" }], "destination": "https://www.domaine.fr/:path*", "permanent": true } ] }
```
HTTPS, HTTP/2-3, compression et cache des assets `/_next/static` automatiques. Régions de fonctions : choisir l'UE (`cdg1`, `fra1`) pour les données personnelles.

## Netlify / Cloudflare Pages (`_headers`, `_redirects`)
```
# _headers
/*
  Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains
/assets/*
  Cache-Control: public, max-age=31536000, immutable
```
```
# _redirects
https://domaine.fr/*  https://www.domaine.fr/:splat  301!
```
`404.html` à la racine du build → servie en 404. Cloudflare (proxy) : mode SSL **Full (strict)** (jamais « Flexible »), « Always Use HTTPS », HSTS dans SSL/TLS → Edge Certificates, TLS minimum 1.2.

## Firebase Hosting (`firebase.json`)
`"headers"` par `source`, `"redirects"` avec `"type": 301`, `"cleanUrls": true`, page `404.html`.

## Docker
Image minimale (alpine/distroless), utilisateur non-root (`USER node`), `NODE_ENV=production`, secrets en variables d'environnement ou secrets Docker (jamais dans l'image ni le Dockerfile), `.dockerignore` (`.env`, `.git`, `node_modules`), reverse proxy (Traefik/Caddy/Nginx) pour TLS, base de données non exposée sur l'hôte public, scan d'image `trivy image`.

## Plesk / cPanel (mutualisé, VPS managé)
- SSL/TLS : Let's Encrypt (Plesk : « SSL It! ») pour domaine + www (+ webmail), **renouvellement automatique**, « Redirection permanente 301 de HTTP vers HTTPS » cochée, HSTS activé dans SSL It!.
- Paramètres Apache & nginx : directives supplémentaires (en-têtes, cache) ; attention au double-proxy nginx→Apache pour la détection HTTPS (`X-Forwarded-Proto`).
- Racine du document sur `public/` (Laravel/Symfony) ou `dist/` ; version PHP supportée ; `display_errors` off dans les paramètres PHP.
- Sauvegardes planifiées vers un stockage distant ; accès FTP remplacé par SFTP ; comptes avec MFA.
