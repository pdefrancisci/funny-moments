#!/usr/bin/env python3
"""Turn a plain .txt blog draft into a complete Funny Moments .html page.

Rules (matching usoc.html's structure):
  * First line of the file (if it stands alone) -> <h1>.
  * Blank line = new paragraph; each paragraph -> <p>.
  * A line starting with "## " -> <h2>.
  * Consecutive shell-command lines (rsync, ssh, sudo, git, ...) -> <pre><code>.
  * [link text](https://example.com) -> <a href="...">link text</a>.
  * Everything is HTML-escaped (& < >), so it's safe to paste anything.

Usage:
    python txt2html.py chumby_new_dawn_rises.txt
    python txt2html.py post.txt -o post.html
    python txt2html.py post.txt --page-title "Funny Moments - Chumby"

Options: --title, --page-title, --template FILE ({{title}} {{page_title}}
{{content}}), --keep-linebreaks, --autolink, --no-code.
"""
import argparse
import html
import re
from pathlib import Path

DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{page_title}}</title>
    <link href="/contentStyle.css" rel="stylesheet" type="text/css" media="all">
  </head>
  <body>
  <center>
    <div class="blog-post">
{{content}}
    </div>
  </center>
  </body>
</html>
"""

INDENT = "      "  # matches the 6-space indent inside .blog-post in usoc.html

COMMAND_RE = re.compile(
    r"^(rsync|ssh|scp|sudo|git|cd|pip3?|python3?|curl|wget|systemctl|"
    r"mkdir|nano|vim|apt(-get)?|npm|chmod|chown|cp|mv|rm)\b"
)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
BARE_URL_RE = re.compile(r'(?<!["=>])(https?://[^\s<]+)')


def inline(text, autolink=False):
    """Escape text, then apply [text](url) links (and optional autolinking)."""
    text = html.escape(text, quote=False)
    text = MD_LINK_RE.sub(r'<a href="\2">\1</a>', text)
    if autolink:
        def link(m):
            url = m.group(1)
            trail = re.search(r"[.,;:!?)]+$", url)
            tail = trail.group(0) if trail else ""
            url = url[: len(url) - len(tail)]
            return f'<a href="{url}">{url}</a>{tail}'
        text = BARE_URL_RE.sub(link, text)
    return text


def render_block(lines, keep_br, autolink, detect_code):
    """Turn one blank-line-separated block into a list of HTML strings."""
    out, prose, code = [], [], []

    def flush_prose():
        if prose:
            sep = "<br>\n" if keep_br else " "
            body = sep.join(inline(l, autolink) for l in prose)
            out.append(f"{INDENT}<p>{body}</p>")
            prose.clear()

    def flush_code():
        if code:
            body = "\n".join(html.escape(l, quote=False) for l in code)
            out.append(f"{INDENT}<pre><code>{body}</code></pre>")
            code.clear()

    for line in lines:
        if line.startswith("## "):
            flush_prose(); flush_code()
            out.append(f"{INDENT}<h2>{inline(line[3:].strip(), autolink)}</h2>")
        elif detect_code and COMMAND_RE.match(line):
            flush_prose()
            code.append(line)
        else:
            flush_code()
            prose.append(line)
    flush_prose(); flush_code()
    return out


def convert(text, keep_br=False, autolink=False, detect_code=True, title=None):
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = [[l.strip() for l in b.split("\n") if l.strip()]
              for b in re.split(r"\n\s*\n", text)]
    blocks = [b for b in blocks if b]

    h1 = title
    if h1 is None and blocks and len(blocks[0]) == 1 and len(blocks[0][0]) <= 120:
        h1 = blocks.pop(0)[0]
    elif title is not None and blocks and len(blocks[0]) == 1 and blocks[0][0] == title:
        blocks.pop(0)

    parts = []
    if h1:
        parts.append(f"{INDENT}<h1>{html.escape(h1, quote=False)}</h1>")
    for b in blocks:
        parts.extend(render_block(b, keep_br, autolink, detect_code))
    return "\n".join(parts), h1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="default: same name, .html")
    ap.add_argument("-t", "--title", help="h1 text (default: first line of the file)")
    ap.add_argument("--page-title", default="Funny Moments",
                    help='<title> tag text (default: "Funny Moments")')
    ap.add_argument("--template", type=Path)
    ap.add_argument("--keep-linebreaks", action="store_true")
    ap.add_argument("--autolink", action="store_true", help="link bare http(s) URLs")
    ap.add_argument("--no-code", action="store_true", help="don't detect shell commands")
    args = ap.parse_args()

    content, _ = convert(args.input.read_text(encoding="utf-8"), args.keep_linebreaks,
                         args.autolink, not args.no_code, args.title)
    template = (args.template.read_text(encoding="utf-8") if args.template
                else DEFAULT_TEMPLATE)
    page = (template.replace("{{page_title}}", html.escape(args.page_title))
                    .replace("{{title}}", html.escape(args.page_title))
                    .replace("{{content}}", content))
    out = args.output or args.input.with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
