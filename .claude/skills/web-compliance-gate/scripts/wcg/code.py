"""Analyse statique du dépôt (toutes stacks) + audit des dépendances + outils SAST/secrets optionnels."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .stack import iter_files

CODE_EXT = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".php", ".py", ".rb", ".java", ".kt", ".cs",
            ".go", ".rs", ".ex", ".exs", ".twig", ".blade.php", ".erb", ".html", ".htm", ".cshtml", ".razor", ".jsp", ".scala", ".dart", ".lua")
CONF_EXT = (".env", ".json", ".yml", ".yaml", ".toml", ".ini", ".conf", ".config", ".xml", ".properties", ".htaccess", ".cfg", ".neon")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|fixtures?|mocks?|examples?|docs?|stories|e2e|cypress|playwright)(/|$)|\.(test|spec|stories)\.", re.I)

SECRET_PATTERNS = [
    ("Clé AWS", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("Clé privée", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    ("Stripe live", r"\b(sk|rk)_live_[0-9a-zA-Z]{20,}"),
    ("GitHub token", r"\b(ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{36}\b|github_pat_[0-9A-Za-z_]{60,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    ("Slack token", r"\bxox[baprs]-[0-9A-Za-z-]{10,}"),
    ("SendGrid", r"\bSG\.[0-9A-Za-z_-]{22}\.[0-9A-Za-z_-]{43}\b"),
    ("Twilio", r"\bSK[0-9a-fA-F]{32}\b"),
    ("Mailgun", r"\bkey-[0-9a-zA-Z]{32}\b"),
    ("OpenAI/Anthropic", r"\bsk-(proj-|ant-)?[A-Za-z0-9_-]{32,}"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("Identifiants BDD en dur", r"(mysqli?_connect|mysqli)\s*\(\s*['\"][^'\"]*['\"]\s*,\s*['\"][^'\"]*['\"]\s*,\s*['\"][^'\"]{4,}['\"]|new\s+PDO\s*\([^,]+,\s*['\"][^'\"]*['\"]\s*,\s*['\"][^'\"]{4,}['\"]"),
    ("URL avec identifiants", r"\b(mysql|postgres(ql)?|mongodb(\+srv)?|redis|amqp|ftp|smtp)://[^:\s'\"/]+:[^@\s'\"]{3,}@"),
    ("Mot de passe/secret en dur", r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key|db_pass(word)?)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
]
PLACEHOLDER = re.compile(r"(?i)(changeme|change_me|your[_-]|example|exemple|dummy|placeholder|xxx+|\*\*\*|<.*>|\$\{|process\.env|env\(|getenv|os\.environ|config\(|settings\.|test|fake|lorem|password123|secret_key_here|%s|\{\{)")

SQL_PATTERNS = [
    r"(query|execute|exec|raw|prepare|whereRaw|selectRaw|DB::select|DB::statement|executeQuery|executeUpdate|createQuery|Query|QueryRow|Exec|find_by_sql|RawSQL|FromSqlRaw|ExecuteSqlRaw)\s*\(\s*[`'\"f]?[^)]{0,80}\b(SELECT|INSERT|UPDATE|DELETE|WHERE|ORDER BY)\b[^)]{0,200}(\$\{|\"\s*\+\s*\w|'\s*\+\s*\w|\+\s*req\.|\{\w+\}|%s['\"]\s*%|\.format\(|\$_(GET|POST|REQUEST|COOKIE)|#\{|\$\w+)",
    r"\b(mysqli_query|mysql_query|pg_query|->query|->exec)\s*\([^;]*\$_(GET|POST|REQUEST|COOKIE)",
    r"\b(mysqli_query|pg_query|->query)\s*\(\s*\"[^\"]*(SELECT|INSERT|UPDATE|DELETE)[^\"]*\$\w+",
    r"cursor\.execute\(\s*f['\"]|cursor\.execute\([^,)]*%\s*\(|cursor\.execute\([^,)]*\.format\(",
    r"(fmt\.Sprintf)\(\s*\"[^\"]*(SELECT|INSERT|UPDATE|DELETE)",
    r"\$\"(SELECT|INSERT|UPDATE|DELETE)[^\"]*\{",
]
XSS_PATTERNS = [
    r"\.innerHTML\s*[+]?=(?!\s*['\"`]\s*['\"`]?\s*;?$)", r"\.outerHTML\s*=", r"insertAdjacentHTML\(", r"document\.write(ln)?\(",
    r"dangerouslySetInnerHTML", r"\bv-html\s*=", r"\{!!.*!!\}", r"\|\s*safe\b", r"mark_safe\(", r"\.html_safe\b", r"\braw\(",
    r"\[innerHTML\]\s*=", r"bypassSecurityTrust", r"@html\s", r"Html\.Raw\(", r"\{\{\{.*\}\}\}", r"<%-", r"\|\s*raw\b",
    r"echo\s+\$_(GET|POST|REQUEST|COOKIE)", r"print\s+\$_(GET|POST|REQUEST)",
]
EVAL_PATTERNS = [
    r"(?<![\w.])eval\s*\(", r"new\s+Function\s*\(", r"setTimeout\(\s*['\"]", r"setInterval\(\s*['\"]",
    r"\b(shell_exec|system|passthru|proc_open|popen)\s*\(\s*[^)]*\$", r"\bexec\s*\(\s*[^)]*\$_(GET|POST|REQUEST)",
    r"subprocess\.\w+\([^)]*shell\s*=\s*True", r"os\.system\(", r"child_process.*exec\(\s*[`'\"][^`'\"]*\$\{", r"execSync\(\s*`[^`]*\$\{",
    r"Runtime\.getRuntime\(\)\.exec\(", r"pickle\.loads?\(", r"yaml\.load\((?![^)]*SafeLoader)", r"unserialize\(\s*\$_",
]
WEAK_HASH = [
    r"(?i)(md5|sha1)\s*\(\s*\$?\w*(pass|pwd|mdp|motdepasse)", r"(?i)hashlib\.(md5|sha1|sha256)\([^)]*(pass|pwd)",
    r"(?i)createHash\(\s*['\"](md5|sha1|sha256)['\"]\)[^;]{0,80}(pass|pwd)", r"(?i)(pass|pwd|password)\w*\s*=\s*(md5|sha1)\(",
    r"(?i)MessageDigest\.getInstance\(\s*\"(MD5|SHA-?1)\"", r"(?i)(pass|pwd)\w*\s*=\s*base64",
]
GOOD_HASH = re.compile(r"(password_hash|password_verify|bcrypt|argon2|scrypt|pbkdf2|Hash::make|make_password|check_password|has_secure_password|BCryptPasswordEncoder|PasswordHasher|passlib|werkzeug\.security|generate_password_hash|IdentityUser|devise)", re.I)
TLS_OFF = [r"rejectUnauthorized\s*:\s*false", r"NODE_TLS_REJECT_UNAUTHORIZED['\"]?\s*[\]=:]\s*['\"]?0", r"verify\s*=\s*False",
           r"CURLOPT_SSL_VERIFY(PEER|HOST)\s*,\s*(false|0)", r"InsecureSkipVerify\s*:\s*true", r"ServerCertificateValidationCallback\s*=.*true",
           r"strictSSL\s*:\s*false", r"danger_accept_invalid_certs\(true\)", r"'verify'\s*=>\s*false", r"ssl_verify\s*=\s*false"]
CORS_ANY = [r"Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*", r"origin\s*:\s*['\"]\*['\"]", r"cors\(\s*\)", r"allow_origins\s*=\s*\[\s*['\"]\*",
            r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True", r"CORS_ORIGIN_ALLOW_ALL\s*=\s*True", r"AllowAnyOrigin\(\)", r"'allowed_origins'\s*=>\s*\[\s*'\*'",
            r"Header\s+(always\s+)?set\s+Access-Control-Allow-Origin\s+\"?\*", r"add_header\s+Access-Control-Allow-Origin\s+['\"]?\*"]
DEBUG_PATTERNS = [
    (r"^\s*APP_DEBUG\s*=\s*true", ".env*"), (r"^\s*DEBUG\s*=\s*True", "settings"), (r"app\.run\([^)]*debug\s*=\s*True", "py"),
    (r"display_errors\s*=\s*(On|1)", "ini"), (r"ini_set\(\s*['\"]display_errors['\"]\s*,\s*['\"]?(1|On|true)", "php"),
    (r"error_reporting\(\s*E_ALL\s*\)", "php"), (r"WP_DEBUG['\"]?\s*,\s*true", "php"), (r"config\.consider_all_requests_local\s*=\s*true", "rb"),
    (r"UseDeveloperExceptionPage\(\)", "cs"), (r"\"ASPNETCORE_ENVIRONMENT\"\s*:\s*\"Development\"", "json"),
    (r"^\s*APP_ENV\s*=\s*(local|dev)", ".env*"), (r"server\.error\.include-stacktrace\s*=\s*always", "properties"),
]
RATE_LIMIT = re.compile(r"(express-rate-limit|rate-limiter-flexible|@nestjs/throttler|express-slow-down|@fastify/rate-limit|hono-rate-limiter|"
                        r"throttle:|ThrottleRequests|RateLimiter::|->middleware\(['\"]throttle|symfony/rate-limiter|login_throttling|"
                        r"django-axes|django_ratelimit|ratelimit\(|slowapi|flask[_-]limiter|Limiter\(|rack-attack|Rack::Attack|bucket4j|"
                        r"AddRateLimiter|RateLimitPartition|limit_req|tollbooth|golang.org/x/time/rate|governor|tower_governor|actix-governor|"
                        r"upstash/ratelimit|@upstash/ratelimit|limiter|brute|fail2ban|Login attempts|max_attempts|MAX_LOGIN_ATTEMPTS)", re.I)
AUTH_HINT = re.compile(r"(login|signin|sign_in|authenticate|passport\.|next-auth|@auth/|lucia|devise|Auth::attempt|authenticate\(|jwt\.sign|bcrypt|password_verify|LoginView|check_password)", re.I)
ACCESS_MW = re.compile(r"(isAuthenticated|requireAuth|ensureAuth|authMiddleware|auth\(\)|->middleware\(['\"]auth|@login_required|login_required|IsAuthenticated|"
                       r"\[Authorize|@PreAuthorize|@Secured|authorize!|before_action\s*:authenticate|getServerSession|auth\(\)\s*;|withAuth|"
                       r"middleware\.(ts|js)|protect\(|verifyToken|requireUser|session\.user|Gate::|->can\(|@can|policy|Policy)", re.I)
UPLOAD = re.compile(r"(multer|formidable|busboy|move_uploaded_file|\$_FILES|UploadedFile|request\.FILES|FileField|IFormFile|MultipartFile|"
                    r"has_one_attached|@fastify/multipart|upload\.single|file_uploads)", re.I)
UPLOAD_VALID = re.compile(r"(fileFilter|mimetype|mimes:|mimetypes:|max:\d+|limits\s*:\s*\{|fileSize|getClientMimeType|finfo_file|mime_content_type|"
                          r"FileExtensionValidator|content_type|allowed_extensions|ALLOWED_EXTENSIONS|validate_file|ContentType|Length\s*>|"
                          r"file-type|magic\.from|imghdr|validates\s*:\w*,\s*(content_type|size))", re.I)
LOGGING = re.compile(r"(winston|pino|bunyan|morgan|log4j|logback|slf4j|monolog|Log::(warning|error|info)|logging\.getLogger|structlog|"
                     r"ILogger|Serilog|NLog|zap\.|logrus|zerolog|tracing::|Rails\.logger|logger\.(warn|error|info)|console\.error|error_log\()", re.I)
PWD_MIN = re.compile(r"(?is)(password|mot.?de.?passe|mdp|passwd)[^\n]{0,120}?(min(imum)?[_ -]?(length|len|size)?|minlength|min:|\.min\(|Length\(min\s*=|MinimumLength|RequiredLength|\{)\s*[:=(]?\s*['\"]?(\d{1,2})")


def _lines(text, pattern, flags=0, limit=30):
    out = []
    rx = re.compile(pattern, flags | re.M)
    for m in rx.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        line = text.splitlines()[ln - 1].strip() if text else ""
        out.append((ln, line[:160]))
        if len(out) >= limit:
            break
    return out


def _run(cmd, cwd, timeout=240):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, shell=os.name == "nt")
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except FileNotFoundError:
        return None, "", "introuvable"
    except subprocess.TimeoutExpired:
        return None, "", "timeout"


def run(ctx):
    R = ctx.results
    ids = [k for k in ("SEC-C01", "SEC-C02", "SEC-C03", "SEC-C04", "SEC-C05", "SEC-C06", "SEC-C07", "SEC-C08", "SEC-C09",
                       "SEC-C10", "SEC-C11", "SEC-C12", "SEC-C13", "SEC-C14", "SEC-C15", "SEC-C16", "SEC-C17", "SEC-C18")]
    if not ctx.src:
        for fid in ids:
            R.na(fid, "Pas de code source fourni (--src)", note="Audit boîte noire : ajouter --src pour l'analyse du code.")
        return
    root = Path(ctx.src)
    files = list(iter_files(root, CODE_EXT + CONF_EXT + (".env",), 12000))
    env_files = [p for p in root.rglob(".env*") if "node_modules" not in p.parts and "vendor" not in p.parts and p.is_file()]
    files += [p for p in env_files if p not in files]
    hits = {k: [] for k in ("secret", "sql", "xss", "eval", "weak", "tls", "cors", "debug")}
    good_hash = auth = ratelimit = access = upload = upload_valid = logging_ = False
    pwd_mins = []
    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        try:
            if f.stat().st_size > 1_500_000:
                continue
            text = f.read_text(errors="replace")
        except Exception:  # noqa: BLE001
            continue
        is_test = bool(TEST_PATH.search(rel))
        is_min = f.name.endswith((".min.js", ".min.css", ".bundle.js")) or (len(text) > 5000 and text.count("\n") < 5)
        if is_min:
            continue
        is_example = re.search(r"\.(example|sample|dist|template)$|example", f.name, re.I)
        # secrets
        if not is_example:
            for label, pat in SECRET_PATTERNS:
                for ln, line in _lines(text, pat):
                    if label == "Mot de passe/secret en dur" and PLACEHOLDER.search(line):
                        continue
                    if is_test and label in ("JWT", "Mot de passe/secret en dur"):
                        continue
                    hits["secret"].append(f"{rel}:{ln} [{label}] {line[:90]}")
        if f.name.startswith(".env") and not is_example:
            for ln, line in _lines(text, r"^\s*[A-Z0-9_]*(SECRET|PASSWORD|PASS|KEY|TOKEN)[A-Z0-9_]*\s*=\s*\S{6,}"):
                ctx.env_secrets = getattr(ctx, "env_secrets", []) + [f"{rel}:{ln}"]
        if is_test:
            continue
        for pat in SQL_PATTERNS:
            for ln, line in _lines(text, pat, re.I):
                hits["sql"].append(f"{rel}:{ln} {line}")
        for pat in XSS_PATTERNS:
            for ln, line in _lines(text, pat):
                hits["xss"].append(f"{rel}:{ln} {line}")
        for pat in EVAL_PATTERNS:
            for ln, line in _lines(text, pat):
                if "eval" in pat and re.search(r"\.eval\(|evaluate\(|page\.eval", line):
                    continue
                hits["eval"].append(f"{rel}:{ln} {line}")
        for pat in WEAK_HASH:
            for ln, line in _lines(text, pat):
                hits["weak"].append(f"{rel}:{ln} {line}")
        for pat in TLS_OFF:
            for ln, line in _lines(text, pat):
                hits["tls"].append(f"{rel}:{ln} {line}")
        for pat in CORS_ANY:
            for ln, line in _lines(text, pat, re.I):
                hits["cors"].append(f"{rel}:{ln} {line}")
        for pat, scope in DEBUG_PATTERNS:
            if scope == ".env*" and not f.name.startswith(".env"):
                continue
            if scope == ".env*" and re.search(r"(example|sample|local|development|dev|test)", f.name, re.I):
                continue
            for ln, line in _lines(text, pat, re.I):
                hits["debug"].append(f"{rel}:{ln} {line}")
        good_hash |= bool(GOOD_HASH.search(text))
        auth |= bool(AUTH_HINT.search(text))
        ratelimit |= bool(RATE_LIMIT.search(text))
        access |= bool(ACCESS_MW.search(text))
        upload |= bool(UPLOAD.search(text))
        upload_valid |= bool(UPLOAD_VALID.search(text))
        logging_ |= bool(LOGGING.search(text))
        for m in PWD_MIN.finditer(text[:300_000]):
            n = int(m.group(5))
            if 4 <= n <= 64:
                pwd_mins.append((n, f"{rel}:{text.count(chr(10), 0, m.start()) + 1}"))
    # html statiques / pages : minlength sur input password
    for p in ctx.pages:
        for form in p.doc.forms:
            for i in form["_inputs"]:
                if (i.get("type") or "").lower() == "password" and i.get("minlength", "").isdigit():
                    pwd_mins.append((int(i["minlength"]), f"{p.url} minlength"))

    uniq = lambda l: list(dict.fromkeys(l))  # noqa: E731
    seen_loc, dedup = set(), []
    for h in hits["secret"]:
        loc = h.split(" ", 1)[0]
        if loc not in seen_loc:
            seen_loc.add(loc)
            dedup.append(h)
    hits["secret"] = dedup
    R.check("SEC-C01", not hits["secret"], f"{len(files)} fichiers analysés, aucun secret en dur", f"{len(uniq(hits['secret']))} secret(s) potentiel(s)", uniq(hits["secret"]))
    # .env versionné ?
    gi = (root / ".gitignore").read_text(errors="replace") if (root / ".gitignore").exists() else ""
    tracked = []
    if (root / ".git").exists() and shutil.which("git"):
        code, out, _ = _run(["git", "ls-files"], str(root))
        if code == 0:
            tracked = [l for l in out.splitlines() if re.search(r"(^|/)\.env(\.|$)", l) and not re.search(r"example|sample|dist|template", l, re.I)]
    ignored = bool(re.search(r"^\s*/?\.env", gi, re.M))
    if tracked:
        R.ko("SEC-C02", ".env versionné dans git", tracked)
    elif env_files and not ignored:
        R.ko("SEC-C02", ".env présent mais non ignoré par .gitignore", [str(p.relative_to(root)) for p in env_files])
    elif env_files or ignored:
        R.ok("SEC-C02", ".env ignoré par git")
    else:
        R.na("SEC-C02", "Aucun fichier .env")
    R.check("SEC-C03", not hits["debug"], "Pas de mode debug trouvé", "Mode debug/dev dans la config", uniq(hits["debug"]),
            note="Vérifier que ces valeurs ne sont pas celles de la prod (fichier d'environnement de prod séparé).")
    R.check("SEC-C04", not hits["sql"], "Aucune concaténation SQL détectée", f"{len(uniq(hits['sql']))} requête(s) SQL construite(s) par concaténation", uniq(hits["sql"]))
    R.check("SEC-C05", not hits["xss"], "Aucun sink HTML non échappé", f"{len(uniq(hits['xss']))} insertion(s) HTML à vérifier", uniq(hits["xss"]), soft=True)
    R.check("SEC-C06", not hits["eval"], "Aucune évaluation dynamique", f"{len(uniq(hits['eval']))} appel(s) dangereux", uniq(hits["eval"]), soft=True)
    if hits["weak"]:
        R.ko("SEC-C07", "Hachage faible de mots de passe", uniq(hits["weak"]))
    elif good_hash:
        R.ok("SEC-C07", "Algorithme de hachage adapté détecté (bcrypt/argon2/…)")
    elif auth:
        R.warn("SEC-C07", "Authentification détectée mais aucun algorithme de hachage reconnu", note="Vérifier manuellement le stockage des mots de passe.")
    else:
        R.na("SEC-C07", "Pas d'authentification détectée")
    R.check("SEC-C08", not hits["tls"], "Vérification TLS jamais désactivée", "Vérification TLS désactivée", uniq(hits["tls"]))
    R.check("SEC-C09", not hits["cors"], "CORS non ouvert à *", "CORS ouvert à *", uniq(hits["cors"]), soft=True)
    lock_needed = {"package.json": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock"),
                   "composer.json": ("composer.lock",), "Pipfile": ("Pipfile.lock",), "pyproject.toml": ("poetry.lock", "uv.lock", "pdm.lock", "requirements.txt"),
                   "Gemfile": ("Gemfile.lock",), "Cargo.toml": ("Cargo.lock",), "go.mod": ("go.sum",)}
    missing_locks = [f"{m} sans {' / '.join(locks)}" for m, locks in lock_needed.items() if (root / m).exists() and not any((root / l).exists() for l in locks)]
    if any((root / m).exists() for m in lock_needed):
        R.check("SEC-C11", not missing_locks, "Fichiers de verrouillage présents", "Lockfile manquant", missing_locks)
    else:
        R.na("SEC-C11", "Aucun gestionnaire de dépendances détecté")
    if auth:
        R.check("SEC-C12", ratelimit, "Limitation de débit détectée", "Authentification sans rate limiting détecté",
                note="Si géré par le reverse-proxy/WAF (fail2ban, Cloudflare), le confirmer.")
        weak = [f"{loc} : min {n}" for n, loc in pwd_mins if n < 12]
        if weak:
            R.ko("SEC-C13", "Longueur minimale de mot de passe < 12", weak)
        elif pwd_mins:
            R.ok("SEC-C13", f"Longueur minimale ≥ 12 ({', '.join(str(n) for n, _ in pwd_mins[:3])})")
        else:
            R.manual("SEC-C13", "Règle de longueur minimale introuvable", note="Vérifier : ≥ 12 caractères avec 4 types (ou ≥ 14 sans spéciaux) — recommandation CNIL 2022.")
        if access:
            R.manual("SEC-C17", "Contrôle d'accès présent — revue route par route requise",
                     note="Pour chaque route protégée : authentification + vérification que la ressource appartient à l'utilisateur (IDOR) + rôle.")
        else:
            R.ko("SEC-C17", "Authentification détectée mais aucun contrôle d'accès identifié")
    else:
        R.na("SEC-C12", "Pas d'authentification détectée")
        R.na("SEC-C13", "Pas d'authentification détectée")
        R.na("SEC-C17", "Pas de zone protégée détectée")
    if upload:
        R.check("SEC-C14", upload_valid, "Upload avec validation détectée", "Upload sans validation type/taille détectée", soft=True,
                note="Vérifier aussi le stockage hors webroot et le renommage des fichiers.")
    else:
        R.na("SEC-C14", "Pas d'upload de fichiers détecté")
    if auth:
        R.check("SEC-C18", logging_, "Bibliothèque de journalisation présente", "Aucune journalisation détectée", soft=True,
                note="Vérifier que connexions, échecs et actions admin sont journalisés sans données sensibles.")
    else:
        R.check("SEC-C18", logging_, "Journalisation présente", "Aucune journalisation détectée", soft=True)
    R.guard(["SEC-C10"], _deps, ctx, root)
    R.guard(["SEC-C15"], _semgrep, ctx, root)
    R.guard(["SEC-C16"], _gitleaks, ctx, root)


def _deps(ctx, root):
    R = ctx.results
    ran, crit, high, other, errors = [], [], [], [], []
    has = lambda f: (root / f).exists()  # noqa: E731
    if has("package.json"):
        if has("pnpm-lock.yaml") and shutil.which("pnpm"):
            cmd = ["pnpm", "audit", "--json", "--prod"]
        elif has("yarn.lock") and shutil.which("yarn"):
            cmd = ["yarn", "npm", "audit", "--json", "--environment", "production"] if has(".yarnrc.yml") else ["yarn", "audit", "--json", "--groups", "dependencies"]
        elif shutil.which("npm") and (has("package-lock.json") or has("npm-shrinkwrap.json")):
            cmd = ["npm", "audit", "--json", "--omit=dev"]
        elif shutil.which("npm"):
            # pas de lockfile : on en génère un dans un dossier temporaire (le dépôt n'est pas modifié)
            import tempfile
            tmp = tempfile.mkdtemp(prefix="wcg-npm-")
            shutil.copy(root / "package.json", tmp)
            _run(["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--silent"], tmp, 300)
            cmd = ["npm", "audit", "--json", "--omit=dev"] if (Path(tmp) / "package-lock.json").exists() else None
            npm_cwd = tmp
            if not cmd:
                errors.append("npm : impossible de résoudre les dépendances (npm install --package-lock-only a échoué)")
        else:
            cmd = None
            errors.append("npm non installé")
        if cmd:
            code, out, err = _run(cmd, locals().get("npm_cwd") or str(root))
            ran.append(" ".join(cmd[:2]))
            try:
                data = json.loads(out) if out.strip().startswith("{") else {}
                meta = data.get("metadata", {}).get("vulnerabilities", {})
                if meta:
                    for sev, lst in (("critical", crit), ("high", high)):
                        if meta.get(sev):
                            lst.append(f"npm : {meta[sev]} {sev}")
                    if meta.get("moderate"):
                        other.append(f"npm : {meta['moderate']} moderate")
                    for name, v in list(data.get("vulnerabilities", {}).items())[:25]:
                        if v.get("severity") in ("critical", "high"):
                            (crit if v["severity"] == "critical" else high).append(f"  · {name} ({v['severity']}) {v.get('range', '')} fix: {'oui' if v.get('fixAvailable') else 'non'}")
                else:
                    for line in out.splitlines():  # yarn v1 ndjson
                        if '"auditSummary"' in line:
                            s = json.loads(line)["data"]["vulnerabilities"]
                            if s.get("critical"):
                                crit.append(f"yarn : {s['critical']} critical")
                            if s.get("high"):
                                high.append(f"yarn : {s['high']} high")
            except Exception as e:  # noqa: BLE001
                errors.append(f"npm audit illisible : {e}")
    if has("composer.lock"):
        if shutil.which("composer"):
            code, out, err = _run(["composer", "audit", "--format=json", "--locked", "--no-dev"], str(root))
            ran.append("composer audit")
            try:
                data = json.loads(out)
                for pkg, advs in (data.get("advisories") or {}).items():
                    for a in advs:
                        sev = (a.get("severity") or "high").lower()
                        (crit if sev == "critical" else high if sev == "high" else other).append(f"composer : {pkg} — {a.get('title', '')[:80]} ({sev})")
            except Exception as e:  # noqa: BLE001
                errors.append(f"composer audit illisible : {e}")
        else:
            errors.append("composer non installé")
    if has("requirements.txt") or has("poetry.lock") or has("Pipfile.lock") or has("pyproject.toml"):
        tool = shutil.which("pip-audit")
        if tool:
            args = ["pip-audit", "-f", "json", "--progress-spinner", "off"] + (["-r", "requirements.txt"] if has("requirements.txt") else [])
            code, out, err = _run(args, str(root), 400)
            ran.append("pip-audit")
            try:
                data = json.loads(out)
                deps = data.get("dependencies", data) if isinstance(data, dict) else data
                for d in deps:
                    for v in d.get("vulns", []):
                        high.append(f"pip : {d['name']} {d.get('version', '')} — {v.get('id')} (fix {', '.join(v.get('fix_versions', [])) or '?'})")
            except Exception as e:  # noqa: BLE001
                errors.append(f"pip-audit illisible : {e}")
        else:
            errors.append("pip-audit non installé (pipx install pip-audit)")
    if has("Gemfile.lock"):
        if shutil.which("bundle-audit"):
            code, out, err = _run(["bundle-audit", "check", "--update"], str(root), 400)
            ran.append("bundle-audit")
            if code not in (0, None):
                high += [f"ruby : {l}" for l in out.splitlines() if l.startswith(("Name:", "Criticality:", "Title:"))][:30]
        else:
            errors.append("bundler-audit non installé (gem install bundler-audit)")
    if has("go.mod"):
        if shutil.which("govulncheck"):
            code, out, err = _run(["govulncheck", "./..."], str(root), 400)
            ran.append("govulncheck")
            if code == 3 or "Vulnerability #" in out:
                high += [f"go : {l.strip()}" for l in out.splitlines() if l.startswith("Vulnerability #")][:30]
        else:
            errors.append("govulncheck non installé (go install golang.org/x/vuln/cmd/govulncheck@latest)")
    if has("Cargo.lock"):
        if shutil.which("cargo-audit") or shutil.which("cargo"):
            code, out, err = _run(["cargo", "audit", "--json"], str(root), 400)
            if code is not None and out.strip().startswith("{"):
                ran.append("cargo audit")
                data = json.loads(out)
                for v in data.get("vulnerabilities", {}).get("list", []):
                    high.append(f"rust : {v['package']['name']} — {v['advisory']['id']}")
            else:
                errors.append("cargo-audit non installé (cargo install cargo-audit)")
    if list(root.glob("**/*.csproj"))[:1]:
        if shutil.which("dotnet"):
            code, out, err = _run(["dotnet", "list", "package", "--vulnerable", "--include-transitive"], str(root), 400)
            ran.append("dotnet list package --vulnerable")
            for l in out.splitlines():
                if re.search(r"\b(Critical|High)\b", l):
                    (crit if "Critical" in l else high).append(f".NET : {l.strip()[:120]}")
        else:
            errors.append("dotnet SDK non installé")
    if has("pom.xml") or has("build.gradle") or has("build.gradle.kts"):
        errors.append("JVM : lancer OWASP dependency-check (mvn org.owasp:dependency-check-maven:check) ou Snyk/Trivy")
    if not ran and not errors:
        R.na("SEC-C10", "Aucun manifeste de dépendances")
        return
    if crit or high:
        R.ko("SEC-C10", f"Vulnérabilités connues ({', '.join(ran)})", crit + high + other, note="; ".join(errors))
    elif not ran:
        R.err("SEC-C10", "Aucun outil d'audit disponible", note="; ".join(errors))
    elif errors:
        R.warn("SEC-C10", f"Aucune vulnérabilité haute ({', '.join(ran)}) mais audit partiel", other, note="; ".join(errors))
    else:
        R.check("SEC-C10", True, f"Aucune vulnérabilité critique/haute ({', '.join(ran)})", details=other)


def _semgrep(ctx, root):
    R = ctx.results
    if not shutil.which("semgrep"):
        R.err("SEC-C15", "Semgrep non installé", note="pipx install semgrep (ou pip install semgrep), puis relancer l'audit.")
        return
    configs = [c for c in os.environ.get("WCG_SEMGREP_CONFIG", "p/owasp-top-ten,p/secrets").split(",") if c]
    args = ["semgrep", "scan", "--json", "--quiet", "--metrics", "off"]
    for c in configs:
        args += ["--config", c]
    for ex in ("node_modules", "vendor", "dist", "build", ".next", "wcg-report"):
        args += ["--exclude", ex]
    code, out, err = _run(args, str(root), 900)
    try:
        data = json.loads(out)
    except Exception:  # noqa: BLE001
        lines = [l for l in (err + "\n" + out).splitlines() if l.strip()]
        why = next((l for l in reversed(lines) if re.search(r"error|Error|refused|Forbidden|timed out|failed", l)), lines[-1] if lines else f"code retour {code}")
        R.err("SEC-C15", f"Semgrep n'a pas pu s'exécuter : {why.strip()[:160]}",
              note="Les règles p/owasp-top-ten et p/secrets sont téléchargées depuis semgrep.dev : vérifier l'accès réseau.")
        return
    res = data.get("results", [])
    errs = [r for r in res if r.get("extra", {}).get("severity") == "ERROR"]
    det = [f"{r['path']}:{r['start']['line']} [{r['extra'].get('severity')}] {r['check_id'].split('.')[-1]} — {r['extra'].get('message', '')[:100]}" for r in res]
    if errs:
        R.ko("SEC-C15", f"{len(errs)} alerte(s) ERROR, {len(res)} au total", det)
    elif res:
        R.warn("SEC-C15", f"{len(res)} alerte(s) WARNING/INFO", det)
    else:
        R.ok("SEC-C15", "Semgrep (OWASP Top 10 + secrets) : aucune alerte")


def _gitleaks(ctx, root):
    R = ctx.results
    if not (root / ".git").exists():
        R.na("SEC-C16", "Pas de dépôt git")
        return
    if not shutil.which("gitleaks"):
        R.err("SEC-C16", "Gitleaks non installé", note="https://github.com/gitleaks/gitleaks (brew install gitleaks / binaire release / docker).")
        return
    rpt = Path(ctx.out_dir) / "gitleaks.json"
    code, out, err = _run(["gitleaks", "detect", "--no-banner", "--redact", "-f", "json", "-r", str(rpt), "-s", str(root)], str(root), 600)
    try:
        leaks = json.loads(rpt.read_text()) if rpt.exists() else []
    except Exception:  # noqa: BLE001
        leaks = []
    if leaks:
        R.ko("SEC-C16", f"{len(leaks)} secret(s) dans l'historique git", [f"{l.get('File')}:{l.get('StartLine')} {l.get('RuleID')} (commit {str(l.get('Commit'))[:8]})" for l in leaks])
    elif code == 0:
        R.ok("SEC-C16", "Historique git sans secret")
    else:
        R.err("SEC-C16", f"Gitleaks a échoué ({err[:120]})")
