# Stack Node.js — Express, Fastify, NestJS, Koa, Hono, Next.js, Nuxt, SvelteKit, Remix/React Router

Lire la section du framework détecté + la partie commune. Principe : **une seule** couche pose les en-têtes (l'app OU le serveur/proxy OU la plateforme), pour éviter doublons et contradictions.

## Commun
| Besoin | Solution |
|---|---|
| En-têtes de sécurité + CSP | `helmet` (Express/Koa via `koa-helmet`), `@fastify/helmet`, Nest : `app.use(helmet())` |
| Compression | `compression` · `@fastify/compress` (ou laisser Nginx/la plateforme) |
| Rate limiting | `express-rate-limit` · `@fastify/rate-limit` · `@nestjs/throttler` · `rate-limiter-flexible` (Redis) |
| CSRF | `csrf-csrf` (double-submit) ou `csrf-sync` ; `csurf` est déprécié |
| Hachage | `argon2` (argon2id) ou `bcrypt` (≥ v6, coût 12) |
| Validation | `zod`, `joi`, `class-validator` (Nest) |
| SQL | Prisma, Drizzle, Knex, Sequelize, `pg` avec `$1`, `mysql2` avec `?` (`execute`) — jamais de template string dans la requête |
| Sessions | `express-session` + store Redis, cookie `{secure:true, httpOnly:true, sameSite:'lax'}`, `app.set('trust proxy', 1)` derrière un proxy |
| Logs | `pino` / `winston` (sans mots de passe ni jetons) |
| Audit | `npm audit --omit=dev` · `pnpm audit --prod` · `yarn npm audit` |
| Prod | `NODE_ENV=production`, `app.disable('x-powered-by')`, gestionnaire d'erreurs final qui ne renvoie pas la stack |

### Express — socle sécurisé
```js
import express from 'express'; import helmet from 'helmet'; import compression from 'compression';
import rateLimit from 'express-rate-limit'; import crypto from 'node:crypto';
const app = express();
app.set('trust proxy', 1);
app.disable('x-powered-by');
app.use((req, res, next) => { res.locals.nonce = crypto.randomBytes(16).toString('base64'); next(); });
app.use(helmet({
  contentSecurityPolicy: { directives: {
    defaultSrc: ["'self'"], scriptSrc: ["'self'", (req, res) => `'nonce-${res.locals.nonce}'`],
    styleSrc: ["'self'"], imgSrc: ["'self'", 'data:'], fontSrc: ["'self'"], objectSrc: ["'none'"],
    baseUri: ["'self'"], formAction: ["'self'"], frameAncestors: ["'self'"], upgradeInsecureRequests: [] } },
  strictTransportSecurity: { maxAge: 31536000, includeSubDomains: true },
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
}));
app.use((req, res, next) => { res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'); next(); });
app.use(compression());
app.use(express.static('public', { maxAge: '1y', immutable: true, index: false }));   // assets versionnés
app.use('/auth/login', rateLimit({ windowMs: 15 * 60_000, limit: 5, standardHeaders: 'draft-7', legacyHeaders: false }));
// … routes …
app.use((req, res) => res.status(404).render('404'));                                  // vrai 404
app.use((err, req, res, next) => { req.log?.error(err); res.status(500).render('500'); });  // sans stack
```
Redirection HTTPS si pas de proxy : `app.use((req,res,next) => req.secure ? next() : res.redirect(301, 'https://' + req.headers.host + req.originalUrl))`.

### Fastify
`@fastify/helmet` (mêmes options), `@fastify/compress`, `@fastify/rate-limit`, `@fastify/csrf-protection`, `@fastify/cookie` avec `secure/httpOnly/sameSite`, `setNotFoundHandler` (404 réel), `setErrorHandler` (message générique).

### NestJS
`app.use(helmet())`, `ThrottlerModule.forRoot([{ ttl: 60000, limit: 10 }])` + `@Throttle` sur le login, `ValidationPipe({ whitelist: true, forbidNonWhitelisted: true })`, Guards (`AuthGuard`, `RolesGuard`) sur chaque contrôleur protégé, `enableCors({ origin: ['https://domaine.fr'], credentials: true })`.

## Next.js (App Router)
- **En-têtes** : `next.config.js` → `async headers() { return [{ source: '/(.*)', headers: [...] }] }`. **CSP avec nonce** dans `middleware.ts` (générer le nonce, poser `Content-Security-Policy` et `x-nonce` ; Next applique le nonce à ses scripts ; les pages deviennent dynamiques).
- `poweredByHeader: false` dans next.config.
- **SEO** : `export const metadata` / `generateMetadata` (title, description, alternates.canonical, openGraph, twitter), `app/sitemap.ts`, `app/robots.ts`, JSON-LD via `<script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} />` (donnée maîtrisée, pas d'entrée utilisateur), `notFound()` pour les 404.
- **Perf** : `next/image` (AVIF/WebP, tailles, `priority` sur l'image LCP), `next/font` (auto-hébergement Google Fonts au build = conforme RGPD), `next/script` avec `strategy="lazyOnload"` ; Server Components par défaut, `"use client"` au minimum.
- **Consentement** : charger GA via `next/script` **uniquement** quand la CMP renvoie le consentement (état React/contexte), ou `@next/third-parties` + Consent Mode par défaut en « denied ».
- **Sécurité** : Server Actions (vérification d'Origin intégrée) ; vérifier l'auth **dans chaque Server Action / Route Handler** (le middleware seul ne suffit pas) ; Auth.js/NextAuth ou Lucia ; variables `NEXT_PUBLIC_*` = publiques, jamais de secret dedans.
- Build : `next build && next start`, ou `output: 'standalone'`, ou `output: 'export'` (statique).

## Nuxt 3/4
- `nuxt-security` (en-têtes, CSP nonce, rate limiter, XSS validator, CORS) — module de référence.
- SEO : `useSeoMeta`, `useHead`, `@nuxtjs/sitemap`, `@nuxtjs/robots`, `nuxt-schema-org` ; `createError({ statusCode: 404, fatal: true })`.
- Perf/RGPD : `@nuxt/image`, `@nuxt/fonts` (auto-héberge les polices), `@nuxt/scripts` (chargement conditionnel au consentement), `routeRules` (`prerender`, `swr`, en-têtes de cache).
- Secrets : `runtimeConfig` (privé) vs `runtimeConfig.public`.

## SvelteKit
`hooks.server.ts` → `handle` pour poser les en-têtes ; CSP native dans `svelte.config.js` (`kit.csp: { mode: 'auto', directives: {...} }` → nonces/hashes automatiques) ; CSRF : vérification d'Origin intégrée (`csrf.checkOrigin`) ; `error(404)` ; `export const prerender = true` pour le statique ; `$env/static/private` pour les secrets.

## Remix / React Router (mode framework)
En-têtes via `headers` export ou serveur Express ; `meta` export pour le SEO ; `throw new Response(null, { status: 404 })` ; sessions `createCookieSessionStorage({ cookie: { secure: true, httpOnly: true, sameSite: 'lax', secrets: [process.env.SESSION_SECRET] } })`.

## Déploiement Node
Derrière Nginx/Apache (reverse proxy : TLS, HSTS, compression, cache des assets) ou plateforme (Vercel, Netlify, Render, Fly.io) ; process manager `pm2` ou systemd ; ne jamais exposer le port Node directement ; voir serveurs-hebergement.md.
