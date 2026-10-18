#!/usr/bin/env node
/* Navel Desk: build the subject library catalog.  Plain Node (>= 18), no dependencies.

   What it does, for every subject listed in library/catalog.json:
     1. Validates the subject file with the app's OWN normaliser (spNormalise from the app's
        SP-CORE block, run unchanged), so a file that builds here loads in the app.
     2. Computes bytes, sha256 and counts, and writes them (and rev) back into catalog.json.
     3. Compares with the released version (git) and warns when learners' saved progress could break.
     4. Bumps rev when the file content changed since the released version.

   Hand-written catalog fields: id, title, category, level, lang, description, tags, file, added.
   Generated fields (never edit by hand): rev, bytes, sha256, counts.

   Usage:  node tools/build-library.mjs [--force] [--check] [--stats] [--allow-warnings]
                                         [--app <path to index.html>] [--ref <git ref>]
     --force            write the catalog even if the progress-compatibility check found problems
     --check            change nothing; exit 1 if catalog.json is out of date (for CI)
     --stats            also print gzip sizes (GitHub Pages gzips JSON on its own; this only informs)
     --allow-warnings   do not treat "skipped item" warnings from the normaliser as failures
     --app              the app file that contains the SP-CORE block (default: ../index.html)
     --ref              git ref that counts as "released" (default: HEAD)

   Exit codes: 0 ok, 1 invalid file / catalog or --check out of date, 2 compatibility warnings (use --force). */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const libDir = path.resolve(here, '..', 'library');
const appPath = path.resolve(opt('--app', existsSync(path.resolve(here, '..', 'index.html')) ? path.resolve(here, '..', 'index.html') : path.resolve(here, '..', 'bleeding_edge.html')));
const ref = opt('--ref', 'HEAD');
const FORCE = flag('--force'), CHECK = flag('--check'), STATS = flag('--stats'), ALLOW_WARN = flag('--allow-warnings');

const bad = '\x1b[31m', warnC = '\x1b[33m', ok = '\x1b[32m', dim = '\x1b[2m', off = '\x1b[0m';
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

/* ---------- the app's own normaliser ---------- */
const html = readFileSync(appPath, 'utf8');
const a = html.indexOf('/* SP-CORE-BEGIN'), b = html.indexOf('/* SP-CORE-END */');
if (a < 0 || b < a) { console.error(`${bad}Could not find the SP-CORE block in ${appPath}.${off}`); process.exit(1); }
const core = vm.runInNewContext(html.slice(a, b) + '\n;({ spNormalise, spSerialise, spParse })', {});
/* English texts for the normaliser's message keys, taken from the app's own table (first = English) */
const TEXT = {};
for (const m of html.matchAll(/\bv_([a-z_0-9]+):\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")/g)) if (!(m[1] in TEXT)) TEXT[m[1]] = (m[2] ?? m[3]).replace(/\\'/g, "'").replace(/\\"/g, '"');
const say = (m) => {
  let t = TEXT[m.key] ?? `${m.key} ${JSON.stringify(m.vars || {})}`;
  t = t.replace(/\{(\w+)\}/g, (_, k) => (m.vars && m.vars[k] != null ? m.vars[k] : `{${k}}`));
  return (m.node ? `[${m.node}] ` : '') + t;
};

/* ---------- git helpers (released version) ---------- */
const gitShow = (rel) => {
  try { return execFileSync('git', ['show', `${ref}:./${rel}`], { cwd: libDir, stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 1 << 28 }); } catch { return null; }
};

/* ---------- catalog ---------- */
const catPath = path.join(libDir, 'catalog.json');
if (!existsSync(catPath)) { console.error(`${bad}${catPath} not found.${off}`); process.exit(1); }
let catalog;
try { catalog = JSON.parse(readFileSync(catPath, 'utf8')); } catch (e) { console.error(`${bad}catalog.json is not valid JSON: ${e.message}${off}`); process.exit(1); }
if (!catalog || catalog.schema !== 1 || !Array.isArray(catalog.subjects)) { console.error(`${bad}catalog.json must look like { "schema": 1, "subjects": [ ... ] }.${off}`); process.exit(1); }
const releasedCatalogBuf = gitShow('catalog.json');
let releasedCatalog = null;
try { releasedCatalog = releasedCatalogBuf ? JSON.parse(releasedCatalogBuf.toString('utf8')) : null; } catch { releasedCatalog = null; }
if (!releasedCatalog) console.log(`${dim}No released catalog found in git (${ref}); rev changes are judged against the sha256 stored in catalog.json.${off}`);

const HAND = ['id', 'title', 'category', 'level', 'lang', 'description', 'tags', 'file', 'added'];
const ORDER = ['id', 'title', 'category', 'level', 'lang', 'description', 'tags', 'rev', 'bytes', 'sha256', 'counts', 'file', 'added'];
const problems = [];       /* hard failures: invalid files / catalog */
const compat = [];         /* progress-compatibility warnings */
const seen = new Set();
const out = [];
let i = 0;

for (const entry of catalog.subjects) {
  i++;
  const where = `subject #${i}${entry && entry.id ? ` "${entry.id}"` : ''}`;
  const fail = (m) => problems.push(`${where}: ${m}`);
  if (!entry || typeof entry !== 'object') { fail('is not an object'); continue; }
  for (const k of HAND) if (entry[k] == null || entry[k] === '') fail(`missing hand-written field "${k}"`);
  if (!/^[a-z0-9][a-z0-9-]{1,63}$/.test(entry.id || '')) fail('id must be 2-64 characters of a-z, 0-9 and "-" (it is also the progress key; never change it after release)');
  if (seen.has(entry.id)) fail('duplicate id'); seen.add(entry.id);
  if (!/^subjects\/[A-Za-z0-9._-]+\.json$/.test(entry.file || '')) fail('file must look like "subjects/<name>.json"');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(entry.added || '')) fail('"added" must be a date like 2026-10-20');
  if (!/^[a-z]{2,3}(-[A-Za-z0-9]+)?$/.test(entry.lang || '')) fail('"lang" must be a language code such as "en" or "vi"');
  if (!Array.isArray(entry.tags) || entry.tags.some((t) => typeof t !== 'string')) fail('"tags" must be a list of strings');
  const filePath = path.join(libDir, entry.file || '');
  if (!entry.file || !existsSync(filePath)) { fail(`file not found: ${entry.file}`); continue; }

  const buf = readFileSync(filePath), text = buf.toString('utf8');
  let data;
  try { data = JSON.parse(text); } catch (e) { fail(`${entry.file} is not valid JSON: ${e.message}`); continue; }
  if (data && data.id != null && data.id !== entry.id) console.log(`${warnC}note${off} ${entry.file}: the file has "id": "${data.id}"; the app ignores it and uses lib:${entry.id}.`);
  const n = core.spNormalise(JSON.parse(text));
  if (!n.pack) { for (const e of n.errors) fail(`${entry.file}: ${say(e)}`); continue; }
  if (n.warnings.length && !ALLOW_WARN) for (const w of n.warnings) fail(`${entry.file}: ${say(w)} (a published subject must not silently drop items; fix the file or use --allow-warnings)`);
  const counts = { topics: n.pack.topics.length, cards: 0, questions: 0 };
  for (const t of n.pack.topics) { counts.cards += t.cards.length; counts.questions += t.questions.length; }

  /* ----- compatibility with the released version ----- */
  const relBuf = gitShow(entry.file);
  const relCat = releasedCatalog && releasedCatalog.subjects.find((s) => s.id === entry.id);
  if (relBuf) {
    let old = null;
    try { old = core.spNormalise(JSON.parse(relBuf.toString('utf8'))); } catch { old = null; }
    if (old && old.pack) {
      const W = (m) => compat.push(`${entry.id}: ${m}`);
      const newTopics = new Map(n.pack.topics.map((t) => [t.id, t]));
      for (const t of old.pack.topics) {
        const nt = newTopics.get(t.id);
        if (!nt) { W(`topic "${t.id}" was removed or its id changed (${t.cards.length} cards, ${t.questions.length} questions). Progress saved for it will be orphaned.`); continue; }
        if (nt.cards.length < t.cards.length) W(`topic "${t.id}": cards decreased from ${t.cards.length} to ${nt.cards.length}.`);
        if (nt.questions.length < t.questions.length) W(`topic "${t.id}": questions decreased from ${t.questions.length} to ${nt.questions.length}.`);
        /* progress is keyed by position: an item that still exists but moved is a reorder/insert in the middle */
        const moved = (olds, news, key) => olds.some((o, idx) => idx < news.length && key(news[idx]) !== key(o) && news.some((x, j) => j !== idx && key(x) === key(o)));
        if (moved(t.cards, nt.cards, (c) => c.front)) W(`topic "${t.id}": cards were reordered or inserted before existing ones. Progress is saved by position, so it would point at the wrong cards.`);
        if (moved(t.questions, nt.questions, (q) => q.prompt)) W(`topic "${t.id}": questions were reordered or inserted before existing ones.`);
      }
      const oldIds = old.pack.topics.map((t) => t.id).filter((id) => newTopics.has(id)), newIds = n.pack.topics.map((t) => t.id).filter((id) => oldIds.includes(id));
      if (oldIds.join('\u0000') !== newIds.join('\u0000')) W('the order of existing topics changed.');
      const newNodes = new Set((n.pack.nodes || []).map((x) => x.path));
      for (const x of old.pack.nodes || []) if (!newNodes.has(x.path)) W(`subpack "${x.path}" was removed or its id changed.`);
      const on = (old.pack.nodes || []).map((x) => x.path).filter((p) => newNodes.has(p)), nn = (n.pack.nodes || []).map((x) => x.path).filter((p) => on.includes(p));
      if (on.join('\u0000') !== nn.join('\u0000')) W('the order of existing subpacks changed.');
    } else compat.push(`${entry.id}: the released version could not be read by the normaliser, so no compatibility check was possible.`);
  }

  /* ----- rev ----- */
  const hash = sha256(buf);
  let rev;
  if (relBuf && relCat && Number.isInteger(relCat.rev)) rev = sha256(relBuf) === hash ? relCat.rev : relCat.rev + 1;
  else if (Number.isInteger(entry.rev) && entry.sha256) rev = entry.sha256 === hash ? entry.rev : entry.rev + 1;
  else rev = Number.isInteger(entry.rev) ? entry.rev : 1;

  const built = { ...entry, rev, bytes: buf.length, sha256: hash, counts };
  const row = {}; for (const k of ORDER) if (k in built) row[k] = built[k];
  for (const k of Object.keys(built)) if (!(k in row)) row[k] = built[k];
  out.push(row);
  const changed = entry.rev !== rev || entry.sha256 !== hash || entry.bytes !== buf.length || JSON.stringify(entry.counts) !== JSON.stringify(counts);
  console.log(`${ok}ok${off}  ${entry.id}  rev ${rev}${entry.rev !== rev ? ` ${warnC}(was ${entry.rev ?? '-'})${off}` : ''}  ${buf.length} B  ${counts.topics} topics / ${counts.cards} cards / ${counts.questions} questions${changed ? '' : `  ${dim}unchanged${off}`}` +
    (STATS ? `  ${dim}gzip ${gzipSync(buf).length} B${off}` : ''));
}

if (problems.length) {
  console.error(`\n${bad}${problems.length} problem(s), nothing written:${off}`);
  for (const p of problems) console.error(`${bad}  x${off} ${p}`);
  process.exit(1);
}

if (compat.length) {
  const bar = '!'.repeat(72);
  console.error(`\n${warnC}${bar}\n  PROGRESS COMPATIBILITY WARNING (${compat.length})\n  Learners' saved progress is keyed by topic id and position. Only fixing text\n  and adding to the END of a list is safe. Compared with ${ref}:\n${bar}${off}`);
  for (const w of compat) console.error(`${warnC}  !${off} ${w}`);
  if (!FORCE) { console.error(`\n${warnC}Nothing written. Fix the file, or re-run with --force if this is intentional.${off}`); process.exit(2); }
  console.error(`\n${warnC}--force given: continuing anyway.${off}`);
}

const next = JSON.stringify({ ...catalog, subjects: out }, null, 2) + '\n';
if (readFileSync(catPath, 'utf8') === next) { console.log(`${dim}catalog.json is up to date.${off}`); process.exit(0); }
if (CHECK) { console.error(`${bad}catalog.json is out of date. Run: node tools/build-library.mjs${off}`); process.exit(1); }
writeFileSync(catPath, next);
console.log(`${ok}catalog.json updated.${off}`);
