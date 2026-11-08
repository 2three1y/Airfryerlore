#!/usr/bin/env python3
"""Build the Airfryerlore series site.

Add a book = add one file to src/books/ (book-6.html, book-7.html, ...) and run:

    python3 build.py

Each book file starts with a <!--book {...} --> block (JSON: title, released,
synopsis, title_page) and then the book itself as plain HTML: <section>s with
<h2 id> chapters and <h3 id> scenes. A Tab vs Poke message can be pulled in,
word for word, with <tvp-msg ref="MESSAGE-ID"></tvp-msg> (from src/data/tab-vs-poke.json).

This regenerates: index.html (welcome screen + old link redirects),
books/book-N.html (web version), books/book-N-text.html (plain text version),
stats.html, and the book list in README.md. Only the Python standard library.
"""
import datetime, html, json, math, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
WORDS_PER_PAGE = 250
esc = html.escape

series = json.load(open(os.path.join(SRC, "series.json"), encoding="utf-8"))
TVP = json.load(open(os.path.join(SRC, "data", "tab-vs-poke.json"), encoding="utf-8"))
MSGS = {m["id"]: m for d in TVP["days"] for r in d["rounds"] for m in r["messages"]}
SPEAKER = {"tab": "Tab", "poke": "Poke"}


def load_books():
    books = []
    folder = os.path.join(SRC, "books")
    for name in os.listdir(folder):
        m = re.fullmatch(r"book-(\d+)\.html", name)
        if not m:
            continue
        raw = open(os.path.join(folder, name), encoding="utf-8").read()
        head = re.match(r"\s*<!--book\s*(\{.*?\})\s*-->\s*", raw, re.S)
        if not head:
            raise SystemExit(f"{name}: missing the <!--book {{...}} --> block at the top")
        meta = json.loads(head.group(1))
        meta["n"] = int(m.group(1))
        meta["body"] = raw[head.end():]
        meta["label"] = f"Book {meta['n']}: {meta['title']}"
        meta["page"] = f"books/book-{meta['n']}.html"
        meta["text_page"] = f"books/book-{meta['n']}-text.html"
        books.append(meta)
    books.sort(key=lambda b: b["n"])
    return books


def clock(iso):
    t = datetime.datetime.fromisoformat(iso)
    return t.strftime("%I:%M %p").lstrip("0")


def msg_lines_html(text):
    out, bullets = [], []
    def flush():
        if bullets:
            out.append("<ul>" + "".join(f"<li>{esc(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()
    for line in text.split("\n"):
        if line.startswith("- "):
            bullets.append(line[2:])
        else:
            flush()
            if line.strip():
                out.append(f"<p>{esc(line)}</p>")
    flush()
    return "".join(out)


def render_msgs(body, mode):
    def rep(m):
        msg = MSGS[m.group(1)]
        who, when = SPEAKER[msg["speaker"]], clock(msg["time"])
        inner = msg_lines_html(msg["text"])
        if mode == "web":
            return (f'<div class="msg msg-{msg["speaker"]}"><p class="msg-who">{who}, {when}</p>'
                    f'<div class="msg-text">{inner}</div></div>')
        # The story around every message already says who sent it and when.
        return f"<blockquote>{inner}</blockquote>"
    return re.sub(r'<tvp-msg ref="([^"]+)"></tvp-msg>', rep, body)


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def count(book):
    text_body = render_msgs(book["body"], "text")
    blocks = re.findall(r"<(p|li|h2|h3|h4)\b[^>]*>(.*?)</\1>", text_body, re.S)
    lines = [plain(b) for _, b in blocks]
    lines = [l for l in lines if l]
    words = sum(len(l.split()) for l in lines)
    chapters = len(re.findall(r"<h2\b[^>]*>\s*Chapter \d+", book["body"]))
    return {"words": words, "lines": len(lines), "chapters": chapters,
            "pages": max(1, math.ceil(words / WORDS_PER_PAGE))}


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day} {d.year}"


def head(title, prefix, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(series['tagline'])}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(series['tagline'])}">
<link rel="stylesheet" href="{prefix}assets/book.css">
{extra}</head>
"""


PICKER_JS = ('<script>(function(){var f=document.getElementById("book-picker-form");if(!f)return;'
             'f.hidden=false;f.addEventListener("submit",function(e){e.preventDefault();'
             'location.href=f.elements.book.value;});})();</script>')


def picker(books, prefix, current=None):
    """The book menu: a native <select> (the iPhone picker) plus a Read button.
    The small script right after it shows it and opens the chosen book.
    Without JavaScript the menu stays hidden and the <noscript> links show instead."""
    opts = []
    for b in books:
        sel = " selected" if current == b["n"] else ""
        opts.append(f'<option value="{prefix}{b["page"]}"{sel}>{esc(b["label"])}</option>')
    links = []
    for b in books:
        cur = ' aria-current="page"' if current == b["n"] else ""
        links.append(f'<li><a href="{prefix}{b["page"]}"{cur}>{esc(b["label"])}</a></li>')
    return ('<form class="picker" id="book-picker-form" method="get" action="#" hidden>\n'
            '<label for="book-picker">Choose a book</label>\n'
            '<select id="book-picker" name="book">\n' + "\n".join(opts) + '\n</select>\n'
            '<button type="submit">Read</button>\n</form>\n' + PICKER_JS + '\n'
            '<noscript>\n<ul class="book-list">\n' + "\n".join(links) + '\n</ul>\n</noscript>\n')


def selector(books, prefix, current=None):
    """The book menu at the top of a book page (and the stats page)."""
    return '<nav class="selector" aria-label="Books">\n' + picker(books, prefix, current) + '</nav>\n'


def footer(prefix):
    return f"""<footer>
<p>{esc(series['credits'])} <a href="{series['made_by_url']}">{esc(series['made_by_text'])}</a>.</p>
<p><a href="{series['repo_url']}">The Airfryerlore repository on GitHub</a></p>
</footer>
"""


def toc(body):
    rows = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.S)
    return ('<nav class="toc" aria-labelledby="contents">\n<h2 id="contents">Contents</h2>\n<ul>\n' +
            "\n".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in rows) + "\n</ul>\n</nav>\n")


def book_page(books, b):
    i = books.index(b)
    prev = books[i - 1] if i > 0 else None
    nxt = books[i + 1] if i + 1 < len(books) else None
    ends = []
    if prev:
        ends.append(f'<li><a href="book-{prev["n"]}.html">Previous book: {esc(prev["label"])}</a></li>')
    if nxt:
        ends.append(f'<li><a href="book-{nxt["n"]}.html">Next book: {esc(nxt["label"])}</a></li>')
    ends.append('<li><a href="../index.html">Welcome screen</a></li>')
    tp = "".join(f'<p>{esc(x)}</p>\n' for x in b.get("title_page", []))
    return (head(f'{b["label"]} - {series["series"]}', "../") +
            f"""<body>
<div class="desk">
{selector(books, "../", b["n"])}<div class="paper">
<main>
<header class="title-page">
<p class="series">{esc(series['series'])}</p>
<h1>{esc(b['label'])}</h1>
<p class="author">by {esc(series['author'])}</p>
{tp}<p><a href="book-{b['n']}-text.html">Read {esc(b['label'])} as plain text</a></p>
</header>
{toc(b['body'])}<div class="story">
{render_msgs(b['body'], 'web')}
</div>
<nav class="end-nav" aria-labelledby="keep-reading">
<h2 id="keep-reading">Keep reading</h2>
<ul>
{chr(10).join(ends)}
</ul>
</nav>
</main>
{footer('../')}</div>
</div>
</body>
</html>
""")


def text_page(books, b):
    tp = "".join(f'<p>{esc(x)}</p>\n' for x in b.get("title_page", []))
    return (head(f'{b["label"]}, plain text - {series["series"]}', "../") +
            f"""<body class="plain">
<main>
<h1>{esc(b['label'])}, plain text</h1>
<p>This is the plain text version of {esc(b['label'])}, from the {esc(series['series'])} series by {esc(series['author'])}. It has no buttons. Everything is written out as text.</p>
{tp}<p><a href="book-{b['n']}.html">Read the web version of {esc(b['label'])}</a></p>
<p><a href="../index.html">Welcome screen</a></p>
{render_msgs(b['body'], 'text')}
<p>This is the end of {esc(b['label'])}.</p>
<p><a href="../index.html">Welcome screen</a></p>
</main>
</body>
</html>
""")


def old_links(books):
    """Old single-page links like index.html#chapter-5 -> the book that has that id now."""
    where = {"contents": books[0]["page"]}
    for b in books:
        for i in re.findall(r'\bid="([^"]+)"', b["body"]):
            if i in where and where[i] != b["page"] and i != "contents":
                raise SystemExit(f'id "{i}" is used in two books; ids must be unique across the series')
            where[i] = b["page"]
    return where


def welcome(books):
    where = json.dumps(old_links(books), separators=(",", ":"))
    redirect = ('<script>(function(){var m=' + where +
                ';var h=decodeURIComponent(location.hash.slice(1));if(h&&m[h]){location.replace(m[h]+"#"+encodeURIComponent(h));}})();</script>\n')
    txt = "\n".join(f'<li><a href="{b["text_page"]}">{esc(b["label"])}, plain text</a></li>' for b in books)
    return (head(series["series"], "", redirect) + f"""<body>
<div class="desk">
<div class="paper">
<main>
<header class="title-page">
<p class="series">A book series</p>
<h1>{esc(series['series'])}</h1>
<p class="author">by {esc(series['author'])}</p>
<p>{esc(series['tagline'])}</p>
</header>
<p>Welcome to the Dreamor Council. Start with Book 1 and keep going, or jump to any book. Every book also has a plain text version with no buttons.</p>
<nav aria-labelledby="select-a-book">
<h2 id="select-a-book">Books</h2>
{picker(books, "")}</nav>
<nav aria-labelledby="plain-text">
<h2 id="plain-text">Plain text versions</h2>
<ul class="book-list">
{txt}
</ul>
</nav>
<h2 id="more">More</h2>
<ul class="book-list">
<li><a href="stats.html">Stats</a></li>
</ul>
</main>
{footer('')}</div>
</div>
</body>
</html>
""")


def stats_page(books, counts):
    parts = []
    for b in books:
        c = counts[b["n"]]
        parts.append(f"""<section>
<h2 id="book-{b['n']}"><a href="{b['page']}">{esc(b['label'])}</a></h2>
<p>Synopsis: {esc(b['synopsis'])}</p>
<ul>
<li>Release date: {nice_date(b['released'])}</li>
<li>Pages: {c['pages']}</li>
<li>Words: {c['words']}</li>
<li>Lines: {c['lines']}</li>
<li>Chapters: {c['chapters']}</li>
</ul>
</section>""")
    tot = {k: sum(c[k] for c in counts.values()) for k in ("pages", "words", "lines", "chapters")}
    return (head(f'Stats - {series["series"]}', "") + f"""<body>
<div class="desk">
{selector(books, "")}<div class="paper">
<main>
<h1>Stats</h1>
<p>Every number on this page is counted from the books themselves, each time the site is built. A page is about {WORDS_PER_PAGE} words. A line is one paragraph, heading, or list item. The release date is the day that book's story was first saved to the repository.</p>
{chr(10).join(parts)}
<section>
<h2 id="all-books">Stats for all books</h2>
<ul>
<li>Books: {len(books)}</li>
<li>Pages: {tot['pages']}</li>
<li>Words: {tot['words']}</li>
<li>Lines: {tot['lines']}</li>
<li>Chapters: {tot['chapters']}</li>
</ul>
</section>
<p><a href="index.html">Welcome screen</a></p>
</main>
{footer('')}</div>
</div>
</body>
</html>
""")


def readme(books, counts):
    p = os.path.join(ROOT, "README.md")
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    rows = "\n".join(f"- [{b['label']}]({series['site_url']}{b['page']}) ([plain text]({series['site_url']}{b['text_page']}))"
                     for b in books)
    block = f"<!-- books:start -->\n{rows}\n<!-- books:end -->"
    if "<!-- books:start -->" in old:
        new = re.sub(r"<!-- books:start -->.*?<!-- books:end -->", block, old, flags=re.S)
    else:
        new = old + "\n" + block + "\n"
    open(p, "w", encoding="utf-8").write(new)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def main():
    books = load_books()
    counts = {b["n"]: count(b) for b in books}
    for b in books:
        write(b["page"], book_page(books, b))
        write(b["text_page"], text_page(books, b))
    write("index.html", welcome(books))
    write("stats.html", stats_page(books, counts))
    readme(books, counts)
    for b in books:
        c = counts[b["n"]]
        print(f"{b['label']}: {c['words']} words, {c['lines']} lines, {c['chapters']} chapters, {c['pages']} pages")


if __name__ == "__main__":
    main()
