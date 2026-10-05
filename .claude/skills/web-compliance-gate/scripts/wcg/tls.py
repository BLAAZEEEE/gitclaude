"""Contrôles SSL/TLS : certificat, chaîne, protocoles, chiffrements, redirection, HSTS, CAA."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import socket
import ssl
import subprocess
import urllib.parse
from pathlib import Path

from .core import registrable
from .stack import iter_files

LOCAL_IDS = ["TLS-01", "TLS-02", "TLS-03", "TLS-04", "TLS-05", "TLS-06", "TLS-07", "TLS-08", "TLS-09", "TLS-10", "TLS-11", "TLS-12", "TLS-14"]


class OpenSSLMissing(Exception):
    pass


def _openssl(args, host, port, timeout=15, stdin=b""):
    """Sortie de openssl s_client ; None si la connexion a expiré ; OpenSSLMissing si l'outil est absent."""
    if not shutil.which("openssl"):
        raise OpenSSLMissing()
    try:
        p = subprocess.run(["openssl", "s_client", "-connect", f"{host}:{port}", "-servername", host, *args],
                           input=stdin, capture_output=True, timeout=timeout)
        return (p.stdout + p.stderr).decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return None


def _handshake(host, port, minv=None, maxv=None, ciphers=None, verify=True):
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if ciphers:
        ctx.set_ciphers(ciphers)
    if minv:
        ctx.minimum_version = minv
    if maxv:
        ctx.maximum_version = maxv
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            return s.version(), s.cipher(), s.getpeercert(), s.getpeercert(binary_form=True)


def _legacy_supported(host, port, version):
    """True = le serveur accepte, False = refuse, None = impossible à tester depuis cette machine."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        ctx.minimum_version = version
        ctx.maximum_version = version
    except (ValueError, ssl.SSLError):
        return None
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True
    except ssl.SSLError as e:
        msg = str(e).lower()
        if "no protocols available" in msg or "unsupported protocol" in msg and "alert" not in msg:
            return None
        return False
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
        return False          # le serveur coupe la poignée de main : protocole refusé
    except OSError:
        return None           # hôte injoignable / délai : impossible de conclure


def run(ctx):
    R = ctx.results
    target = ctx.prod_url or (ctx.base if ctx.base.startswith("https://") and not ctx.is_local else None)

    # ------------------------------------------------------------ mode local : vérification de la config versionnée
    def local_config():
        if not ctx.src:
            R.na("TLS-13", "Pas de code source fourni (--src)")
            return
        root = Path(ctx.src)
        redirect_pat = re.compile(
            r"(RewriteRule.*https://|return 301 https://|redirect.*https|SECURE_SSL_REDIRECT\s*=\s*True|UseHttpsRedirection|"
            r"requiresChannel|requires_secure|force_ssl|forceScheme\(['\"]https|URL::forceScheme|HTTPS_REDIRECT|"
            r"x-forwarded-proto.*https|redirect_https|\"forceHttps\"|https_only|RequireHttps)", re.I)
        hsts_pat = re.compile(r"(Strict-Transport-Security|SECURE_HSTS_SECONDS|UseHsts|helmet\(|hsts|HSTS)", re.I)
        found_r, found_h = [], []
        exts = (".htaccess", ".conf", ".js", ".mjs", ".cjs", ".ts", ".php", ".py", ".rb", ".cs", ".java", ".kt", ".go", ".rs",
                ".json", ".toml", ".yaml", ".yml", "Caddyfile", "_headers", "_redirects", ".config", ".env.example")
        for f in iter_files(root, exts, 4000):
            try:
                t = f.read_text(errors="replace")[:300_000]
            except Exception:  # noqa: BLE001
                continue
            if redirect_pat.search(t):
                found_r.append(str(f.relative_to(root)))
            if hsts_pat.search(t):
                found_h.append(str(f.relative_to(root)))
        if (root / "Caddyfile").exists():
            found_r.append("Caddyfile (HTTPS automatique)")
        hosted = {"vercel.json", "netlify.toml", "firebase.json", "wrangler.toml"} & {p.name for p in root.iterdir()}
        if hosted:
            found_r.append(f"{', '.join(hosted)} (HTTPS forcé par la plateforme)")
        details = [f"Redirection HTTPS : {', '.join(found_r[:5]) or 'introuvable'}", f"HSTS : {', '.join(found_h[:5]) or 'introuvable'}"]
        if found_r and found_h:
            R.ok("TLS-13", "Redirection HTTPS et HSTS prévus dans le dépôt", details)
        elif found_r or found_h:
            R.warn("TLS-13", "Configuration HTTPS partielle dans le dépôt", details,
                   note="Si la redirection/HSTS est gérée par l'hébergeur ou le reverse-proxy (Plesk, Cloudflare), le confirmer.")
        else:
            R.warn("TLS-13", "Aucune redirection HTTPS ni HSTS trouvée dans le dépôt", details,
                   note="Peut être géré hors dépôt (vhost Apache/Nginx, Plesk). À confirmer, puis tester en prod avec --prod-url.")

    R.guard(["TLS-13"], local_config)

    if not target:
        for fid in LOCAL_IDS:
            R.na(fid, "Site local en HTTP : test réel du certificat impossible", note="Relancer avec --prod-url https://domaine.fr pour l'audit SSL complet.")
        if "SEC-18" in R.items:
            s = R.items["SEC-18"]
            R.add("TLS-15", s.status if s.status != "fail" else "warn", s.evidence, s.details)
        else:
            R.na("TLS-15", "Non testable en local HTTP")
        return

    u = urllib.parse.urlsplit(target)
    host, port = u.hostname, u.port or 443

    # ------------------------------------------------------------ certificat
    def cert_checks():
        try:
            version, cipher, cert, der = _handshake(host, port)
            R.ok("TLS-01", f"Certificat reconnu ({version}, {cipher[0]})")
            R.ok("TLS-02", f"Nom {host} couvert")
        except ssl.SSLCertVerificationError as e:
            reason = getattr(e, "verify_message", str(e))
            if "hostname" in str(e).lower() or "match" in str(e).lower():
                R.ok("TLS-01", "Chaîne de confiance OK")
                R.ko("TLS-02", f"Le certificat ne couvre pas {host}", [reason])
            else:
                R.ko("TLS-01", f"Certificat non reconnu : {reason}", [str(e)[:300]])
                R.manual("TLS-02", "Vérification du nom impossible tant que la chaîne est invalide")
            version, cipher, cert, der = _handshake(host, port, verify=False)
            cert = {}
        pem = ssl.DER_cert_to_PEM_cert(der)
        text = ""
        if shutil.which("openssl"):
            p = subprocess.run(["openssl", "x509", "-noout", "-text"], input=pem.encode(), capture_output=True)
            text = p.stdout.decode("utf-8", "replace")
        # expiration
        not_after = cert.get("notAfter") if cert else None
        if not not_after:
            m = re.search(r"Not After\s*:\s*(.+)", text)
            not_after = m.group(1).strip() if m else None
        if not_after:
            exp = dt.datetime.strptime(not_after.replace("  ", " "), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)
            days = (exp - dt.datetime.now(dt.timezone.utc)).days
            ev = f"Expire le {exp:%d/%m/%Y} (dans {days} j)"
            if days < 7:
                R.ko("TLS-03", ev)
            elif days < 30:
                R.warn("TLS-03", ev, note="Vérifier que le renouvellement automatique fonctionne (certbot renew --dry-run).")
            else:
                R.ok("TLS-03", ev, note="Durée max des certificats : 200 j depuis mars 2026, 100 j en 2027, 47 j en 2029 → renouvellement automatique indispensable.")
        else:
            R.err("TLS-03", "Date d'expiration illisible")
        # SAN / www
        sans = [v for k, v in cert.get("subjectAltName", [])] if cert else re.findall(r"DNS:([^,\s]+)", text)
        base = host[4:] if host.startswith("www.") else host
        other = base if host.startswith("www.") else "www." + base

        def covered(name):
            return any(s == name or (s.startswith("*.") and name.endswith(s[1:]) and name.count(".") == s.count(".")) for s in sans)
        if "TLS-02" in R.items and R.items["TLS-02"].status == "pass":
            try:
                socket.getaddrinfo(other, 443)
                other_exists = True
            except OSError:
                other_exists = False
            if not other_exists or covered(other):
                R.ok("TLS-02", f"Noms couverts : {', '.join(sans[:6])}" + ("" if other_exists else f" ({other} ne résout pas)"))
            else:
                # la variante peut servir son propre certificat : on la teste avec son propre SNI
                try:
                    _handshake(other, port)
                    R.ok("TLS-02", f"{host} et {other} ont chacun un certificat valide")
                except ssl.SSLCertVerificationError as e:
                    R.ko("TLS-02", f"{other} résout mais présente un certificat invalide", [getattr(e, "verify_message", str(e))[:200]])
                except OSError:
                    R.warn("TLS-02", f"{other} résout mais ne répond pas en HTTPS", sans)
        # clé & signature
        if text:
            m = re.search(r"Public-Key:\s*\((\d+) bit\)", text)
            algo = re.search(r"Public Key Algorithm:\s*(\S+)", text)
            bits = int(m.group(1)) if m else 0
            a = (algo.group(1) if algo else "").lower()
            ok = (("rsa" in a and bits >= 2048) or ("ec" in a and bits >= 256) or "ed25519" in a)
            R.check("TLS-06", ok, f"{a} {bits} bits", f"Clé faible : {a} {bits} bits")
            sig = re.search(r"Signature Algorithm:\s*(\S+)", text)
            s = (sig.group(1) if sig else "").lower()
            R.check("TLS-07", not re.search(r"md5|sha1(?!\d)", s), f"Signature {s}", f"Signature faible : {s}")
        else:
            R.err("TLS-06", "openssl indisponible pour lire la clé", note="Installer openssl.")
            R.err("TLS-07", "openssl indisponible pour lire la signature", note="Installer openssl.")

    # ------------------------------------------------------------ chaîne & OCSP
    def chain_checks():
        try:
            out = _openssl(["-showcerts", "-status"], host, port)
        except OpenSSLMissing:
            R.err("TLS-09", "openssl non installé", note="Installer openssl (Git Bash/WSL sous Windows).")
            R.na("TLS-14", "openssl non installé")
            return
        if out is None:
            R.err("TLS-09", "Connexion openssl expirée")
            R.na("TLS-14", "Connexion expirée")
            return
        n = out.count("-----BEGIN CERTIFICATE-----")
        m = re.search(r"Verify return code:\s*(\d+)\s*\(([^)]*)\)", out)
        code = m.group(1) if m else "?"
        reason = m.group(2) if m else ""
        if code == "0":
            R.ok("TLS-09", f"{n} certificat(s) servi(s), chaîne vérifiée")
        elif n < 2 and re.search(r"unable to get local issuer|unable to verify the first", reason):
            R.ko("TLS-09", f"Certificat intermédiaire manquant ({reason})", note="Servir fullchain.pem au lieu de cert.pem.")
        else:
            R.warn("TLS-09", f"Vérification openssl : {code} {reason}")
        if "OCSP Response Status: successful" in out:
            R.ok("TLS-14", "OCSP stapling actif")
        else:
            R.na("TLS-14", "Pas d'OCSP stapling (informatif)")

    # ------------------------------------------------------------ protocoles & suites
    def proto_checks():
        legacy = {}
        for name, v in (("TLS 1.0", ssl.TLSVersion.TLSv1), ("TLS 1.1", ssl.TLSVersion.TLSv1_1)):
            res = _legacy_supported(host, port, v)
            if res is None:  # repli openssl
                flag = "-tls1" if name == "TLS 1.0" else "-tls1_1"
                try:
                    out = _openssl([flag, "-cipher", "ALL:@SECLEVEL=0"], host, port)
                except OpenSSLMissing:
                    out = None
                if out and "Cipher is (NONE)" not in out and re.search(r"Protocol\s*:\s*TLSv1(\.1)?\b", out):
                    res = True
                elif out and ("unknown option" in out or "wrong version" in out.lower() or "no protocols" in out.lower()):
                    res = None if "unknown option" in out else False
                elif out:
                    res = False
            legacy[name] = res
        on = [k for k, v in legacy.items() if v]
        unk = [k for k, v in legacy.items() if v is None]
        if on:
            R.ko("TLS-04", f"Protocoles obsolètes acceptés : {', '.join(on)}")
        elif unk:
            R.warn("TLS-04", f"Impossible de tester {', '.join(unk)} depuis cette machine (OpenSSL local trop récent)",
                   note="Contrôle croisé : https://www.ssllabs.com/ssltest/ ou testssl.sh.")
        else:
            R.ok("TLS-04", "TLS 1.0 et 1.1 refusés")
        try:
            v, *_ = _handshake(host, port, minv=ssl.TLSVersion.TLSv1_3, verify=False)
            R.ok("TLS-05", f"{v} négocié")
        except ssl.SSLError:
            R.ko("TLS-05", "TLS 1.3 non supporté")
        except OSError as e:
            R.err("TLS-05", f"Connexion impossible ({type(e).__name__})")
        weak = []
        for label, suite in (("RC4", "RC4"), ("3DES", "3DES"), ("NULL", "eNULL:NULL"), ("EXPORT", "EXP"), ("Anonymes", "aNULL"), ("DES", "DES")):
            try:
                ctx_ = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx_.check_hostname = False
                ctx_.verify_mode = ssl.CERT_NONE
                ctx_.maximum_version = ssl.TLSVersion.TLSv1_2
                ctx_.set_ciphers(suite + ":@SECLEVEL=0")
            except (ssl.SSLError, ValueError):
                continue  # suite absente de la lib locale : non testable ici
            try:
                with socket.create_connection((host, port), timeout=8) as sock:
                    with ctx_.wrap_socket(sock, server_hostname=host) as s:
                        weak.append(f"{label} ({s.cipher()[0]})")
            except Exception:  # noqa: BLE001
                pass
        # CBC en TLS 1.2 : acceptable (Mozilla Intermediate l'exclut, on le signale seulement)
        R.check("TLS-08", not weak, "Aucune suite faible acceptée (suites testables localement)", "Suites faibles acceptées", weak)

    # ------------------------------------------------------------ redirection & HSTS
    def redirect_checks():
        http_url = f"http://{host}/"
        r = ctx.http.get(http_url, follow=False, use_cache=False)
        loc = r.h("location")
        deep = ctx.http.get(f"http://{host}/wcg-test-redirect?x=1", follow=False, use_cache=False)
        if r.status in (301, 308) and loc.startswith("https://"):
            ok_deep = deep.status in (301, 308) and deep.h("location").startswith("https://") and "wcg-test-redirect" in deep.h("location")
            R.check("TLS-10", ok_deep, f"http:// → {r.status} {loc}", "La redirection ne conserve pas le chemin", [f"{deep.status} → {deep.h('location')}"], soft=True)
        elif r.status in (302, 307) and loc.startswith("https://"):
            R.warn("TLS-10", f"Redirection temporaire ({r.status}) vers HTTPS : utiliser 301/308")
        elif r.status == 0:
            R.warn("TLS-10", f"Port 80 injoignable ({r.error[:80]})", note="Si le port 80 est fermé volontairement, HSTS preload est nécessaire.")
        else:
            R.ko("TLS-10", f"http:// ne redirige pas vers HTTPS (statut {r.status})")
        hr = ctx.http.get(target)
        hsts = hr.h("strict-transport-security")
        m = re.search(r"max-age=(\d+)", hsts)
        age = int(m.group(1)) if m else 0
        probs = []
        if not hsts:
            R.ko("TLS-11", "En-tête Strict-Transport-Security absent")
        else:
            if age < 31536000:
                probs.append(f"max-age={age} (< 31536000)")
            if "includesubdomains" not in hsts.lower():
                probs.append("includeSubDomains absent")
            R.check("TLS-11", not probs, f"HSTS: {hsts}", f"HSTS incomplet : {hsts}", probs, soft=age >= 15552000)

    # ------------------------------------------------------------ CAA
    def caa_checks():
        dom = registrable(host)
        records = []
        for name in dict.fromkeys([host, dom]):
            if shutil.which("dig"):
                out = subprocess.run(["dig", "+short", "CAA", name], capture_output=True, timeout=10).stdout.decode()
                records += [l for l in out.splitlines() if l.strip()]
            else:
                r = ctx.http.get(f"https://dns.google/resolve?name={name}&type=CAA", use_cache=False)
                try:
                    records += [a["data"] for a in json.loads(r.text).get("Answer", []) if a.get("type") == 257]
                except Exception:  # noqa: BLE001
                    pass
            if records:
                break
        R.check("TLS-12", bool(records), f"CAA : {', '.join(records[:3])}", f"Aucun enregistrement CAA pour {dom}", soft=True)

    R.guard(["TLS-01", "TLS-02", "TLS-03", "TLS-06", "TLS-07"], cert_checks)
    R.guard(["TLS-09", "TLS-14"], chain_checks)
    R.guard(["TLS-04", "TLS-05", "TLS-08"], proto_checks)
    R.guard(["TLS-10", "TLS-11"], redirect_checks)
    R.guard(["TLS-12"], caa_checks)
    s = R.items.get("SEC-18")
    if s:
        R.add("TLS-15", s.status, s.evidence, s.details)
    else:
        R.na("TLS-15", "Voir SEC-18")
