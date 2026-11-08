#!/usr/bin/env python3
"""Build the Airfryerlore series site.

Add a book = add one file to src/books/ (book-6.html, book-7.html, ...) and run:

    python3 build.py

Each book file starts with a <!--book {...} --> block (JSON: title, released,
synopsis, title_page) and then the book itself as plain HTML: <section>s with
<h2 id> chapters and <h3 id> scenes. A Tab vs Poke message can be pulled in,
word for word, with <tvp-msg ref="MESSAGE-ID"></tvp-msg> (from src/data/tab-vs-poke.json).

This regenerates: index.html (welcome screen + old link redirects),
books/book-N.html (web version), books/book-N.txt (plain text download of that
book), airfryerlore-complete-series.txt (the whole series as one plain text
download), stats.html, and the book list in README.md. Only the Python standard library.
"""
import datetime, html, json, math, os, re
from html.parser import HTMLParser

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
        meta["txt"] = f"books/book-{meta['n']}.txt"
        meta["txt_name"] = f"{series['series']} Book {meta['n']} - {meta['title']}.txt"
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


# ---- Plain text downloads (.txt): no HTML, no Markdown, one paragraph per line ----

SERIES_TXT = "airfryerlore-complete-series.txt"
SERIES_TXT_NAME = f"{series['series']} - The Complete Series.txt"
BLOCKS = {"p", "li", "h2", "h3", "h4", "blockquote", "div"}


class _Lines(HTMLParser):
    """Turns a book's HTML into plain text blocks, in reading order."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.tag, self.lists = [], [], None, []

    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.out.append((self.tag or "p", t))
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "ul":
            self.lists.append(dict(attrs).get("class"))
        if tag in BLOCKS:
            self.flush()
            self.tag = tag
            if tag == "li" and self.lists and not self.lists[-1]:
                self.buf.append("\u2022 ")  # a plain bullet character, for the bullet points in real messages
        elif tag == "br":
            self.flush()

    def handle_endtag(self, tag):
        if tag == "ul" and self.lists:
            self.lists.pop()
        if tag in BLOCKS:
            self.flush()
            self.tag = None

    def handle_data(self, data):
        self.buf.append(data)


def book_txt_lines(b):
    """The book as plain text: title block, contents, then every chapter."""
    p = _Lines()
    p.feed(render_msgs(b["body"], "text"))  # the same words the Stats page counts
    p.flush()
    blocks = p.out
    chapters = [t for tag, t in blocks if tag == "h2"]
    out = [series["series"], b["label"], f"by {series['author']}"]
    out += list(b.get("title_page", []))
    out += [f"Read it online: {series['site_url']}{b['page']}", "", "", "Contents", ""]
    out += chapters
    for tag, t in blocks:
        if tag in ("h2", "h3", "h4"):
            out += ["", "", t, ""]
        else:
            out += [t, ""]
    out += ["", f"This is the end of {b['label']}."]
    return out


def tidy(lines):
    """Paragraphs separated by one blank line, headings by two. Never more."""
    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip("\n")
    return text + "\n"


def book_txt(b):
    return tidy(book_txt_lines(b))


def series_txt(books):
    out = [f"{series['series']}: The Complete Series", f"by {series['author']}",
           series["tagline"], f"Read it online: {series['site_url']}", "", "", "Books in this file", ""]
    out += [b["label"] for b in books]
    for b in books:
        out += ["", "", "", ""] + book_txt_lines(b)
    out += ["", "", f"This is the end of the {series['series']} series, for now."]
    return tidy(out)


def downloads(books, prefix, current=None):
    """Footer download links: real <a href download> links, no JavaScript."""
    links = []
    if current is not None:
        b = next(x for x in books if x["n"] == current)
        links.append(f'<li><a href="{prefix}{b["txt"]}" download="{esc(b["txt_name"])}" type="text/plain">'
                     f'Download this book (.txt)</a></li>')
    links.append(f'<li><a href="{prefix}{SERIES_TXT}" download="{esc(SERIES_TXT_NAME)}" type="text/plain">'
                 f'Download the whole series (.txt)</a></li>')
    return ('<nav class="downloads" aria-label="Downloads">\n<ul>\n' + "\n".join(links) + "\n</ul>\n"
            '<p>Plain text files for offline reading, with no formatting.</p>\n</nav>\n')


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


def footer(books, prefix, current=None):
    return f"""<footer>
{downloads(books, prefix, current)}<p>{esc(series['credits'])} <a href="{series['made_by_url']}">{esc(series['made_by_text'])}</a>.</p>
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
{tp}</header>
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
{footer(books, '../', b['n'])}</div>
</div>
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
<p>Welcome to the Dreamor Council. Start with Book 1 and keep going, or jump to any book. To read offline, the bottom of every page has a download link for the whole series as a plain text file, and every book page has one for that book.</p>
<nav aria-labelledby="select-a-book">
<h2 id="select-a-book">Books</h2>
{picker(books, "")}</nav>
<h2 id="more">More</h2>
<ul class="book-list">
<li><a href="stats.html">Stats</a></li>
</ul>
</main>
{footer(books, '')}</div>
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
{footer(books, '')}</div>
</div>
</body>
</html>
""")


def readme(books, counts):
    p = os.path.join(ROOT, "README.md")
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    rows = "\n".join(f"- [{b['label']}]({series['site_url']}{b['page']}) ([download as .txt]({series['site_url']}{b['txt']}))"
                     for b in books)
    rows += f"\n\nThe whole series as one plain text file: [{SERIES_TXT}]({series['site_url']}{SERIES_TXT})"
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
        write(b["txt"], book_txt(b))
    write(SERIES_TXT, series_txt(books))
    for name in os.listdir(os.path.join(ROOT, "books")):
        if re.fullmatch(r"book-\d+-text\.html", name):  # the old plain text pages, replaced by the .txt downloads
            os.remove(os.path.join(ROOT, "books", name))
    write("index.html", welcome(books))
    write("stats.html", stats_page(books, counts))
    readme(books, counts)
    for b in books:
        c = counts[b["n"]]
        print(f"{b['label']}: {c['words']} words, {c['lines']} lines, {c['chapters']} chapters, {c['pages']} pages")


if __name__ == "__main__":
    main()
