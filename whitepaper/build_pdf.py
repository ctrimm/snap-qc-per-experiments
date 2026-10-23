"""Build a whitepaper's HTML and PDF from its Markdown, in the house style (_style.css, from the Oct 11 whitepaper).

    python build_pdf.py policy_qa_summary.md project_summary.md
Needs the `markdown` package and Google Chrome (headless print, as the earlier PDFs were made).
"""
import html
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


LIST = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def normalize(text: str) -> str:
    """Python-Markdown wants 4-space nesting and a blank line before a nested list; the sources use 2-3 spaces.
    Code fences are left untouched (keep them at top level: fences inside list items aren't supported)."""
    out, fence = [], False
    for line in text.split("\n"):
        stripped = line.lstrip(" ")
        if stripped.startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        k = len(line) - len(stripped)
        if 0 < k < 8 and stripped:
            line = " " * (4 if k <= 3 else 8) + stripped
        if LIST.match(line) and out and out[-1].strip() and not LIST.match(out[-1]):
            out.append("")
        out.append(line)
    return "\n".join(out)


def build(md_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    title = re.match(r"# (.+)", text).group(1)
    meta = re.search(r"^\*\*(.+?)\*\*\s*$", text, re.M)
    body = text.replace(f"# {title}\n", "", 1)
    if meta:
        body = body.replace(meta.group(0), "", 1)
    out = markdown.markdown(normalize(body), extensions=["tables", "fenced_code", "sane_lists"])
    page = (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>{html.escape(title)}</title>\n'
            f'<style>\n{(HERE / "_style.css").read_text()}</style>\n</head>\n<body>\n<h1>{html.escape(title)}</h1>\n'
            + (f'<div class="meta">{html.escape(meta.group(1))}</div>\n' if meta else "") + out + "\n</body>\n</html>\n")
    h = md_path.with_suffix(".html"); h.write_text(page, encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={md_path.with_suffix('.pdf')}",
                    h.resolve().as_uri()], check=True, capture_output=True)
    print(md_path.with_suffix(".pdf").name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        build(HERE / a)
