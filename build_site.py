#!/usr/bin/env python3
"""
Build the static site 'Home Is Where We Make Our Fire' — the chronicle of
Celenneth, a solo The One Ring 2e campaign.

No build framework: reads the token-friendly markdown in source/narrative/,
the TOR Foundry actor JSONs + portraits + character-sheet PDFs from the
sibling 'TOR Celenneth' folder, and emits plain HTML + one stylesheet.

    python3 build_site.py

Regenerating wipes and rebuilds the generated category directories only;
hearth.css, README.md, source/, build_site.py and .git are preserved.
"""
import os, re, json, glob, shutil, html
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "source", "narrative")
TOR  = "/home/hewhocutsdown/Working/TOR Celenneth"

SITE_TITLE = "Home Is Where We Make Our Fire"
SITE_TAG   = "The Chronicle of Celenneth"

# Character-sheet PDFs are hosted OUTSIDE this repo. Set this to their external
# base URL (no trailing slash) to emit "Full Character Sheet (PDF)" links, e.g.
# "https://sortilege.online/celenneth/sheets".  Empty => no sheet links.
SHEETS_BASE_URL = ""

# ------------------------------------------------------------------ helpers
def slug(s):
    s = s.lower().strip().replace("’","").replace("'","").replace("/","-")
    s = re.sub(r"[^a-z0-9]+","-",s)
    return re.sub(r"-+","-",s).strip("-")

NUMWORDS = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight",
            "Nine","Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen"]

def cap_last(dotted):
    base = dotted.split(".")[-1] if dotted else dotted
    return base[:1].upper()+base[1:] if base else base

def val(x):
    """Foundry fields are often {'value': N}; unwrap them."""
    if isinstance(x, dict):
        return x.get("value")
    return x

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t

def md_to_html(text, img_prefix="../assets/images/"):
    """Minimal markdown -> HTML for our extracted prose.
    Handles: ### headings, ![](..img..) images, '- ' lists, paragraphs
    with **bold**/*italic*.  Blocks are separated by blank lines."""
    out = []
    # ensure a scene-break sentinel is always its own block
    text = re.sub(r"(?m)^[ \t]*⁂[ \t]*$", "\n\n⁂\n\n", text)
    blocks = re.split(r"\n\s*\n", text.strip())
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b == "⁂":  # normalized scene break
            out.append('<div class="scene-break"></div>')
            continue
        # image-only block (may be one or more image lines)
        img_lines = [l for l in b.splitlines() if l.strip()]
        if all(re.match(r"^!\[.*?\]\(.*?\)$", l.strip()) for l in img_lines):
            for l in img_lines:
                m = re.match(r"^!\[.*?\]\((.*?)\)$", l.strip())
                fn = os.path.basename(m.group(1))
                out.append(f'<img src="{img_prefix}{fn}" alt="">')
            continue
        if b.startswith("### "):
            out.append(f"<h3>{inline(b[4:].strip())}</h3>")
            continue
        # list block
        if all(l.strip().startswith("- ") for l in b.splitlines() if l.strip()):
            items = "".join(f"<li>{inline(l.strip()[2:])}</li>"
                            for l in b.splitlines() if l.strip())
            out.append(f"<ul>{items}</ul>")
            continue
        # paragraph (join wrapped lines)
        para = " ".join(l.strip() for l in b.splitlines() if l.strip())
        out.append(f"<p>{inline(para)}</p>")
    return "\n".join(out)

# ------------------------------------------------------------------ footnotes (the actual-play Ledger)
FN_DEF = re.compile(r"^\[\^([\w-]+)\]:\s?(.*)$")
FN_REF = re.compile(r"\[\^([\w-]+)\]")

def md_with_footnotes(text, prefix):
    """Markdown -> (body_html, ledger_html). Footnote definitions
    `[^id]: text` are pulled from the body; inline `[^id]` references become
    numbered superscripts linking to a per-chapter Ledger of game-mechanical
    events (see STORY-BIBLE.md section 5)."""
    defs, body_lines = {}, []
    for l in text.split("\n"):
        m = FN_DEF.match(l.strip())
        if m:
            defs[m.group(1)] = m.group(2).strip()
        else:
            body_lines.append(l)
    body = "\n".join(body_lines)
    order = []
    for m in FN_REF.finditer(body):
        if m.group(1) not in order:
            order.append(m.group(1))
    num = {fid: i + 1 for i, fid in enumerate(order)}
    html_body = md_to_html(body)  # refs survive escaping as literal [^id]

    def _ref(m):
        fid = m.group(1)
        n = num.get(fid)
        if n is None:
            return ""  # dangling reference: drop it
        return (f'<sup class="fnref" id="{prefix}-ref-{fid}">'
                f'<a href="#{prefix}-fn-{fid}">{n}</a></sup>')
    html_body = FN_REF.sub(_ref, html_body)

    ledger = ""
    if order:
        items = ""
        for fid in order:
            items += (f'<li id="{prefix}-fn-{fid}"><span class="fn-n">{num[fid]}</span>'
                      f'<span class="fn-t">{inline(defs.get(fid, ""))}</span>'
                      f'<a class="fn-back" href="#{prefix}-ref-{fid}" title="back to text">↩</a></li>')
        ledger = (f'<aside class="ledger"><h4>Ledger</h4>'
                  f'<ol class="fnlist">{items}</ol></aside>')
    return html_body, ledger

# ------------------------------------------------------------------ page chrome
NAV = [
    ("Home",              "index.html"),
    ("Chronicle",         "chronicle/index.html"),
    ("Company",           "company/index.html"),
    ("Dramatis Personae", "dramatis-personae/index.html"),
    ("Timeline",          "timeline/index.html"),
    ("Atlas",             "atlas/index.html"),
]

def page(title, body, active, depth=0, desc=""):
    up = "../" * depth
    nav = "".join(
        f'<a href="{up}{href}"{" class=\"active\"" if label==active else ""}>{label}</a>'
        for label, href in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Cinzel+Decorative:wght@400;700&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}hearth.css">
</head>
<body>
<nav class="topnav"><span class="brand">Home Is Where We Make Our Fire</span>{nav}</nav>
<div class="wrap">
{body}
</div>
<footer class="foot"><span class="mark">❂ ❂ ❂</span>The Chronicle of Celenneth · A solo The One Ring, 2ⁿᵈ Edition campaign</footer>
</body>
</html>"""

def crumb(depth, *trail):
    up = "../" * depth
    parts = [f'<a href="{up}index.html">Home</a>']
    for label, href in trail[:-1]:
        parts.append(f'<a href="{up}{href}">{label}</a>')
    parts.append(f'<span>{trail[-1][0]}</span>')
    return '<div class="crumb">' + '<span class="sep">›</span>'.join(parts) + '</div>'

# ------------------------------------------------------------------ narrative model
def read_book(bookdir):
    """Return (intro_html, [chapters]) for a book directory."""
    bn = int(re.search(r"book-(\d+)", bookdir).group(1))
    intro = []
    chapters = []
    for fn in sorted(os.listdir(bookdir)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(bookdir, fn), encoding="utf-8").read()
        lines = raw.splitlines()
        h1 = lines[0][2:].strip() if lines and lines[0].startswith("# ") else fn
        # strip the '# heading' line and the '*Book N*' echo — but keep the dateline
        body_lines = lines[1:]
        while body_lines and (not body_lines[0].strip()
                              or re.match(r"^\*Book\b.*\*$", body_lines[0].strip(), re.I)):
            body_lines.pop(0)
        # a leading italic line is the chapter dateline
        cdate = ""
        if body_lines and re.match(r"^\*[^*]+\*$", body_lines[0].strip()):
            cdate = body_lines.pop(0).strip().strip("*").strip()
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
        body = "\n".join(body_lines)
        if "DRAFT DO NOT READ" in h1:
            continue
        m = re.match(r"Chapter\s+(\d+)\s*[:.]\s*(.+)", h1)
        if m:
            cnum = int(m.group(1))
            cbody, cledger = md_with_footnotes(body, f"b{bn}c{cnum}")
            chapters.append({"num": cnum, "name": m.group(2).strip(),
                             "html": cbody, "ledger": cledger, "date": cdate})
        else:
            intro.append(md_to_html(body))
    return "\n".join(intro), chapters

def book_label(dirname):
    m = re.match(r"book-(\d+)", dirname)
    n = int(m.group(1))
    return n, f"Book {NUMWORDS[n]}"

# ------------------------------------------------------------------ TOR stat block
def load_actor(pattern):
    hits = glob.glob(os.path.join(TOR, pattern))
    return json.load(open(hits[0])) if hits else None

def pips(v, mx=6):
    v = max(0, min(int(v or 0), mx))
    return (f'<span class="pips">{"■"*v}<span class="empty">{"□"*(mx-v)}</span></span>')

def stat_block(actor):
    s = actor.get("system", {})
    bio = s.get("biography", {})
    culture = val(bio.get("culture")) or ""
    calling = (val(bio.get("calling")) or "").title()
    blessing = val(bio.get("culturalBlessing")) or ""
    living  = val(bio.get("standardOfLiving")) or ""
    shadowpath = val(bio.get("shadowPath")) or ""

    soh = s.get("stateOfHealth", {})
    def hs(k, lbl):
        on = val(soh.get(k))
        cls = "on" if on else ""
        mark = "▣" if on else "▢"
        return f'<span class="box {cls}">{mark} {lbl}</span>'
    health = f'<div class="health">{hs("weary","Weary")}{hs("wounded","Wounded")}{hs("miserable","Miserable")}</div>'

    res = s.get("resources", {})
    end = res.get("endurance", {}); hope = res.get("hope", {})
    shadow = res.get("shadow", {})
    scars = val(shadow.get("shadowScars")) if isinstance(shadow, dict) else None
    temp_shadow = val(shadow.get("temporary")) if isinstance(shadow, dict) else None
    load = val(res.get("travelLoad"))
    parry = val(s.get("combatAttributes", {}).get("parry"))
    treasure = val(s.get("treasure"))

    def stat(lbl, v, mx=None):
        inner = f'{v}' if mx is None else f'{v}<small>/{mx}</small>'
        return f'<div class="stat"><span class="lbl">{lbl}</span><span class="val">{inner}</span></div>'
    stats = "".join([
        stat("Endurance", val(end) if not isinstance(end,dict) else end.get("value"), end.get("max") if isinstance(end,dict) else None),
        stat("Hope", hope.get("value") if isinstance(hope,dict) else val(hope), hope.get("max") if isinstance(hope,dict) else None),
        stat("Parry", parry if parry is not None else "—"),
        stat("Shadow Scars", scars if scars is not None else 0),
        stat("Load", load if load is not None else 0),
        stat("Treasure", treasure if treasure is not None else 0),
    ])

    # attributes -> diamonds (TN = 20 - rank)
    attrs = s.get("attributes", {})
    order = ["strength","heart","wits"]
    dia = ""
    for a in order:
        rank = None
        for k,v in attrs.items():
            if k.split(".")[-1]==a: rank = val(v)
        if rank is None: rank = 0
        tn = 20 - rank
        dia += (f'<div class="attr"><div class="name">{a.title()}</div>'
                f'<div class="diamond"><span class="tn">{tn}</span>'
                f'<span class="rank"><span>{rank}</span></span></div></div>')
    attr_html = f'<div class="attr-row">{dia}</div>'

    # common skills grouped by associated attribute
    cs = s.get("commonSkills", {})
    groups = {"strength": [], "heart": [], "wits": []}
    for key, sk in cs.items():
        assoc = (sk.get("roll") or {}).get("associatedAttribute")
        if assoc not in groups: continue
        name = cap_last(sk.get("label") or key)
        fav = (sk.get("favoured") or {}).get("value")
        star = '<span class="fav">★</span> ' if fav else ''
        groups[assoc].append((name, star + name, val(sk.get("value")) or 0))
    def skcol(title, items):
        items.sort(key=lambda x: x[0])
        rows = "".join(f'<div class="skill"><span class="nm">{disp}</span>{pips(v)}</div>'
                       for _,disp,v in items)
        return f'<div><h4>{title}</h4>{rows}</div>'
    skills_html = ""
    if any(groups.values()):
        skills_html = ('<h3>Common Skills</h3><div class="skill-cols">'
            + skcol("Strength", groups["strength"])
            + skcol("Heart", groups["heart"])
            + skcol("Wits", groups["wits"]) + '</div>')

    # weapon / combat proficiencies
    cp = s.get("combatProficiencies", {})
    profs = []
    for key, p in cp.items():
        v = val(p) or 0
        if v: profs.append((cap_last(p.get("label") or key), v))
    prof_html = ""
    if profs:
        profs.sort()
        prof_html = ('<h3>Weapon Proficiencies</h3><div class="prof-row">'
            + "".join(f'<span class="prof"><span class="nm">{n}</span>{pips(v)}</span>'
                      for n,v in profs) + '</div>')

    # items
    items = actor.get("items", [])
    bytype = defaultdict(list)
    for it in items: bytype[it.get("type")].append(it)

    gear_html = ""
    weapons = bytype.get("weapon", [])
    if weapons:
        rows = ""
        for w in weapons:
            ws = w.get("system", {})
            rows += (f'<tr><td class="nm">{html.escape(w.get("name",""))}</td>'
                     f'<td>{val(ws.get("damage")) or "—"}</td>'
                     f'<td>{val(ws.get("injury")) or "—"}</td>'
                     f'<td>{val(ws.get("load")) or "0"}</td>'
                     f'<td>{"Ranged" if val(ws.get("ranged")) else "Melee"}</td></tr>')
        gear_html += ('<h3>War Gear</h3><table class="gear-table"><thead><tr>'
            '<th>Weapon</th><th>Damage</th><th>Injury</th><th>Load</th><th>Type</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')
    armour = bytype.get("armour", [])
    if armour:
        rows = ""
        for a in armour:
            asys = a.get("system", {})
            rows += (f'<tr><td class="nm">{html.escape(a.get("name",""))}</td>'
                     f'<td>{val(asys.get("protection")) or "—"}</td>'
                     f'<td>{val(asys.get("load")) or "0"}</td></tr>')
        gear_html += ('<h3>Armour</h3><table class="gear-table"><thead><tr>'
            '<th>Armour</th><th>Protection</th><th>Load</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')

    def desc_list(title, kind):
        arr = bytype.get(kind, [])
        if not arr: return ""
        lis = ""
        for it in arr:
            d = val((it.get("system", {}) or {}).get("description")) or ""
            d = re.sub(r"<[^>]+>", " ", d).strip()
            d = re.sub(r"\s+", " ", d)
            dh = f' <span class="d">— {html.escape(d)}</span>' if d else ""
            lis += f'<li><b>{html.escape(it.get("name",""))}</b>{dh}</li>'
        return f'<h3>{title}</h3><ul class="itemlist">{lis}</ul>'

    virtues = desc_list("Virtues", "virtues")
    rewards = desc_list("Rewards", "reward")
    traits  = ""
    if bytype.get("trait"):
        names = ", ".join(html.escape(t.get("name","")) for t in bytype["trait"])
        traits = f'<h3>Distinctive Features</h3><p class="sheet-note">{names}</p>'
    misc = desc_list("Notable Possessions", "miscellaneous")

    bio_facts = []
    for lbl, v in [("Culture", culture), ("Cultural Blessing", blessing),
                   ("Standard of Living", living), ("Shadow Path", shadowpath)]:
        if v: bio_facts.append(f"<li><b>{lbl}:</b> {html.escape(str(v))}</li>")
    facts_html = f'<ul class="itemlist">{"".join(bio_facts)}</ul>' if bio_facts else ""

    band = (f'<div class="sheet-band"><div class="culture">{html.escape(culture)}'
            + (f' · {html.escape(calling)}' if calling else '') + '</div>'
            + health + '</div>')

    return ('<div class="sheet">' + band + f'<div class="stat-row">{stats}</div>'
            + attr_html + facts_html + skills_html + prof_html + gear_html
            + virtues + rewards + traits + misc + '</div>')

# ------------------------------------------------------------------ character bios
def _is_img_block(b):
    ls = [l for l in b.splitlines() if l.strip()]
    return bool(ls) and all(re.match(r"^!\[.*?\]\(.*?\)$", l.strip()) for l in ls)

_BIO_CACHE = {}
def parse_bio(appendix_file):
    """Return dict(name, lead_images[], first_image, body_html).
    Leading image-only blocks (the character's portrait art) are pulled out of
    the body so we can promote them to a portrait frame without duplicating."""
    if appendix_file in _BIO_CACHE:
        return _BIO_CACHE[appendix_file]
    raw = open(os.path.join(SRC, "appendix-characters", appendix_file), encoding="utf-8").read()
    lines = raw.splitlines()
    name = lines[0][2:].strip() if lines and lines[0].startswith("# ") else appendix_file
    body_lines = lines[1:]
    while body_lines and (not body_lines[0].strip()
                          or re.match(r"^\*.*\*$", body_lines[0].strip())):
        body_lines.pop(0)
    text = "\n".join(body_lines)
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    lead = []
    i = 0
    while i < len(blocks) and _is_img_block(blocks[i]):
        for l in blocks[i].splitlines():
            m = re.match(r"^!\[.*?\]\((.*?)\)$", l.strip())
            if m: lead.append(os.path.basename(m.group(1)))
        i += 1
    all_imgs = [os.path.basename(x) for x in re.findall(r"!\[.*?\]\((.*?)\)", text)]
    result = dict(name=name, lead_images=lead,
                  first_image=(all_imgs[0] if all_imgs else None),
                  body_html=md_to_html("\n\n".join(blocks[i:])))
    _BIO_CACHE[appendix_file] = result
    return result

SRC_PORT = os.path.join(ROOT, "source", "portraits")

def portrait_webp(meta):
    """The optimized portrait webp for a character, if one exists."""
    if not meta.get("portrait"):
        return None
    w = os.path.splitext(meta["portrait"])[0] + ".webp"
    return w if os.path.exists(os.path.join(SRC_PORT, w)) else None

def resolve_portrait(meta, bio):
    """(kind, filename) for the main portrait frame — dedicated portrait, else the
    character's leading appendix art, else None (initial fallback)."""
    w = portrait_webp(meta)
    if w:
        return ("portraits", w)
    if bio["lead_images"]:
        return ("images", bio["lead_images"][0])
    return None

def resolve_thumb(meta, bio):
    """(kind, filename) for the index thumbnail — any portrait art we can find."""
    w = portrait_webp(meta)
    if w:
        return ("portraits", w)
    if bio["first_image"]:
        return ("images", bio["first_image"])
    return None

# roster: slug -> metadata
CHARS = {
    "celenneth": dict(name="Celenneth", role="Ranger of the North · Messenger",
                      appendix="01-celenneth.md", portrait="celenneth.png",
                      pdf="Celenneth.pdf", foundry="fvtt-Actor-celenneth-*.json"),
    "linnea":    dict(name="Linnea", role="Woman of Bree · Warden",
                      appendix="02-linnea.md", portrait="linnea.png",
                      pdf="Linnea.pdf", foundry="fvtt-Actor-linnea-*.json"),
    "brynja":    dict(name="Brynja", role="Daughter of Celenneth & Linnea",
                      appendix="03-brynja.md", portrait=None,
                      pdf=None, foundry="fvtt-Actor-brynja-*.json"),
    "eorlas":    dict(name="Eorlas", role="Herbalist of the Wood",
                      appendix="06-eorlas.md", portrait=None, pdf="Eorlas.pdf"),
    "garin":     dict(name="Garin", role="Rider of the Mark",
                      appendix="07-garin.md", portrait="garin.png", pdf="Garin.pdf"),
    "hallas":    dict(name="Hallas", role="",
                      appendix="08-hallas.md", portrait="hallas.png", pdf="Hallas.pdf"),
    "damrod":    dict(name="Damrod", role="",
                      appendix="09-damrod.md", portrait="damrod.png", pdf="Damrod.pdf"),
    "eira":      dict(name="Eira", role="",
                      appendix="10-eira.md", portrait="eira.png", pdf="Eira.pdf"),
    "eryndil":   dict(name="Eryndil", role="Elf of the Grey Havens",
                      appendix="11-eryndil.md", portrait="eryndil.png", pdf="Eryndil.pdf"),
    "freowyn":   dict(name="Freowyn", role="",
                      appendix="05-freowyn.md", portrait=None, pdf=None),
    "hallas-child": dict(name="Hallas (as a Child)", role="",
                      appendix="04-hallas-child.md", portrait=None, pdf=None),
    "the-orcs":  dict(name="The Orcs", role="Servants of the Shadow",
                      appendix="12-the-orcs.md", portrait=None, pdf=None),
}
COMPANY = ["celenneth", "linnea", "brynja"]
DP_ALLIES = ["eryndil", "garin", "eorlas", "damrod", "eira", "hallas", "hallas-child", "freowyn"]
DP_FOES = ["the-orcs"]

# ------------------------------------------------------------------ build
def wipe_and_dirs():
    for d in ["chronicle", "company", "dramatis-personae", "timeline", "atlas", "assets"]:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p): shutil.rmtree(p)
        os.makedirs(p, exist_ok=True)
    for sub in ["images", "portraits"]:
        os.makedirs(os.path.join(ROOT, "assets", sub), exist_ok=True)

def copy_assets():
    # optimized scene images (source of truth, already webp)
    for f in glob.glob(os.path.join(SRC, "images", "*")):
        shutil.copy2(f, os.path.join(ROOT, "assets", "images", os.path.basename(f)))
    # optimized character portraits (webp)
    for f in glob.glob(os.path.join(SRC_PORT, "*.webp")):
        shutil.copy2(f, os.path.join(ROOT, "assets", "portraits", os.path.basename(f)))
    # character-sheet PDFs are referenced externally (SHEETS_BASE_URL); not bundled.

def write(relpath, contents):
    p = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(contents)

def portrait_html(meta, bio):
    p = resolve_portrait(meta, bio)
    if not p:
        return ""
    kind, fn = p
    return (f'<figure class="portrait-frame">'
            f'<img src="../assets/{kind}/{fn}" alt="{html.escape(meta["name"])}">'
            f'<figcaption>{html.escape(meta["name"])}</figcaption></figure>')

# ---- books
def build_chronicle():
    bookdirs = sorted(d for d in os.listdir(SRC)
                      if re.match(r"book-\d+", d) and os.path.isdir(os.path.join(SRC, d)))
    books = []
    for d in bookdirs:
        n, label = book_label(d)
        intro, chapters = read_book(os.path.join(SRC, d))
        books.append((n, label, d, intro, chapters))

    # index
    cards = ""
    for n, label, d, intro, chapters in books:
        first = chapters[0]["name"] if chapters else ""
        last = chapters[-1]["name"] if chapters else ""
        teaser = f"{first} … {last}" if first else "—"
        cards += (f'<a class="card" href="book-{n:02d}.html">'
                  f'<span class="num">{n}</span>'
                  f'<span class="cat">{len(chapters)} chapters</span>'
                  f'<h3>{label}</h3><p>{html.escape(teaser)}</p></a>')
    body = (crumb(1, ("Chronicle",))
            + '<h1 class="pagetitle">The Chronicle</h1>'
            + '<p class="pagesub">The story of Celenneth, book by book — from the bandits at '
              'Sarn Ford to the far shores beyond the Grey Havens.</p>'
            + '<div class="flourish small"></div>'
            + f'<div class="grid">{cards}</div>')
    write("chronicle/index.html", page("The Chronicle", body, "Chronicle", depth=1,
          desc="The full narrative of Celenneth's journey, book by book."))

    # per-book pages
    for i, (n, label, d, intro, chapters) in enumerate(books):
        toc = "".join(f'<a href="#ch-{c["num"]}"><span class="cn">{c["num"]}</span>{html.escape(c["name"])}</a>'
                      for c in chapters)
        secs = ""
        for c in chapters:
            datep = f'<p class="chapter-date">{html.escape(c["date"])}</p>' if c.get("date") else ""
            secs += (f'<section class="chapter" id="ch-{c["num"]}">'
                     f'<h2 class="chapter-head"><span class="cno">{c["num"]}</span>{html.escape(c["name"])}</h2>'
                     f'{datep}{c["html"]}{c.get("ledger","")}</section>')
        intro_html = f'<div class="panel">{intro}</div>' if intro.strip() else ""
        # pager
        prev_a = (f'<a href="book-{books[i-1][0]:02d}.html"><span class="dir">‹ Previous</span>{books[i-1][1]}</a>'
                  if i > 0 else '<span></span>')
        next_a = (f'<a class="nx" href="book-{books[i+1][0]:02d}.html"><span class="dir">Next ›</span>{books[i+1][1]}</a>'
                  if i < len(books)-1 else '<span></span>')
        body = (crumb(1, ("Chronicle","chronicle/index.html"), (label,))
                + f'<h1 class="pagetitle">{label}</h1>'
                + '<div class="flourish small"></div>'
                + (f'<article><div class="toc">{toc}</div></article>' if len(chapters) > 1 else "")
                + intro_html
                + f'<article>{secs}</article>'
                + f'<div class="pager">{prev_a}{next_a}</div>')
        write(f"chronicle/book-{n:02d}.html",
              page(label, body, "Chronicle", depth=1,
                   desc=f"{label} of the chronicle of Celenneth."))
    return books

# ---- company + dramatis personae
def person_page(slug, meta, section_label, section_href):
    bio = parse_bio(meta["appendix"])
    name = meta["name"]
    body_html = bio["body_html"]
    if not body_html.strip():
        body_html = ('<p class="sheet-note">The threads of ' + html.escape(name)
                     + "'s story are woven through the "
                     + '<a href="../chronicle/index.html">Chronicle</a>.</p>')
    sheet = ""
    if meta.get("foundry"):
        actor = load_actor(meta["foundry"])
        if actor and actor.get("type") == "character":
            sheet = '<div class="flourish small"></div><article>' + stat_block(actor) + '</article>'
    pdf = ""
    if meta.get("pdf") and SHEETS_BASE_URL:
        pdf = (f'<p><a class="pdf-link" href="{SHEETS_BASE_URL}/{meta["pdf"]}">'
               f'⬦ Full Character Sheet (PDF)</a></p>')
    body = (crumb(1, (section_label, section_href), (name,))
            + f'<h1 class="pagetitle">{html.escape(name)}</h1>'
            + (f'<p class="pagesub">{html.escape(meta["role"])}</p>' if meta.get("role") else "")
            + '<div class="flourish small"></div>'
            + '<article>' + portrait_html(meta, bio) + body_html + '</article>'
            + pdf + sheet)
    write(f"{section_href.split('/')[0]}/{slug}.html",
          page(name, body, section_label, depth=1,
               desc=f"{name} — {meta.get('role','a figure in the chronicle of Celenneth')}."))
    return name

def pcard(slug, meta):
    bio = parse_bio(meta["appendix"])
    thumb = resolve_thumb(meta, bio)
    if thumb:
        kind, fn = thumb
        frame = f'<div class="frame"><img src="../assets/{kind}/{fn}" alt="{html.escape(meta["name"])}"></div>'
    else:
        frame = f'<div class="frame"><span class="initial">{html.escape(meta["name"][0])}</span></div>'
    role = f'<span class="rl">{html.escape(meta["role"])}</span>' if meta.get("role") else ""
    return (f'<a class="pcard" href="{slug}.html">{frame}'
            f'<span class="nm">{html.escape(meta["name"])}</span>{role}</a>')

def build_company():
    for slug in COMPANY:
        person_page(slug, CHARS[slug], "Company", "company/index.html")
    cards = "".join(pcard(s, CHARS[s]) for s in COMPANY)
    body = (crumb(1, ("Company",))
            + '<h1 class="pagetitle">The Company</h1>'
            + '<p class="pagesub">Those who make the fire — Celenneth and the family she '
              'gathered against the dark.</p>'
            + '<div class="flourish small"></div>'
            + f'<div class="pgrid">{cards}</div>')
    write("company/index.html", page("The Company", body, "Company", depth=1,
          desc="Celenneth and her companions — the heart of the chronicle."))

def build_dramatis():
    for slug in DP_ALLIES + DP_FOES:
        person_page(slug, CHARS[slug], "Dramatis Personae", "dramatis-personae/index.html")
    allies = "".join(pcard(s, CHARS[s]) for s in DP_ALLIES)
    foes = "".join(pcard(s, CHARS[s]) for s in DP_FOES)
    body = (crumb(1, ("Dramatis Personae",))
            + '<h1 class="pagetitle">Dramatis Personae</h1>'
            + '<p class="pagesub">The souls met upon the long road — companions, kin, and '
              'the shadow\'s servants.</p>'
            + '<div class="group-h">Companions &amp; Kin</div>'
            + '<p class="group-sub">Friends, mentors, and loved ones gathered along the way.</p>'
            + f'<div class="pgrid">{allies}</div>'
            + '<div class="group-h">Servants of the Shadow</div>'
            + '<p class="group-sub">Those who hunted her, and the darkness at their back.</p>'
            + f'<div class="pgrid">{foes}</div>')
    write("dramatis-personae/index.html", page("Dramatis Personae", body,
          "Dramatis Personae", depth=1, desc="Every soul met on Celenneth's journey."))

# ---- timeline
def build_timeline():
    raw = open(os.path.join(SRC, "appendix-timeline", "01-intro.md"), encoding="utf-8").read()
    # entries look like: **DATE***CHAPTER*DESC   (bold date, italic chapter, plain desc)
    entries = []
    for block in re.split(r"\n\s*\n", raw):
        block = block.strip()
        if not block.startswith("**"): continue
        m = re.match(r"\*\*(.+?)\*\*\*(.+?)\*(.*)", block, re.S)
        if m:
            date, chap, desc = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        else:
            m2 = re.match(r"\*\*(.+?):\*\*(.*)", block, re.S)
            if not m2: continue
            date, chap, desc = m2.group(1).strip(), "", m2.group(2).strip()
        entries.append((date, chap, desc))
    rows = ""
    for date, chap, desc in entries:
        rows += ('<div class="tl-entry">'
                 f'<div class="tl-date">{inline(date)}</div>'
                 + (f'<div class="tl-chap">{inline(chap)}</div>' if chap else "")
                 + (f'<p class="tl-desc">{inline(desc)}</p>' if desc else "")
                 + '</div>')
    body = (crumb(1, ("Timeline",))
            + '<h1 class="pagetitle">A Timeline of the Journey</h1>'
            + '<p class="pagesub">The reckoning of days, in the calendar of Middle-earth — '
              'from the Third Age year 2965 onward.</p>'
            + '<div class="flourish small"></div>'
            + f'<div class="timeline">{rows}</div>')
    write("timeline/index.html", page("Timeline", body, "Timeline", depth=1,
          desc="A chronological reckoning of Celenneth's journey through the Third Age."))
    return len(entries)

# ---- atlas (gazetteer of places, keyed to the books they appear in)
ATLAS = [
    ("Bree & the Chetwood", "Book One", "Where the road begins — the Prancing Pony, and Celenneth's home among the Bree-folk."),
    ("Sarn Ford & the Baranduin", "Book One", "The southern crossing where bandits and a cursed diadem set the tale in motion."),
    ("Moria (Khazad-dûm)", "Book One", "The deeps where Celenneth marched with Balin's folk — the Ledge of Woe, Uftak's Lair, the fortress of Malech."),
    ("Rivendell (Imladris)", "Books Two & Eight", "Elrond's hall, and the counsels that shaped her road."),
    ("The Wild & Mirkwood", "Book Three", "The eaves of the great wood — orcs, spirits, and the paths toward Dale."),
    ("Dale & the Long Lake", "Book Three", "The city of Men beneath the Mountain, and audience with its king."),
    ("The Riddermark (Rohan)", "Book Five", "The plains of the horse-lords — Yule, the First Marshal, and a foundling child."),
    ("Minas Tirith & Gondor", "Book Six", "The White City, Steward Turgon, and rumours that drew her south."),
    ("Fangorn Forest", "Book Six", "The oldest wood, where the Ent's test broke and remade her."),
    ("The Shire & Hobbiton", "Book Nine", "Bilbo, the Ring, and quiet days in the Marish."),
    ("The Frost Maw & the North", "Book Ten", "Frozen depths, a ranger station, and an altar beneath the ice."),
    ("The Grey Havens (Mithlond)", "Book Thirteen", "The harbour at the world's edge — the ship, its crew, and the reef beyond."),
]
def build_atlas():
    rows = ""
    for place, books, blurb in ATLAS:
        rows += ('<div class="tl-entry">'
                 f'<div class="tl-date">{html.escape(place)}</div>'
                 f'<div class="tl-chap">{html.escape(books)}</div>'
                 f'<p class="tl-desc">{html.escape(blurb)}</p></div>')
    body = (crumb(1, ("Atlas",))
            + '<h1 class="pagetitle">An Atlas of the Road</h1>'
            + '<p class="pagesub">A gazetteer of the lands Celenneth has walked, west to east '
              'and north to south across Middle-earth.</p>'
            + '<div class="flourish small"></div>'
            + '<p class="intro">From Bree to the deeps of Moria, from the courts of Rivendell '
              'and Dale to the plains of Rohan, the White City, and at last the Grey Havens — '
              'the map of a life lived on the road.</p>'
            + f'<div class="timeline">{rows}</div>')
    write("atlas/index.html", page("Atlas", body, "Atlas", depth=1,
          desc="A gazetteer of the lands walked in the chronicle of Celenneth."))

# ---- home
def build_home(books, n_tl):
    n_ch = sum(len(b[4]) for b in books)
    def card(href, cat, num, title, desc):
        return (f'<a class="card" href="{href}"><span class="num">{num}</span>'
                f'<span class="cat">{cat}</span><h3>{title}</h3><p>{desc}</p></a>')
    cards = "".join([
        card("chronicle/index.html", "Chronicle", len(books), "The Chronicle",
             f"The full story, book by book — {n_ch} chapters across {len(books)} books, from Sarn Ford to the sea."),
        card("company/index.html", "The Company", len(COMPANY), "The Company",
             "Celenneth and the family she made — with full One Ring stat blocks."),
        card("dramatis-personae/index.html", "Dramatis Personae", len(DP_ALLIES)+len(DP_FOES),
             "Dramatis Personae", "Companions, kin, and the shadow's servants met along the way."),
        card("timeline/index.html", "Timeline", n_tl, "Timeline",
             "The reckoning of days in the calendar of Middle-earth."),
        card("atlas/index.html", "Atlas", len(ATLAS), "Atlas",
             "A gazetteer of the lands walked, west to east across Middle-earth."),
    ])
    body = ('<header class="masthead">'
            '<div class="eyebrow">A Solo The One Ring, 2ⁿᵈ Edition Campaign</div>'
            '<div class="cartouche"><h1>Home Is Where<br>We Make Our Fire</h1></div>'
            '<p class="sub">The chronicle of Celenneth — ranger of the North, and the family '
            'she gathered against the gathering dark.</p>'
            '<p class="kicker">One player · one long road · the Third Age of Middle-earth</p>'
            '</header>'
            '<div class="flourish"></div>'
            '<div class="col"><p class="lede">Not quite spring, in Bree. A cloaked figure steps '
            'out of the cold into the light of the Prancing Pony — and from that hearth an errand '
            'unfolds across all of Middle-earth: the deeps of Moria, the halls of Rivendell, the '
            'plains of Rohan, the White City, and at last the grey ships of the Havens. This is the '
            'archive of that journey — who she is, where she has walked, and everyone the road gave '
            'her and took away.</p></div>'
            '<div class="flourish"></div>'
            f'<div class="grid">{cards}</div>')
    write("index.html", page("Home", body, "Home", depth=0, desc=SITE_TAG))

def main():
    wipe_and_dirs()
    copy_assets()
    books = build_chronicle()
    build_company()
    build_dramatis()
    n_tl = build_timeline()
    build_atlas()
    build_home(books, n_tl)
    n_ch = sum(len(b[4]) for b in books)
    print(f"Built: {len(books)} books / {n_ch} chapters, "
          f"{len(COMPANY)} company, {len(DP_ALLIES)+len(DP_FOES)} dramatis personae, "
          f"{n_tl} timeline entries, {len(ATLAS)} atlas places.")

if __name__ == "__main__":
    main()
