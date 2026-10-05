"""Détection de la stack à partir du dépôt, pour orienter vers la bonne fiche de correction."""
from __future__ import annotations

import json
import re
from pathlib import Path

IGNORE_DIRS = {"node_modules", "vendor", ".git", "dist", "build", ".next", ".nuxt", ".output", ".svelte-kit",
               "venv", ".venv", "env", "__pycache__", "target", "bin", "obj", "coverage", ".cache", ".turbo",
               ".idea", ".vscode", "storage", "public/build", ".astro", "out", "tmp", ".parcel-cache", "wcg-report"}

# (marqueur, fiche de référence)
NPM_MARKERS = {
    "next": ("Next.js", "node-js.md"), "nuxt": ("Nuxt", "node-js.md"), "@sveltejs/kit": ("SvelteKit", "node-js.md"),
    "@remix-run/node": ("Remix", "node-js.md"), "@react-router/node": ("React Router (framework)", "node-js.md"),
    "astro": ("Astro", "frontend-static.md"),
    "gatsby": ("Gatsby", "frontend-static.md"), "@angular/core": ("Angular", "frontend-static.md"),
    "react": ("React", "frontend-static.md"), "vue": ("Vue", "frontend-static.md"), "svelte": ("Svelte", "frontend-static.md"),
    "solid-js": ("Solid", "frontend-static.md"), "vite": ("Vite", "frontend-static.md"),
    "express": ("Express", "node-js.md"), "fastify": ("Fastify", "node-js.md"), "@nestjs/core": ("NestJS", "node-js.md"),
    "koa": ("Koa", "node-js.md"), "hono": ("Hono", "node-js.md"), "@hapi/hapi": ("hapi", "node-js.md"),
    "@11ty/eleventy": ("Eleventy", "frontend-static.md"), "@tauri-apps/api": ("Tauri (front)", "frontend-static.md"),
}
COMPOSER_MARKERS = {
    "laravel/framework": ("Laravel", "php.md"), "symfony/framework-bundle": ("Symfony", "php.md"),
    "slim/slim": ("Slim", "php.md"), "cakephp/cakephp": ("CakePHP", "php.md"), "codeigniter4/framework": ("CodeIgniter", "php.md"),
    "drupal/core": ("Drupal", "php.md"), "prestashop/prestashop": ("PrestaShop", "php.md"), "magento/product-community-edition": ("Magento", "php.md"),
}
PY_MARKERS = {"django": ("Django", "python.md"), "flask": ("Flask", "python.md"), "fastapi": ("FastAPI", "python.md"),
              "starlette": ("Starlette", "python.md"), "pyramid": ("Pyramid", "python.md"), "wagtail": ("Wagtail", "python.md")}


def _read(p: Path, limit=400_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:  # noqa: BLE001
        return ""


def iter_files(root: Path, exts: tuple | None = None, max_files=8000):
    n = 0
    for p in root.rglob("*"):
        if n >= max_files:
            return
        parts = set(p.relative_to(root).parts)
        if parts & IGNORE_DIRS:
            continue
        if p.is_file() and (exts is None or p.suffix.lower() in exts or p.name in exts):
            n += 1
            yield p


def detect(src: str | None) -> dict:
    out = {"frameworks": [], "languages": [], "servers": [], "hosting": [], "refs": set(), "manifests": [], "cms": []}
    if not src:
        return _fin(out)
    root = Path(src)
    if not root.exists():
        return _fin(out)

    def add(name, ref, kind="frameworks"):
        if name not in out[kind]:
            out[kind].append(name)
        out["refs"].add(ref)

    for pkg in [root / "package.json", *root.glob("*/package.json")]:
        if pkg.exists() and "node_modules" not in pkg.parts:
            out["manifests"].append(str(pkg.relative_to(root)))
            add("JavaScript/TypeScript", "node-js.md", "languages")
            try:
                data = json.loads(_read(pkg))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for k, (name, ref) in NPM_MARKERS.items():
                    if k in deps:
                        add(name, ref)
            except Exception:  # noqa: BLE001
                pass
    comp = root / "composer.json"
    if comp.exists() or list(iter_files(root, (".php",), 50)):
        add("PHP", "php.md", "languages")
        if comp.exists():
            out["manifests"].append("composer.json")
            txt = _read(comp)
            for k, (name, ref) in COMPOSER_MARKERS.items():
                if f'"{k}"' in txt:
                    add(name, ref)
    if (root / "wp-config.php").exists() or (root / "wp-content").exists() or (root / "wp-config-sample.php").exists():
        add("WordPress", "php.md", "cms")
    py_txt = ""
    for f in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "poetry.lock"):
        if (root / f).exists():
            out["manifests"].append(f)
            py_txt += _read(root / f).lower()
    if py_txt or (root / "manage.py").exists():
        add("Python", "python.md", "languages")
        for k, (name, ref) in PY_MARKERS.items():
            if re.search(rf"(^|[\s\"'=\[]){k}([\s\"'=<>~\[,]|$)", py_txt, re.M):
                add(name, ref)
        if (root / "manage.py").exists():
            add("Django", "python.md")
    if (root / "Gemfile").exists():
        out["manifests"].append("Gemfile")
        add("Ruby", "autres-backends.md", "languages")
        if "rails" in _read(root / "Gemfile"):
            add("Ruby on Rails", "autres-backends.md")
    for f in ("pom.xml", "build.gradle", "build.gradle.kts"):
        if (root / f).exists():
            out["manifests"].append(f)
            add("Java/Kotlin (JVM)", "autres-backends.md", "languages")
            if "spring-boot" in _read(root / f):
                add("Spring Boot", "autres-backends.md")
    if list(iter_files(root, (".csproj",), 5)):
        add("C# / .NET", "autres-backends.md", "languages")
        add("ASP.NET Core", "autres-backends.md")
    if (root / "go.mod").exists():
        out["manifests"].append("go.mod")
        add("Go", "autres-backends.md", "languages")
    if (root / "Cargo.toml").exists():
        out["manifests"].append("Cargo.toml")
        add("Rust", "autres-backends.md", "languages")
        t = _read(root / "Cargo.toml")
        for k in ("axum", "actix-web", "rocket", "leptos", "tauri"):
            if k in t:
                add(k, "autres-backends.md")
    if (root / "mix.exs").exists():
        add("Elixir/Phoenix", "autres-backends.md", "languages")
    for f, name in (("hugo.toml", "Hugo"), ("hugo.yaml", "Hugo"), ("_config.yml", "Jekyll"), (".eleventy.js", "Eleventy"),
                    ("eleventy.config.js", "Eleventy"), ("astro.config.mjs", "Astro"), ("gatsby-config.js", "Gatsby")):
        if (root / f).exists():
            add(name, "frontend-static.md")
    html_files = list(iter_files(root, (".html", ".htm"), 30))
    if html_files and not out["frameworks"] and not out["languages"]:
        add("HTML/CSS/JS statique", "frontend-static.md")
    # serveurs & hébergement
    if list(iter_files(root, (".htaccess",), 5)) or list(root.glob("**/apache*.conf"))[:1]:
        add("Apache", "serveurs-hebergement.md", "servers")
    if list(root.glob("**/nginx*.conf"))[:1] or list(root.glob("**/*.nginx"))[:1] or (root / "nginx").exists():
        add("Nginx", "serveurs-hebergement.md", "servers")
    if (root / "Caddyfile").exists():
        add("Caddy", "serveurs-hebergement.md", "servers")
    if (root / "web.config").exists():
        add("IIS", "serveurs-hebergement.md", "servers")
    for f, name in (("vercel.json", "Vercel"), ("netlify.toml", "Netlify"), ("_headers", "Netlify/Cloudflare Pages"),
                    ("wrangler.toml", "Cloudflare"), ("Dockerfile", "Docker"), ("docker-compose.yml", "Docker Compose"),
                    ("compose.yaml", "Docker Compose"), ("firebase.json", "Firebase Hosting"), ("app.yaml", "Google App Engine"),
                    ("fly.toml", "Fly.io"), ("render.yaml", "Render"), ("Procfile", "Heroku-like")):
        if (root / f).exists():
            add(name, "serveurs-hebergement.md", "hosting")
    return _fin(out)


def _fin(out):
    out["refs"] = sorted(out["refs"] | {"serveurs-hebergement.md"})
    return out
