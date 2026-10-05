# SSL / TLS & HTTPS — exigences et corrections

Sommaire : [certificat](#certificat) · [renouvellement](#renouvellement) · [protocoles & suites](#protocoles) · [redirection HTTPS](#redirection) · [HSTS](#hsts) · [DNS / CAA](#dns) · [vérification](#verification)

Référence de configuration : Mozilla SSL Configuration Generator, profil **Intermediate** (ssl-config.mozilla.org) · guide TLS de l'ANSSI.

<a id="certificat"></a>
## 1. Certificat (TLS-01/02/06/07/09)
- Autorité reconnue : Let's Encrypt (gratuit, ACME), ZeroSSL, ou le certificat de l'hébergeur (Plesk, cPanel, Vercel, Netlify et Cloudflare le gèrent automatiquement).
- Couvre **le domaine nu ET www** (et chaque sous-domaine servi) : `certbot --apache -d domaine.fr -d www.domaine.fr`.
- Clé ECDSA P-256 (recommandé) ou RSA 2048+ ; signature SHA-256.
- **Chaîne complète** : servir `fullchain.pem` (Apache ≥ 2.4.8 : `SSLCertificateFile …/fullchain.pem` ; Nginx : `ssl_certificate …/fullchain.pem`). Servir `cert.pem` seul casse la vérification sur certains clients (Android, curl, API).

<a id="renouvellement"></a>
## 2. Renouvellement automatique (TLS-03)
La durée maximale des certificats publics baisse (CA/Browser Forum, ballot SC-081v3) : **200 jours depuis le 15 mars 2026, 100 jours à partir du 15 mars 2027, 47 jours à partir du 15 mars 2029**. Le renouvellement manuel n'est plus viable.
- Certbot : le timer systemd `certbot.timer` (ou cron) est installé d'office ; tester avec `certbot renew --dry-run`, et `--deploy-hook "systemctl reload apache2"` (ou nginx).
- Caddy : HTTPS automatique intégré.
- Plesk : extension Let's Encrypt / SSL It! avec renouvellement automatique coché, y compris pour www et le webmail.
- Surveiller l'expiration (Uptime Kuma, alerte à J-14).

<a id="protocoles"></a>
## 3. Protocoles et suites (TLS-04/05/08/14)
Uniquement **TLS 1.2 et TLS 1.3**. Suites (Mozilla Intermediate) :
```
ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305
```
**Apache** (vhost 443 ou `ssl.conf`) :
```apache
SSLProtocol             -all +TLSv1.2 +TLSv1.3
SSLCipherSuite          <suites ci-dessus>
SSLHonorCipherOrder     off
SSLSessionTickets       off
Protocols h2 http/1.1
```
**Nginx** :
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers <suites ci-dessus>;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d; ssl_session_cache shared:MozSSL:10m; ssl_session_tickets off;
listen 443 ssl; http2 on;   # (nginx ≥ 1.25.1 ; sinon « listen 443 ssl http2; »)
```
**Caddy** : bons réglages par défaut. **IIS** : désactiver TLS 1.0/1.1 dans le registre (IIS Crypto).
OCSP stapling : optionnel ; Let's Encrypt a abandonné OCSP, son absence n'est pas pénalisée.

<a id="redirection"></a>
## 4. Redirection HTTP → HTTPS (TLS-10/13/15)
Redirection **301 ou 308**, qui conserve le chemin et la query, vers la forme canonique (avec ou sans www, au choix, mais une seule).

**Apache (.htaccess ou vhost :80)** — forme canonique `https://www.` :
```apache
RewriteEngine On
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^ https://www.domaine.fr%{REQUEST_URI} [L,R=301]
```
Derrière un proxy/CDN (Cloudflare, Plesk nginx devant Apache) : tester `%{HTTP:X-Forwarded-Proto} !https` plutôt que `%{HTTPS}` pour éviter les boucles.
**Nginx** :
```nginx
server { listen 80; server_name domaine.fr www.domaine.fr; return 301 https://www.domaine.fr$request_uri; }
server { listen 443 ssl; server_name domaine.fr; return 301 https://www.domaine.fr$request_uri; }
```
**Applicatif** (si pas de config serveur) : Django `SECURE_SSL_REDIRECT = True` (+ `SECURE_PROXY_SSL_HEADER`), Laravel `URL::forceScheme('https')` + redirection serveur, ASP.NET `app.UseHttpsRedirection()`, Rails `config.force_ssl = true`, Spring `requiresChannel().anyRequest().requiresSecure()`, Express : middleware sur `x-forwarded-proto` avec `app.set('trust proxy', 1)`.
**Plateformes** (Vercel, Netlify, Cloudflare Pages, GitHub Pages « Enforce HTTPS ») : activé par défaut, vérifier que le domaine personnalisé est bien concerné.

<a id="hsts"></a>
## 5. HSTS (TLS-11)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```
Déploiement progressif si des sous-domaines ne sont pas encore en HTTPS : `max-age=300` → `86400` → `31536000`. N'ajouter `preload` (et soumettre sur hstspreload.org) que lorsque **tous** les sous-domaines sont en HTTPS de façon permanente : c'est difficilement réversible.
- Apache : `Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"` (vhost 443, mod_headers)
- Nginx : `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;`
- Django `SECURE_HSTS_SECONDS=31536000` + `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` ; Helmet (Express) le fait par défaut ; ASP.NET `app.UseHsts()` ; Rails `force_ssl`.

<a id="dns"></a>
## 6. DNS (TLS-12)
Enregistrement **CAA** qui limite les autorités habilitées à émettre des certificats :
```
domaine.fr.  CAA 0 issue "letsencrypt.org"
domaine.fr.  CAA 0 iodef "mailto:admin@domaine.fr"
```
Chez IONOS/OVH : zone DNS → ajouter un enregistrement de type CAA. Avec plusieurs AC (Let's Encrypt + Cloudflare), une ligne `issue` par AC. Vérifier aussi que les enregistrements A/AAAA de **www** et du domaine nu pointent vers le bon serveur, sinon le certificat ne peut pas être émis pour les deux.

<a id="verification"></a>
## 7. Vérification croisée recommandée
Après la mise en ligne : SSL Labs (viser A ou A+), `testssl.sh domaine.fr`, et l'audit avec `--prod-url https://domaine.fr` (le mode local ne peut pas tester le certificat réel).
