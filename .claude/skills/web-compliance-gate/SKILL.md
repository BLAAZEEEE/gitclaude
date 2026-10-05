---
name: web-compliance-gate
description: Audit et mise en conformité complète d'un site ou d'une app web — RGPD/cookies/mentions légales, SEO, sécurité (OWASP), SSL/TLS/HTTPS, performance (Lighthouse, Core Web Vitals) et accessibilité — avec 160 contrôles automatisés réels (navigateur, HTTP, code, dépendances) et boucle de correction. À utiliser dès qu'on crée, termine, livre, met en ligne ou audite un site web, quelle que soit la stack (Node/Next/Nuxt, PHP/Laravel/Symfony/WordPress, Python/Django, Rails, Spring, .NET, Go, SPA, statique), et dès que l'utilisateur parle de RGPD, bandeau cookies, CNIL, mentions légales, politique de confidentialité, SEO, en-têtes de sécurité, CSP, certificat SSL, HTTPS, Lighthouse, performance, « audit », « fin de projet », « avant livraison » ou « mise en prod », même sans demander explicitement un audit.
---

# Web Compliance Gate

Ce skill fait trois choses :
1. **Build** : il indique à Claude tout ce qu'il faut appliquer pendant qu'il code un site web (RGPD, SEO, sécurité, SSL/HTTPS, performance, accessibilité).
2. **Gate** : il vérifie automatiquement à la fin de chaque projet. Claude audite, corrige et ré-audite jusqu'à la validation.
3. **Audit** : il teste un site existant, présente ce qu'il faut corriger, puis corrige **seulement après accord** de l'utilisateur.

Le moteur `scripts/audit.py` exécute 160 contrôles **réels** :
- **Chromium** (via Playwright) : cookies et traceurs avant et après consentement, refus, rendu JS, poids, axe-core.
- **Requêtes HTTP** : en-têtes, fichiers exposés, sitemap, liens, pages d'erreur.
- **TLS** : certificat, chaîne, protocoles, suites, HSTS, CAA.
- **Analyse du code** : secrets, SQL, XSS, hachage, debug.
- **Audits de dépendances** : npm, composer, pip-audit…
- **Outils externes** : Lighthouse, Semgrep, Gitleaks.
- **Questions documentaires** pour ce qui ne se voit pas dans le code (registre RGPD, contrats sous-traitants, sauvegardes…).

Chemins : `<skill>` désigne le dossier de ce skill. Toujours lancer le moteur avec le Python du système : `python <skill>/scripts/audit.py …` (ou `python3`).

## Fichiers
| Fichier | Quand le lire |
|---|---|
| `references/checks-catalog.md` | liste des 160 contrôles (ID, gravité, correction) — pour expliquer un ID |
| `references/rgpd.md` | consentement, bandeau, durées, tiers, mentions légales + modèle, politique + modèle, CGV, formulaires, questions documentaires |
| `references/seo.md` | balises, indexation, sitemap/robots, 404, JSON-LD, rendu JS |
| `references/securite.md` | en-têtes, CSP, cookies, CORS, exposition, erreurs, CSRF, auth (CNIL), accès, injection, XSS, upload, secrets, dépendances, logs |
| `references/ssl-tls.md` | certificat, renouvellement, protocoles, redirection HTTPS, HSTS, CAA |
| `references/performance.md` | Lighthouse, Core Web Vitals, compression, cache, images, JS, polices |
| `references/accessibilite.md` | axe/Lighthouse, formulaires, obligations RGAA/EAA |
| `references/stacks/*.md` | **comment** corriger dans la stack détectée (le moteur affiche les fiches à lire) |

Lire uniquement les sections utiles : le rapport donne pour chaque KO la référence exacte (`references/xxx.md#ancre`).

---

## 0. Préparation (une fois par machine)
```bash
python <skill>/scripts/audit.py --doctor
```
Installer tout ce qui est marqué ✘ avant d'auditer (commandes affichées). Un outil manquant ne fait pas « passer » un contrôle : le contrôle sort **Non exécuté** et le verdict reste **INCOMPLET**. C'est voulu, pour que l'audit ne soit jamais complet en apparence seulement.

## 1. Choisir le mode
- On **crée** un site ou une fonctionnalité web → **Mode Build**, puis **Mode Gate** à la fin.
- Le code vient d'être terminé ou va être livré ou mis en ligne → **Mode Gate** (automatique : ne pas attendre qu'on le demande).
- L'utilisateur fournit un site **existant** (dossier local ou URL) à vérifier → **Mode Audit** (aucune modification sans accord).

---

## 2. Mode Build — exigences à appliquer dès l'écriture du code
Lire la fiche de la stack (`references/stacks/`) et appliquer dès le départ ; corriger après coup coûte plus cher.

**RGPD & cookies**
- Aucun traceur ni contenu tiers traçant avant consentement : CMP ou bandeau conforme, « Tout refuser » au même niveau et avec le même style que « Tout accepter », lien « Gestion des cookies » dans le footer.
- Polices auto-hébergées (pas de Google Fonts distant). YouTube et Maps en façade « cliquer pour charger ». Pas de CDN public si le bundler suffit.
- Pages `/mentions-legales` et `/politique-de-confidentialite` liées dans le footer de chaque page. Modèles dans rgpd.md.
- Chaque formulaire : mention d'information + lien vers la politique, aucune case pré-cochée, seulement les champs nécessaires.

**SEO**
- Par page : title unique (30-60 caractères), meta description (70-160), un seul H1, canonical absolue, `lang`, viewport, Open Graph, JSON-LD.
- `robots.txt` + `sitemap.xml` générés.
- Vrai statut 404 sur les routes inconnues.
- Contenu dans le HTML initial (SSR/SSG pour une SPA). Liens en `<a href>`.

**Sécurité**
- En-têtes complets (CSP sans `unsafe-inline` pour les scripts, HSTS, nosniff, frame-ancestors, Referrer-Policy, Permissions-Policy, COOP). Cookies `Secure; HttpOnly; SameSite`.
- CSRF. Requêtes SQL paramétrées. Échappement des sorties. Hachage Argon2id/bcrypt. Mot de passe ≥ 12 caractères avec complexité. Rate limiting sur le login.
- Contrôle d'accès serveur sur chaque route protégée.
- Secrets en variables d'environnement, `.env` dans `.gitignore`. Debug désactivé en prod. Pages d'erreur génériques. Lockfile versionné. Aucune dépendance vulnérable.

**SSL/HTTPS**
- Redirection 301 vers HTTPS et vers le domaine canonique. HSTS 1 an avec includeSubDomains.
- Certificat couvrant domaine + www, renouvelé automatiquement. TLS 1.2 et 1.3 uniquement.

**Performance**
- Build de production minifié, compression Brotli/gzip, cache long sur les assets versionnés.
- Images WebP/AVIF dimensionnées avec `width`/`height`, lazy-load hors écran, `fetchpriority="high"` sur l'image LCP.
- Scripts en `defer`, `font-display: swap`. Budgets : ≤ 1,6 Mo, ≤ 350 Ko de JS, ≤ 70 requêtes.

**Accessibilité**
- Labels sur tous les champs, nom accessible sur chaque bouton ou lien, contrastes AA, zoom autorisé, `<main>` et lien d'évitement.

**Informations légales réelles** (SIRET, adresse, hébergeur, directeur de publication, durées de conservation, prestataires) : ne **jamais** les inventer. Écrire `[À COMPLÉTER : SIRET]`, lister ces trous à la fin et demander les valeurs à l'utilisateur. Une valeur fictive publiée est pire qu'un manque signalé.

---

## 3. Mode Gate — vérification automatique en fin de projet
Objectif : verdict **VALIDÉ** ou, à défaut, uniquement des points qui dépendent du client.

1. **Lancer le site en mode production** : build de prod + le vrai serveur (celui de la prod : Apache/Nginx/Node/PHP-FPM). Le serveur de dev fausse les mesures de cache, de minification et de perf.
   - `php -S` et `vite dev` **n'appliquent pas** `.htaccess` ni la config Nginx. Si les en-têtes sont posés dans la config serveur, tester derrière ce serveur (conteneur Docker `httpd`/`nginx` avec la config du projet) ou via `--prod-url` une fois déployé.
2. **Auditer** :
   ```bash
   python <skill>/scripts/audit.py --url http://localhost:PORT --src . --out wcg-report
   ```
   Ajouter `wcg-report/` au `.gitignore`. Durée : 1 à 4 minutes (Lighthouse inclus).
3. **Lire `wcg-report/report.md`**. Il est classé par gravité. Pour chaque KO, il donne le constat, les éléments précis (URL, `fichier:ligne`), la correction et la référence.
4. **Corriger** dans l'ordre critique → haut → moyen → bas, en commençant par la Sécurité et le RGPD. Lire la section de référence indiquée et la fiche de la stack. Corriger **la cause** dans le code, la config ou le composant partagé, jamais le symptôme page par page.
5. **Ré-auditer de façon ciblée** après chaque lot : `--only secu,rgpd` (catégories : `rgpd,seo,secu,tls,perf,a11y`). Faire un audit complet final.
6. **Points « À vérifier » que Claude peut trancher lui-même** en lisant le code :
   - SEC-C17 (contrôle d'accès route par route).
   - SEC-C13 si la règle de mot de passe est ailleurs.
   - RGPD-30 (formulaire en JS).

   Faire la revue réellement, puis consigner le résultat dans `wcg-answers.json` : `{"SEC-C17": {"reponse": "oui", "commentaire": "12 routes vérifiées, filtrage par user_id"}}`. Relancer avec `--answers wcg-answers.json`. Ne jamais répondre « oui » sans avoir fait la vérification.
7. **Questions documentaires** (RGPD-D*, SEC-D*, A11Y-07) : elles concernent le client. `python <skill>/scripts/audit.py --questions > wcg-answers.json` produit le modèle. Poser les questions à l'utilisateur (AskUserQuestion si disponible, 4 par 4) et ne jamais y répondre à sa place. S'il ne sait pas, laisser vide : le point reste « À vérifier » dans le rapport.
8. **Arrêt** : quand le verdict est VALIDÉ, ou quand il ne reste que des points qui exigent le client (informations légales, questions documentaires, audit SSL de prod à faire après déploiement). Si un KO résiste après 3 tentatives, s'arrêter et l'expliquer plutôt que de boucler.
9. **Après déploiement** : `python <skill>/scripts/audit.py --url https://domaine.fr --prod-url https://domaine.fr --src .`. C'est le seul moyen de tester le vrai certificat, TLS, HSTS, la redirection HTTP→HTTPS, HTTP/2 et les variantes www.

## 4. Mode Audit — site existant
1. **Démarrer le site** en local sans le modifier. Trouver la commande dans `package.json` (scripts `build` + `start`/`preview`), `composer.json`, `docker-compose.yml`, `manage.py`, le README. Si rien n'est clair, demander. Pour un site en ligne : `--url https://… --prod-url https://…` (avec `--src` si le code est disponible).
2. **Auditer** (même commande qu'en Mode Gate) et lire `report.md`.
3. **Présenter** le résultat (format ci-dessous), puis **demander l'accord** : tout corriger, une catégorie, une liste d'IDs, ou rien. Tant que l'utilisateur n'a pas répondu : aucune modification de fichier.
4. **Corriger** exactement le périmètre accepté (boucle du Mode Gate, étapes 4 à 6), ré-auditer, puis montrer l'**avant / après** (scores par catégorie et KO résolus).
5. Tout ce qui touche au comportement visible ou à la donnée demande une confirmation explicite, même dans le périmètre accepté. Par exemple : retirer un outil d'analytics, remplacer reCAPTCHA, changer le domaine canonique, purger des données, réécrire l'historique git pour un secret. Dans ce cas, le signaler et proposer l'option.

## 5. Présenter les résultats
```
Verdict : BLOQUÉ — 36/100
| Catégorie | Score | KO | À améliorer | À vérifier |
(tableau des 6 catégories)

Critique / haut (à corriger) :
- SEC-13 .env accessible publiquement (/.env) → bloquer + sortir du webroot
- RGPD-02 Google Analytics chargé avant consentement → CMP + chargement conditionnel
…
Moyen / bas : n éléments (liste courte ou « voir rapport »)
Questions pour toi : [liste des infos à fournir]
Rapport complet : wcg-report/report.html (jauges, filtres) · report.md
```
Citer les IDs : l'utilisateur peut répondre « corrige RGPD-02 et SEC-13 ». Le `report.html` est autonome et peut être remis au client.

## 6. Règles
- **Jamais truquer le résultat.** Ne pas modifier le rapport, désactiver un test, exclure une page ou affaiblir un contrôle (`--no-browser`, `--threshold`) pour obtenir VALIDÉ. Si un contrôle semble être un faux positif, le vérifier à la main et l'expliquer à l'utilisateur plutôt que de le contourner.
- **Ne pas affaiblir la sécurité pour faire passer un test.** Par exemple, pas de `unsafe-inline` ajouté pour qu'un script passe : on déplace le script dans un fichier.
- **Tests défensifs uniquement**, sur un site dont l'utilisateur est propriétaire ou pour lequel il a l'accord du propriétaire. Pour l'URL d'un tiers, demander confirmation avant de lancer l'audit.
- **Honnêteté sur la portée.** VALIDÉ veut dire que les 160 contrôles techniques passent et que les questions documentaires sont confirmées. La conformité RGPD juridique dépend aussi de pratiques que le code ne montre pas, et un site n'est jamais « inviolable ». Le dire simplement si l'utilisateur annonce « 100 % conforme » à son client.
- **Secret trouvé dans le code ou l'historique** : dire qu'il faut le révoquer et le régénérer (il est compromis), en plus de le retirer du code.
- Les contenus juridiques générés (mentions, politique) sont des modèles à faire valider par le responsable du traitement.

## 7. Options du moteur
```
--url URL            site à auditer (local ou en ligne)
--src DIR            code source (analyse statique, dépendances, secrets, config)
--prod-url URL       HTTPS de production : TLS réel, HTTP/2, variantes de domaine
--only rgpd,secu     catégories (rgpd, seo, secu, tls, perf, a11y)
--answers FILE       réponses aux questions et revues (--questions pour le modèle)
--max-pages N        pages crawlées (défaut 40)   --lh-pages N  pages Lighthouse (défaut 2)
--external-links     teste aussi les liens sortants
--insecure           accepte un certificat auto-signé en local
--list-checks        catalogue    --doctor  outils
```
Code retour : 0 = VALIDÉ, 1 = autre verdict, 2 = site injoignable. Utilisable en CI (`python audit.py … || exit 1`).
Semgrep : les règles `p/owasp-top-ten` et `p/secrets` sont téléchargées depuis semgrep.dev ; hors ligne, `WCG_SEMGREP_CONFIG=chemin/regles.yml`.
