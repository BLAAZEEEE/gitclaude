# Stack Python — Django, Flask, FastAPI, Starlette, Wagtail

## Commun
| Besoin | Solution |
|---|---|
| Hachage | `argon2-cffi` / `passlib[argon2]` ; Django : `Argon2PasswordHasher` en premier dans `PASSWORD_HASHERS` |
| SQL | ORM (Django, SQLAlchemy) ou `cursor.execute("… WHERE id = %s", (id,))` — jamais de f-string / `.format` / `%` dans la requête |
| Validation | Pydantic (FastAPI), DRF serializers, Django forms, marshmallow |
| Assainissement HTML | `nh3` (ou `bleach`, déprécié) |
| Audit dépendances | `pip-audit -r requirements.txt` (ou `pip-audit` dans le venv), `uv pip compile` + hashes |
| Serveur | Gunicorn/Uvicorn derrière Nginx/Caddy (TLS, compression, cache, HSTS) ; jamais `runserver`/`app.run(debug=True)` en prod |
| Secrets | variables d'environnement (`django-environ`, `pydantic-settings`, `python-dotenv` en dev) |

## Django — `settings.py` de production
```python
DEBUG = False
ALLOWED_HOSTS = ["domaine.fr", "www.domaine.fr"]
SECRET_KEY = env("DJANGO_SECRET_KEY")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "SAMEORIGIN"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = ["https://domaine.fr", "https://www.domaine.fr"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```
- CSP : `django-csp` (≥ 4 : réglage `CONTENT_SECURITY_POLICY`, nonce `{{ request.csp_nonce }}`) ; Django 6 intègre une CSP native — utiliser celle de la version installée. Permissions-Policy : `django-permissions-policy`.
- Contrôle `python manage.py check --deploy` : zéro avertissement.
- Rate limit login : `django-axes` (blocage après N échecs) ou `django-ratelimit`.
- Autorisation : `@login_required`, `LoginRequiredMixin`, `PermissionRequiredMixin`, filtrage des querysets par `request.user` (anti-IDOR) ; DRF : `permission_classes` + `get_queryset()` filtré.
- XSS : templates auto-échappés ; `|safe` / `mark_safe` uniquement sur du HTML assaini.
- SEO : `django.contrib.sitemaps`, vue `robots.txt`, `raise Http404`, `handler404`/`handler500` avec templates génériques ; `django-meta` ou blocs de template pour title/description/OG.
- Perf : `WhiteNoise` (`CompressedManifestStaticFilesStorage` : compression + noms versionnés + cache long), cache de vues (`cache_page`, Redis), `select_related`/`prefetch_related` contre le N+1, `GZipMiddleware` si pas de proxy.
- Admin : URL non standard, MFA (`django-otp`), accès restreint.
- RGPD : purge via commande de gestion planifiée, `django-cookie-consent` ou CMP JS.

## Flask
- `app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SECRET_KEY=os.environ["SECRET_KEY"])`.
- `flask-talisman` (en-têtes, CSP avec nonce, HTTPS forcé, HSTS), `flask-wtf` (CSRF), `flask-limiter` (rate limit), `flask-login` + décorateurs, `flask-compress`.
- `abort(404)`, `@app.errorhandler(500)` générique ; jamais `debug=True` en prod (le débogueur Werkzeug permet l'exécution de code).

## FastAPI / Starlette
- Middlewares : `HTTPSRedirectMiddleware`, `TrustedHostMiddleware(allowed_hosts=[…])`, `GZipMiddleware`, `CORSMiddleware(allow_origins=["https://domaine.fr"], allow_credentials=True)` (jamais `["*"]` avec credentials) ; en-têtes de sécurité via un middleware maison ou `secure` (package).
- Auth : OAuth2 + JWT (`pyjwt`), dépendances `Depends(get_current_user)` sur chaque route protégée, vérification de propriété des ressources.
- Rate limit : `slowapi`. Validation : modèles Pydantic stricts. Docs `/docs` et `/redoc` désactivées ou protégées en prod (`docs_url=None`).
- Si FastAPI sert un front : SSR/SSG côté front pour le SEO (voir frontend-static.md).
