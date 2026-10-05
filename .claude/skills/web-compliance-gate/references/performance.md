# Performance — exigences et corrections

Sommaire : [Lighthouse](#lighthouse) · [Core Web Vitals](#cwv) · [serveur](#serveur) · [cache](#cache) · [poids & requêtes](#poids) · [images](#images) · [JavaScript & CSS](#js) · [polices](#polices)

Mesurer sur le **build de production** (jamais le serveur de dev : pas de minification, pas de cache, HMR). Lighthouse est lancé en profil mobile avec throttling (4G lente, CPU ×4) : c'est volontairement exigeant.

<a id="lighthouse"></a>
## 1. Objectifs (PERF-01, PERF-19)
Performance ≥ 90 · Best Practices ≥ 90 · Accessibilité ≥ 90 · SEO ≥ 90, sur mobile, pour l'accueil et les pages clés. Les « opportunités » listées dans le rapport indiquent le gain estimé : traiter d'abord les plus grosses.

<a id="cwv"></a>
## 2. Core Web Vitals (PERF-02 à PERF-05)
| Métrique | Bon | Mauvais | Leviers |
|---|---|---|---|
| LCP (plus grand élément affiché) | ≤ 2,5 s | > 4 s | image LCP en `fetchpriority="high"` et **sans** lazy-load, préchargée, WebP/AVIF dimensionnée ; SSR/SSG ; TTFB bas ; CSS critique |
| INP (réactivité, terrain) / TBT en labo | INP ≤ 200 ms / TBT ≤ 200 ms | INP > 500 ms | moins de JS, découpage (code splitting), scripts tiers différés, tâches longues fractionnées, pas d'hydratation inutile (îlots Astro, composants serveur) |
| CLS (stabilité) | ≤ 0,1 | > 0,25 | `width`/`height` ou `aspect-ratio` sur images, vidéos, iframes ; espace réservé pour bannières/pubs/cookies ; `font-display: swap` + `size-adjust` |
| FCP | ≤ 1,8 s | > 3 s | pas de CSS/JS bloquant, HTML léger, compression |

<a id="serveur"></a>
## 3. Serveur (PERF-06, PERF-07, PERF-16)
- **TTFB ≤ 800 ms** : cache de page (Varnish, cache applicatif, ISR/SSG), requêtes BDD indexées (pas de N+1), OPcache pour PHP, pool de connexions, CDN.
- **Compression** Brotli (prioritaire) + gzip pour HTML, CSS, JS, JSON, SVG, XML, polices non-woff2 :
  - Apache : `mod_brotli` + `mod_deflate` → `AddOutputFilterByType BROTLI_COMPRESS text/html text/css application/javascript application/json image/svg+xml` (et DEFLATE en repli)
  - Nginx : `gzip on; gzip_types text/css application/javascript application/json image/svg+xml;` + module brotli si disponible
  - Express : `compression()` ; Fastify : `@fastify/compress` ; ASP.NET : `AddResponseCompression` ; Django : `GZipMiddleware` (ou au niveau du serveur) ; Caddy : `encode zstd gzip`
  - Vercel/Netlify/Cloudflare : automatique
- **HTTP/2** (ou HTTP/3) activé : Apache `Protocols h2 http/1.1` (mod_http2, MPM event) ; Nginx `http2 on;`.

<a id="cache"></a>
## 4. Cache navigateur (PERF-08)
- Assets versionnés (nom avec empreinte, ex. `app.3f9a2c.js`, sortie par défaut de Vite/Webpack/Next/Nuxt/Laravel Vite) : `Cache-Control: public, max-age=31536000, immutable`.
- HTML : `Cache-Control: no-cache` (revalidation) ou courte durée.
- Assets non versionnés : ajouter une empreinte au build, sinon `max-age=86400` + ETag.
- Apache : `mod_expires` + `<FilesMatch "\.(js|css|woff2|webp|avif|svg)$"> Header set Cache-Control "public, max-age=31536000, immutable" </FilesMatch>` ; Nginx : `location ~* \.(js|css|woff2|webp|avif|svg)$ { expires 1y; add_header Cache-Control "public, immutable"; }`.

<a id="poids"></a>
## 5. Budgets (PERF-09, PERF-10, PERF-17)
| Budget (page d'accueil, mobile) | Cible |
|---|---|
| Poids transféré total | ≤ 1,6 Mo (idéal < 1 Mo) |
| JavaScript transféré | ≤ 350 Ko (idéal < 170 Ko) |
| Requêtes | ≤ 70 |
| Images au-dessus de la ligne de flottaison | ≤ 500 Ko cumulés |

<a id="images"></a>
## 6. Images (PERF-11, PERF-12, PERF-13, PERF-20)
- Formats : **AVIF/WebP** (repli JPEG via `<picture>`), SVG pour les icônes et logos.
- Dimensionnement : `srcset` + `sizes`, jamais une image 4000 px affichée en 400 px ; ≤ 300 Ko par image (≤ 150 Ko idéalement).
- Toujours `width` + `height` (ou `aspect-ratio` CSS).
- `loading="lazy"` + `decoding="async"` sous la ligne de flottaison ; **jamais** sur l'image LCP (`fetchpriority="high"` à la place).
- Outils : sharp (Node), `@astrojs/image`/`<Image>` Astro, `next/image`, `@nuxt/image`, Intervention Image (PHP), Pillow (Python), squoosh-cli, `cwebp`/`avifenc` ; WordPress : conversion WebP native (6.1+) ou plugin (Imagify, EWWW).
```html
<picture>
  <source srcset="/img/hero-800.avif 800w, /img/hero-1600.avif 1600w" type="image/avif">
  <source srcset="/img/hero-800.webp 800w, /img/hero-1600.webp 1600w" type="image/webp">
  <img src="/img/hero-1600.jpg" sizes="100vw" width="1600" height="900" alt="…" fetchpriority="high">
</picture>
```

<a id="js"></a>
## 7. JavaScript & CSS (PERF-14, PERF-18)
- Scripts externes : `defer` (ou `type="module"`) ; `async` pour les scripts indépendants. Rien de bloquant dans le `<head>`.
- Build de production minifié et tree-shaké (Vite/esbuild, Webpack mode production, `next build`, `nuxi build`) ; code splitting par route ; import dynamique des composants lourds (carte, éditeur, graphiques).
- Supprimer jQuery et les librairies monolithiques quand du JS natif suffit ; remplacer moment.js par date-fns/Intl, lodash complet par des imports ciblés.
- Scripts tiers (chat, analytics, vidéos) : chargés après l'interaction ou `requestIdleCallback`, façades.
- CSS : un seul fichier critique inline si nécessaire, le reste différé ; PurgeCSS/Tailwind JIT pour retirer le CSS inutilisé.

<a id="polices"></a>
## 8. Polices (PERF-15)
- Auto-hébergées (voir rgpd.md#tiers), format **woff2** uniquement, sous-ensemble latin.
- `font-display: swap` dans chaque `@font-face` ; précharger la police principale : `<link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>`.
- Limiter à 2 familles et 3-4 graisses (ou une police variable).
