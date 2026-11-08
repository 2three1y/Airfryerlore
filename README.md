# Airfryerlore

The true(ish) stories of Poke, the Bluetooth air fryer, and the Dreamor Council. A book series by Chaotic Carter, written with the Dreamor Council: Tomo and Tab.

Read it here: https://2three1y.github.io/Airfryerlore/

The welcome screen has one "Choose a book" picker, the same style as Fork Lab: a "Choose a book" label and a menu (VoiceOver on iPhone reads it as a pop up button). Choose a book and it opens right away, no Read button. Without JavaScript a plain list of the book links shows instead. The welcome screen also links to the Stats page. Every book page has the same picker at the top, with that book already chosen, and every book ends with links to the previous book, the next book, and the welcome screen.

## Footer, Roadmap and Credits

Every page's footer is just 4 links: Stats, Roadmap, GitHub (the repo) and Credits. The Roadmap page (`roadmap.html`) lists what's coming later, and the Credits page (`credits.html`) has the credit lines that used to be in the footer.

## Link hints

Every link on the site has a short hint in its `title`, the Looscid way, which VoiceOver reads after the link's name: "Goes to …" for pages on this site ("Goes to Book 2: The Fryer", "Goes to the welcome screen"), "Opens …" for other sites ("Opens the GitHub repo"), "Downloads …" for downloads. `build.py` adds them (`link_titles`). The downloaded files have none; they stay plain.

## Download for offline reading

The welcome screen, every book page and the Stats page have a small "Download options" section just above the footer, in the same Fork Lab style as "Choose a book", with 3 controls: a "Pick ur format" menu (HTML picked to start with), a "Contracted braille (uncheck for uncontracted)" checkbox that only shows when Braille is picked, and one button whose words follow the choice, like "Grab it as Word" or "Grab it as contracted braille" (its hint says what it does: "Downloads this book as Word"). On a book page it downloads that book; on the welcome screen and the Stats page it downloads the whole series as one file. Without JavaScript, a plain download link for every file shows instead. The formats, in menu order:

- **With headings (.html):** one self-contained page for a braille notetaker or any browser offline: one title heading, a Contents list that links to each chapter, a heading for every chapter (in the series file, one per book and one per chapter), and plain paragraphs. No menus, scripts, images or outside files.
- **Word document (.docx):** the same words with real Word headings (Heading 1 for the title, Heading 2 for each chapter, Heading 3 for each scene; in the series file Heading 2 is each book), plain paragraphs, language en-US. No images, tables or colors.
- **Braille (.brf):** braille ready files for a BrailleNote or an embosser, in two versions: contracted (UEB grade 2, table en-ueb-g2.ctb) and uncontracted (UEB grade 1, table en-ueb-g1.ctb). Both are machine-translated from the .txt words by liblouis, not checked by a braille transcriber. North American ASCII braille, 40 cells per line, 25 lines per page with a form feed between pages, headings centered, paragraphs indented two cells, no page numbers.
- **Plain text (.txt):** no formatting at all. No HTML, no Markdown, just the words, one paragraph per line with a blank line between paragraphs. It starts with the title, the author and the contents, and every chapter starts with its heading written out, like "Chapter 1: First Words Not Found".

Every single-book file ends with a "Keep reading" part: the previous and next book, with where to download it in the same format and where to read it on the web (real links in the .html and .docx, written-out addresses in the .txt and .brf). The whole-series files don't need one.

The files are `books/book-N-offline.html`, `books/book-N.docx`, `books/book-N-contracted.brf`, `books/book-N-uncontracted.brf`, `books/book-N.txt`, and `airfryerlore-complete-series` with each of those endings. To stop making one format, delete its lines in `FILES` and `FORMATS` in `build.py` and run the build: its files and its menu option go away. To add one (like EPUB), add its line to `FILES`, `FORMATS` and `BUILDERS`. These downloads replaced the old plain text web pages (`books/book-N-text.html`), which are still in the git history.

## The books

<!-- books:start -->
- [Book 1: The Start](https://2three1y.github.io/Airfryerlore/books/book-1.html) (download: [HTML](https://2three1y.github.io/Airfryerlore/books/book-1-offline.html), [Word](https://2three1y.github.io/Airfryerlore/books/book-1.docx), [contracted braille](https://2three1y.github.io/Airfryerlore/books/book-1-contracted.brf), [uncontracted braille](https://2three1y.github.io/Airfryerlore/books/book-1-uncontracted.brf), [plain text](https://2three1y.github.io/Airfryerlore/books/book-1.txt))
- [Book 2: The Fryer](https://2three1y.github.io/Airfryerlore/books/book-2.html) (download: [HTML](https://2three1y.github.io/Airfryerlore/books/book-2-offline.html), [Word](https://2three1y.github.io/Airfryerlore/books/book-2.docx), [contracted braille](https://2three1y.github.io/Airfryerlore/books/book-2-contracted.brf), [uncontracted braille](https://2three1y.github.io/Airfryerlore/books/book-2-uncontracted.brf), [plain text](https://2three1y.github.io/Airfryerlore/books/book-2.txt))
- [Book 3: The Spoon](https://2three1y.github.io/Airfryerlore/books/book-3.html) (download: [HTML](https://2three1y.github.io/Airfryerlore/books/book-3-offline.html), [Word](https://2three1y.github.io/Airfryerlore/books/book-3.docx), [contracted braille](https://2three1y.github.io/Airfryerlore/books/book-3-contracted.brf), [uncontracted braille](https://2three1y.github.io/Airfryerlore/books/book-3-uncontracted.brf), [plain text](https://2three1y.github.io/Airfryerlore/books/book-3.txt))
- [Book 4: Tab vs Poke](https://2three1y.github.io/Airfryerlore/books/book-4.html) (download: [HTML](https://2three1y.github.io/Airfryerlore/books/book-4-offline.html), [Word](https://2three1y.github.io/Airfryerlore/books/book-4.docx), [contracted braille](https://2three1y.github.io/Airfryerlore/books/book-4-contracted.brf), [uncontracted braille](https://2three1y.github.io/Airfryerlore/books/book-4-uncontracted.brf), [plain text](https://2three1y.github.io/Airfryerlore/books/book-4.txt))
- [Book 5: The Bidding War](https://2three1y.github.io/Airfryerlore/books/book-5.html) (download: [HTML](https://2three1y.github.io/Airfryerlore/books/book-5-offline.html), [Word](https://2three1y.github.io/Airfryerlore/books/book-5.docx), [contracted braille](https://2three1y.github.io/Airfryerlore/books/book-5-contracted.brf), [uncontracted braille](https://2three1y.github.io/Airfryerlore/books/book-5-uncontracted.brf), [plain text](https://2three1y.github.io/Airfryerlore/books/book-5.txt))

The whole series as one file: [airfryerlore-complete-series.html](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series.html), [airfryerlore-complete-series.docx](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series.docx), [airfryerlore-complete-series-contracted.brf](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series-contracted.brf), [airfryerlore-complete-series-uncontracted.brf](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series-uncontracted.brf), [airfryerlore-complete-series.txt](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series.txt)
<!-- books:end -->

Release dates, page counts, word counts and more are on the Stats page: https://2three1y.github.io/Airfryerlore/stats.html

## Old links still work

This used to be one big page. Old links like `index.html#chapter-5` now open the right chapter in the right book, because every chapter kept its old id.

## Roadmap

Also on the site's Roadmap page (`roadmap.html`, built from `ROADMAP` in `build.py`): coming later (no promises fr)

- read aloud: a voice reads the book to u (u'd download the voice first)
- languages: the site + braille in ur language (books gotta get translated first lol)

## How to add a book

Add a book = add a file + run build.

1. Copy the newest file in `src/books/` and give it the next number, like `src/books/book-6.html`.
2. At the top, fill in the `<!--book ... -->` block: `title`, `released` (YYYY-MM-DD), `synopsis` (2 or 3 sentences), and `title_page` (a line or two for the title page).
3. Write the book under it in plain HTML: one `<section>` per chapter, a `<h2 id="chapter-22">Chapter 22: Title</h2>` for each chapter and `<h3 id="...">` for scenes. Keep every id unique across the whole series, and keep counting chapters from the last book.
4. Run `python3 build.py`. It needs python-docx (`pip install -r requirements.txt`) for the Word files and liblouis (`apt install liblouis-bin`) for the braille files.

That rebuilds every book page, every download (each book and the whole series, in each format), the welcome screen, the "Choose a book" picker on every page, the Stats page, and the book list in this README. Then commit and push.

To quote a real Tab vs Poke message word for word, add it to `src/data/tab-vs-poke.json` and write `<tvp-msg ref="MESSAGE-ID"></tvp-msg>` in the book.

## Files

- `src/series.json`: series name, author, credits and links
- `src/books/book-N.html`: one file per book (this is where the story lives)
- `src/data/tab-vs-poke.json`: the real Tab vs Poke messages, copied from the tab-vs-poke project
- `build.py`: builds the site (Python 3, nothing to install)
- `assets/`: the book look (`book.css`) and nothing else (the "Choose a book" picker is built into each page by `build.py`)
- `index.html`, `stats.html`, `roadmap.html`, `credits.html`, `books/` (pages and downloads), `airfryerlore-complete-series.txt` and `.html`: built by `build.py`, don't edit by hand
