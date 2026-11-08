# Airfryerlore

The true(ish) stories of Poke, the Bluetooth air fryer, and the Dreamor Council. A book series by Chaotic Carter, written with the Dreamor Council: Tomo and Tab.

Read it here: https://2three1y.github.io/Airfryerlore/

The welcome screen has one "Choose a book" menu (the iPhone picker, plus a Read button) and the Stats page. Every book page has the same menu at the top with that book already chosen, and every book ends with links to the previous book, the next book, and the welcome screen.

## Download for offline reading

Every page ends with a small Download section. On a book page it downloads that book; on the welcome screen and the Stats page it downloads the whole series as one file. Each comes in two formats:

- **Plain text (.txt):** no formatting at all. No HTML, no Markdown, just the words, one paragraph per line with a blank line between paragraphs. It starts with the title, the author and the contents, and every chapter starts with its heading written out, like "Chapter 1: First Words Not Found".
- **With headings (.html):** one self-contained page for a braille notetaker or any browser offline: one title heading, a Contents list that links to each chapter, a heading for every chapter (in the series file, one per book and one per chapter), and plain paragraphs. No menus, scripts, images or outside files.

The files are `books/book-N.txt`, `books/book-N-offline.html`, `airfryerlore-complete-series.txt` and `airfryerlore-complete-series.html`. To stop making one format, delete its line in `FORMATS` in `build.py` and run the build: its files and footer links go away. These downloads replaced the old plain text web pages (`books/book-N-text.html`), which are still in the git history.

## The books

<!-- books:start -->
- [Book 1: The Start](https://2three1y.github.io/Airfryerlore/books/book-1.html) (download: [.txt](https://2three1y.github.io/Airfryerlore/books/book-1.txt), [.html](https://2three1y.github.io/Airfryerlore/books/book-1-offline.html))
- [Book 2: The Fryer](https://2three1y.github.io/Airfryerlore/books/book-2.html) (download: [.txt](https://2three1y.github.io/Airfryerlore/books/book-2.txt), [.html](https://2three1y.github.io/Airfryerlore/books/book-2-offline.html))
- [Book 3: The Spoon](https://2three1y.github.io/Airfryerlore/books/book-3.html) (download: [.txt](https://2three1y.github.io/Airfryerlore/books/book-3.txt), [.html](https://2three1y.github.io/Airfryerlore/books/book-3-offline.html))
- [Book 4: Tab vs Poke](https://2three1y.github.io/Airfryerlore/books/book-4.html) (download: [.txt](https://2three1y.github.io/Airfryerlore/books/book-4.txt), [.html](https://2three1y.github.io/Airfryerlore/books/book-4-offline.html))
- [Book 5: The Bidding War](https://2three1y.github.io/Airfryerlore/books/book-5.html) (download: [.txt](https://2three1y.github.io/Airfryerlore/books/book-5.txt), [.html](https://2three1y.github.io/Airfryerlore/books/book-5-offline.html))

The whole series as one file: [airfryerlore-complete-series.txt](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series.txt), [airfryerlore-complete-series.html](https://2three1y.github.io/Airfryerlore/airfryerlore-complete-series.html)
<!-- books:end -->

Release dates, page counts, word counts and more are on the Stats page: https://2three1y.github.io/Airfryerlore/stats.html

## Old links still work

This used to be one big page. Old links like `index.html#chapter-5` now open the right chapter in the right book, because every chapter kept its old id.

## How to add a book

Add a book = add a file + run build.

1. Copy the newest file in `src/books/` and give it the next number, like `src/books/book-6.html`.
2. At the top, fill in the `<!--book ... -->` block: `title`, `released` (YYYY-MM-DD), `synopsis` (2 or 3 sentences), and `title_page` (a line or two for the title page).
3. Write the book under it in plain HTML: one `<section>` per chapter, a `<h2 id="chapter-22">Chapter 22: Title</h2>` for each chapter and `<h3 id="...">` for scenes. Keep every id unique across the whole series, and keep counting chapters from the last book.
4. Run `python3 build.py`.

That rebuilds every book page, every download (each book and the whole series, in each format), the welcome screen, the "Choose a book" menu on every page, the Stats page, and the book list in this README. Then commit and push.

To quote a real Tab vs Poke message word for word, add it to `src/data/tab-vs-poke.json` and write `<tvp-msg ref="MESSAGE-ID"></tvp-msg>` in the book.

## Files

- `src/series.json`: series name, author, credits and links
- `src/books/book-N.html`: one file per book (this is where the story lives)
- `src/data/tab-vs-poke.json`: the real Tab vs Poke messages, copied from the tab-vs-poke project
- `build.py`: builds the site (Python 3, nothing to install)
- `assets/`: the book look (`book.css`) and nothing else (the "Choose a book" menu is built into each page by `build.py`)
- `index.html`, `stats.html`, `books/` (pages and downloads), `airfryerlore-complete-series.txt` and `.html`: built by `build.py`, don't edit by hand
