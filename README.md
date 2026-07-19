# Home Is Where We Make Our Fire

A no-build static website for **the chronicle of Celenneth** — a solo
*The One Ring, 2ⁿᵈ Edition* campaign set in the Third Age of Middle-earth.
Warm parchment / dark-red aesthetic drawn from the **istya** style guide;
solo-play framing after **Children of Fear**; separate section pages after
**Caul**. Plain HTML + one stylesheet, generated from source markdown.

Open `index.html` in a browser, or serve the folder statically:

```sh
python3 -m http.server 8791
```

## Pages

| Path | What it holds |
| --- | --- |
| `index.html` | **The Codex** — masthead and cards into every section. |
| `chronicle/` | The narrative, **one page per book** (13 books), each with an on-page table of contents, its chapters as sections, and prev/next paging. |
| `company/` | **The Company** — Celenneth, Linnea, and Brynja, each with bio, portrait, and a full **One Ring 2e stat block** rendered from the Foundry actor JSON. |
| `dramatis-personae/` | Everyone met along the way — **Companions & Kin** and **Servants of the Shadow** — with portraits and (where they exist) sheet PDFs. |
| `timeline/` | A chronological reckoning in the calendar of Middle-earth. |
| `atlas/` | A gazetteer of the lands walked, keyed to the books they appear in. |
| `hearth.css` | The theme. |

## Source

The narrative is extracted from `TOR Celenneth/Celenneth Narrative.docx` into
token-friendly markdown under **`source/narrative/`** — one file per chapter,
grouped into `book-01/` … `book-13/`, plus `appendix-characters/`,
`appendix-timeline/`, `images/`, and an `INDEX.md` manifest. This markdown is
the source of truth for the site's prose.

Character portraits (optimized) and the extracted scene `images/` live in
`source/` and are copied into `assets/` at build. The TOR Foundry actor JSONs
are read at build time from the sibling `../TOR Celenneth/` folder. The
character-sheet **PDFs are not stored in this repo** — set `SHEETS_BASE_URL`
in `build_site.py` to their external host to emit "Full Character Sheet" links.

## Regenerating

```sh
python3 build_site.py
```

Re-running wipes and rebuilds the generated category directories only
(`chronicle/`, `company/`, `dramatis-personae/`, `timeline/`, `atlas/`,
`assets/`, `index.html`). `hearth.css`, `README.md`, `source/`, `build_site.py`
and `.git` are preserved.

### Images

Scene images and portraits are stored web-optimized as **WebP** (resized, ~q80)
under `source/narrative/images/` and `source/portraits/`; `build_site.py` copies
them into `assets/`. To re-derive them from the originals (the docx's extracted
PNGs and the portrait PNGs in `../TOR Celenneth/`):

```sh
npm install sharp && node tools/optimize_images.mjs
```

### Editing the roster

The Company / Dramatis Personae split, roles, portraits, PDFs, and Foundry
actors are defined in the `CHARS` / `COMPANY` / `DP_ALLIES` / `DP_FOES`
tables near the bottom of `build_site.py`. Adjust and rebuild.

> **First pass.** Prose is passed through from the narrative extraction. Several
> appendix character bios are sparse in the source (their story lives in the
> chronicle) and are marked as such; the Atlas gazetteer text is authored.
