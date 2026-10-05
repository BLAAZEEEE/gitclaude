"""Scores, verdict de la gate et rapports (JSON, Markdown, HTML autonome)."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .catalog import CATEGORIES, SEVERITY_WEIGHT

CREDIT = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
SEV_ORDER = ["critical", "high", "medium", "low", "info"]
STATUS_FR = {"pass": "OK", "fail": "KO", "warn": "À améliorer", "manual": "À vérifier", "na": "N/A", "error": "Non exécuté"}


def score(findings, cats, threshold, tls_untested=False):
    by_cat = {}
    for cat in cats:
        items = [f for f in findings if f["category"] == cat]
        num = den = 0.0
        crit_fail = False
        for f in items:
            w = SEVERITY_WEIGHT[f["severity"]]
            if f["status"] in CREDIT and w:
                num += w * CREDIT[f["status"]]
                den += w
            if f["status"] == "fail" and f["severity"] == "critical":
                crit_fail = True
        s = round(100 * num / den) if den else None
        if s is not None and crit_fail:
            s = min(s, 40)
        if cat == "tls" and tls_untested:
            s = None   # certificat/protocoles non testables en local : pas de note trompeuse
        counts = {st: sum(1 for f in items if f["status"] == st) for st in STATUS_FR}
        by_cat[cat] = {"label": CATEGORIES[cat], "score": s, "grade": grade(s), "counts": counts, "total": len(items)}
    scored = [v["score"] for v in by_cat.values() if v["score"] is not None]
    glob = round(sum(scored) / len(scored)) if scored else None
    blocking = [f for f in findings if f["status"] == "fail" and f["severity"] in ("critical", "high")]
    errors = [f for f in findings if f["status"] == "error"]
    pending = [f for f in findings if f["status"] == "manual"]
    low_cats = [v["label"] for v in by_cat.values() if v["score"] is not None and v["score"] < threshold]
    if blocking:
        verdict = "BLOQUÉ"
    elif errors:
        verdict = "INCOMPLET"
    elif low_cats or any(f["status"] == "fail" for f in findings):
        verdict = "À AMÉLIORER"
    elif pending:
        verdict = "VALIDÉ SOUS RÉSERVE"
    else:
        verdict = "VALIDÉ"
    return {"categories": by_cat, "global": glob, "grade": grade(glob), "verdict": verdict, "threshold": threshold,
            "blocking": len(blocking), "errors": len(errors), "pending": len(pending), "low_categories": low_cats}


def grade(s):
    if s is None:
        return "-"
    return "A" if s >= 90 else "B" if s >= 80 else "C" if s >= 65 else "D" if s >= 50 else "E"


def sort_key(f):
    st = {"fail": 0, "error": 1, "warn": 2, "manual": 3, "pass": 4, "na": 5}[f["status"]]
    return (st, SEV_ORDER.index(f["severity"]), f["id"])


def write_all(out_dir: Path, meta: dict, findings: list, summary: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"meta": meta, "summary": summary, "findings": sorted(findings, key=sort_key)}
    (out_dir / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(to_markdown(data), encoding="utf-8")
    (out_dir / "report.html").write_text(to_html(data), encoding="utf-8")
    return data


def to_markdown(data):
    m, s, F = data["meta"], data["summary"], data["findings"]
    L = [f"# Audit web — {m['target']}", "",
         f"_{m['date']} · mode {m['mode']} · {m['pages']} page(s) crawlée(s) · {m['requests']} requêtes · stack : {', '.join(m['stack']) or 'non détectée'}_", "",
         f"## Verdict : **{s['verdict']}** — score global {s['global'] if s['global'] is not None else '-'}/100 ({s['grade']})", "",
         f"Seuil de validation : {s['threshold']}/100 par catégorie, 0 KO critique/haut, 0 test non exécuté, 0 point à vérifier.", "",
         *( ["> ⚠ Mode local : le certificat, les protocoles TLS, HSTS, la redirection HTTPS et HTTP/2 n'ont pas pu être testés. "
             "Relancer avec `--prod-url https://domaine` une fois en ligne pour l'audit SSL réel.", ""] if m['mode'] == 'local' and not m.get('prod_url') and 'tls' in m['categories'] else [] ),
         "| Catégorie | Score | Note | KO | À améliorer | À vérifier | Non exécutés | OK |", "|---|---|---|---|---|---|---|---|"]
    for cat, v in s["categories"].items():
        c = v["counts"]
        L.append(f"| {v['label']} | {v['score'] if v['score'] is not None else '-'} | {v['grade']} | {c['fail']} | {c['warn']} | {c['manual']} | {c['error']} | {c['pass']} |")
    L.append("")
    fails = [f for f in F if f["status"] == "fail"]
    warns = [f for f in F if f["status"] == "warn"]
    errs = [f for f in F if f["status"] == "error"]
    man = [f for f in F if f["status"] == "manual"]
    if fails:
        L += ["## Corrections obligatoires (KO)", "", "Classées par gravité. Chaque ligne indique l'ID à citer pour demander la correction.", ""]
        for f in fails:
            L += _md_item(f)
    if warns:
        L += ["## À améliorer", ""]
        for f in warns:
            L += _md_item(f)
    if errs:
        L += ["## Tests non exécutés (audit incomplet tant qu'ils ne tournent pas)", ""]
        for f in errs:
            L.append(f"- **{f['id']}** {f['title']} — {f['evidence']}" + (f" → {f['note']}" if f["note"] else ""))
        L.append("")
    if man:
        L += ["## À vérifier (revue humaine ou question au client)", ""]
        for f in man:
            L.append(f"- **{f['id']}** [{f['severity']}] {f['title']} — {f['evidence']}" + (f"  \n  {f['note']}" if f["note"] else ""))
        L.append("")
    oks = [f for f in F if f["status"] == "pass"]
    L += ["## Contrôles validés", "", ", ".join(f"{f['id']}" for f in oks) or "aucun", ""]
    nas = [f for f in F if f["status"] == "na"]
    if nas:
        L += ["## Non applicables", ""] + [f"- {f['id']} {f['title']} — {f['evidence']}" for f in nas] + [""]
    L += ["---", "Audit technique automatisé + contrôles documentaires. Les points juridiques (RGPD) relèvent de la conformité technique observable ; "
          "le contenu des documents légaux doit être relu par le responsable du traitement."]
    return "\n".join(L)


def _md_item(f):
    out = [f"### {f['id']} · {f['severity'].upper()} · {f['title']}", f"- **Constat** : {f['evidence']}"]
    if f["details"]:
        out.append("- **Détail** :")
        out += [f"  - `{d}`" if len(d) < 200 else f"  - {d}" for d in f["details"][:15]]
        if f["details_total"] > 15:
            out.append(f"  - … et {f['details_total'] - 15} autre(s) (voir report.json)")
    if f["note"]:
        out.append(f"- **Note** : {f['note']}")
    out += [f"- **Correction** : {f['fix']}", f"- **Référence** : `{f['ref']}`", ""]
    return out


def to_html(data):
    m, s, F = data["meta"], data["summary"], data["findings"]
    e = html.escape

    def gauge(label, val, grd):
        v = val if val is not None else 0
        color = "var(--ok)" if v >= 90 else "var(--warn)" if v >= 65 else "var(--ko)"
        c = 2 * 3.14159 * 42
        return (f'<div class="g"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" class="t"/>'
                f'<circle cx="50" cy="50" r="42" class="v" style="stroke:{color};stroke-dasharray:{c * v / 100:.1f} {c:.1f}"/>'
                f'<text x="50" y="50" class="n">{val if val is not None else "–"}</text><text x="50" y="66" class="l">{grd}</text></svg>'
                f'<div class="gl">{e(label)}</div></div>')
    gauges = gauge("Global", s["global"], s["grade"]) + "".join(gauge(v["label"], v["score"], v["grade"]) for v in s["categories"].values())
    rows = []
    for f in F:
        det = "".join(f"<li><code>{e(d)}</code></li>" for d in f["details"][:25])
        more = f"<li>… {f['details_total'] - 25} de plus</li>" if f["details_total"] > 25 else ""
        rows.append(f'<details class="f s-{f["status"]}" data-cat="{f["category"]}" data-st="{f["status"]}"><summary>'
                    f'<span class="b b-{f["status"]}">{STATUS_FR[f["status"]]}</span><span class="sev sev-{f["severity"]}">{f["severity"]}</span>'
                    f'<b>{f["id"]}</b> {e(f["title"])}<span class="ev">{e(f["evidence"])}</span></summary>'
                    f'<div class="body">{"<ul>" + det + more + "</ul>" if det else ""}'
                    f'{"<p><b>Note :</b> " + e(f["note"]) + "</p>" if f["note"] else ""}'
                    f'<p><b>Correction :</b> {e(f["fix"])}</p><p class="ref">{e(f["ref"])}</p></div></details>')
    cats = "".join(f'<option value="{k}">{e(v)}</option>' for k, v in CATEGORIES.items() if k in s["categories"])
    vcls = {"VALIDÉ": "ok", "VALIDÉ SOUS RÉSERVE": "warn", "À AMÉLIORER": "warn", "INCOMPLET": "warn", "BLOQUÉ": "ko"}[s["verdict"]]
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit web</title><style>
:root{{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--mut:#6b6b66;--line:#e4e4df;--ok:#1f8a4c;--warn:#b7791f;--ko:#c53030;--na:#8a8a85}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--fg:#ecece8;--mut:#a3a39c;--line:#33332f;--ok:#48bb78;--warn:#ecc94b;--ko:#fc8181;--na:#77776f}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px}}h1{{font-size:22px;margin:0 0 4px}}.meta{{color:var(--mut);font-size:13px}}
.verdict{{margin:18px 0;padding:14px 16px;border-radius:10px;background:var(--card);border:1px solid var(--line);font-size:17px}}
.verdict b.ok{{color:var(--ok)}}.verdict b.warn{{color:var(--warn)}}.verdict b.ko{{color:var(--ko)}}
.gs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;margin:16px 0}}
.g{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;text-align:center}}.g svg{{width:92px;height:92px}}
.t{{fill:none;stroke:var(--line);stroke-width:9}}.v{{fill:none;stroke-width:9;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}}
.n{{font-size:24px;font-weight:700;text-anchor:middle;fill:var(--fg)}}.l{{font-size:11px;text-anchor:middle;fill:var(--mut)}}.gl{{font-size:13px;color:var(--mut)}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 10px}}select,input{{font:inherit;padding:6px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg)}}
.f{{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:6px 0}}summary{{cursor:pointer;padding:9px 12px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}}
.ev{{color:var(--mut);font-size:13px;flex-basis:100%}}.body{{padding:0 14px 12px;font-size:14px}}.body code{{font-size:12px;word-break:break-all}}
.b{{font-size:11px;padding:2px 7px;border-radius:99px;color:#fff;font-weight:600}}.b-pass{{background:var(--ok)}}.b-fail{{background:var(--ko)}}.b-warn{{background:var(--warn)}}
.b-manual{{background:#5a67d8}}.b-na,.b-error{{background:var(--na)}}.b-error{{background:#805ad5}}
.sev{{font-size:11px;text-transform:uppercase;color:var(--mut);min-width:58px}}.sev-critical{{color:var(--ko);font-weight:700}}.sev-high{{color:var(--ko)}}
.ref{{color:var(--mut);font-size:12px}}footer{{color:var(--mut);font-size:12px;margin-top:24px}}
</style></head><body><main>
<h1>Audit web — {e(m['target'])}</h1><div class="meta">{e(m['date'])} · mode {e(m['mode'])} · {m['pages']} pages · stack : {e(', '.join(m['stack']) or 'non détectée')}</div>
<div class="verdict">Verdict : <b class="{vcls}">{e(s['verdict'])}</b> · {s['blocking']} KO bloquant(s) · {s['errors']} test(s) non exécuté(s) · {s['pending']} point(s) à vérifier</div>
<div class="gs">{gauges}</div>
<div class="bar"><select id="c"><option value="">Toutes catégories</option>{cats}</select>
<select id="s"><option value="">Tous statuts</option><option value="fail">KO</option><option value="warn">À améliorer</option><option value="manual">À vérifier</option><option value="error">Non exécuté</option><option value="pass">OK</option><option value="na">N/A</option></select>
<input id="q" placeholder="Rechercher…"></div>
<div id="list">{''.join(rows)}</div>
<footer>{len(F)} contrôles · web-compliance-gate · Audit technique ; le contenu juridique des documents doit être validé par le responsable du traitement.</footer>
</main><script>
const c=document.getElementById('c'),s=document.getElementById('s'),q=document.getElementById('q');
function f(){{const qq=q.value.toLowerCase();document.querySelectorAll('.f').forEach(d=>{{d.style.display=(!c.value||d.dataset.cat===c.value)&&(!s.value||d.dataset.st===s.value)&&(!qq||d.textContent.toLowerCase().includes(qq))?'':'none'}})}}
[c,s].forEach(x=>x.onchange=f);q.oninput=f;
</script></body></html>"""
