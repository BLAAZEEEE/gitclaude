# Front-end & sites statiques — React, Vue, Angular, Svelte, Solid (SPA Vite), Astro, Gatsby, Hugo, Jekyll, Eleventy, HTML/CSS/JS

Un front statique ne pose **aucun en-tête HTTP lui-même** : en-têtes, compression, cache, redirection HTTPS et vraies 404 se configurent sur l'hébergement (voir serveurs-hebergement.md : `.htaccess`, Nginx, `_headers` Netlify/Cloudflare, `vercel.json`).

## SPA (React/Vue/Angular/Svelte + Vite)
- **SEO** : rendu client = HTML vide (SEO-31 KO). Migrer les pages publiques vers SSG/SSR (Astro, Next, Nuxt, SvelteKit, Angular SSR) ou prérendre les routes (`vite-plugin-prerender`, `vite-ssg` pour Vue). Métas par route : `react-helmet-async`, `@unhead/vue`, Angular `Meta`/`Title` — efficaces seulement avec prérendu/SSR.
- **404** : le fallback `index.html` doit renvoyer 404 pour les routes inconnues → prérendu + page 404 statique, ou config serveur qui ne réécrit que les routes connues.
- **Liens** : `<Link to>` / `<RouterLink>` / `routerLink` (rendus en `<a href>`), jamais `onClick={() => navigate()}` sur un `<div>`.
- **Sécurité** : pas de secret dans le bundle (`VITE_*`, `REACT_APP_*`, `NG_APP_*` sont **publics**) ; échappement natif du framework ; `dangerouslySetInnerHTML`/`v-html`/`[innerHTML]`/`{@html}` → DOMPurify ; jetons d'API en cookie `HttpOnly` plutôt qu'en localStorage ; CSP par hash compatible (Vite ne produit pas de script inline en build, sauf plugins).
- **Perf** : `build` de production, `React.lazy`/`defineAsyncComponent`/lazy routes Angular, images optimisées (`vite-imagetools`, `@unpic`), analyse du bundle (`rollup-plugin-visualizer`), budgets Angular (`angular.json` → `budgets`).
- **RGPD** : CMP JS (orestbida/cookieconsent, tarteaucitron), chargement conditionnel de GA via la CMP ; polices via `@fontsource/*`.

## Astro (recommandé pour les sites vitrines)
Statique par défaut, zéro JS hors îlots ; `@astrojs/sitemap` ; composant `<Image>`/`<Picture>` (AVIF/WebP, dimensions) ; `src/pages/404.astro` ; métas dans un layout `<SEO>` ; polices locales (`@fontsource`) ; CSP : `experimental.csp`/`security.csp` selon la version installée (hashes automatiques) sinon en-têtes chez l'hébergeur ; adaptateur Node/Vercel/Netlify pour les parties dynamiques.

## Gatsby
`gatsby-plugin-sitemap`, `gatsby-plugin-image`, Head API pour les métas, `gatsby-plugin-gatsby-cloud`/`_headers` pour les en-têtes. Projet peu maintenu : pour un nouveau projet, préférer Astro/Next.

## Générateurs statiques (Hugo, Jekyll, Eleventy)
- Sitemap et RSS natifs (Hugo), `jekyll-sitemap` + `jekyll-seo-tag` (Jekyll), `@quasibit/eleventy-plugin-sitemap` (Eleventy) ; `robots.txt` dans le dossier statique.
- Images : Hugo Pipes (`.Resize`, `.Process "webp"`), `@11ty/eleventy-img`, `jekyll_picture_tag`.
- Minification : `hugo --minify`, `html-minifier-terser` en transform Eleventy.
- Page `404.html` servie avec statut 404 par l'hébergeur.

## HTML/CSS/JS sans framework
- Gabarit `<head>` : seo.md#balises ; un fichier par page, footer commun avec mentions légales / confidentialité / gestion des cookies.
- `<script src defer>` ; CSS en fichier externe (CSP sans `unsafe-inline`) ; images `width`/`height`/`loading="lazy"` ; WebP via `<picture>`.
- Formulaire de contact : traité côté serveur (PHP, fonction serverless, service UE type Formspree-like conforme) avec honeypot + limitation de débit ; mention RGPD sous le formulaire.
- Build minimal recommandé pour la minification et l'empreinte des assets : Vite en mode multi-pages (`build.rollupOptions.input`).

## Tauri (front d'app desktop)
Hors périmètre « site public » (pas de SEO/cookies), mais CSP stricte dans `tauri.conf.json` (`app.security.csp`), capacités minimales, pas de `dangerousRemoteDomainIpcAccess`.
