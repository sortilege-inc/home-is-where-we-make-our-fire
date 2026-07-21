/* tor-sheet.js — client-side renderer for playable One Ring 2e sheets.
   Reads window.SHEET, builds the DOM, rolls dice (tor-dice.js), and persists
   trackable state to localStorage. Two shapes: a Player-hero and a Band.     */
(function () {
  "use strict";
  const S = window.SHEET;
  const KEY = "hearth.play." + S.id;
  const STATE_V = 2;
  const QUAL = ["Success", "Great Success", "Extraordinary Success"];
  const G = window.TorDice.GLYPHS;
  const gi = name => '<span class="gi">' + G[name] + "</span>";   // inline glyph

  // ---------------------------------------------------------------- state
  function blank() {
    if (S.kind === "band") {
      return { v: STATE_V, readiness: S.readiness, allies: S.allies,
               disp: S.dispositions.map(x => x.rating),
               burden: (S.burdenLevels || []).indexOf(S.burdenDefault),
               roster: S.roster.map(() => ({ injury: -1, fatigue: -1, out: false })),
               log: [] };
    }
    return { v: STATE_V, end: S.endurance.value, hope: S.hope.value,
             shadowTemp: S.shadow.temporary,
             weary: !!S.conditions.weary, wounded: !!S.conditions.wounded,
             miserable: !!S.conditions.miserable,
             valour: S.valour, wisdom: S.wisdom, log: [] };
  }
  let st;
  try { st = JSON.parse(localStorage.getItem(KEY)); } catch (e) {}
  if (!st || st.v !== STATE_V) st = blank();
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };

  // ---------------------------------------------------------------- helpers
  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  const mount = document.getElementById("sheet");
  let favour = 0;                    // per-roll: -1 ill, 0 normal, +1 favoured
  let resultBox, logBox, tnInput, rankLabel, curRank = 0, curTn = "";

  // ---------------------------------------------------------------- rolling
  function logLine(e) { st.log.unshift(e); if (st.log.length > 40) st.log.pop(); save(); }
  function describe(r) {
    const cls = r.success === true ? "ok" : (r.success === false ? "no" : "");
    let verdict = r.success === true ? QUAL[r.quality]
                : (r.success === false ? "Failure" : "—");
    if (r.gandalf) verdict = "Gandalf rune — " + (r.success !== false ? QUAL[r.quality] : "auto-success");
    if (r.eye) verdict += " · the Eye";
    return { cls, verdict };
  }
  function renderResult(label, r) {
    const dv = describe(r);
    let dice = '<div class="dice">';
    // Feat die(s): favoured/ill-favoured rolls two — show both, dim the discarded one.
    r.feats.forEach((f, idx) => {
      const isG = f.kind === "gandalf", isE = f.kind === "eye";
      const cls = "die feat" + (isG ? " gandalf" : (isE ? " eye" : "")) + (idx === 0 ? "" : " discarded");
      dice += '<span class="' + cls + '">' + (isG ? G.gandalf : (isE ? G.eye : f.val)) + "</span>";
    });
    r.succ.forEach(s => {
      const mark = s.tengwar ? '<span class="teng-mark">' + G.tengwar + "</span>" : "";
      dice += '<span class="die ' + (s.tengwar ? "tengwar" : "") + (s.zeroed ? " zero" : "") + '">'
            + s.face + mark + "</span>";   // the 6 shows as a number, with the Tengwar superimposed
    });
    dice += "</div>";
    const head = '<div class="roll-result"><span class="total">' + r.total + "</span>"
      + (r.tn != null && r.tn !== "" ? ' <small>vs TN ' + r.tn + "</small>" : "")
      + '<span class="verdict ' + dv.cls + '">' + dv.verdict
      + (r.success && r.tengwar ? ' <span class="quality">(' + r.tengwar + " " + gi("tengwar") + ")</span>" : "")
      + "</span></div>";
    resultBox.innerHTML = '<div class="col-h">' + label + "</div>" + head + dice;
  }
  function doRoll(label, rank, tn, extraFav) {
    const weary = S.kind === "band" ? false : !!st.weary;
    const r = window.TorDice.roll({ rank, tn, weary, favour: (extraFav || 0) + favour });
    setTray(rank, tn);
    renderResult(label, r);
    const dv = describe(r);
    logLine({ label, total: r.total, tn: r.tn, cls: dv.cls, verdict: dv.verdict,
              feat: (r.gandalf ? "G" : (r.eye ? "E" : r.feat.val)), teng: r.tengwar, rank });
    renderLog();
  }
  function renderLog() {
    if (!logBox) return;
    logBox.innerHTML = st.log.map(e => {
      const featMark = e.feat === "G" ? gi("gandalf") : e.feat === "E" ? gi("eye") : e.feat;
      const teng = e.teng ? " ·" + e.teng + gi("tengwar") : "";
      return '<div class="log-line"><span class="lbl">' + e.label + "</span> — <b>" + e.total + "</b>"
        + (e.tn != null && e.tn !== "" ? " vs " + e.tn : "")
        + ' <span class="' + e.cls + '">' + e.verdict + "</span>"
        + ' <span class="g">[' + featMark + (e.rank ? "+" + e.rank + "d" : "") + teng + "]</span></div>";
    }).join("");
  }

  // ---------------------------------------------------------------- dice tray
  function setTray(rank, tn) {
    curRank = rank; curTn = (tn == null ? "" : tn);
    if (rankLabel) rankLabel.textContent = curRank + "d";
    if (tnInput) tnInput.value = curTn;
  }
  function buildTray(defaultRank) {
    const tray = el("section", "col");
    tray.appendChild(el("div", "col-h", "Dice Tray"));
    const ctl = el("div", "tray-ctl");
    const seg = el("div", "seg");
    [["Ill", -1], ["Normal", 0], ["Favoured", 1]].forEach(([t, v]) => {
      const b = el("button", null, t);
      if (v === favour) b.classList.add("on");
      b.onclick = () => { favour = v; [...seg.children].forEach(c => c.classList.remove("on")); b.classList.add("on"); };
      seg.appendChild(b);
    });
    ctl.appendChild(seg);
    const rs = el("div", "stepper");
    const minus = el("button", null, "−"), plus = el("button", null, "+"), cur = el("span", "cur");
    rankLabel = cur; curRank = defaultRank || 0; cur.textContent = curRank + "d";
    minus.onclick = () => { curRank = Math.max(0, curRank - 1); cur.textContent = curRank + "d"; };
    plus.onclick = () => { curRank = Math.min(12, curRank + 1); cur.textContent = curRank + "d"; };
    rs.append(minus, cur, plus);
    ctl.appendChild(el("span", "note", "Success dice")); ctl.appendChild(rs);
    tnInput = el("input", "tn-in"); tnInput.type = "number"; tnInput.placeholder = "TN"; tnInput.value = curTn;
    ctl.appendChild(el("span", "note", "TN")); ctl.appendChild(tnInput);
    tray.appendChild(ctl);
    const big = el("button", "big-roll", "⚄ Roll the Dice");
    big.onclick = () => doRoll("Feat Roll", curRank, tnInput.value === "" ? null : +tnInput.value);
    tray.appendChild(big);
    resultBox = el("div");
    resultBox.innerHTML = '<div class="roll-result"><span class="note">Click a skill, weapon, or roll here.</span></div>';
    tray.appendChild(resultBox);
    logBox = el("div", "roll-log"); tray.appendChild(logBox); renderLog();
    return tray;
  }

  // ---------------------------------------------------------------- widgets
  function pipTrack(cls, label, getCur, setCur, max, isScar) {
    const t = el("div", "track " + cls);
    const top = el("div", "track-top"); top.innerHTML = "<span>" + label + "</span>";
    const n = el("span", "n"); top.appendChild(n); t.appendChild(top);
    const boxes = el("div", "track-boxes");
    function paint() {
      n.textContent = getCur() + " / " + max; boxes.innerHTML = "";
      for (let i = 1; i <= max; i++) {
        const scar = isScar && isScar(i);
        const pip = el("span", "pip" + (i <= getCur() ? " on" : "") + (scar ? " scar" : ""));
        pip.onclick = () => { if (scar) return; setCur(getCur() === i ? i - 1 : i); paint(); save(); };
        boxes.appendChild(pip);
      }
    }
    t.appendChild(boxes); paint(); return t;
  }
  function ladder(label, levels, getIdx, setIdx) {
    const wrap = el("div");
    wrap.appendChild(el("div", "track-top", "<span>" + label + "</span>"));
    const row = el("div", "ladder");
    const clear = el("span", "rung clear", "None");
    function paint() {
      [...row.children].forEach((c, i) => c.classList.toggle("on", (i - 1) <= getIdx() && getIdx() >= 0 && i >= 1));
      clear.classList.toggle("on", getIdx() < 0);
    }
    clear.onclick = () => { setIdx(-1); paint(); save(); };
    row.appendChild(clear);
    levels.forEach((lv, i) => {
      const r = el("span", "rung", lv);
      r.onclick = () => { setIdx(getIdx() === i ? i - 1 : i); paint(); save(); };
      row.appendChild(r);
    });
    wrap.appendChild(row);
    // repaint marks rungs up to current index
    function repaint() {
      const rungs = [...row.children];
      rungs.forEach((c, i) => { if (i === 0) return; c.classList.toggle("on", (i - 1) <= getIdx()); });
      clear.classList.toggle("on", getIdx() < 0);
    }
    clear.onclick = () => { setIdx(-1); repaint(); save(); };
    levels.forEach((lv, i) => { row.children[i + 1].onclick = () => { setIdx(getIdx() === i ? i - 1 : i); repaint(); save(); }; });
    repaint();
    return wrap;
  }

  // ---------------------------------------------------------------- hero
  function renderHero() {
    const head = el("header", "sheet-head");
    head.innerHTML = '<div class="sh-name">' + S.name + "</div>"
      + '<div class="sh-sub">' + [S.meta.culture, S.meta.calling].filter(Boolean).join(" · ") + "</div>"
      + (S.meta.fellowshipFocus ? '<div class="sh-line">Fellowship focus: ' + S.meta.fellowshipFocus + "</div>" : "")
      + '<div class="flourish-line"></div>';
    mount.appendChild(head);
    const grid = el("div", "sheet-grid");

    // --- column 1: attributes, resources, conditions
    const c1 = el("section", "col");
    c1.appendChild(el("div", "col-h", "Attributes"));
    const attrs = el("div", "attrs");
    ["strength", "heart", "wits"].forEach(a => {
      const rank = S.attributes[a] || 0, tn = 20 - rank;
      const box = el("div", "attr");
      box.innerHTML = '<div class="an">' + a[0].toUpperCase() + a.slice(1) + "</div>"
        + '<div class="diamond"><span class="tn">' + tn + '</span><span class="rank">' + rank + "</span></div>";
      box.title = "TN " + tn + " — roll " + a + " tests here";
      box.onclick = () => doRoll(a[0].toUpperCase() + a.slice(1) + " (raw)", 0, tn);
      attrs.appendChild(box);
    });
    c1.appendChild(attrs);

    c1.appendChild(el("div", "col-h", "Resources"));
    c1.appendChild(pipTrack("end", "Endurance", () => st.end, v => st.end = v, S.endurance.max));
    c1.appendChild(pipTrack("hope", "Hope", () => st.hope, v => st.hope = v, S.hope.max));
    const scarN = S.shadow.scars || 0, shadowMax = Math.max(6, scarN + 6);
    c1.appendChild(pipTrack("shadow", "Shadow (scars + temporary)",
      () => scarN + st.shadowTemp, v => st.shadowTemp = Math.max(0, v - scarN),
      shadowMax, i => i <= scarN));

    c1.appendChild(el("div", "col-h", "Conditions"));
    const conds = el("div", "conds");
    [["weary", "Weary"], ["wounded", "Wounded"], ["miserable", "Miserable"]].forEach(([k, lbl]) => {
      const b = el("div", "cond" + (st[k] ? " on" : ""), lbl);
      b.onclick = () => { st[k] = !st[k]; b.classList.toggle("on", st[k]); save(); };
      conds.appendChild(b);
    });
    c1.appendChild(conds);
    c1.appendChild(el("div", "note", "When Weary, Success dice showing 1–3 count as 0."));

    c1.appendChild(el("div", "col-h", "Stature"));
    const stt = el("div", "statline");
    [["Valour", "valour"], ["Wisdom", "wisdom"], ["Parry", null]].forEach(([lbl, k]) => {
      const v = k ? st[k] : S.parry;
      stt.appendChild(el("div", "stat", '<span class="v">' + v + '</span><span class="k">' + lbl + "</span>"));
    });
    c1.appendChild(stt);
    grid.appendChild(c1);

    // --- column 2: dice tray
    grid.appendChild(buildTray(0));

    // --- column 3: skills, proficiencies, gear
    const c3 = el("section", "col");
    c3.appendChild(el("div", "col-h", "Common Skills"));
    const cols = el("div", "skill-cols");
    ["strength", "heart", "wits"].forEach(a => {
      const list = S.skills.filter(s => s.attr === a).sort((x, y) => x.name.localeCompare(y.name));
      if (!list.length) return;
      const grp = el("div");
      grp.appendChild(el("h5", null, a[0].toUpperCase() + a.slice(1) + " · TN " + (20 - (S.attributes[a] || 0))));
      const rolls = el("div", "rolls");
      list.forEach(s => rolls.appendChild(skillRow(s)));
      grp.appendChild(rolls); cols.appendChild(grp);
    });
    c3.appendChild(cols);

    if (S.proficiencies.some(p => p.rank > 0) || S.proficiencies.length) {
      c3.appendChild(el("div", "col-h", "Weapon Skills"));
      const rolls = el("div", "rolls");
      S.proficiencies.forEach(p => rolls.appendChild(skillRow(p, true)));
      c3.appendChild(rolls);
    }

    if (S.weapons.length) {
      c3.appendChild(el("div", "col-h", "War Gear"));
      c3.appendChild(gearTable(["Weapon", "Dmg", "Injury", "Load", ""], S.weapons.map(w => {
        const atk = el("button", "atk", "Attack");
        const prof = S.proficiencies.find(p => p.name.toLowerCase() === (w.skill || "").toLowerCase())
                   || S.proficiencies.find(p => w.name.toLowerCase().includes(p.name.toLowerCase().replace(/s$/, "")));
        const rank = prof ? prof.rank : 0, attr = prof ? prof.attr : "strength";
        atk.onclick = () => doRoll(w.name, rank, 20 - (S.attributes[attr] || 0));
        return [w.name + (w.ranged ? " ⇢" : ""), w.damage, w.injury, w.load, atk];
      })));
    }
    if (S.armour.length) {
      c3.appendChild(el("div", "col-h", "Armour"));
      c3.appendChild(gearTable(["Armour", "Protection", "Load"], S.armour.map(a =>
        [a.name + (a.equipped ? " ·worn" : ""), a.protection, a.load])));
    }
    grid.appendChild(c3);
    mount.appendChild(grid);

    // --- full width: virtues / rewards / features / possessions
    if (S.features.length) {
      const sec = el("section", "col"); sec.style.marginTop = "1rem";
      sec.appendChild(el("div", "col-h", "Distinctive Features"));
      const chips = el("div", "feature-chips");
      S.features.forEach(f => chips.appendChild(el("span", "chip", f)));
      sec.appendChild(chips); mount.appendChild(sec);
    }
    const cardGroups = [["Virtues", S.virtues], ["Rewards", S.rewards], ["Notable Possessions", S.possessions]];
    if (cardGroups.some(([, arr]) => arr.length)) {
      const sec = el("section", "col"); sec.style.marginTop = "1rem";
      cardGroups.forEach(([title, arr]) => {
        if (!arr.length) return;
        sec.appendChild(el("div", "col-h", title));
        const cards = el("div", "cards");
        arr.forEach(v => cards.appendChild(el("div", "vcard",
          '<div class="vn">' + v.name + "</div>" + (v.text ? '<div class="vt">' + v.text + "</div>" : ""))));
        sec.appendChild(cards);
      });
      mount.appendChild(sec);
    }
    resetRow();
  }

  function skillRow(s, isProf) {
    const attr = s.attr, tn = 20 - (S.attributes[attr] || 0);
    const row = el("div", "roll-row");
    row.innerHTML = '<span class="nm">' + (s.favoured ? '<span class="fav">★</span> ' : "") + s.name + "</span>"
      + '<span class="rk">' + s.rank + "d<span class=\"tn\">TN " + tn + "</span></span>";
    row.title = "Roll " + s.name + " (" + s.rank + " Success dice vs TN " + tn + ")";
    row.onclick = () => doRoll(s.name, s.rank, tn, s.favoured ? 1 : 0);
    return row;
  }
  function gearTable(headers, rows) {
    const t = el("table", "gtable");
    t.appendChild(el("thead", null, "<tr>" + headers.map(h => "<th>" + h + "</th>").join("") + "</tr>"));
    const tb = el("tbody");
    rows.forEach(cells => {
      const tr = el("tr");
      cells.forEach((c, i) => {
        const td = el("td", i === 0 ? "nm" : null);
        if (c instanceof HTMLElement) td.appendChild(c); else td.innerHTML = (c == null || c === "" ? "—" : c);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    t.appendChild(tb); return t;
  }

  // ---------------------------------------------------------------- band
  function renderBand() {
    const head = el("header", "sheet-head");
    head.innerHTML = '<div class="sh-name">' + S.name + "</div>"
      + '<div class="sh-sub">' + S.subtitle + "</div>"
      + (S.sharedCalling ? '<div class="sh-line">Shared Calling: ' + S.sharedCalling.name
          + " — " + S.sharedCalling.focus + " focus</div>" : "")
      + '<div class="flourish-line"></div>';
    mount.appendChild(head);
    const grid = el("div", "sheet-grid");

    // col 1: readiness / allies / dispositions
    const c1 = el("section", "col");
    c1.appendChild(el("div", "col-h", "The Band"));
    const stt = el("div", "statline");
    const rdBox = el("div", "stat"); const alBox = el("div", "stat");
    function paintStats() {
      rdBox.innerHTML = '<span class="v">' + st.readiness + '</span><span class="k">Readiness · TN ' + (20 - st.readiness) + "</span>";
      alBox.innerHTML = '<span class="v">' + st.allies + '</span><span class="k">Allies</span>';
    }
    paintStats();
    const rd2 = el("div"); rd2.style.marginTop = ".4rem";
    stt.appendChild(rdBox); stt.appendChild(alBox);
    stt.appendChild(el("div", "stat", '<span class="v">' + S.dispositions.length + '</span><span class="k">Dispositions</span>'));
    c1.appendChild(stt);
    c1.appendChild(el("div", "track-top", "<span>Readiness</span>"));
    c1.appendChild((function () {
      const w = el("div", "stepper");
      const m = el("button", null, "−"), c = el("span", "cur"), p = el("button", null, "+");
      const upd = () => c.textContent = st.readiness;
      m.onclick = () => { st.readiness = Math.max(0, st.readiness - 1); upd(); paintStats(); save(); };
      p.onclick = () => { st.readiness = Math.min(12, st.readiness + 1); upd(); paintStats(); save(); };
      w.append(m, c, p); upd(); return w;
    })());
    c1.appendChild(el("div", "track-top", "<span>Allies</span>"));
    c1.appendChild((function () {
      const w = el("div", "stepper");
      const m = el("button", null, "−"), c = el("span", "cur"), p = el("button", null, "+");
      const upd = () => c.textContent = st.allies;
      m.onclick = () => { st.allies = Math.max(0, st.allies - 1); upd(); paintStats(); save(); };
      p.onclick = () => { st.allies = Math.min(20, st.allies + 1); upd(); paintStats(); save(); };
      w.append(m, c, p); upd(); return w;
    })());

    c1.appendChild(el("div", "col-h", "Burden — the whole Band"));
    c1.appendChild(ladder("Burden", S.burdenLevels, () => st.burden, v => st.burden = v));
    c1.appendChild(el("div", "note", "Burden reflects the Band’s gear for the mission — a single "
      + "level for all of them. Injury and Fatigue are tracked per crew-member below."));
    grid.appendChild(c1);

    // col 2: dice tray
    grid.appendChild(buildTray(2));

    // col 3: dispositions (rollable), shared calling, roster
    const c3 = el("section", "col");
    c3.appendChild(el("div", "col-h", "Dispositions — roll a group action"));
    const rolls = el("div", "rolls");
    S.dispositions.forEach((d, i) => {
      const row = el("div", "roll-row");
      function paint() {
        row.innerHTML = '<span class="nm">' + d.name + (d.name === (S.sharedCalling && S.sharedCalling.focus) ? ' <span class="fav">★</span>' : "") + "</span>"
          + '<span class="rk">' + st.disp[i] + "d</span>";
      }
      paint();
      row.title = "Roll " + d.name + " (" + st.disp[i] + " Success dice; set TN in the tray)";
      row.onclick = () => doRoll("Disposition: " + d.name, st.disp[i], tnInput && tnInput.value !== "" ? +tnInput.value : null);
      rolls.appendChild(row);
    });
    c3.appendChild(rolls);
    c3.appendChild(el("div", "note", "Adjust a Disposition rating in the tray’s Success-dice stepper before rolling, or step it here:"));
    const dstep = el("div", "rolls");
    S.dispositions.forEach((d, i) => {
      const w = el("div", "roll-row");
      const label = el("span", "nm", d.name);
      const s = el("div", "stepper");
      const m = el("button", null, "−"), c = el("span", "cur"), p = el("button", null, "+");
      const upd = () => c.textContent = st.disp[i] + "d";
      m.onclick = () => { st.disp[i] = Math.max(0, st.disp[i] - 1); upd(); save(); };
      p.onclick = () => { st.disp[i] = Math.min(12, st.disp[i] + 1); upd(); save(); };
      s.append(m, c, p); upd();
      w.append(label, s); dstep.appendChild(w);
    });
    c3.appendChild(dstep);

    if (S.sharedCalling) {
      c3.appendChild(el("div", "col-h", "Shared Calling — " + S.sharedCalling.name));
      c3.appendChild(el("div", "vcard",
        '<div class="vn">' + S.sharedCalling.focus + " focus · Shadow Path: " + S.sharedCalling.shadowPath + "</div>"
        + '<div class="vt">Favoured skills: ' + S.sharedCalling.skills.join(", ")
        + ". " + (S.sharedCalling.description || "") + "</div>"));
    }

    grid.appendChild(c3);
    mount.appendChild(grid);

    // full-width: roster, with per-Ally Injury & Fatigue conditions
    const sec = el("section", "col"); sec.style.marginTop = "1rem";
    sec.appendChild(el("div", "col-h", "Roster — the crew of the " + (S.shipName || S.name)));
    const wearyNote = el("div", "band-weary"); sec.appendChild(wearyNote);
    const injOpts = ["—"].concat(S.injuryLevels), fatOpts = ["—"].concat(S.fatigueLevels);
    const serSet = (levels, serious) => new Set((levels || [])
      .map((n, i) => (serious || []).includes(n) ? i : -1).filter(i => i >= 0));
    const injSerious = serSet(S.injuryLevels, S.seriousInjury);
    const fatSerious = serSet(S.fatigueLevels, S.seriousFatigue);
    const isSerious = r => r.out || injSerious.has(r.injury) || fatSerious.has(r.fatigue);
    function paintWeary() {
      const bad = st.roster.filter(isSerious).length;
      const weary = st.roster.length > 0 && bad * 2 >= st.roster.length;
      wearyNote.className = "band-weary" + (weary ? " on" : "");
      wearyNote.textContent = weary
        ? "⚑ The Band is Weary — " + bad + " of " + st.roster.length
          + " lost or seriously afflicted (Success dice 1–3 count as 0)."
        : bad + " of " + st.roster.length + " afflicted — the Band turns Weary at half.";
    }
    const table = el("table", "roster-table");
    table.appendChild(el("thead", null,
      "<tr><th>Ally</th><th>Role</th><th>Injury</th><th>Fatigue</th><th>Status</th></tr>"));
    const tb = el("tbody");
    S.roster.forEach((m, i) => {
      const tr = el("tr");
      const paintRow = () => {
        const r = st.roster[i];
        tr.classList.toggle("afflicted", r.out || r.injury >= 0 || r.fatigue >= 0);
        tr.classList.toggle("serious", isSerious(r));
      };
      const selInj = mkSelect(injOpts, st.roster[i].injury, v => { st.roster[i].injury = v; save(); paintWeary(); paintRow(); }, injSerious);
      const selFat = mkSelect(fatOpts, st.roster[i].fatigue, v => { st.roster[i].fatigue = v; save(); paintWeary(); paintRow(); }, fatSerious);
      const out = el("button", "out-btn" + (st.roster[i].out ? " on" : ""), st.roster[i].out ? "Out of action" : "Present");
      out.onclick = () => {
        st.roster[i].out = !st.roster[i].out;
        out.className = "out-btn" + (st.roster[i].out ? " on" : "");
        out.textContent = st.roster[i].out ? "Out of action" : "Present";
        save(); paintWeary(); paintRow();
      };
      const cell = c => { const td = el("td"); if (typeof c === "string") td.innerHTML = c; else td.appendChild(c); return td; };
      tr.appendChild(cell('<span class="rn">' + m.name + "</span>"));
      tr.appendChild(cell('<span class="rr">' + m.role + "</span>"));
      tr.appendChild(cell(selInj));
      tr.appendChild(cell(selFat));
      tr.appendChild(cell(out));
      paintRow(); tb.appendChild(tr);
    });
    table.appendChild(tb); sec.appendChild(table);
    if (S.note) sec.appendChild(el("div", "note", S.note));
    paintWeary(); mount.appendChild(sec);
    resetRow();
  }

  function mkSelect(opts, cur, onChange, seriousSet) {
    const s = el("select", "lvl-sel");
    opts.forEach((o, idx) => {
      const op = document.createElement("option");
      op.value = idx - 1; op.textContent = o;
      if (idx - 1 === cur) op.selected = true;
      s.appendChild(op);
    });
    const sev = () => {
      const v = +s.value;
      const serious = seriousSet && seriousSet.has(v);
      s.className = "lvl-sel" + (serious ? " sev" : (v >= 0 ? " mild" : ""));
    };
    sev();
    s.onchange = () => { sev(); onChange(+s.value); };
    return s;
  }

  // ---------------------------------------------------------------- reset
  function resetRow() {
    const row = el("div", "reset-row");
    const clr = el("button", null, "Clear roll log");
    clr.onclick = () => { st.log = []; save(); renderLog(); };
    const rst = el("button", null, "Reset all trackers");
    rst.onclick = () => { if (confirm("Reset this sheet's trackers to its starting values?")) { st = blank(); save(); location.reload(); } };
    row.append(clr, rst);
    mount.appendChild(row);
  }

  // ---------------------------------------------------------------- go
  if (S.kind === "band") renderBand(); else renderHero();
})();
