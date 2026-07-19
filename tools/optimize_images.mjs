import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const REPO = '/home/hewhocutsdown/Working/home-is-where-we-make-our-fire';
const TOR  = '/home/hewhocutsdown/Working/TOR Celenneth';
const SCENE_DIR = path.join(REPO, 'source', 'narrative', 'images');
const PORT_DIR  = path.join(REPO, 'source', 'portraits');

fs.mkdirSync(PORT_DIR, { recursive: true });

let before = 0, after = 0;
const kb = n => (n / 1024).toFixed(0) + 'KB';

async function conv(src, dst, maxEdge, quality) {
  const inSize = fs.statSync(src).size;
  await sharp(src)
    .rotate()
    .resize(maxEdge, maxEdge, { fit: 'inside', withoutEnlargement: true })
    .webp({ quality })
    .toFile(dst);
  const outSize = fs.statSync(dst).size;
  before += inSize; after += outSize;
  console.log(`  ${path.basename(src)} ${kb(inSize)} -> ${path.basename(dst)} ${kb(outSize)}`);
}

// --- scene images: png -> webp in place, remove png ---
console.log('Scene images:');
for (const f of fs.readdirSync(SCENE_DIR).filter(f => f.endsWith('.png')).sort()) {
  const src = path.join(SCENE_DIR, f);
  const dst = path.join(SCENE_DIR, f.replace(/\.png$/, '.webp'));
  await conv(src, dst, 1400, 80);
  fs.unlinkSync(src);
}

// --- portraits from TOR Celenneth -> source/portraits/*.webp ---
console.log('Portraits:');
const portraits = ['celenneth', 'linnea', 'damrod', 'eira', 'eryndil', 'garin', 'hallas'];
for (const slug of portraits) {
  const src = path.join(TOR, `${slug}.png`);
  if (!fs.existsSync(src)) { console.log(`  (missing ${slug}.png)`); continue; }
  await conv(src, path.join(PORT_DIR, `${slug}.webp`), 900, 82);
}

console.log(`\nTotal: ${kb(before)} -> ${kb(after)}  (${(100 * (1 - after / before)).toFixed(1)}% smaller)`);
