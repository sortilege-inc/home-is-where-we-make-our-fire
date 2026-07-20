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

  return { roll, rollFeat };
})();
