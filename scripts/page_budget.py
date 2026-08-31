"""Estimate the manuscript's body length in pages, without rendering it.

This host cannot build the PDF (the bundled tectonic wants GLIBC 2.36+ and the
box has 2.35 — see CLAUDE.md §11), so the page count that matters for a
submission limit cannot be read directly. What this does instead is calibrate
against a commit whose PDF *was* rendered and is committed: measure that PDF's
real body length, count the rendered characters of the same span in its LaTeX,
and project the current revision from the ratio.

It is an estimate and it is stated as a range, because added prose and an
average page do not have the same character density. The lower bound prices new
text as solid prose (86 chars per 13pt line, measured off the anchor); the upper
bound prices it at the anchor's page average, which carries headings, paragraph
gaps and figures. A submission decision should use the upper bound.

    uv run python scripts/page_budget.py
    uv run python scripts/page_budget.py --rev <sha> --ceiling 8
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

TEX = "docs/manuscript/manuscript.tex"
PDF = "docs/manuscript/manuscript.pdf"

# Page geometry, measured from the anchor PDF's own word boxes rather than
# assumed from \geometry: text runs 73pt to 803pt on A4, and body leading is 13pt
# with a full prose line holding about 86 characters.
TEXT_TOP, TEXT_BOTTOM = 73.0, 803.0
PAGE_PTS = TEXT_BOTTOM - TEXT_TOP
LINE_PITCH = 13.0
CHARS_PER_LINE = 86.0


def show_bytes(rev: str, path: str) -> bytes:
    out = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True)
    if out.returncode:
        sys.exit(f"cannot read {path} at {rev}: {out.stderr.decode().strip()}")
    return out.stdout


def show(rev: str, path: str) -> str:
    return show_bytes(rev, path).decode("utf-8", "replace")


def tex_body(rev: str) -> str:
    """The span the page limit applies to: document start to the bibliography."""
    t = show(rev, TEX)
    if "\\bibliographystyle" not in t:
        sys.exit(f"{rev} has no \\bibliographystyle; cannot find where the body ends")
    return re.sub(r"(?m)(?<!\\)%.*$", "", t[: t.index("\\bibliographystyle")])


def rendered_chars(t: str) -> int:
    """Approximate the characters LaTeX actually sets on the page.

    Markup is not typeset, so counting raw source over-weights table and TikZ
    heavy sections; citations are counted at their rendered width instead of
    their key length.
    """
    t = re.sub(r"\\cite[a-z]*\{([^}]*)\}", lambda m: "[00]" * len(m.group(1).split(",")), t)
    t = re.sub(r"\\(ref|autoref|pageref)\{[^}]*\}", "0", t)
    t = re.sub(r"\\label\{[^}]*\}", "", t)
    t = re.sub(r"\\(texttt|emph|textbf|textit|text)\{([^{}]*)\}", r"\2", t)
    t = re.sub(
        r"\\(usepackage|documentclass|easrp[a-z]*|needspace|bibliographystyle)\b(\[[^\]]*\])?\{[^}]*\}",
        "", t,
    )
    t = re.sub(r"\\begin\{[^}]*\}(\[[^\]]*\])?|\\end\{[^}]*\}", "", t)
    t = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", t)
    t = re.sub(r"[{}&~\\$]", " ", t)
    return len(re.sub(r"\s+", " ", t).strip())


def anchor_pages(rev: str, scratch: Path) -> float:
    """Measure the anchor PDF's body: full pages before the References heading,
    plus the fraction of the page above it."""
    pdf = scratch / f"anchor-{rev}.pdf"
    pdf.write_bytes(show_bytes(rev, PDF))
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True)
    if out.returncode:
        sys.exit("pdftotext is required to measure the anchor PDF")
    pages = re.findall(r'<page width="[\d.]+" height="[\d.]+">(.*?)</page>', out.stdout, re.S)
    for i, body in enumerate(pages, start=1):
        for y, word in re.findall(
            r'<word xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">([^<]*)</word>', body
        ):
            if word.strip() == "References":
                return (i - 1) + (float(y) - TEXT_TOP) / PAGE_PTS
    sys.exit("no 'References' heading found in the anchor PDF")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--anchor", default="1bb78d1", help="commit whose committed PDF is a true render"
    )
    ap.add_argument("--rev", default="HEAD", help="revision to project")
    ap.add_argument("--ceiling", type=float, default=8.0, help="page limit for the body")
    ap.add_argument("--scratch", default="/tmp", help="where to drop the extracted anchor PDF")
    args = ap.parse_args()

    pages_a = anchor_pages(args.anchor, Path(args.scratch))
    chars_a = rendered_chars(tex_body(args.anchor))
    chars_r = rendered_chars(tex_body(args.rev))
    delta = chars_r - chars_a

    per_page = chars_a / pages_a
    lo = pages_a + (delta / CHARS_PER_LINE * LINE_PITCH) / PAGE_PTS
    hi = pages_a + delta / per_page

    print(
        f"anchor {args.anchor}: {chars_a:,} rendered chars "
        f"= {pages_a:.3f} pages (measured from its PDF)"
    )
    print(f"{args.rev:>14s}: {chars_r:,} rendered chars ({delta:+,})")
    print(f"calibration   : {per_page:,.0f} rendered chars per page")
    print(f"\nPROJECTED BODY: {lo:.2f} - {hi:.2f} pages   (ceiling {args.ceiling:g})")

    over = hi > args.ceiling
    if over:
        cut_lo = max(0, int((lo - args.ceiling) * PAGE_PTS / LINE_PITCH * CHARS_PER_LINE))
        cut_hi = int((hi - args.ceiling) * per_page)
        print(f"\n*** OVER THE LIMIT — cut roughly {cut_lo:,}-{cut_hi:,} characters ***")
    else:
        print(f"\nunder the limit; {int((args.ceiling - hi) * per_page):,} characters of headroom")
    print("\nEstimate, not a render. Tables and figures carry height this cannot see,")
    print("so confirm on a machine that builds the PDF before submitting.")
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
