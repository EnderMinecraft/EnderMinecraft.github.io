# Sloppy Slop — Maintenance Guide

A single-file, no-build revision app. Teachers generate a **study pack** (JSON) from a Word document with an AI assistant; students open it and revise with notes, flashcards and quizzes. Everything runs in the browser and is stored in `localStorage`. Nothing is uploaded.

Current file: `index.html` (one file, ~190 KB, no dependencies except Google Fonts).

---

## 1. Architecture

### 1.1 File layout (top to bottom)

| Section | What it is |
|---|---|
| `<head>` first `<style>` | Bare reset, PWA meta tags, inline manifest (`data:` URL). |
| Main `<style>` | Design tokens, layout, components, sky animation, mobile drawer. See 1.3. |
| `<svg width=0>` | Hidden `<defs>` (cloud gradients and `#cloudShape` symbol). |
| `.sky#sky` | Fixed background: sun, moon, clouds, stars. Decorative, `aria-hidden`. |
| `<header class="top">` | Brand button, language switch, theme switch, focus timer chip and panel. |
| `#app` | Mount point. **Everything below the header is rendered into it by `render()`.** |
| `<script type="text/plain" id="promptText">` | The AI prompt shown on the "Make a pack" page. |
| `<script type="application/json" id="sampleEn" / "sampleVi">` | Built-in example packs. |
| Script 1 | `I18N` dictionary → core helpers (`spParse`, `spNormalise`, `spMerge`, `spHash`) → app IIFE. |
| Script 2 | Service worker registration (see Known issues). |

Script 1 is one long block made of three logical files that were concatenated: `i18n.js`, `core.js`, `app.js`. The `module.exports` guards in the first two are leftovers from that split and are harmless in the browser.

### 1.2 Rendering model

There is no framework. The app is a state object `S` plus string-template functions.

- `render()` builds HTML strings and assigns `#app.innerHTML`. It **rebuilds the whole shell** (rail + main) every time.
- Views: `overview`, `study`, `load`, `teacher`. Picked by `S.view`. The `study` view has three modes (`notes`, `cards`, `quiz`) in `S.mode`, scoped to one topic or all topics via `S.scope` (`'all'` or a topic id).
- View HTML comes from `overviewHTML()`, `studyHTML()` (→ `notesHTML()`, `cardsHTML()`, `quizHTML()`), `loadHTML()`, `teacherHTML()`. Navigation HTML comes from `navHTML()`.
- **Events are delegated** on `document`. Any element with `data-go="overview|topic|all|load|teacher"` calls `go()`. Any element with `data-act="name"` calls `act(name, el)` (a big `switch`). Add behaviour by adding a `data-act` in HTML and a `case` in `act()`.
- Because the DOM is rebuilt, never keep references to elements across renders, and never attach listeners directly to rendered nodes. Use delegation.
- `go()` fades `#main` out (`.is-switching`), swaps state after ~120 ms (220 ms if the mobile drawer was open), calls `render()`, then fades in. It ignores clicks on the view you are already on, and ignores clicks during a transition.
- Tab switches inside `study` use the same trick on `#tabContent`.

### 1.3 CSS organisation

The stylesheet is append-only in practice, so later blocks override earlier ones. Rough order:

1. Tokens (`:root`, dark overrides)
2. WebKit/iOS 16 fixes for `.prog` and `.big`
3. Top bar, switches, timer
4. Buttons, shell/rail, overview, tabs, notes, flashcards, quiz, load/teacher
5. Sky (sun/moon orbit, clouds, stars)
6. Hover glow, transitions, streak card, recent packs, debug popup
7. Collapsible sidebar + make-a-pack fixes + swipe styles
8. "Mobile / responsive fixes" (`860px`, `560px`, `360px` blocks)
9. **Mobile slide-over drawer** (last block, `max-width: 860px`)

Because of that ordering, to change a style, find the **last** rule that sets it (search the selector in all blocks) rather than the first.

### 1.4 Mobile drawer vs desktop rail

- **Desktop (>860px):** sticky left rail. Collapsible with the logo button. State is `S.railOff`, persisted in `sp:rail`.
- **Mobile (≤860px):** the rail is a fixed slide-over drawer, closed by default every load. State is `S.drawerOpen`, **not persisted**. `.shell.drawer-open` opens it; `.scrim` is the backdrop; `html.drawer-lock` stops body scroll.
- Both are driven by the same button (`#brandBtn`, `data-act="toggleRail"`). `toggleRail()` checks `isMobile()` and routes to `setDrawer()` or the desktop toggle.
- The breakpoint lives in **two places** and must match: the CSS `@media (max-width: 860px)` blocks and `mqMobile = matchMedia('(max-width: 860px)')` in JS.
- `#app { z-index: auto }` inside the mobile media block is intentional. Without it `#app` forms a stacking context and the drawer cannot rise above the sticky header.
- Drawer items are single-line with ellipsis (`.rail .nav-i span`). Topic buttons also carry a `title` with the full name.
- Closing paths: scrim tap, × button (`data-act="closeDrawer"`), `Esc`, choosing an item (`go()` calls `setDrawer(false)`), or crossing the breakpoint.
- Long-press on the logo opens the **debug popup** (not the drawer). `BR.long` suppresses the click that follows a long-press.

---

## 2. State

### 2.1 `S` (in-memory, app IIFE)

| Field | Meaning |
|---|---|
| `pack` | The active normalised pack (see 5.2). |
| `key` | Progress key: `'example'` for the sample, otherwise `spHash(title + topic ids/titles)`. |
| `sample` | `true` while the built-in example is shown. |
| `prog` | Progress object, persisted per pack (see 3). |
| `view`, `scope`, `mode` | Current view, topic scope, study tab. |
| `cards` | Flashcard session: `{scope, queue, total, flipped, got, again, hist}`. |
| `quiz` | Quiz session: `{scope, items, i, phase('ask'\|'fb'), started, deadline, done, ...}`. |
| `qiv` | `setInterval` handle for the per-question timer. Always cleared with `stopQT()`. |
| `qopts` / `copts` | Quiz options `{count, secs, shuffle}` and card options `{shuffle, skipKnown}`. Not persisted. |
| `notice` / `loadMsg` | Post-load banner and load-error data. |
| `confirmReset` | Two-step "reset progress" confirmation. |
| `animateMain` | One-shot flag: render `#main` in the hidden state so `go()` can fade it in. |
| `railOff` / `drawerOpen` | Desktop rail collapsed / mobile drawer open. |
| `streakView` | `'week'` (7 cells) or `'month'` (30 cells) on the overview heatmap. |

Other module-level state: `LANG` (current language), `T` (focus timer), `SW` (flashcard swipe gesture), `BR` (logo long-press), `currentRotation` (sky arm angle).

### 2.2 Setting a pack

`setPack(pack, sample)` is the single entry point. It sets `S.pack/key/sample`, loads progress from `sp:prog:<key>`, clears sessions, writes `sp:pack` (empty string for the sample), and updates the header pack name. Always go through it; do not assign `S.pack` directly.

Loading files: `handleFiles` → `loadTexts` → `spParse` → `spNormalise` → `spMerge` (several files become one pack) → `setPack` → `go('overview')`. Errors and warnings are collected as `{file, m:{key, vars}}` and shown via `msgHTML()` / the overview notice.

### 2.3 Progress model (`S.prog`)

```json
{
  "notes": { "<topicId>": true },
  "cards": { "<topicId>:<cardIndex>": { "box": 1 } },
  "quiz":  { "<topicId>": 80 }
}
```

- `notes`: topic marked as read.
- `cards`: Leitner-style box 1–3 (`gotit` promotes, `again` resets to 1). Older saves may hold `true` instead of an object.
- `quiz`: best percentage per topic. Only written when at least `min(3, topic question count)` questions of that topic were answered in a quiz.
- "Ready %" per topic (`topicStats`) averages: notes read (0/1), cards known ratio, best quiz score. Components with no content are skipped.

---

## 3. Storage keys (`localStorage`)

All access goes through the `store` wrapper, which swallows exceptions (private mode, quota).

| Key | Value | Written by |
|---|---|---|
| `sp:lang` | `'vi'` or `'en'`. If absent, `navigator.language` starting with `vi` selects Vietnamese. | `setLang` |
| `sp:theme` | `'light'`, `'dark'` or `'system'` (default when absent). | `setThemeMode`, `toggleTheme` |
| `sp:rail` | `'1'` = desktop rail collapsed, `'0'` = open. | `toggleRail` (desktop only) |
| `sp:pack` | JSON of the last loaded user pack. `''` when the sample is active. | `setPack` |
| `sp:prog:<key>` | JSON progress object (2.3). `<key>` is `example` or a hash. | `saveProg` |
| `sp:recent_packs` | JSON array, newest first, max 5: `{id, title, text, updatedAt}`. `text` is the **raw file text**. | `saveRecentPackToStorage`, rename/delete |
| `sp:timer:<YYYY>-<M>-<D>` | JSON `{n, m}`: focus sessions completed and minutes that day. Month and day are **not** zero-padded (e.g. `2026-3-9`). | `tDone` |

Notes:

- The streak is computed by walking back day by day through `sp:timer:*` keys.
- A recent pack with the same title replaces the older entry.
- The debug popup (long-press the logo) shows key count and approximate storage size.
- To add a key: use the `sp:` prefix, read/write only through `store`, and add a row here.
- Clearing site data wipes everything. There is no export of progress.

---

## 4. Internationalisation

### 4.1 Dictionary

`I18N = { en: {...}, vi: {...} }`. `en` is the fallback for any missing key.

- `tr(key, vars)` looks up the key and replaces `{name}` placeholders from `vars`.
- **Plurals:** if a value is an array `[one, other]`, `vars.n === 1` picks the first, anything else the second. Vietnamese entries are plain strings.
- Static HTML in `index.html`: `data-i18n="key"` sets `textContent`; `data-i18n-attr="title:key;aria-label:key2"` sets attributes. `applyStatic()` applies both and sets `<html lang>`.
- Dynamic HTML calls `tr()` while building strings, so it re-translates on every `render()`.

### 4.2 Validation messages

`core.js` helpers return `spMsg(key, vars)` objects, not text. The UI renders them with `msgText()`, which looks up **`'v_' + key`**. So a core message with key `q_idx` needs an `I18N.<lang>.v_q_idx` entry.

### 4.3 Language switch

`setLang(l)` stores `sp:lang`, calls `applyStatic()`, `syncTheme()`, `tRender()`, reloads the sample pack in the new language if the sample is active, and re-renders. It then animates only elements whose text changed.

The example packs are separate JSON blobs (`sampleEn`, `sampleVi`). User packs keep their own language; the UI language and the pack language are independent.

### 4.4 Known gaps

Some strings are hard-coded Vietnamese or English and are not in `I18N`: the streak card ("Days", "Study Streak", "7 Days", "30 Days", heatmap tooltips), the Recent Packs card (headings, Mở / Sửa / Đổi tên / Xóa, the rename prompt, the "loaded into paste box" flash), and the debug popup. Move them into `I18N` when touching those areas.

---

## 5. Study pack format

### 5.1 File (what the AI produces)

```json
{
  "format": "studypack", "version": 1,
  "title": "", "subject": "", "level": "", "language": "en",
  "topics": [{
    "id": "t1", "title": "", "summary": "",
    "notes": [{ "heading": "", "points": ["... **key term** ..."] }],
    "key_terms": [{ "term": "", "definition": "" }],
    "flashcards": [{ "front": "", "back": "" }],
    "questions": [
      { "type": "mcq", "prompt": "", "options": ["","","",""], "answer": 1, "explanation": "" },
      { "type": "truefalse", "prompt": "", "answer": false, "explanation": "" },
      { "type": "short", "prompt": "", "answer": "model answer", "explanation": "" }
    ]
  }]
}
```

The prompt in `#promptText` is the contract with the AI. If you change the schema, change the prompt, the table on the teacher page (`teacherHTML`, `row1`–`row6` i18n keys), both sample packs, and `spNormalise` together.

### 5.2 Normalised pack (in memory)

`spNormalise` returns `{pack, errors, warnings}`. Bad items are skipped with a warning rather than failing the file; a file fails only if there are no topics or no usable items. Field names change on normalisation:

| File | Normalised topic |
|---|---|
| `key_terms[]` | `terms[]` |
| `flashcards[]` | `cards[]` |
| `notes`, `questions`, `title`, `summary`, `id` | same names |

Topic ids are de-duplicated (`t1`, `t1-2`, …). `spMerge` concatenates topics from several files and re-uniquifies ids. `spParse` tolerates BOMs, ` ```json ` fences and text around the JSON.

`**bold**` inside note points is the only formatting; `rich()` turns it into `<mark>`. Everything else is escaped with `esc()`. Always escape user/pack text before putting it in a template string.

---

## 6. Theme

### 6.1 Tokens

Colours, fonts and the sky's glow values are CSS custom properties on `:root`. The dark palette is defined **three times** and must be kept in sync:

1. `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` — system dark.
2. `:root[data-theme="dark"] { ... }` — forced dark.
3. `:root { ... }` — light defaults.

To add or change a token, edit all three.

### 6.2 Modes

Three modes via the segmented control: `light`, `dark`, `system`. `getThemeMode()` reads `sp:theme`; `isDark()` resolves `system` through `matchMedia('(prefers-color-scheme: dark)')`.

- `setThemeMode(mode)` writes the key, sets or removes `data-theme` on `<html>`, calls `syncTheme()`, and rotates the sky arm by 180° if the resolved dark/light state flipped.
- `syncTheme()` toggles `.dark` on `#sky` and updates the switch (`data-theme-mode` drives the sliding thumb) and `aria-pressed`.
- `:root.theme-anim` is added for 1.5 s during a change to enable colour transitions, then removed.
- A `MutationObserver` on `data-theme` re-runs `syncTheme()`. A system-theme listener handles OS changes while in `system` mode.
- `toggleTheme()` and `data-act="theme"` are legacy (the old single toggle button); the segmented control uses `theme-mode`.

### 6.3 Sky

`.sky` holds a sun and a moon on opposite ends of one rotating arm (`.orbit`, angle in `--deg`). Orbs counter-rotate to stay upright. `.sky.ready` is added after two animation frames so the first paint does not animate. Clouds fade out and stars fade in under `.sky.dark`. Stars are generated in `makeStars()` (64 `<i>` elements). `prefers-reduced-motion` disables the animations.

---

## 7. Other subsystems

**Focus timer.** `T = {focus, brk, mode, left, running, endsAt, ...}`. Uses an absolute `endsAt` timestamp, so it stays correct when the tab is throttled. `tDone()` plays a beep (Web Audio), flips mode, and on a completed focus session increments `sp:timer:<day>`. The panel is `#timerPanel`; `openPanel(bool)` shows or hides it.

**Flashcards.** Queue-based. `cardRate`, `cardSkip`, `cardPrev` mutate `S.cards` and keep a history stack (max 100) so "Previous" can undo a rating. Swipe uses pointer events (`SW`): right = got it, left = again, up = skip, down = previous. A short drag suppresses the click-to-flip (`SW.lastEnd`).

**Quiz.** `startQuiz` builds `items` (`{tid, ttitle, q, order, res, ...}`). Phases: `ask` → `fb` → next. Short-answer questions are self-graded. The timer uses `deadline` and `tickQ` every 200 ms. `finishQuiz` computes per-topic scores and saves bests.

**Recent packs.** Raw file text is stored, then re-parsed on open. "Sửa" (edit) loads the text into the paste box.

**Keyboard.** Cards: `Space`/`Enter` flip, arrows rate/skip/back. Quiz: `A–D` or `1–4`, `T`/`F`, `Enter`/`Space` for next. `Esc` closes the timer panel, debug popup and mobile drawer.

---

## 8. How-tos

### Add or change UI text
1. Add the key to **both** `I18N.en` and `I18N.vi` (use an array for plural-sensitive strings).
2. In JS use `tr('key', {n: 3})`. In static HTML use `data-i18n="key"`, or `data-i18n-attr="aria-label:key"`.

### Add a language
1. Add a full `I18N.xx` block (copy `en`).
2. Extend `detectLang()` and the `setLang` guard (`l !== 'vi' && l !== 'en'`), and `applyStatic`'s `aria-pressed` logic already works from `data-l`.
3. Add a button to `#langSeg`. The switch is a **2-column grid** with a thumb that is moved by `.seg[data-lang="en"]::before`, so a third option needs the same treatment as `.seg.seg-3` (3 columns, `translateX` per state).
4. Add a sample pack `<script id="sampleXx">` and update `sampleFor()`.

### Add a new view or page
1. Write `fooHTML()`.
2. Add it to the `if/else` chain in `render()`.
3. Add a nav button with `data-go="foo"` in `navHTML()` and an active-view guard line in `go()`.
4. If it needs a click action, add a `data-act` and a `case` in `act()`.

### Add a field to the study pack
1. Add it to the prompt (`#promptText`) and to the teacher page table + i18n row.
2. Read and validate it in `spNormalise` (decide on a warning key, add `v_…` messages in both languages).
3. Render it in the relevant `*HTML()` function, escaping the value.
4. Add it to both sample packs.
5. Remember the saved-pack caveat in section 9 when choosing field names.

### Add a question type
1. `spNormalise`: validate and normalise it.
2. `questionHTML()`: render the answer UI. `answer()`/`gradeShort()` show the existing patterns for auto- and self-graded types.
3. `quizResultHTML()`: the "To review" answer text.
4. Prompt, teacher table and `v_q_type` message text.

### Add a persisted setting
Pick an `sp:` key, read it into `S` at declaration (like `railOff`), write through `store.set`, and document it in section 3.

### Change the mobile breakpoint
Update every `max-width: 860px` in CSS **and** `mqMobile` in JS. Check the `560px` and `360px` blocks still make sense.

### Change colours or fonts
Edit tokens in all three places (6.1). Fonts: `--font-ui`, `--font-read`, `--font-mono`; the Google Fonts `<link>` must load any new family.

### Reset everything while testing
Run `localStorage.clear()` in the console and reload, or use "Reset my progress" on the overview (progress only).

### Release checklist
- Load the sample in EN and VI; switch language mid-quiz and mid-deck.
- Load a malformed file, a partially valid file, and two files at once.
- Light, dark and system themes; flip OS theme while on `system`.
- Desktop: collapse and expand the rail, reload (state persists).
- Mobile width: drawer starts closed after every reload, opens and closes by all five paths, scroll is locked while open, long topic names are truncated.
- Flashcards: swipe in four directions, `Previous` after each.
- Quiz with a time limit, including time-out on a short-answer question.
- Timer: run a focus session to completion; the streak updates.
- iOS Safari: inputs do not zoom (16 px), safe-area insets respected.

---

## 9. Known issues and gotchas

~~1. **Saved pack loses terms and flashcards on reload.** `setPack` stores the *normalised* pack (`terms`, `cards`), but boot re-runs `spNormalise`, which reads `key_terms` and `flashcards`. After a refresh the key terms and flashcards of a user pack are empty. Fix by storing the original data, or by making `spNormalise` also accept `terms`/`cards`.~~
~~2. **"Again" counts as known.** `cardRate(false)` stores `{box: 1}`, which is truthy, and `topicStats` / the deck counters / "skip known" test truthiness. Use `box >= 2` (or similar) as the "known" test everywhere cards are counted.~~
3. **Service worker probably never registers.** It is created from a `blob:` URL, which browsers generally refuse for service workers; the failure is only logged. Real offline support needs a separate `sw.js` file. The inline manifest also does not include icons.
4. **Whole-shell re-render.** Any `render()` resets scroll inside the rail and any uncommitted input outside `#typed`. Keep that in mind when adding forms.
~~5. **Dead or duplicate code.** `toggleTheme` / `data-act="theme"`, `initStars` (skipped because `makeStars` already fills `.stars`), and unused `S.animateTab`.~~
~~6. **Progress key depends on titles.** Renaming a pack's title or topics changes `S.key`, which orphans its saved progress.~~
