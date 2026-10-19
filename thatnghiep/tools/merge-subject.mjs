#!/usr/bin/env node
/* Merge per-chapter JSON files (one chapter object each, as produced by the AI) into one subject file.
   Usage: node tools/merge-subject.mjs --id bio-10 --title "Biology 10" --subject Biology --level "High school" \
            --lang en --out library/subjects/bio-10.json  ch01.json ch02.json ...
   Each chapter file may be a bare chapter {id,title,topics:[...]}, or {"packs":[chapter]}. Chapters become subpacks.
   It checks duplicate ids and duplicate question prompts, then you run: node tools/build-library.mjs */
import { readFileSync, writeFileSync } from 'node:fs';
const argv = process.argv.slice(2), opts = {}, files = [];
for (let i = 0; i < argv.length; i++) argv[i].startsWith('--') ? (opts[argv[i].slice(2)] = argv[++i]) : files.push(argv[i]);
for (const k of ['id', 'title', 'out']) if (!opts[k]) { console.error(`missing --${k}`); process.exit(1); }
if (!files.length) { console.error('give at least one chapter .json file'); process.exit(1); }
const problems = [], chapters = [], chIds = new Set(), prompts = new Map();
for (const f of files) {
  let raw = readFileSync(f, 'utf8').trim().replace(/^```(?:json)?\s*|\s*```$/g, ''); /* tolerate a pasted code fence */
  let d; try { d = JSON.parse(raw); } catch (e) { problems.push(`${f}: not valid JSON (${e.message})`); continue; }
  const list = Array.isArray(d.packs) && !d.topics ? d.packs : [d];
  for (const ch of list) {
    if (!ch.title || !Array.isArray(ch.topics)) { problems.push(`${f}: a chapter needs "title" and "topics"`); continue; }
    ch.id = ch.id || 'ch' + (chapters.length + 1);
    if (chIds.has(ch.id)) problems.push(`${f}: duplicate chapter id "${ch.id}"`); chIds.add(ch.id);
    const tIds = new Set();
    for (const t of ch.topics) {
      if (!/^[a-z0-9][a-z0-9-]*$/.test(t.id || '')) problems.push(`${f}: topic id "${t.id}" should be lowercase-with-dashes`);
      if (tIds.has(t.id)) problems.push(`${f}: duplicate topic id "${t.id}" in chapter ${ch.id}`); tIds.add(t.id);
      for (const q of t.questions || []) {
        const key = String(q.prompt || '').trim().toLowerCase();
        if (prompts.has(key)) problems.push(`${f}: question prompt repeated in ${ch.id}/${t.id} (also in ${prompts.get(key)}): "${q.prompt}"`); else prompts.set(key, `${ch.id}/${t.id}`);
        if (q.type === 'mcq' && (!Array.isArray(q.options) || q.options.length < 2 || !Number.isInteger(q.answer) || q.answer >= q.options.length)) problems.push(`${f}: bad mcq in ${ch.id}/${t.id}: "${q.prompt}" (check the answer index)`);
      }
    }
    chapters.push(ch);
  }
}
if (problems.length) { console.error(`${problems.length} problem(s), nothing written:`); problems.forEach((p) => console.error('  x ' + p)); process.exit(1); }
const out = { id: opts.id, title: opts.title, subject: opts.subject || '', level: opts.level || '', language: opts.lang || 'en', topics: [], packs: chapters };
writeFileSync(opts.out, JSON.stringify(out, null, 1) + '\n');
console.log(`wrote ${opts.out}: ${chapters.length} chapter(s), ${chapters.reduce((n, c) => n + c.topics.length, 0)} topics.`);
