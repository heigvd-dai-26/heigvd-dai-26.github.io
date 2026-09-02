#!/usr/bin/env python3
"""convert.py — convert legacy Marp course material to Quarto .qmd.

Two modes:
  chapter  convert a chapter's 01-course-material/README.md to chapters/NN-topic.qmd
  slides   convert a PRESENTATION.md (Marp) to slides/NN-topic.qmd (reveal.js)

The output is a ~90% conversion: places needing human attention are marked
with "<!-- TODO(convert):" comments. Always do an editorial pass after.

Usage:
  tools/convert.py chapter path/to/README.md --images-prefix images/05-docker > chapters/05-docker.qmd
  tools/convert.py slides path/to/PRESENTATION.md > slides/05-docker.qmd
"""

import argparse
import re
import sys

# ---------------------------------------------------------------- helpers

ALERT_MAP = {
    "NOTE": "note",
    "TIP": "tip",
    "IMPORTANT": "important",
    "WARNING": "warning",
    "CAUTION": "caution",
}


def convert_github_alerts(text: str) -> str:
    """> [!NOTE] blockquotes -> ::: {.callout-note} blocks."""
    out, i, lines = [], 0, text.split("\n")
    while i < len(lines):
        m = re.match(r">\s*\[!(\w+)\]\s*$", lines[i])
        if m and m.group(1) in ALERT_MAP:
            kind = ALERT_MAP[m.group(1)]
            body = []
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
                if lines[i].strip() == "" and not (i + 1 < len(lines) and lines[i + 1].startswith(">")):
                    break
                body.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append(f"::: {{.callout-{kind}}}")
            out.extend(body)
            out.append(":::")
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def strip_section(text: str, heading_re: str) -> str:
    """Remove a '## Heading' section including its content (up to next same-level heading)."""
    lines = text.split("\n")
    out, skipping, level = [], False, 0
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            if skipping and len(m.group(1)) <= level:
                skipping = False
            if not skipping and re.match(heading_re, m.group(2).strip(), re.IGNORECASE):
                skipping, level = True, len(m.group(1))
                continue
        if not skipping:
            out.append(line)
    return "\n".join(out)


def extract_title(text: str) -> tuple[str, str]:
    """Pop the first H1 and return (title, remaining text)."""
    m = re.search(r"^#\s+(.*)$", text, re.MULTILINE)
    if not m:
        return "Untitled", text
    title = m.group(1).strip()
    text = text[: m.start()] + text[m.end():]
    return title, text


def rewrite_image_paths(text: str, prefix: str | None) -> str:
    """./images/x.png -> {prefix}/x.png (idempotent: skips already-rewritten paths)."""
    if not prefix:
        return text
    tail = prefix.split("/", 1)[1] + "/" if "/" in prefix else None
    text = re.sub(r"\]\(\./images/", f"]({prefix}/", text)
    guard = f"(?!{re.escape(tail)})" if tail else ""
    return re.sub(rf"\]\(images/{guard}", f"]({prefix}/", text)


# ---------------------------------------------------------------- chapter

def convert_chapter(text: str, images_prefix: str | None) -> str:
    title, text = extract_title(text)

    # Boilerplate sections that the site handles globally
    for pat in (r"Resources$", r"Table of contents$", r"Sources$",
                r"Finished\? Was it easy\? Was it hard\?$", r"Solution$"):
        text = strip_section(text, pat)

    # Author + license lines from the header block
    text = re.sub(r"^.*with the help of\n?.*GitHub Copilot.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^This work is licensed under.*$", "", text, flags=re.MULTILINE)

    text = convert_github_alerts(text)

    text = rewrite_image_paths(text, images_prefix)

    # Cross-chapter links to the old repo layout need manual retargeting
    text = re.sub(
        r"(\[[^\]]*\]\((?:\.\./)+[0-9]{2}\.[0-9]{2}-[^)]*\))",
        r"\1 <!-- TODO(convert): retarget cross-chapter link -->",
        text,
    )

    # Collapse >2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    header = f'---\ntitle: "{title}"\n---\n\n'
    footer = (
        "\n## Sources\n\n"
        "- O. Tischhauser, with the help of\n"
        "  [Claude](https://claude.com) (Anthropic).\n"
        "- Adapted from the\n"
        "  [HEIG-VD DAI course](https://github.com/heig-vd-dai-course/heig-vd-dai-course)\n"
        "  by L. Delafontaine and H. Louis, licensed\n"
        "  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).\n"
        "<!-- TODO(convert): re-add image credits from the original Sources section -->\n"
    )
    return header + text + footer


# ---------------------------------------------------------------- slides

BG_RE = re.compile(r"!\[bg([^\]]*)\]\(([^)]+)\)")


def convert_slides(text: str, images_prefix: str | None = None) -> str:
    # Drop Marp YAML frontmatter
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)

    # Extract title from the directive comment block, then drop the block
    title = "Untitled"
    m = re.search(r"<!--\n(.*?)-->", text, flags=re.DOTALL)
    if m and "theme:" in m.group(1):
        tm = re.search(r"^title:\s*(?:HEIG-VD DAI - )?(.*)$", m.group(1), re.MULTILINE)
        if tm:
            title = tm.group(1).strip()
        text = text[: m.start()] + text[m.end():]

    # First H1 is the title slide; its body (author/license/links) is replaced
    # by YAML + the shared theme, so drop until the first H2
    h1 = re.search(r"^#\s+.*$", text, re.MULTILINE)
    if h1:
        nxt = re.search(r"^##\s+", text[h1.end():], re.MULTILINE)
        text = text[h1.end() + nxt.start():] if nxt else text[h1.end():]

    lines = text.split("\n")
    out: list[str] = []
    lead_pending = False
    for i, line in enumerate(lines):
        # Per-slide directives: remember 'lead' (section slide), drop the rest
        dm = re.match(r"\s*<!--\s*_class:\s*lead\s*-->", line)
        if dm:
            lead_pending = True
            continue
        if re.match(r"\s*<!--\s*_[a-z]+:.*-->", line):
            continue

        hm = re.match(r"^(#{2,6})\s+(.*)$", line)
        if hm:
            depth, heading = len(hm.group(1)), hm.group(2)
            if depth == 2:
                # Marp H2 = section slide (usually lead) -> reveal.js section (#)
                out.append(f"# {heading}")
                lead_pending = False
                continue
            out.append(f"## {heading}" if depth == 3 else f"### {heading}")
            continue

        # Background images -> right column layout (best effort)
        bm = BG_RE.search(line)
        if bm:
            attrs, url = bm.group(1), bm.group(2)
            wm = re.search(r"right:(\d+)%", attrs)
            width = wm.group(1) if wm else "40"
            out.append(f"<!-- TODO(convert): was Marp background image ({attrs.strip()}) -->")
            out.append(f"![]({url}){{width=\"{width}%\"}}")
            continue

        # Drop "More details for this section..." lead filler (two lines)
        if re.match(r"More details for this section", line) or \
           re.match(r"other resources and alternatives as well\.", line):
            lead_pending = False
            continue
        out.append(line)

    body = "\n".join(out)
    body = rewrite_image_paths(body, images_prefix)
    # Drop reference-style link definitions for course/license/qr boilerplate
    body = re.sub(r"^\[(course|license|discussions|illustration|course-qr-code)\]:.*(\n\t.*)*$",
                  "", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

    header = (
        f'---\ntitle: "{title}"\n'
        f'subtitle: "DAI"  # TODO(convert): set chapter number\n---\n\n'
    )
    return header + body


# ---------------------------------------------------------------- main

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["chapter", "slides"])
    p.add_argument("input")
    p.add_argument("--images-prefix", default=None,
                   help="rewrite ./images/ to this prefix (chapter: images/NN-topic, "
                        "slides: ../chapters/images/NN-topic)")
    a = p.parse_args()

    with open(a.input, encoding="utf-8") as f:
        text = f.read()

    if a.mode == "chapter":
        sys.stdout.write(convert_chapter(text, a.images_prefix))
    else:
        sys.stdout.write(convert_slides(text, a.images_prefix))


if __name__ == "__main__":
    main()
