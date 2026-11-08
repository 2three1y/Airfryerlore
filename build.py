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
whole series (see FILES: books/book-N-offline.html, book-N.docx, book-N-contracted.brf,
book-N-uncontracted.brf, book-N.txt + airfryerlore-complete-series with the same endings), stats.html, and the book list in README.md. The Python standard library, plus
python-docx for the .docx files (requirements.txt) and liblouis's lou_translate for the
.brf braille files (Debian/Ubuntu: apt install liblouis-bin).
"""
import datetime, html, io, json, math, os, re, shutil, subprocess, unicodedata, zipfile
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
# FILES and FORMATS (below) are the one list of downloads. To drop a format, delete its lines there;
# the footer menu, the no-JS links and the files follow.

# FILES: every download file. key: (end of the file on the site, file type, end of the download name,
#   no-JS link text, what the button says after "Grab it as").
FILES = {
    "html": ("-offline", "html", "", "(html, w headings)", "HTML"),        # one self-contained page: headings + contents links
    "docx": ("", "docx", "", "(word doc, .docx)", "Word"),               # real Word headings, plain paragraphs
    "brf-g2": ("-contracted", "brf", " (contracted)", "(contracted braille, ueb grade 2, .brf)", "contracted braille"),
    "brf-g1": ("-uncontracted", "brf", " (uncontracted)", "(uncontracted braille, ueb grade 1, .brf)", "uncontracted braille"),
    "txt": ("", "txt", "", "(plain text, just the words, .txt)", "plain text"),                    # plain text, no formatting at all
}
MIME = {"html": "text/html", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "brf": "text/plain", "txt": "text/plain"}
# FORMATS: the "Pick ur format" menu in Download options, in order (the first is picked to start with): (option value, option text, its files).
# Braille is one option with two files; the "Contracted braille" checkbox picks between them.
# A new format (EPUB…) is one line here plus its line in FILES and BUILDERS.
FORMATS = [
    ("html", "HTML, with headings (.html)", ["html"]),
    ("docx", "Word document (.docx)", ["docx"]),
    ("brf", "Braille (.brf)", ["brf-g2", "brf-g1"]),
    ("txt", "Plain text, no formatting (.txt)", ["txt"]),
]
FILE_KEYS = [k for _, _, keys in FORMATS for k in keys]
SERIES_FILE = "airfryerlore-complete-series"     # + .txt / .html / .docx / -contracted.brf …, at the top of the site
BLOCKS = {"p", "li", "h2", "h3", "h4", "blockquote", "div"}


def book_file(b, key):
    end, ext = FILES[key][:2]
    return f"books/book-{b['n']}{end}.{ext}"


def book_file_name(b, key):
    _, ext, tag = FILES[key][:3]
    return f"{series['series']} Book {b['n']} - {b['title']}{tag}.{ext}"


def series_file(key):
    end, ext = FILES[key][:2]
    return f"{SERIES_FILE}{'' if key == 'html' else end}.{ext}"


def series_file_name(key):
    _, ext, tag = FILES[key][:3]
    return f"{series['series']} - The Complete Series{tag}.{ext}"


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

def neighbors(b, books):
    """[("Previous book", book), ("Next book", book)] for the "Keep reading" part of a single-book download."""
    i = books.index(b)
    out = []
    if i > 0:
        out.append(("Previous book", books[i - 1]))
    if i + 1 < len(books):
        out.append(("Next book", books[i + 1]))
    return out


def keep_reading_lines(b, books, key):
    """Plain lines for .txt and .brf: where to get the previous and next book, in the same format."""
    out = []
    for which, o in neighbors(b, books):
        out += [f"{which}: {o['label']}. Download it at {series['site_url']}{book_file(o, key)}", "",
                f"Read {o['label'].split(':')[0]} on the web at {series['site_url']}{o['page']}", ""]
    return (["", "", "Keep reading", ""] + out) if out else []


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


def book_txt(b, books, key="txt"):
    """key: the format the Keep reading lines point at (txt, or a .brf made from this text)."""
    return tidy(book_txt_lines(b) + keep_reading_lines(b, books, key))


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


def keep_reading_html(b, books):
    out = []
    for which, o in neighbors(b, books):
        short = o["label"].split(":")[0]
        out.append(f"<p>{which}: {esc(o['label'])}</p>\n<ul>\n"
                   f'<li><a href="{series["site_url"]}{book_file(o, "html")}">Download {esc(o["label"])} (HTML)</a></li>\n'
                   f'<li><a href="{series["site_url"]}{o["page"]}">Read {esc(short)} on the web</a></li>\n</ul>\n')
    return ('<h2 id="keep-reading">Keep reading</h2>\n' + "".join(out)) if out else ""


def book_html(b, books):
    tp = "".join(f"<p>{esc(x)}</p>\n" for x in [series["series"], f"by {series['author']}"] + list(b.get("title_page", [])))
    toc_rows = "\n".join(f'<li><a href="#{esc(i)}">{esc(t)}</a></li>' for i, t in chapters(b))
    body = (f"<h1>{esc(b['label'])}</h1>\n{tp}"
            f'<h2 id="contents">Contents</h2>\n<ul>\n{toc_rows}\n</ul>\n' +
            book_html_body(b, 0) + f"<p>This is the end of {esc(b['label'])}.</p>\n" + keep_reading_html(b, books))
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


# -- .docx: a Word document with real headings (Heading 1 title, Heading 2 chapters, Heading 3 scenes) --

DOCX_FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # zip entry times, so a rebuild with the same words gives the same file


def _docx():
    try:
        import docx  # python-docx (requirements.txt)
    except ImportError:
        raise SystemExit("The .docx downloads need python-docx: pip install -r requirements.txt")
    return docx


def docx_bytes(title, released, build):
    """A plain Word document: headings + paragraphs, no images, tables or colors, language en-US."""
    docx = _docx()
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    d = docx.Document()
    rpr = d.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    for a in ("w:val", "w:eastAsia", "w:bidi"):
        lang.set(qn(a), "en-US")
    for c in list(d.styles.element.iter(qn("w:color"))):  # no colors anywhere: headings in the same black as the text
        c.getparent().remove(c)
    cp = d.core_properties
    cp.title, cp.author, cp.language, cp.subject = title, series["author"], "en-US", series["series"]
    cp.last_modified_by, cp.revision, cp.comments, cp.keywords, cp.category = series["author"], 1, "", "", ""
    when = datetime.datetime.combine(datetime.date.fromisoformat(released), datetime.time())
    cp.created = cp.modified = when
    build(d)
    raw = io.BytesIO()
    d.save(raw)
    out = io.BytesIO()
    with zipfile.ZipFile(raw) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zi = zipfile.ZipInfo(item.filename, DOCX_FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, zin.read(item.filename))
    return out.getvalue()


def _docx_book(d, b, shift):
    """The book's headings and paragraphs. shift=0: chapters are Heading 2; shift=1: Heading 3 (series file)."""
    for tag, t, _ in book_blocks(b):
        if tag == "p":
            d.add_paragraph(t)
        else:
            d.add_heading(t, level=min(9, int(tag[1]) + shift))


def docx_link(d, url, text):
    """A real hyperlink paragraph in Word (underlined, no color)."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    p = d.add_paragraph()
    rid = p.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rpr.append(u)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    h.append(r)
    p._p.append(h)


def book_docx(b, books):
    def build(d):
        d.add_heading(b["label"], level=1)
        for x in [series["series"], f"by {series['author']}"] + list(b.get("title_page", [])):
            d.add_paragraph(x)
        d.add_heading("Contents", level=2)
        for _, t in chapters(b):
            d.add_paragraph(t)
        _docx_book(d, b, 0)
        d.add_paragraph(f"This is the end of {b['label']}.")
        if neighbors(b, books):
            d.add_heading("Keep reading", level=2)
            for which, o in neighbors(b, books):
                d.add_paragraph(f"{which}: {o['label']}")
                docx_link(d, series["site_url"] + book_file(o, "docx"), f"Download {o['label']} (Word)")
                docx_link(d, series["site_url"] + o["page"], f"Read {o['label'].split(':')[0]} on the web")
    return docx_bytes(f"{b['label']} - {series['series']}", b.get("released") or "2026-01-01", build)


def series_docx(books):
    def build(d):
        d.add_heading(f"{series['series']}: The Complete Series", level=1)
        d.add_paragraph(f"by {series['author']}")
        d.add_paragraph(series["tagline"])
        d.add_heading("Contents", level=2)
        for b in books:
            d.add_paragraph(b["label"])
        for b in books:
            d.add_heading(b["label"], level=2)
            for x in b.get("title_page", []):
                d.add_paragraph(x)
            _docx_book(d, b, 1)
            d.add_paragraph(f"This is the end of {b['label']}.")
        d.add_paragraph(f"This is the end of the {series['series']} series, for now.")
    newest = max((b.get("released") or "2026-01-01") for b in books)
    return docx_bytes(f"{series['series']}: The Complete Series", newest, build)


# -- .brf: braille ready file, machine-translated from the .txt words by liblouis --
# UEB grade 2 (contracted, en-ueb-g2.ctb) or grade 1 (uncontracted, en-ueb-g1.ctb), North American ASCII braille, 40 cells per line, 25 lines per page,
# a form feed between pages. Headings centered with a blank line around them, paragraphs start
# two cells in (the usual braille layout). No page numbers.

BRF_DISPLAY = "en-us-brf.dis"  # North American ASCII braille
BRF_WIDTH, BRF_PAGE = 40, 25


def _no_emoji(t):
    """Emoji have no braille in the table (they come out as escape codes), so they are written as words."""
    def name(c):
        try:
            return "(" + unicodedata.name(c).lower() + " emoji)"
        except ValueError:
            return ""
    return "".join(name(c) if (ord(c) >= 0x1F000 or 0x2600 <= ord(c) < 0x2800) else
                   ("" if ord(c) in (0xFE0F, 0x200D) else c) for c in t).replace("  ", " ").strip()


def louis(lines, table):
    """Translate each line with lou_translate; one braille line comes back per print line."""
    exe = shutil.which("lou_translate")
    if not exe:
        raise SystemExit("The .brf downloads need liblouis: sudo apt-get install liblouis-bin")
    out = subprocess.run([exe, "--forward", f"{BRF_DISPLAY},{table}"], input="\n".join(lines) + "\n",
                         capture_output=True, text=True, encoding="utf-8", check=True, timeout=300).stdout
    got = out.split("\n")[:len(lines)]
    if len(got) != len(lines):
        raise SystemExit(f"lou_translate gave {len(got)} lines for {len(lines)}")
    return got


def _wrap(cells, first_indent=0):
    """Word-wrap one braille paragraph at BRF_WIDTH cells. A word longer than a line (a web address)
    is split across lines, as braille does."""
    rows, cur = [], " " * first_indent
    for w in cells.split(" "):
        if not w:
            continue
        while len(w) > BRF_WIDTH:
            room = BRF_WIDTH - len(cur) - (1 if cur.strip() else 0)
            if room < 8:
                rows.append(cur.rstrip()); cur = ""; room = BRF_WIDTH
            cur = (cur + " " if cur.strip() else cur) + w[:room]
            w = w[room:]
            rows.append(cur); cur = ""
        if not cur.strip():
            cur = cur + w
        elif len(cur) + 1 + len(w) <= BRF_WIDTH:
            cur += " " + w
        else:
            rows.append(cur); cur = w
    if cur.strip():
        rows.append(cur)
    return rows


def brf(txt, table):
    """Turn the .txt text (the same words) into a braille ready file."""
    paras, gap = [], 0
    for line in txt.split("\n"):
        if line.strip():
            paras.append((gap, _no_emoji(line))); gap = 0
        else:
            gap += 1
    braille = louis([t for _, t in paras], table)
    rows = []
    for (gap, _), cells in zip(paras, braille):
        if gap >= 2:  # a heading: centered, blank line before and after
            if rows and rows[-1]:
                rows.append("")
            for r in _wrap(cells):
                rows.append(" " * ((BRF_WIDTH - len(r)) // 2) + r)
            rows.append("")
        else:
            rows += _wrap(cells, 2)
    while rows and not rows[-1]:
        rows.pop()
    pages = [rows[i:i + BRF_PAGE] for i in range(0, len(rows), BRF_PAGE)]
    for p in pages:
        while p and not p[0] and p is not pages[0]:
            p.pop(0)  # no blank line at the top of a page
    return "\f".join("\r\n".join(p) + "\r\n" for p in pages if p)


BUILDERS = {"txt": (book_txt, series_txt), "html": (book_html, series_html), "docx": (book_docx, series_docx),
            "brf-g2": (lambda b, books: brf(book_txt(b, books, "brf-g2"), "en-ueb-g2.ctb"), lambda books: brf(series_txt(books), "en-ueb-g2.ctb")),
            "brf-g1": (lambda b, books: brf(book_txt(b, books, "brf-g1"), "en-ueb-g1.ctb"), lambda books: brf(series_txt(books), "en-ueb-g1.ctb"))}


DOWNLOAD_JS = """<script>(function(){
// Format menu + (for braille) a Contracted checkbox + one button whose words follow the choice.
var w=document.getElementById("download-pick");if(!w)return;w.hidden=false;
var what=WHAT, files=FILES; // key: [file, download name, "Grab it as …" words]
var s=document.getElementById("download-format"), box=document.getElementById("braille-choice"),
    c=document.getElementById("contracted"), btn=document.getElementById("download-go");
function key(){ return s.value=="brf" ? (c.checked ? "brf-g2" : "brf-g1") : s.value; }
function sync(){
  box.hidden = s.value!="brf";
  var f=files[key()];
  btn.textContent="Grab it as "+f[2];
  btn.title="Downloads "+what+" as "+f[2];
}
s.onchange=sync; c.onchange=sync; window.addEventListener("pageshow",sync);
btn.onclick=function(){ // a temporary <a download>, so a .txt or .brf saves as a file instead of opening as a page
  var f=files[key()], a=document.createElement("a"); a.href=f[0]; a.download=f[1];
  document.body.appendChild(a); a.click(); a.remove();
};
sync();
})();</script>"""


def downloads(books, prefix, current=None):
    """Download options, just above the footer, 3 controls: a Fork Lab style labelled select
    ("Pick ur format", HTML picked to start with), a "Contracted braille (uncheck for uncontracted)"
    checkbox shown only while Braille is picked, and one button ("Grab it as Word") whose words and
    title hint ("Downloads this book as Word") follow the choice. Without JavaScript the
    picker stays hidden and the <noscript> shows a plain <a href download> link per file instead.
    A book page downloads that book; the welcome and Stats pages download the whole series."""
    if current is not None:
        b = next(x for x in books if x["n"] == current)
        what, path, name = "this book", (lambda k: prefix + book_file(b, k)), (lambda k: book_file_name(b, k))
    else:
        what, path, name = "the whole series", (lambda k: prefix + series_file(k)), (lambda k: series_file_name(k))
    files = ",\n  ".join(f"{json.dumps(k)}: {json.dumps([path(k), name(k), FILES[k][4]], ensure_ascii=False)}" for k in FILE_KEYS)
    script = DOWNLOAD_JS.replace("WHAT", json.dumps(what)).replace("FILES", "{\n  " + files + "}")
    opts = "\n".join(f'<option value="{v}"{" selected" if i == 0 else ""}>{esc(t)}</option>' for i, (v, t, _) in enumerate(FORMATS))
    first = FILES[FORMATS[0][2][0]][4]
    links = "\n".join(f'<li><a href="{path(k)}" download="{esc(name(k))}" type="{MIME[FILES[k][1]]}" title="Downloads {what} as {FILES[k][4]}">'
                      f'download {what} {FILES[k][3]}</a></li>' for k in FILE_KEYS)
    return ('<section class="downloads" aria-labelledby="download">\n<h2 id="download">Download options</h2>\n'
            f'<p>wanna read offline? pick a format n hit grab. html + word got headings, braille is for ur notetaker, plain text works on literally anything.</p>\n'
            '<div class="download-pick" id="download-pick" hidden>\n'
            f'<label for="download-format">Pick ur format</label>\n<select id="download-format">\n{opts}\n</select>\n'
            '<p id="braille-choice" hidden><input type="checkbox" id="contracted" checked> <label for="contracted">Contracted braille (uncheck for uncontracted)</label></p>\n'
            f'<button type="button" id="download-go" title="Downloads {what} as {first}">Grab it as {first}</button>\n'
            '</div>\n' + script +
            f'\n<noscript>\n<ul>\n{links}\n</ul>\n</noscript>\n</section>\n')


def link_titles(page, books):
    """Looscid-style link hints (Carter, Nov 7): every link on a site page gets a short title that
    VoiceOver reads as a hint after the link's name. "Goes to …" for pages on this site, "Opens …"
    for other sites, "Downloads …" for download links. Not used inside the downloaded files."""
    labels = {f"book-{b['n']}.html": b["label"] for b in books}
    def hint(m):
        attrs, text = m.group(1), m.group(2)
        if " title=" in attrs:
            return m.group(0)
        href = re.search(r'href="([^"]*)"', attrs).group(1)
        words = re.sub(r"<[^>]+>", "", html.unescape(text)).strip()
        if href.startswith("#"):
            t = f"Goes to {words}"
        elif href.startswith(("http://", "https://")):
            if href.rstrip("/") == series["repo_url"].rstrip("/"):
                t = "Opens the GitHub repo"
            elif href.rstrip("/") == series["made_by_url"].rstrip("/"):
                t = "Opens Chaotic Carter's website"
            else:
                t = f"Opens {words}"
        else:
            name = href.split("#")[0].rsplit("/", 1)[-1]
            if "#" in href:
                t = f"Goes to {words}"
            elif name == "index.html":
                t = "Goes to the welcome screen"
            elif name == "stats.html":
                t = "Goes to Stats"
            elif name == "roadmap.html":
                t = "Goes to Roadmap"
            elif name == "credits.html":
                t = "Goes to Credits"
            elif name in labels:
                t = f"Goes to {labels[name]}"
            else:
                t = f"Goes to {words}"
        return f'<a {attrs} title="{esc(t)}">{text}</a>'
    return re.sub(r'<a ((?:[^>]*\s)?href="[^"]*"[^>]*)>(.*?)</a>', hint, page, flags=re.S)


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


PICK_JS = """<script>(function(){
// Fork Lab's picker (2three1y/forklab home.js): choosing a book opens it right away. No Read button.
var w=document.getElementById("book-pick");if(!w)return;w.hidden=false;
var pick=document.getElementById("pick");
pick.addEventListener("change",function(){ if(pick.value) location.href=pick.value; });
// Coming back with the Back button: reset to how the page started ("Choose a book…", or this book on a book page).
window.addEventListener("pageshow",function(){ for(var i=0;i<pick.options.length;i++) pick.options[i].selected=pick.options[i].defaultSelected; });
})();</script>"""


def book_links(books, prefix, current):
    rows = []
    for b in books:
        cur = ' aria-current="page"' if current == b["n"] else ""
        rows.append(f'<li><a href="{prefix}{b["page"]}"{cur}>{esc(b["label"])}</a></li>')
    return "\n".join(rows)


def picker(books, prefix, current=None, hint=False):
    """The book picker, copied from Fork Lab: a visible "Choose a book" label, then a native
    <select> (iPhone VoiceOver reads it as a pop up button). The first option is "Choose a book…",
    or on a book page that book is already chosen. Choosing a book opens it right away; there is
    no Read button. The small script right after it shows the picker and runs it. Without
    JavaScript the picker stays hidden and the <noscript> list of book links shows instead."""
    first = ' selected' if current is None else ''
    opts = [f'<option value=""{first}>Choose a book…</option>']
    for b in books:
        sel = ' selected' if current == b["n"] else ''
        opts.append(f'<option value="{prefix}{b["page"]}"{sel}>{esc(b["label"])}</option>')
    say = '<p>Choose a book from the menu and it opens right away.</p>\n' if hint else ''
    return ('<div class="book-pick" id="book-pick" hidden>\n' + say +
            '<label for="pick">Choose a book</label>\n<select id="pick">\n' + "\n".join(opts) +
            '\n</select>\n</div>\n' + PICK_JS + '\n<noscript>\n<ul class="book-list">\n' +
            book_links(books, prefix, current) + '\n</ul>\n</noscript>\n')


def selector(books, prefix, current=None):
    """The book picker at the top of a book page (and the stats page)."""
    return '<div class="selector">\n' + picker(books, prefix, current) + '</div>\n'


def footer(prefix):
    """Just 4 links. The credit lines live on the Credits page."""
    return f"""<footer>
<ul class="footer-links">
<li><a href="{prefix}stats.html">Stats</a></li>
<li><a href="{prefix}roadmap.html">Roadmap</a></li>
<li><a href="{series['repo_url']}">GitHub</a></li>
<li><a href="{prefix}credits.html">Credits</a></li>
</ul>
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
{downloads(books, '../', b['n'])}</main>
{footer('../')}</div>
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
<p>Welcome to the Dreamor Council. Start with Book 1 and keep going, or jump to any book. To read offline, Download options near the bottom of this page has the whole series as one file, and every book page has Download options for that book.</p>
<h2 id="select-a-book">Books</h2>
{picker(books, "", hint=True)}
{downloads(books, '')}</main>
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
{downloads(books, '')}</main>
{footer('')}</div>
</div>
</body>
</html>
""")



ROADMAP = ["read aloud: a voice reads the book to u (u'd download the voice first)",
           "languages: the site + braille in ur language (books gotta get translated first lol)"]


def simple_page(books, title, body):
    """A small page in the same style as Stats: the book picker, one h1, a bit of text, the footer."""
    return (head(f'{title} - {series["series"]}', "") + f"""<body>
<div class="desk">
{selector(books, "")}<div class="paper">
<main>
<h1>{esc(title)}</h1>
{body}<p><a href="index.html">Welcome screen</a></p>
</main>
{footer('')}</div>
</div>
</body>
</html>
""")


def roadmap_page(books):
    items = "\n".join(f"<li>{esc(x)}</li>" for x in ROADMAP)
    return simple_page(books, "Roadmap", f"<p>coming later (no promises fr)</p>\n<ul>\n{items}\n</ul>\n")


def credits_page(books):
    return simple_page(books, "Credits",
                       f'<p>made by <a href="{series["made_by_url"]}">Chaotic Carter</a>. '
                       f'written w the Dreamor Council: Carter, Tomo and Tab.</p>\n')


def readme(books, counts):
    p = os.path.join(ROOT, "README.md")
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    rows = "\n".join(f"- [{b['label']}]({series['site_url']}{b['page']}) (download: " + ", ".join(f"[{FILES[k][4]}]({series['site_url']}{book_file(b, k)})" for k in FILE_KEYS) + ")"
                     for b in books)
    rows += "\n\nThe whole series as one file: " + ", ".join(f"[{series_file(k)}]({series['site_url']}{series_file(k)})" for k in FILE_KEYS)
    block = f"<!-- books:start -->\n{rows}\n<!-- books:end -->"
    if "<!-- books:start -->" in old:
        new = re.sub(r"<!-- books:start -->.*?<!-- books:end -->", block, old, flags=re.S)
    else:
        new = old + "\n" + block + "\n"
    open(p, "w", encoding="utf-8").write(new)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(text, bytes):
        open(path, "wb").write(text)
    elif rel.endswith(".brf"):
        open(path, "w", encoding="ascii", newline="").write(text)  # braille ASCII, CRLF lines + form feeds as written
    else:
        open(path, "w", encoding="utf-8").write(text)


def main():
    books = load_books()
    counts = {b["n"]: count(b) for b in books}
    for b in books:
        write(b["page"], link_titles(book_page(books, b), books))
        for k in FILE_KEYS:
            write(book_file(b, k), BUILDERS[k][0](b, books))
    for k in FILE_KEYS:
        write(series_file(k), BUILDERS[k][1](books))
    dropped = [key for key in BUILDERS if key not in FILE_KEYS]
    for ext in dropped:  # a format taken out of FORMATS: remove its old files too
        for rel in [book_file(b, ext) for b in books] + [series_file(ext)]:
            if os.path.exists(os.path.join(ROOT, rel)):
                os.remove(os.path.join(ROOT, rel))
    for name in os.listdir(os.path.join(ROOT, "books")):
        if re.fullmatch(r"book-\d+-text\.html", name):  # the old plain text pages, replaced by the .txt downloads
            os.remove(os.path.join(ROOT, "books", name))
    write("index.html", link_titles(welcome(books), books))
    write("stats.html", link_titles(stats_page(books, counts), books))
    write("roadmap.html", link_titles(roadmap_page(books), books))
    write("credits.html", link_titles(credits_page(books), books))
    readme(books, counts)
    for b in books:
        c = counts[b["n"]]
        print(f"{b['label']}: {c['words']} words, {c['lines']} lines, {c['chapters']} chapters, {c['pages']} pages")


if __name__ == "__main__":
    main()
