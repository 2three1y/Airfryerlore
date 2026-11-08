#!/usr/bin/env python3
"""Build the Airfryerlore series site.

Add a book = add one file to src/books/ (book-6.html, book-7.html, ...) and run:

    python3 build.py

Each book file starts with a <!--book {...} --> block (JSON: title, released,
synopsis, title_page) and then the book itself as plain HTML: <section>s with
<h2 id> chapters and <h3 id> scenes. A Tab vs Poke message can be pulled in,
word for word, with <tvp-msg ref="MESSAGE-ID"></tvp-msg> (from src/data/tab-vs-poke.json).

This regenerates: index.html (welcome screen + old link redirects),
books/book-N.html (web version), the offline downloads for each book and for the
whole series (see FORMATS: books/book-N.txt + books/book-N-offline.html,
airfryerlore-complete-series.txt + .html), stats.html, and the book list in README.md. Only the Python standard library.
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


# ---- Offline downloads: one file per book + one file for the whole series, per format ----
# FORMATS is the one list of download formats. To drop a format, delete its line here
# (and, if you like, its *_file function below); the footer links and the files follow.

def _fmt(ext, label):
    return {"ext": ext, "label": label}


FORMATS = [
    _fmt("txt", "(.txt, plain)"),                # plain text, no formatting at all
    _fmt("html", "(with headings, .html)"),      # one self-contained page: headings + contents links
]
SERIES_FILE = "airfryerlore-complete-series"     # + .txt / .html, at the top of the site
BLOCKS = {"p", "li", "h2", "h3", "h4", "blockquote", "div"}


def book_file(b, ext):
    return f"books/book-{b['n']}.{ext}" if ext == "txt" else f"books/book-{b['n']}-offline.{ext}"


def book_file_name(b, ext):
    return f"{series['series']} Book {b['n']} - {b['title']}.{ext}"


def series_file(ext):
    return f"{SERIES_FILE}.{ext}"


def series_file_name(ext):
    return f"{series['series']} - The Complete Series.{ext}"


class _Blocks(HTMLParser):
    """Turns a book's HTML into blocks (tag, text, id), in reading order."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.tag, self.id, self.lists = [], [], None, None, []

    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.out.append((self.tag or "p", t, self.id))
        self.buf, self.id = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "ul":
            self.lists.append(dict(attrs).get("class"))
        if tag in BLOCKS:
            self.flush()
            self.tag, self.id = tag, dict(attrs).get("id")
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


def book_blocks(b):
    p = _Blocks()
    p.feed(render_msgs(b["body"], "text"))  # the same words the Stats page counts
    p.flush()
    return [(("p" if tag in ("li", "blockquote", "div") else tag), t, i) for tag, t, i in p.out]


def title_lines(b):
    return [series["series"], b["label"], f"by {series['author']}"] + list(b.get("title_page", []))


# -- .txt: no HTML, no Markdown, one paragraph per line with a blank line between --

def book_txt_lines(b):
    blocks = book_blocks(b)
    out = title_lines(b) + [f"Read it online: {series['site_url']}{b['page']}", "", "", "Contents", ""]
    out += [t for tag, t, _ in blocks if tag == "h2"]
    for tag, t, _ in blocks:
        out += ["", "", t, ""] if tag != "p" else [t, ""]
    return out + ["", f"This is the end of {b['label']}."]


def tidy(lines):
    """Paragraphs separated by one blank line, headings by two. Never more."""
    return re.sub(r"\n{4,}", "\n\n\n", "\n".join(lines)).strip("\n") + "\n"


def book_txt(b):
    return tidy(book_txt_lines(b))


def series_txt(books):
    out = [f"{series['series']}: The Complete Series", f"by {series['author']}",
           series["tagline"], f"Read it online: {series['site_url']}", "", "", "Books in this file", ""]
    out += [b["label"] for b in books]
    for b in books:
        out += ["", "", "", ""] + book_txt_lines(b)
    return tidy(out + ["", "", f"This is the end of the {series['series']} series, for now."])


# -- .html: one self-contained page, headings + a Contents list, nothing else --

OFFLINE_STYLE = ("body{font-family:Georgia,serif;line-height:1.6;max-width:40em;margin:0 auto;padding:1em}")


def offline_doc(title, body):
    return (f'<!DOCTYPE html>\n<html lang="en-US">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{esc(title)}</title>\n<style>{OFFLINE_STYLE}</style>\n</head>\n<body>\n'
            f'{body}</body>\n</html>\n')


def book_html_body(b, shift, idp=""):
    """The book's headings and paragraphs. shift=0: chapters are h2; shift=1: h3 (series file)."""
    out = []
    for tag, t, i in book_blocks(b):
        if tag == "p":
            out.append(f"<p>{esc(t)}</p>")
        else:
            h = min(6, int(tag[1]) + shift)
            out.append(f'<h{h} id="{esc(idp + i)}">{esc(t)}</h{h}>' if i else f"<h{h}>{esc(t)}</h{h}>")
    return "\n".join(out) + "\n"


def chapters(b):
    return [(i, t) for tag, t, i in book_blocks(b) if tag == "h2" and i]


def book_html(b):
    tp = "".join(f"<p>{esc(x)}</p>\n" for x in [series["series"], f"by {series['author']}"] + list(b.get("title_page", [])))
    toc_rows = "\n".join(f'<li><a href="#{esc(i)}">{esc(t)}</a></li>' for i, t in chapters(b))
    body = (f"<h1>{esc(b['label'])}</h1>\n{tp}"
            f'<h2 id="contents">Contents</h2>\n<ul>\n{toc_rows}\n</ul>\n' +
            book_html_body(b, 0) + f"<p>This is the end of {esc(b['label'])}.</p>\n")
    return offline_doc(f"{b['label']} - {series['series']}", body)


def series_html(books):
    toc_rows = []
    for b in books:
        sub = "\n".join(f'<li><a href="#{esc(i)}">{esc(t)}</a></li>' for i, t in chapters(b))
        toc_rows.append(f'<li><a href="#book-{b["n"]}">{esc(b["label"])}</a>\n<ul>\n{sub}\n</ul>\n</li>')
    parts = []
    for b in books:
        tp = "".join(f"<p>{esc(x)}</p>\n" for x in b.get("title_page", []))
        parts.append(f'<h2 id="book-{b["n"]}">{esc(b["label"])}</h2>\n{tp}' + book_html_body(b, 1) +
                     f"<p>This is the end of {esc(b['label'])}.</p>\n")
    body = (f"<h1>{esc(series['series'])}: The Complete Series</h1>\n<p>by {esc(series['author'])}</p>\n"
            f"<p>{esc(series['tagline'])}</p>\n"
            f'<h2 id="contents">Contents</h2>\n<ul>\n' + "\n".join(toc_rows) + "\n</ul>\n" + "".join(parts) +
            f"<p>This is the end of the {esc(series['series'])} series, for now.</p>\n")
    return offline_doc(f"{series['series']}: The Complete Series", body)


BUILDERS = {"txt": (book_txt, series_txt), "html": (book_html, series_html)}


def downloads(books, prefix, current=None):
    """Footer Download group: real <a href download> links, no JavaScript.
    A book page downloads that book; the welcome and Stats pages download the whole series."""
    if current is not None:
        b = next(x for x in books if x["n"] == current)
        what, files = "Download this book", [(prefix + book_file(b, f["ext"]), book_file_name(b, f["ext"]), f) for f in FORMATS]
    else:
        what, files = "Download the whole series", [(prefix + series_file(f["ext"]), series_file_name(f["ext"]), f) for f in FORMATS]
    mime = {"txt": "text/plain", "html": "text/html"}
    links = "\n".join(f'<li><a href="{href}" download="{esc(name)}" type="{mime.get(f["ext"], "")}">{what} {esc(f["label"])}</a></li>'
                      for href, name, f in files)
    return ('<nav class="downloads" aria-labelledby="download">\n<h2 id="download">Download</h2>\n'
            '<p>For offline reading. The .txt file is plain text with no formatting. The .html file has headings and a Contents list.</p>\n'
            f'<ul>\n{links}\n</ul>\n</nav>\n')


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


MENU_JS = """<script>(function(){
var w=document.getElementById("book-menu");if(!w)return;
var b=document.getElementById("book-menu-button"),l=document.getElementById("book-menu-list");
var a=[].slice.call(l.querySelectorAll("a"));
w.hidden=false;
function go(i){a[(i+a.length)%a.length].focus();}
function open(i){l.hidden=false;b.setAttribute("aria-expanded","true");
if(i==null){i=0;for(var k=0;k<a.length;k++){if(a[k].hasAttribute("aria-current"))i=k;}}go(i);}
function close(back){if(l.hidden)return;l.hidden=true;b.setAttribute("aria-expanded","false");if(back)b.focus();}
b.addEventListener("click",function(){if(l.hidden)open();else close(true);});
b.addEventListener("keydown",function(e){
if(e.key==="ArrowDown"){e.preventDefault();open();}
else if(e.key==="ArrowUp"){e.preventDefault();open(a.length-1);}});
l.addEventListener("keydown",function(e){var i=a.indexOf(document.activeElement);
if(e.key==="ArrowDown"){e.preventDefault();go(i+1);}
else if(e.key==="ArrowUp"){e.preventDefault();go(i-1);}
else if(e.key==="Home"){e.preventDefault();go(0);}
else if(e.key==="End"){e.preventDefault();go(a.length-1);}});
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&!l.hidden){e.preventDefault();close(true);}});
document.addEventListener("pointerdown",function(e){if(!w.contains(e.target))close(false);});
document.addEventListener("click",function(e){if(!w.contains(e.target))close(false);});
w.addEventListener("focusout",function(e){if(e.relatedTarget&&!w.contains(e.relatedTarget))close(false);});
})();</script>"""


def book_links(books, prefix, current):
    rows = []
    for b in books:
        cur = ' aria-current="page"' if current == b["n"] else ""
        rows.append(f'<li><a href="{prefix}{b["page"]}"{cur}>{esc(b["label"])}</a></li>')
    return "\n".join(rows)


def picker(books, prefix, current=None):
    """The book menu: a "Choose a book" menu pop-up button. Tapping it opens the 5 books
    right below it as plain links; tapping one opens that book. The small script right after it
    shows the button and runs the menu (focus to the first or current book, arrow keys, Escape,
    tap outside). Without JavaScript the button stays hidden and the <noscript> links show instead."""
    links = book_links(books, prefix, current)
    return ('<div class="book-menu" id="book-menu" hidden>\n'
            '<button type="button" id="book-menu-button" aria-haspopup="menu" aria-expanded="false">Choose a book</button>\n'
            '<ul class="book-menu-list" id="book-menu-list" hidden>\n' + links + '\n</ul>\n</div>\n' +
            MENU_JS + '\n<noscript>\n<ul class="book-list">\n' + links + '\n</ul>\n</noscript>\n')


def selector(books, prefix, current=None):
    """The book menu at the top of a book page (and the stats page)."""
    return '<div class="selector">\n' + picker(books, prefix, current) + '</div>\n'


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
<p>Welcome to the Dreamor Council. Start with Book 1 and keep going, or jump to any book. To read offline, the Download section at the bottom of this page has the whole series as one file, and every book page has a Download section for that book.</p>
<h2 id="select-a-book">Books</h2>
{picker(books, "")}
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
    rows = "\n".join(f"- [{b['label']}]({series['site_url']}{b['page']}) (download: " + ", ".join(f"[.{f['ext']}]({series['site_url']}{book_file(b, f['ext'])})" for f in FORMATS) + ")"
                     for b in books)
    rows += "\n\nThe whole series as one file: " + ", ".join(f"[{series_file(f['ext'])}]({series['site_url']}{series_file(f['ext'])})" for f in FORMATS)
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
        for f in FORMATS:
            write(book_file(b, f["ext"]), BUILDERS[f["ext"]][0](b))
    for f in FORMATS:
        write(series_file(f["ext"]), BUILDERS[f["ext"]][1](books))
    dropped = [ext for ext in BUILDERS if ext not in {f["ext"] for f in FORMATS}]
    for ext in dropped:  # a format taken out of FORMATS: remove its old files too
        for rel in [book_file(b, ext) for b in books] + [series_file(ext)]:
            if os.path.exists(os.path.join(ROOT, rel)):
                os.remove(os.path.join(ROOT, rel))
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
