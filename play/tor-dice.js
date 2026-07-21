/* tor-dice.js — The One Ring 2e dice engine.
   Feat die: d12. Faces 1–10 count as their number; the Gandalf rune (11)
   is an automatic success; the Eye of Sauron (12) counts as 0.
   Success dice: d6, one per rank. A 6 is a Tengwar rune (a "great success"
   tally). When Weary, Success dice showing 1–3 count as 0.               */
window.TorDice = (function () {
  const d = n => Math.floor(Math.random() * n) + 1;

  function rollFeat() {
    const r = d(12);
    if (r === 11) return { kind: "gandalf", val: 11, face: "G" };
    if (r === 12) return { kind: "eye", val: 0, face: "☉" };
    return { kind: "num", val: r, face: String(r) };
  }
  // favour: 0 normal, +1 favoured (keep best), -1 ill-favoured (keep worst)
  function featWithFavour(favour) {
    const rolls = [rollFeat()];
    if (favour !== 0) {
      rolls.push(rollFeat());
      // Gandalf beats all; Eye (0) is lowest.
      rolls.sort((a, b) => (favour > 0 ? b.val - a.val : a.val - b.val));
    }
    return { chosen: rolls[0], all: rolls };
  }
  function rollSuccessDie(weary) {
    const r = d(6);
    const tengwar = r === 6;
    const val = (weary && r <= 3) ? 0 : r;
    return { face: r, val, tengwar, zeroed: weary && r <= 3 };
  }

  // opts: {rank, tn, weary, favour}
  function roll(opts) {
    const rank = Math.max(0, opts.rank | 0);
    const weary = !!opts.weary;
    const favour = opts.favour | 0;
    const feat = featWithFavour(favour);
    const succ = [];
    for (let i = 0; i < rank; i++) succ.push(rollSuccessDie(weary));

    const gandalf = feat.chosen.kind === "gandalf";
    const eye = feat.chosen.kind === "eye";
    const featNum = gandalf ? 0 : feat.chosen.val;      // Gandalf adds nothing numerically
    const succSum = succ.reduce((a, x) => a + x.val, 0);
    const total = featNum + succSum;
    const tengwar = succ.filter(x => x.tengwar).length;

    let success = null;
    if (opts.tn != null && opts.tn !== "") {
      success = gandalf || total >= Number(opts.tn);
    }
    const quality = success ? Math.min(2, tengwar) : 0; // 0 ordinary,1 great,2 extraordinary
    return { feat: feat.chosen, feats: feat.all, succ, featNum, succSum,
             total, tengwar, gandalf, eye, success, quality, tn: opts.tn };
  }

  // Glyph art for the special faces (inherit `currentColor`, scale to any size).
  const GLYPHS = {
    // Feat 11 — the Gandalf rune (branching stave with dots): automatic success.
    gandalf: '<svg viewBox="0 0 30 44" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9V34M8 9h8M8 34h8"/><path d="M12 20C16 18 19 13 20 8"/><path d="M12 24C17 22 21 16 22 10"/><circle cx="20" cy="8" r="1.8" fill="currentColor" stroke="none"/><circle cx="22" cy="10" r="1.8" fill="currentColor" stroke="none"/><circle cx="12" cy="3.5" r="1.8" fill="currentColor" stroke="none"/><circle cx="12" cy="40" r="1.8" fill="currentColor" stroke="none"/><circle cx="3.5" cy="21.5" r="1.8" fill="currentColor" stroke="none"/><circle cx="26.5" cy="21.5" r="1.8" fill="currentColor" stroke="none"/></svg>',
    // Feat 12 — the Eye of Sauron: counts as 0.
    eye: '<svg viewBox="0 0 44 30" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15C13 5 31 5 40 15 31 25 13 25 4 15Z"/><path d="M22 9C24.2 12 24.2 18 22 21 19.8 18 19.8 12 22 9Z" fill="currentColor" stroke="none"/><path d="M22 3V0.5M22 29.5V27M6.5 6.5 5 5M37.5 6.5 39 5M6.5 23.5 5 25M37.5 23.5 39 25"/></svg>',
    // Success die 6 — the Tengwar rune (per reference): a flat top stroke with a
    // curve descending on the left. Tallies great successes.
    tengwar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 7L8.5 7C5.8 7.2 4.8 10.3 5.6 13.4 6.3 16.3 9 18 12 17"/></svg>'
  };

  return { roll, rollFeat, GLYPHS };
})();
