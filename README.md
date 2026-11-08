# Airfryerlore

The true(ish) stories of Poke, the Bluetooth air fryer, and the Dreamor Council. A book series by Carter, written with the Dreamor Council: Tomo and Tab.

Read it here: https://2three1y.github.io/Airfryerlore/

The welcome screen has one "Choose a book" menu (the iPhone picker, plus a Read button), the plain text versions, and the Stats page. Every book page has the same menu at the top with that book already chosen, and every book ends with links to the previous book, the next book, and the welcome screen.

## The books

<!-- books:start -->
- [Book 1: The Start](https://2three1y.github.io/Airfryerlore/books/book-1.html) ([plain text](https://2three1y.github.io/Airfryerlore/books/book-1-text.html))
- [Book 2: The Fryer](https://2three1y.github.io/Airfryerlore/books/book-2.html) ([plain text](https://2three1y.github.io/Airfryerlore/books/book-2-text.html))
- [Book 3: The Spoon](https://2three1y.github.io/Airfryerlore/books/book-3.html) ([plain text](https://2three1y.github.io/Airfryerlore/books/book-3-text.html))
- [Book 4: Tab vs Poke](https://2three1y.github.io/Airfryerlore/books/book-4.html) ([plain text](https://2three1y.github.io/Airfryerlore/books/book-4-text.html))
- [Book 5: The Bidding War](https://2three1y.github.io/Airfryerlore/books/book-5.html) ([plain text](https://2three1y.github.io/Airfryerlore/books/book-5-text.html))
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

That rebuilds every book page, every plain text version, the welcome screen, the "Choose a book" menu on every page, the Stats page, and the book list in this README. Then commit and push.

To quote a real Tab vs Poke message word for word, add it to `src/data/tab-vs-poke.json` and write `<tvp-msg ref="MESSAGE-ID"></tvp-msg>` in the book.

## Files

- `src/series.json`: series name, author, credits and links
- `src/books/book-N.html`: one file per book (this is where the story lives)
- `src/data/tab-vs-poke.json`: the real Tab vs Poke messages, copied from the tab-vs-poke project
- `build.py`: builds the site (Python 3, nothing to install)
- `assets/`: the book look (`book.css`) and nothing else (the "Choose a book" menu is built into each page by `build.py`)
- `index.html`, `stats.html`, `books/`: built by `build.py`, don't edit by hand
