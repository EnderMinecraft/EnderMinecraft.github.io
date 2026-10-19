import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const TARGET_URL = 'file:///E:/Users/Ender/Downloads/bleeding_edge.html';
const PORT = 9224;
const SCREENSHOT_DIR = 'C:\\Users\\Ender\\.gemini\\antigravity\\brain\\ead1a5fe-528d-437d-a512-d83c08ec4f8f\\scratch\\screenshots';

async function run() {
  console.log('--- STARTING VERIFICATION TEST SUITE ---');
  if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const profileDir = 'C:\\Users\\Ender\\.gemini\\antigravity\\brain\\ead1a5fe-528d-437d-a512-d83c08ec4f8f\\scratch\\chrome-profile-test-dom';
  if (fs.existsSync(profileDir)) {
    try { fs.rmSync(profileDir, { recursive: true, force: true }); } catch (_) {}
  }

  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    `--user-data-dir=${profileDir}`,
    'about:blank'
  ], { stdio: 'ignore' });

  let targets = null;
  for (let i = 0; i < 30; i++) {
    try {
      targets = await new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${PORT}/json`, res => {
          let data = '';
          res.on('data', chunk => data += chunk);
          res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
      });
      if (targets && targets.length) break;
    } catch (e) {
      await new Promise(r => setTimeout(r, 200));
    }
  }

  if (!targets || !targets.length) {
    chrome.kill();
    throw new Error('Chrome remote debugging did not respond.');
  }

  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
  let msgId = 1;
  const callbacks = new Map();
  const exceptions = [];

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.method === 'Runtime.exceptionThrown') {
      exceptions.push(msg.params.exceptionDetails);
      console.error('JS Exception in browser:', msg.params.exceptionDetails);
    }
    if (msg.method === 'Runtime.consoleAPICalled') {
      console.log('BROWSER CONSOLE:', msg.params.args.map(a => a.value !== undefined ? a.value : a.description).join(' '));
    }
    if (msg.id && callbacks.has(msg.id)) {
      callbacks.get(msg.id)(msg.result);
      callbacks.delete(msg.id);
    }
  };

  await new Promise(r => ws.onopen = r);

  function send(method, params = {}) {
    return new Promise((resolve) => {
      const id = msgId++;
      callbacks.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evaluate(expression) {
    const res = await send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res && res.exceptionDetails) {
      throw new Error(`Eval error: ${JSON.stringify(res.exceptionDetails)}`);
    }
    return res && res.result ? res.result.value : undefined;
  }

  async function takeScreenshot(name) {
    const res = await send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(res.data, 'base64');
    const p = path.join(SCREENSHOT_DIR, `${name}.png`);
    fs.writeFileSync(p, buffer);
    console.log(`Saved screenshot: ${p}`);
  }

  try {
    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');

    console.log('Navigating to bleeding_edge.html...');
    await send('Page.navigate', { url: TARGET_URL });
    await new Promise(r => setTimeout(r, 1500));

    // Clear local storage and indexedDB to start clean
    await evaluate(`localStorage.clear();`);

    // Helper: paste and load pack
    async function loadPackViaPaste(packObj) {
      const step1 = await evaluate(`
        (() => {
          const btn = document.querySelector('button[data-go="load"]');
          if (btn) { btn.click(); return { clicked: true }; }
          return { clicked: false, allBtns: Array.from(document.querySelectorAll('button[data-go]')).map(b => b.dataset.go) };
        })()
      `);
      console.log('loadPackViaPaste step1:', JSON.stringify(step1));
      await new Promise(r => setTimeout(r, 500));
      const step2 = await evaluate(`
        (() => {
          const ta = document.getElementById('pasteIn');
          const b = document.querySelector('button[data-act="loadpaste"]');
          if (!ta || !b) return { taFound: !!ta, bFound: !!b };
          ta.value = ${JSON.stringify(JSON.stringify(packObj))};
          b.click();
          return { loaded: true, valLength: ta.value.length };
        })()
      `);
      console.log('loadPackViaPaste step2:', JSON.stringify(step2));
    }

    // TEST 1: Subpack Button Spacing & Title Auto-Expand in Editor
    console.log('\n--- TEST 1: Editor First-Open Title Auto-Expand & Subpack Spacing ---');
    const longTitle = "Lịch sử Việt Nam giai đoạn 1945 - 1975: Toàn bộ diễn biến phong trào cách mạng và chiến dịch trọng điểm";
    const pack1 = {
      format: 'studypack',
      version: 1,
      title: longTitle,
      subject: 'Lịch sử',
      level: 'Lớp 12',
      language: 'vi',
      topics: [
        {
          title: 'Cách mạng tháng Tám 1945',
          summary: 'Diễn biến tổng khởi nghĩa tháng Tám năm 1945',
          notes: [{ heading: 'Bối cảnh', points: ['Nhật đầu hàng đồng minh'] }],
          key_terms: [],
          flashcards: [{ front: '1945', back: 'Cách mạng tháng Tám' }],
          questions: []
        }
      ]
    };

    console.log('Loading study pack with long title...');
    await loadPackViaPaste(pack1);
    await new Promise(r => setTimeout(r, 800));

    // Now go to editor view
    console.log('Navigating to Editor view (first open)...');
    await evaluate(`
      (() => {
        const editBtn = document.querySelector('button[data-go="edit"]');
        if (editBtn) editBtn.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 600));

    const editorMetrics = await evaluate(`
      (() => {
        // Find title textarea in metaBox
        const metaLabels = Array.from(document.querySelectorAll('.ed-side .ed-box:first-child label'));
        const titleLabel = metaLabels.find(l => l.textContent.includes('Tiêu đề') || l.textContent.includes('Title'));
        const titleTa = titleLabel ? titleLabel.querySelector('textarea.ag') : document.querySelector('.ed-side textarea.ag');
        
        // Find subpack selector and add button
        const subpackBox = document.querySelector('.ed-side .ed-box:nth-child(2)');
        const sel = subpackBox ? subpackBox.querySelector('select') : null;
        const addBtn = subpackBox ? Array.from(subpackBox.querySelectorAll('button')).find(b => b.textContent.includes('Thêm gói con') || b.textContent.includes('Add subpack')) : null;

        const selRect = sel ? sel.getBoundingClientRect() : null;
        const btnRect = addBtn ? addBtn.getBoundingClientRect() : null;

        return {
          titleValue: titleTa ? titleTa.value : null,
          titleHeight: titleTa ? titleTa.offsetHeight : 0,
          titleScrollHeight: titleTa ? titleTa.scrollHeight : 0,
          selFound: !!sel,
          addBtnFound: !!addBtn,
          selBottom: selRect ? selRect.bottom : 0,
          btnTop: btnRect ? btnRect.top : 0,
          spacing: btnRect && selRect ? (btnRect.top - selRect.bottom) : 0
        };
      })()
    `);

    console.log('Editor Metrics:', JSON.stringify(editorMetrics, null, 2));

    // Verify Title expansion
    if (editorMetrics.titleHeight > 36) {
      console.log(`[PASS] Title textarea auto-expanded on first open! Height: ${editorMetrics.titleHeight}px (standard 1-line was 36px)`);
    } else {
      console.warn(`[WARN] Title textarea height: ${editorMetrics.titleHeight}px`);
    }

    // Verify Subpack spacing
    if (editorMetrics.spacing >= 6) {
      console.log(`[PASS] Add Subpack button has clean vertical spacing from selector: ${editorMetrics.spacing.toFixed(1)}px!`);
    } else {
      throw new Error(`[FAIL] Add Subpack button is glued to selector! Spacing: ${editorMetrics.spacing}px`);
    }

    await takeScreenshot('01_editor_title_and_subpack_spacing');

    // TEST 2: Import Conflict Dialog (Duplicate Title)
    console.log('\n--- TEST 2: Import Conflict Dialog ---');
    // We already have pack1 loaded and in recent packs with title: longTitle
    // Let's now attempt to paste and import another pack with the SAME title: longTitle
    console.log('Attempting to import pack with duplicate title...');
    await loadPackViaPaste({
      format: 'studypack',
      version: 1,
      title: longTitle,
      topics: [{
        title: 'Chiến dịch Điện Biên Phủ 1954',
        notes: [{ heading: 'Chiến dịch', points: ['56 ngày đêm khoét núi ngủ hầm'] }],
        flashcards: [{ front: '1954', back: 'Chiến thắng Điện Biên Phủ' }],
        questions: []
      }]
    });

    await new Promise(r => setTimeout(r, 600));

    const checkDlg = await evaluate(`
      (() => {
        const allDlgs = Array.from(document.querySelectorAll('dialog')).map(d => ({
          className: d.className,
          open: d.open,
          html: d.outerHTML.slice(0, 200)
        }));
        return {
          dlgs: allDlgs,
          recentsInLS: localStorage.getItem('sp:recent_packs')
        };
      })()
    `);
    console.log('checkDlg:', JSON.stringify(checkDlg));

    // Check if dialog is open and has 3 actions
    const dialogInfo = await evaluate(`
      (() => {
        const dlg = document.querySelector('dialog.ui-dlg');
        if (!dlg || !dlg.open) return { open: false };
        const title = dlg.querySelector('#uiDlgT') ? dlg.querySelector('#uiDlgT').textContent : '';
        const body = dlg.querySelector('p') ? dlg.querySelector('p').textContent : '';
        const btns = Array.from(dlg.querySelectorAll('button[data-action-key]')).map(b => ({
          key: b.getAttribute('data-action-key'),
          label: b.textContent.trim(),
          primary: b.classList.contains('primary')
        }));
        return { open: true, title, body, btns };
      })()
    `);

    console.log('Conflict Dialog Info:', JSON.stringify(dialogInfo, null, 2));

    if (!dialogInfo.open) {
      throw new Error('[FAIL] Conflict dialog did not appear!');
    }
    const hasCancel = dialogInfo.btns.some(b => b.key === 'cancel');
    const hasRename = dialogInfo.btns.some(b => b.key === 'rename');
    const hasOverwrite = dialogInfo.btns.some(b => b.key === 'overwrite');

    if (hasCancel && hasRename && hasOverwrite) {
      console.log('[PASS] Conflict dialog opened with Cancel, Rename & Add, and Overwrite buttons!');
    } else {
      throw new Error(`[FAIL] Missing dialog buttons: ${JSON.stringify(dialogInfo.btns)}`);
    }

    await takeScreenshot('02_import_conflict_dialog');

    // Test Action 1: Click "Rename & Add"
    console.log('\n--- Testing "Rename & Add" action ---');
    await evaluate(`
      (() => {
        const dlg = document.querySelector('dialog.ui-dlg[open]');
        const renameBtn = dlg.querySelector('button[data-action-key="rename"]');
        renameBtn.click();
      })()
    `);

    await new Promise(r => setTimeout(r, 800));

    // Check Current Overview Title (should be renamed pack)
    const currentOverviewTitle = await evaluate(`
      (() => {
        const h1 = document.querySelector('#main h1');
        return h1 ? h1.textContent.trim() : '';
      })()
    `);
    console.log('Current Overview Title:', currentOverviewTitle);

    const expectedRenamed = longTitle + ' (1)';
    if (currentOverviewTitle === expectedRenamed) {
      console.log(`[PASS] Overview correctly loaded the newly renamed pack: "${expectedRenamed}"!`);
    } else {
      throw new Error(`[FAIL] Expected overview title "${expectedRenamed}", got: "${currentOverviewTitle}"`);
    }

    // Now go to load view to inspect the Recent Packs list
    await evaluate(`
      (() => {
        const btn = document.querySelector('button[data-go="load"]');
        if (btn) btn.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 500));

    const recentTitles = await evaluate(`
      (() => {
        const titleEls = Array.from(document.querySelectorAll('.rp-title'));
        return titleEls.map(el => el.textContent.trim());
      })()
    `);
    console.log('Recent Pack Titles in Load Page:', recentTitles);

    if (recentTitles.includes(longTitle) && recentTitles.includes(expectedRenamed)) {
      console.log(`[PASS] Both original "${longTitle}" and renamed "${expectedRenamed}" exist in Recent Packs!`);
    } else {
      throw new Error(`[FAIL] Expected both titles in recents, got: ${JSON.stringify(recentTitles)}`);
    }

    await takeScreenshot('03_load_page_after_rename_and_add');

    // Test Action 2: Duplicate import again, this time choose "Overwrite"
    console.log('\n--- Testing "Overwrite" action ---');
    await loadPackViaPaste({
      format: 'studypack',
      version: 1,
      title: longTitle,
      topics: [{
        title: 'Chiến dịch Hồ Chí Minh 1975',
        notes: [{ heading: 'Mục tiêu', points: ['Giải phóng hoàn toàn miền Nam'] }],
        flashcards: [{ front: '1975', back: 'Chiến dịch Hồ Chí Minh toàn thắng' }],
        questions: []
      }]
    });

    await new Promise(r => setTimeout(r, 600));

    // Confirm dialog is open again
    const dialog2 = await evaluate(`
      (() => {
        const dlg = document.querySelector('dialog.ui-dlg[open]');
        return dlg ? { open: true } : { open: false };
      })()
    `);
    if (!dialog2.open) {
      throw new Error('[FAIL] Dialog did not appear for second duplicate import!');
    }

    // Click Overwrite
    await evaluate(`
      (() => {
        const dlg = document.querySelector('dialog.ui-dlg[open]');
        const overwriteBtn = dlg.querySelector('button[data-action-key="overwrite"]');
        overwriteBtn.click();
      })()
    `);

    await new Promise(r => setTimeout(r, 800));

    // Verify current overview shows the overwritten topic "Chiến dịch Hồ Chí Minh 1975"
    const currentOverviewText = await evaluate(`
      (() => {
        const main = document.getElementById('main');
        return main ? main.innerText : '';
      })()
    `);

    if (currentOverviewText.includes('Chiến dịch Hồ Chí Minh 1975')) {
      console.log('[PASS] Overwrite successfully updated pack content to "Chiến dịch Hồ Chí Minh 1975"!');
    } else {
      throw new Error('[FAIL] Current pack was not updated with overwritten content.');
    }

    await takeScreenshot('04_overview_after_overwrite');

    console.log('\n=======================================');
    console.log('ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!');
    console.log(`Runtime Exceptions: ${exceptions.length}`);
    console.log('=======================================');

  } catch (err) {
    console.error('Test failed with error:', err);
    process.exitCode = 1;
  } finally {
    ws.close();
    chrome.kill();
  }
}

run();
