# SEO technique & on-page — exigences et corrections

Sommaire : [balises](#balises) · [structure](#structure) · [indexation](#indexation) · [contenu](#contenu) · [liens](#liens) · [réseaux sociaux](#social) · [données structurées](#donnees-structurees) · [international](#international) · [rendu JS](#rendu)

<a id="balises"></a>
## 1. Balises du `<head>` (SEO-01/02/04/05/09/10/25/33/34)

Gabarit de référence, à produire pour **chaque** page avec des valeurs uniques :
```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mot-clé principal — Contexte | Marque</title>            <!-- 50-60 car., unique -->
  <meta name="description" content="Promesse claire + bénéfice + appel à l'action (120-155 car.)">
  <link rel="canonical" href="https://www.domaine.fr/chemin-canonique">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <meta property="og:type" content="website">
  <meta property="og:title" content="…"><meta property="og:description" content="…">
  <meta property="og:image" content="https://www.domaine.fr/og/page.jpg">  <!-- 1200×630, URL absolue -->
  <meta property="og:url" content="https://www.domaine.fr/chemin-canonique">
  <meta property="og:locale" content="fr_FR">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{ … }</script>
</head>
```
- `<title>` : mot-clé au début, 30-60 caractères (au-delà, tronqué). Jamais identique entre deux pages.
- Meta description : 70-160 caractères, pas un facteur de classement direct mais du taux de clic.
- Le score SEO Lighthouse (SEO-34) doit atteindre 90 ou plus.

<a id="structure"></a>
## 2. Structure (SEO-07/08)
- Un seul `<h1>` par page, qui reprend l'intention de la page.
- Hiérarchie sans saut : H1 → H2 → H3. Les titres servent la structure, pas le style (utiliser des classes CSS pour la taille).
- Balises sémantiques : `<header> <nav> <main> <article> <section> <footer>`.

<a id="indexation"></a>
## 3. Indexation (SEO-11/12/13/14/15/16/21/30)

**robots.txt** (à la racine, en texte brut) :
```
User-agent: *
Disallow: /admin/
Disallow: /panier
Sitemap: https://www.domaine.fr/sitemap.xml
```
Ne jamais laisser `Disallow: /` en production (souvent hérité de la préprod). Ne pas bloquer CSS/JS.

**sitemap.xml** : uniquement des URLs canoniques qui renvoient 200, pas de pages en noindex ni redirigées. `<lastmod>` exact si utilisé. Générer au build :
Next.js `app/sitemap.ts`, Nuxt `@nuxtjs/sitemap`, Astro `@astrojs/sitemap`, Laravel `spatie/laravel-sitemap`, Symfony `presta/sitemap-bundle`, Django `django.contrib.sitemaps`, WordPress natif (`/wp-sitemap.xml`) ou Yoast/Rank Math, Hugo/Jekyll/Eleventy natifs ou plugin. Déclarer le sitemap dans Google Search Console et Bing Webmaster Tools.

**noindex** : `<meta name="robots" content="noindex">` ou en-tête `X-Robots-Tag: noindex` uniquement sur les pages à exclure (panier, compte, recherche interne, merci). Préprod : noindex + authentification HTTP, et **retirer à la mise en ligne**.

**Canonical** : absolue, auto-référente sur les pages originales, une seule par page, pointe vers une URL 200 indexable.

**Vrai 404** (SEO-21) : les routes inconnues renvoient le **code HTTP 404** (pas une page « introuvable » en 200). SPA : configurer le serveur/l'hébergeur pour servir la page 404 avec le bon statut sur les routes non déclarées ; frameworks SSR : `notFound()` (Next), `createError({statusCode:404})` (Nuxt), `abort(404)` (Laravel), `Http404` (Django).

**Une seule version du site** (SEO-30) : `http://`, `http://www.`, `https://` et `https://www.` redirigent en **301** vers une seule forme canonique (voir ssl-tls.md#redirection).

<a id="contenu"></a>
## 4. Contenu (SEO-17/26/27)
- `alt` descriptif sur toute image informative ; `alt=""` sur les décoratives (pas d'omission de l'attribut).
- Pages de contenu : 300 mots utiles minimum, répondant à l'intention de recherche.
- Pas de contenu dupliqué entre URLs (paramètres, slash final, majuscules, http/https) → canonical ou 301.
- Maillage interne : chaque page importante est à 3 clics maximum de l'accueil ; ancres descriptives (pas « cliquez ici »).

<a id="liens"></a>
## 5. Liens & URLs (SEO-18/19/20/28/32)
- Zéro lien interne en 4xx/5xx. Page supprimée → redirection 301 vers l'équivalent le plus proche.
- Pas de chaînes de redirection : lien → destination finale directement.
- URLs : minuscules, mots séparés par des tirets, sans accents ni espaces, sans paramètres de session, stables dans le temps.
- Navigation en `<a href="/chemin">` (crawlable). `onclick`/`router.push` sans `href` = invisible pour les robots. Les frameworks fournissent `<Link>`/`<NuxtLink>`/`<RouterLink>` qui rendent un vrai `<a href>`.
- Liens sortants sponsorisés : `rel="sponsored"` ; contenus d'utilisateurs : `rel="ugc"`.

<a id="social"></a>
## 6. Réseaux sociaux (SEO-22/23)
Open Graph complet (`og:title`, `og:description`, `og:image` 1200×630 en URL absolue, `og:url`, `og:type`) + `twitter:card`. Tester avec l'outil de partage LinkedIn (Post Inspector) et le débogueur Facebook.

<a id="donnees-structurees"></a>
## 7. Données structurées JSON-LD (SEO-24)
Au minimum sur l'accueil : `Organization` ou `LocalBusiness` (commerce local : adresse, téléphone, horaires, `geo`) + `WebSite`. Selon les pages : `BreadcrumbList`, `Article`/`BlogPosting`, `Product` + `Offer`, `FAQPage` (uniquement si la FAQ est visible), `Event`, `Service`.
```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"LocalBusiness","name":"…","url":"https://www.domaine.fr/",
 "telephone":"+33…","address":{"@type":"PostalAddress","streetAddress":"…","postalCode":"…","addressLocality":"…","addressCountry":"FR"},
 "openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday"],"opens":"09:00","closes":"18:00"}]}
</script>
```
Valider avec le test des résultats enrichis de Google et le validateur schema.org. Les données doivent correspondre au contenu visible.

<a id="international"></a>
## 8. Multilingue (SEO-29)
Chaque version liste **toutes** les versions (y compris elle-même) + `x-default`, en URLs absolues, de façon réciproque :
```html
<link rel="alternate" hreflang="fr-FR" href="https://www.domaine.fr/">
<link rel="alternate" hreflang="en" href="https://www.domaine.fr/en/">
<link rel="alternate" hreflang="x-default" href="https://www.domaine.fr/">
```

<a id="rendu"></a>
## 9. Rendu JavaScript (SEO-31)
Une SPA en rendu client (React/Vue/Angular + Vite/CRA) livre un HTML vide : l'indexation est retardée et incomplète, les aperçus sociaux ne fonctionnent pas. Solutions, par ordre de préférence :
1. **SSG** (pages statiques générées au build) : Astro, Next `output: 'export'`/SSG, Nuxt `nuxi generate`, SvelteKit prerender, VitePress.
2. **SSR** : Next.js, Nuxt, SvelteKit, Remix/React Router framework, Angular SSR.
3. **Prérendu** des routes publiques (vite-plugin-prerender, react-snap) si la migration est impossible.
Les balises `<title>`, meta et JSON-LD doivent être dans le HTML initial (Next `metadata`, Nuxt `useSeoMeta`, `@unhead/vue`, `react-helmet-async` + SSR).

## Après la mise en ligne
Search Console : propriété de domaine, sitemap soumis, rapport « Pages » sans erreur, Core Web Vitals terrain. Bing Webmaster Tools (import depuis Search Console). Fiche Google Business Profile pour un commerce local.
