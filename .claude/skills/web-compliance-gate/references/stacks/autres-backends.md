# Autres backends — Ruby on Rails, Java/Kotlin (Spring Boot), C#/.NET (ASP.NET Core), Go, Rust, Elixir/Phoenix

Pour chaque stack : mêmes exigences que securite.md ; ci-dessous, **où** et **comment** les implémenter.

## Ruby on Rails
- `config/environments/production.rb` : `config.force_ssl = true` (HTTPS + HSTS + cookies Secure), `config.consider_all_requests_local = false`, `config.assume_ssl = true` derrière un proxy.
- CSP : `config/initializers/content_security_policy.rb` avec `content_security_policy_nonce_generator` ; `config.action_dispatch.default_headers` pour les autres en-têtes.
- CSRF : `protect_from_forgery with: :exception` (par défaut). Rate limit : `rate_limit to: 10, within: 3.minutes, only: :create` (Rails 7.2+) ou `rack-attack`.
- Mots de passe : `has_secure_password` (bcrypt) ; Devise (`config.password_length = 12..128`, lockable).
- SQL : `where(email: params[:email])`, jamais `where("email = '#{…}'")`. XSS : `html_safe`/`raw` uniquement sur du contenu assaini (`sanitize`).
- Autorisation : Pundit / CanCanCan, `authorize @record` dans chaque action.
- Audit : `bundle exec bundle-audit check --update`, `brakeman` (SAST Rails dédié).
- SEO : `meta-tags` gem, `sitemap_generator` ; perf : `rack-deflater` ou proxy, assets avec empreinte (Propshaft), cache HTTP.

## Java / Kotlin — Spring Boot
- Spring Security : `http.requiresChannel(c -> c.anyRequest().requiresSecure())`, `headers(h -> h.contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'; …")).httpStrictTransportSecurity(hsts -> hsts.includeSubDomains(true).maxAgeInSeconds(31536000)).frameOptions(f -> f.sameOrigin()).referrerPolicy(r -> r.policy(STRICT_ORIGIN_WHEN_CROSS_ORIGIN)))`.
- CSRF actif par défaut (cookie `CookieCsrfTokenRepository` pour les SPA). Autorisation : `authorizeHttpRequests` + `@PreAuthorize` au niveau des méthodes, filtrage par propriétaire.
- Mots de passe : `Argon2PasswordEncoder` ou `BCryptPasswordEncoder(12)`. SQL : JPA/Spring Data, `@Query` avec paramètres nommés, `JdbcTemplate` avec `?`.
- `application-prod.properties` : `server.error.include-stacktrace=never`, `server.error.include-message=never`, `server.compression.enabled=true`, `server.http2.enabled=true`, `server.servlet.session.cookie.secure=true`, `…http-only=true`, `…same-site=lax`, `management.endpoints.web.exposure.include=health` (Actuator restreint).
- Audit : OWASP dependency-check (`mvn org.owasp:dependency-check-maven:check` / plugin Gradle), Trivy, Snyk.

## C# — ASP.NET Core
```csharp
if (!app.Environment.IsDevelopment()) { app.UseExceptionHandler("/Error"); app.UseHsts(); }
app.UseHttpsRedirection();
app.UseStatusCodePagesWithReExecute("/Error/{0}");   // vraies 404
app.UseResponseCompression();
app.Use(async (ctx, next) => {
    var h = ctx.Response.Headers;
    h["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'";
    h["X-Content-Type-Options"] = "nosniff"; h["Referrer-Policy"] = "strict-origin-when-cross-origin";
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"; h["Cross-Origin-Opener-Policy"] = "same-origin";
    await next();
});
builder.Services.AddRateLimiter(o => o.AddFixedWindowLimiter("login", l => { l.PermitLimit = 5; l.Window = TimeSpan.FromMinutes(15); }));
```
- `builder.Services.AddHsts(o => { o.MaxAge = TimeSpan.FromDays(365); o.IncludeSubDomains = true; })` ; Kestrel `AddServerHeader = false` ; web.config (IIS) : `<requestFiltering removeServerHeader="true" />`, retirer `X-Powered-By`.
- Anti-forgery : `[ValidateAntiForgeryToken]` / `AutoValidateAntiforgeryToken` ; Identity : `PasswordOptions.RequiredLength = 12`, lockout activé ; `[Authorize(Policy=…)]` + vérification de propriété.
- EF Core : LINQ ou `FromSqlInterpolated` (paramétré) ; jamais `FromSqlRaw` avec concaténation. Razor échappe ; `Html.Raw` seulement sur du HTML assaini (HtmlSanitizer).
- `ASPNETCORE_ENVIRONMENT=Production`. Audit : `dotnet list package --vulnerable --include-transitive`.

## Go (net/http, Gin, Echo, Fiber, Chi)
- Middleware d'en-têtes (`unrolled/secure`, `gin-contrib/secure`, Echo `middleware.Secure()`, Fiber `helmet`) ; CSRF : `gorilla/csrf` ou `filippo.io/csrf` ; rate limit : `golang.org/x/time/rate`, `ulule/limiter`, `tollbooth`.
- `html/template` (échappement contextuel) — jamais `text/template` pour du HTML ; `template.HTML` seulement sur du contenu assaini (bluemonday).
- SQL : `db.Query("… WHERE id = $1", id)` ; jamais `fmt.Sprintf` dans une requête. Mots de passe : `golang.org/x/crypto/argon2` ou `bcrypt`.
- `http.Server{ReadHeaderTimeout, ReadTimeout, WriteTimeout, IdleTimeout}` définis ; `autocert` pour Let's Encrypt si pas de proxy. Audit : `govulncheck ./...`, `gosec`.

## Rust (Axum, Actix-web, Rocket, Leptos)
- En-têtes : `tower-http` (`SetResponseHeaderLayer`, `CompressionLayer`) pour Axum ; `actix-web` `DefaultHeaders` + `Compress` ; rate limit : `tower_governor` / `actix-governor`.
- SQL : `sqlx::query!("… WHERE id = $1", id)` (vérifié à la compilation), Diesel, SeaORM. Mots de passe : crate `argon2`. Templates : Askama/Tera (échappement par défaut).
- CSRF : `axum_csrf` ou vérification d'Origin + SameSite. Audit : `cargo audit`, `cargo deny`.
- Tauri (app desktop) : hors périmètre web public, mais CSP stricte dans `tauri.conf.json` et capacités minimales restent de mise.

## Elixir — Phoenix
`plug :put_secure_browser_headers` (+ CSP personnalisée), `force_ssl: [hsts: true]` dans l'endpoint, `protect_from_forgery` (par défaut), Ecto (requêtes paramétrées), `Bcrypt`/`Argon2` (comeonin), `PlugAttack`/`Hammer` pour le rate limit, `mix deps.audit` / `mix hex.audit`, `sobelow` (SAST).
