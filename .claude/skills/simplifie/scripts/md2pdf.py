"""Convertit un ou plusieurs fichiers Markdown en PDF A4 via Chrome ou Edge en mode headless.

Usage : python md2pdf.py doc.md [autre.md ...] [--paysage] [--out dossier]
"""
import argparse
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import markdown
except ImportError:
    sys.exit("Module manquant : lancer  pip install markdown")

CSS = """
@page { size: A4 __ORIENT__; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 9.5pt;
       line-height: 1.45; color: #1c2024; margin: 0; }
h1 { font-size: 17pt; color: #0f2b46; border-bottom: 2px solid #0f2b46;
     padding-bottom: 4px; margin: 0 0 12px; page-break-after: avoid; }
h2 { font-size: 12.5pt; color: #0f2b46; margin: 18px 0 7px;
     border-bottom: 1px solid #c8d2dc; padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 10.5pt; color: #24486d; margin: 13px 0 5px; page-break-after: avoid; }
p { margin: 6px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 8.5pt; }
td, th { overflow-wrap: break-word; }
td:first-child, th:first-child { white-space: nowrap; }
th { background: #0f2b46; color: #fff; text-align: left; font-weight: 600;
     padding: 5px 6px; border: 1px solid #0f2b46; }
td { padding: 4px 6px; border: 1px solid #c8d2dc; vertical-align: top; }
tr:nth-child(even) td { background: #f4f7fa; }
tr { page-break-inside: avoid; }
td:empty { background: #fffbe6; min-width: 58px; }
td:empty::after { content: ""; display: block; height: 13px; }
blockquote { margin: 8px 0; padding: 7px 11px; background: #eef3f8;
             border-left: 3px solid #24486d; }
code { font-family: Consolas, monospace; font-size: 8.5pt;
       background: #eef1f4; padding: 1px 3px; border-radius: 2px; }
pre { background: #f4f7fa; border: 1px solid #c8d2dc; padding: 8px;
      font-size: 8pt; page-break-inside: avoid; }
ul, ol { margin: 6px 0 6px 18px; padding: 0; }
li { margin: 2px 0; }
hr { border: 0; border-top: 1px solid #c8d2dc; margin: 14px 0; }
strong { color: #0f2b46; }
"""

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge",
]


def find_browser():
    for candidate in BROWSERS:
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def convert(md_path, out_dir, orient, browser):
    text = io.open(md_path, encoding="utf-8").read()
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = match.group(1).strip() if match else md_path.stem
    body = markdown.markdown(text, extensions=["tables", "sane_lists", "attr_list"])
    html = ("<!doctype html><html lang=fr><head><meta charset=utf-8><title>%s</title>"
            "<style>%s</style></head><body>%s</body></html>"
            % (title, CSS.replace("__ORIENT__", orient), body))

    pdf_path = out_dir / (md_path.stem + ".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        html_path = pathlib.Path(tmp) / (md_path.stem + ".html")
        io.open(html_path, "w", encoding="utf-8").write(html)
        subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", "--print-to-pdf=%s" % pdf_path, html_path.as_uri()],
            capture_output=True, timeout=120,
        )
    if not pdf_path.exists():
        sys.exit("Echec de la generation : %s" % pdf_path)
    print("PDF : %s" % pdf_path)


def main():
    parser = argparse.ArgumentParser(description="Markdown vers PDF A4")
    parser.add_argument("fichiers", nargs="+", help="fichiers .md a convertir")
    parser.add_argument("--paysage", action="store_true", help="A4 paysage")
    parser.add_argument("--out", help="dossier de sortie (defaut : a cote du .md)")
    args = parser.parse_args()

    browser = find_browser()
    if not browser:
        sys.exit("Chrome ou Edge introuvable.")

    orient = "landscape" if args.paysage else "portrait"
    for name in args.fichiers:
        md_path = pathlib.Path(name).resolve()
        out_dir = pathlib.Path(args.out).resolve() if args.out else md_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        convert(md_path, out_dir, orient, browser)


if __name__ == "__main__":
    main()
