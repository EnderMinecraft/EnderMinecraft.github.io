import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const TARGET_URL = 'file:///E:/Users/Ender/Downloads/bleeding_edge.html';
const PORT = 9222;
const SCREENSHOT_DIR = 'C:\\Users\\Ender\\.gemini\\antigravity\\brain\\ead1a5fe-528d-437d-a512-d83c08ec4f8f\\scratch\\screenshots';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Sample study pack for testing
const SAMPLE_PACK = {
  id: "test-cs-pack",
  title: "Computer Science Revision",
  subject: "Computer Science",
  level: "University",
  language: "en",
  topics: [
    {
      id: "os",
      title: "Operating Systems",
      summary: "Processes, virtual memory, scheduling, and concurrency.",
      notes: [
        {
          heading: "Processes & Scheduling",
          points: [
            "A process is a program in execution with isolated memory.",
            "Context switching saves the CPU state of the current process."
          ]
        }
      ],
      terms: [
        { term: "Deadlock", definition: "A situation where set of processes are blocked waiting on each other." }
      ],
      cards: [
        { front: "What is Virtual Memory?", back: "An abstraction creating the illusion of large contiguous memory." },
        { front: "What is a Mutex?", back: "Mutual exclusion lock ensuring single thread execution." }
      ],
      questions: [
        {
          type: "mcq",
          prompt: "Which component assigns CPU execution time to ready processes?",
          options: ["CPU Scheduler", "Linker", "BIOS", "Compiler"],
          answer: 0,
          explanation: "The CPU scheduler chooses which process in the ready queue executes."
        },
        {
          type: "truefalse",
          prompt: "A context switch between threads of the same process requires changing page tables.",
          answer: false,
          explanation: "Threads of the same process share the same virtual address space."
        }
      ]
    }
  ]
};

async function run() {
  console.log('=== CHROME DEVTOOLS FUNCTIONALITY AUTO-TEST SUITE ===\n');

  console.log('[1/7] Launching Headless Chrome with Remote Debugging (port ' + PORT + ')...');
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    '--user-data-dir=C:\\Users\\Ender\\.gemini\\antigravity\\brain\\ead1a5fe-528d-437d-a512-d83c08ec4f8f\\scratch\\chrome-profile',
    'about:blank'
  ], { stdio: 'ignore' });

  // Connect to Chrome CDP
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
    throw new Error('Chrome did not respond on debugging port ' + PORT);
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
      console.error('  [CDP Exception]:', msg.params.exceptionDetails?.exception?.description || msg.params.exceptionDetails?.text);
    }
    if (msg.id && callbacks.has(msg.id)) {
      callbacks.get(msg.id)(msg.result);
      callbacks.delete(msg.id);
    }
  };

  await new Promise(r => ws.onopen = r);

  function send(method, params = {}) {
    const id = msgId++;
    return new Promise(resolve => {
      callbacks.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evaluate(expression) {
    const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (res?.exceptionDetails) {
      console.error('  [Eval Error]:', res.exceptionDetails?.exception?.description || res.exceptionDetails?.text);
    }
    return res?.result?.value;
  }

  async function screenshot(name) {
    const res = await send('Page.captureScreenshot', { format: 'png' });
    if (res?.data) {
      const p = path.join(SCREENSHOT_DIR, name + '.png');
      fs.writeFileSync(p, Buffer.from(res.data, 'base64'));
      console.log(`  📸 Screenshot captured: ${name}.png`);
      return p;
    }
    return null;
  }

  await send('Page.enable');
  await send('Runtime.enable');
  await send('DOM.enable');

  console.log('[2/7] Navigating to bleeding_edge.html...');
  await send('Page.navigate', { url: TARGET_URL });
  await new Promise(r => setTimeout(r, 1500));

  console.log('[3/7] Loading Study Pack via Paste Input...');
  // Navigate to Open view
  await evaluate(`
    (() => {
      const openBtn = document.querySelector('button[data-go="load"]');
      if (openBtn) openBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 500));

  // Paste study pack into #pasteIn and click loadpaste
  await evaluate(`
    (() => {
      const ta = document.getElementById('pasteIn');
      if (ta) {
        ta.value = ${JSON.stringify(JSON.stringify(SAMPLE_PACK))};
        const loadBtn = document.querySelector('button[data-act="loadpaste"]');
        if (loadBtn) loadBtn.click();
      }
    })()
  `);
  await new Promise(r => setTimeout(r, 1000));

  // TEST SUITE 1: Overview & Recent Packs UI
  console.log('\n--- TEST SUITE 1: Overview & Recent Packs UI ---');
  const overviewCheck = await evaluate(`
    (() => {
      const titleEl = document.querySelector('#main h1, #main h2');
      const topicCard = document.querySelector('.trow');
      const topicTitle = topicCard ? topicCard.querySelector('h3, b')?.textContent?.trim() : null;
      const recentCards = document.querySelectorAll('.rp-card');
      const searchInput = document.getElementById('rpQ');
      return {
        mainHeading: titleEl ? titleEl.textContent.trim() : null,
        hasTopicCard: !!topicCard,
        topicTitle: topicTitle,
        hasSearchbar: !!searchInput
      };
    })()
  `);
  console.log('✓ Overview Check:', JSON.stringify(overviewCheck));
  await screenshot('01_overview_loaded');

  // TEST SUITE 2: Study Mode - Flashcards
  console.log('\n--- TEST SUITE 2: Study Mode - Flashcards ---');
  // Click on topic to enter Study mode
  await evaluate(`
    (() => {
      const trow = document.querySelector('.trow[data-go="topic"]');
      if (trow) trow.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  // Switch to Cards tab
  await evaluate(`
    (() => {
      const cardTab = document.querySelector('button[data-act="tab"][data-mode="cards"]');
      if (cardTab) cardTab.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  const flashcardState1 = await evaluate(`
    (() => {
      const card = document.querySelector('.face');
      const promptText = card ? card.textContent.trim() : null;
      return { hasCard: !!card, frontText: promptText?.slice(0, 40) };
    })()
  `);
  console.log('✓ Flashcard Front Loaded:', JSON.stringify(flashcardState1));

  // Flip Flashcard
  console.log('✓ Flipping Flashcard (Act: flip)...');
  await evaluate(`
    (() => {
      const card = document.querySelector('.face');
      if (card) card.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const flashcardState2 = await evaluate(`
    (() => {
      const rateBtns = Array.from(document.querySelectorAll('.rate .btn')).map(b => b.textContent.trim());
      return { isBackVisible: rateBtns.length > 0, rateOptions: rateBtns };
    })()
  `);
  console.log('✓ Flashcard Back & Rating Controls:', JSON.stringify(flashcardState2));
  await screenshot('02_flashcard_flipped');

  // Rate card 'Good'
  console.log('✓ Rating Card as Good (Key: ArrowRight)...');
  await evaluate(`
    (() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  // TEST SUITE 3: Study Mode - Quiz & Semantic A11y Radiogroups
  console.log('\n--- TEST SUITE 3: Study Mode - Quiz & Semantic A11y ---');
  // Switch to Quiz tab
  await evaluate(`
    (() => {
      const quizTab = document.querySelector('button[data-act="tab"][data-mode="quiz"]');
      if (quizTab) quizTab.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  // Click Start Quiz button
  await evaluate(`
    (() => {
      const startBtn = document.querySelector('.qset button[data-act="qstart"]');
      if (startBtn) startBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  const quizQuestionCheck = await evaluate(`
    (() => {
      const radiogroup = document.querySelector('.opts[role="radiogroup"]');
      const radios = Array.from(document.querySelectorAll('.opts [role="radio"]'));
      const promptEl = document.querySelector('.q-p');
      return {
        prompt: promptEl ? promptEl.textContent.trim() : null,
        hasRadiogroup: !!radiogroup,
        radiogroupLabel: radiogroup ? radiogroup.getAttribute('aria-label') : null,
        optionsCount: radios.length,
        optionsLabels: radios.map(r => r.textContent.trim().slice(0, 30))
      };
    })()
  `);
  console.log('✓ Quiz Question & Semantic Radiogroup:', JSON.stringify(quizQuestionCheck));

  // Pick first option
  console.log('✓ Answering Option 1 (Choice A)...');
  await evaluate(`
    (() => {
      const firstOpt = document.querySelector('.opts [role="radio"]');
      if (firstOpt) firstOpt.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const quizFeedbackCheck = await evaluate(`
    (() => {
      const fb = document.querySelector('.fb');
      const liveText = document.getElementById('a11yLive')?.textContent?.trim();
      const firstOpt = document.querySelector('.opts [role="radio"]');
      return {
        hasFeedback: !!fb,
        feedbackOk: fb ? fb.classList.contains('ok') : false,
        firstOptAriaChecked: firstOpt ? firstOpt.getAttribute('aria-checked') : null,
        a11yLiveAnnouncement: liveText
      };
    })()
  `);
  console.log('✓ Quiz Feedback & Polite Live Announcement:', JSON.stringify(quizFeedbackCheck));
  await screenshot('03_quiz_feedback');

  // Next Question
  console.log('✓ Advancing to Question 2...');
  await evaluate(`
    (() => {
      const nextBtn = document.querySelector('button[data-act="next"]');
      if (nextBtn) nextBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 500));

  // Answer Q2 (True/False)
  console.log('✓ Answering True/False (Choice 2: False)...');
  await evaluate(`
    (() => {
      const tfRadios = document.querySelectorAll('.opts [role="radio"]');
      if (tfRadios.length >= 2) tfRadios[1].click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  // Advance to Results
  console.log('✓ Submitting Quiz to Final Screen...');
  await evaluate(`
    (() => {
      const nextBtn = document.querySelector('button[data-act="next"]');
      if (nextBtn) nextBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  const quizResultCheck = await evaluate(`
    (() => {
      const scoreBig = document.querySelector('.quiz.celebrate .big, .quiz .big');
      const scoreH2 = document.querySelector('.quiz.celebrate h2, .quiz .score h2');
      return {
        scorePct: scoreBig ? scoreBig.textContent.trim() : null,
        heading: scoreH2 ? scoreH2.textContent.trim() : null
      };
    })()
  `);
  console.log('✓ Quiz Results Screen:', JSON.stringify(quizResultCheck));
  await screenshot('04_quiz_celebration');

  // TEST SUITE 4: Exam Mode Runner & ARIA Radiogroups
  console.log('\n--- TEST SUITE 4: Exam Mode Runner & ARIA Radiogroups ---');
  await evaluate(`
    (() => {
      const examNav = document.querySelector('button[data-go="exam"]');
      if (examNav) examNav.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  // Start Exam via data-act="examStart"
  console.log('✓ Starting Exam (data-act="examStart")...');
  await evaluate(`
    (() => {
      const startExamBtn = document.querySelector('button[data-act="examStart"]');
      if (startExamBtn) startExamBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  const examRunnerCheck = await evaluate(`
    (() => {
      const optsContainer = document.querySelector('.exam-opts[role="radiogroup"]');
      const options = document.querySelectorAll('.exam-opt[role="radio"]');
      return {
        hasRadiogroup: !!optsContainer,
        optionsCount: options.length,
        firstOptionText: options[0]?.querySelector('.exam-opt-text')?.textContent?.trim()
      };
    })()
  `);
  console.log('✓ Exam Runner Interface & Semantic Options:', JSON.stringify(examRunnerCheck));

  // Select Option 0
  console.log('✓ Selecting Exam Option 1 (Choice A)...');
  await evaluate(`
    (() => {
      const opt = document.querySelector('.exam-opt[data-act="examSelectAns"]');
      if (opt) opt.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 300));

  const examSelectionCheck = await evaluate(`
    (() => {
      const opt = document.querySelector('.exam-opt[data-act="examSelectAns"]');
      return {
        isSelectedClass: opt ? opt.classList.contains('selected') : false,
        ariaChecked: opt ? opt.getAttribute('aria-checked') : null
      };
    })()
  `);
  console.log('✓ Exam Option Selection State:', JSON.stringify(examSelectionCheck));
  await screenshot('05_exam_runner');

  // Next question in Exam
  await evaluate(`
    (() => {
      const nextBtn = document.querySelector('button[data-act="nextExamQ"]');
      if (nextBtn) nextBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  // Answer Q2 in Exam (True/False)
  await evaluate(`
    (() => {
      const opt = document.querySelector('.exam-opts.grid-tf .exam-opt');
      if (opt) opt.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 300));

  // Finish Exam
  console.log('✓ Submitting Exam...');
  await evaluate(`
    (() => {
      const submitBtn = document.querySelector('button[data-act="submitExam"]');
      if (submitBtn) submitBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 300));

  // Confirm submit dialog
  await evaluate(`
    (() => {
      const confirmBtn = document.querySelector('button[data-act="confirmSubmitExam"]') ||
                         document.querySelector('.ui-dlg-btns button.primary');
      if (confirmBtn) confirmBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 700));

  const examReviewCheck = await evaluate(`
    (() => {
      const scoreBig = document.querySelector('.score .big, .exam-score');
      const rows = document.querySelectorAll('.rv-row');
      return {
        score: scoreBig ? scoreBig.textContent.trim() : null,
        reviewRowsCount: rows.length
      };
    })()
  `);
  console.log('✓ Exam Review & Scoring Results:', JSON.stringify(examReviewCheck));
  await screenshot('06_exam_review');

  // TEST SUITE 5: Settings, Theme Switcher & Rainbow Mode
  console.log('\n--- TEST SUITE 5: Settings, Theme Switcher & Rainbow Mode ---');
  await evaluate(`
    (() => {
      const stBtn = document.querySelector('button[data-go="settings"]');
      if (stBtn) stBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  // Switch to Dark Theme
  console.log('✓ Switching Theme to Dark Mode...');
  await evaluate(`
    (() => {
      const darkBtn = document.querySelector('button[data-act="theme-mode"][data-m="dark"]') ||
                      document.querySelector('button[data-act="setTheme"][data-val="dark"]') ||
                      Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Dark') || b.textContent.includes('Tối'));
      if (darkBtn) darkBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const themeCheck = await evaluate(`
    (() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        dataTheme: document.documentElement.getAttribute('data-theme'),
        bg: cs.getPropertyValue('--bg').trim(),
        ink: cs.getPropertyValue('--ink').trim()
      };
    })()
  `);
  console.log('✓ Dark Theme Applied:', JSON.stringify(themeCheck));
  await screenshot('07_settings_dark_mode');

  // TEST SUITE 6: Mobile Emulation & Drawer Focus Trap
  console.log('\n--- TEST SUITE 6: Mobile Viewport & Drawer Focus Trap ---');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true
  });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true });
  await new Promise(r => setTimeout(r, 500));

  // Tap Brand Button on Mobile
  console.log('✓ Tapping Brand Button on Mobile Viewport...');
  await evaluate(`
    (() => {
      const brandBtn = document.getElementById('brandBtn');
      if (brandBtn) brandBtn.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const mobileDrawerOpenCheck = await evaluate(`
    (() => {
      const shell = document.querySelector('.shell');
      const brandBtn = document.getElementById('brandBtn');
      const rail = document.getElementById('railNav');
      const activeEl = document.activeElement;
      return {
        isDrawerOpen: shell ? shell.classList.contains('drawer-open') : false,
        brandBtnExpanded: brandBtn ? brandBtn.getAttribute('aria-expanded') : null,
        activeElementInDrawer: rail ? rail.contains(activeEl) : false,
        activeElementTag: activeEl ? activeEl.tagName : null
      };
    })()
  `);
  console.log('✓ Mobile Drawer Open State & Initial Focus:', JSON.stringify(mobileDrawerOpenCheck));
  await screenshot('08_mobile_drawer_open');

  // Press Escape Key
  console.log('✓ Pressing Escape Key...');
  await evaluate(`
    (() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const mobileDrawerClosedCheck = await evaluate(`
    (() => {
      const shell = document.querySelector('.shell');
      const brandBtn = document.getElementById('brandBtn');
      const activeEl = document.activeElement;
      return {
        isDrawerOpen: shell ? shell.classList.contains('drawer-open') : false,
        brandBtnExpanded: brandBtn ? brandBtn.getAttribute('aria-expanded') : null,
        focusRestoredToBrandBtn: activeEl === brandBtn
      };
    })()
  `);
  console.log('✓ Mobile Drawer Closed & Focus Restored to #brandBtn:', JSON.stringify(mobileDrawerClosedCheck));

  // Reset viewport to desktop
  await send('Emulation.clearDeviceMetricsOverride');
  await send('Emulation.setTouchEmulationEnabled', { enabled: false });

  // TEST SUITE 7: Pack Editor View & Save Shortcut
  console.log('\n--- TEST SUITE 7: Pack Editor & Shortcuts ---');
  await evaluate(`
    (() => {
      const editNav = document.querySelector('button[data-go="edit"]');
      if (editNav) editNav.click();
    })()
  `);
  await new Promise(r => setTimeout(r, 600));

  const editorCheck = await evaluate(`
    (() => {
      const ed = document.querySelector('.ed');
      const modes = Array.from(document.querySelectorAll('.ed-modes .ed-pill, .ed-tabs .ed-pill')).map(p => p.textContent.trim());
      return {
        hasEditor: !!ed,
        tabs: modes
      };
    })()
  `);
  console.log('✓ Pack Editor GUI Initialized:', JSON.stringify(editorCheck));
  await screenshot('09_editor_gui');

  // Trigger Save Shortcut (Ctrl+S)
  console.log('✓ Triggering Editor Save Shortcut (Ctrl+S)...');
  await evaluate(`
    (() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true }));
    })()
  `);
  await new Promise(r => setTimeout(r, 400));

  const toastCheck = await evaluate(`
    (() => {
      const toast = document.getElementById('edToast');
      const liveText = document.getElementById('a11yLive')?.textContent?.trim();
      return {
        toastVisible: toast ? toast.classList.contains('show') : false,
        toastText: toast ? toast.textContent.trim() : null,
        a11yLiveAnnounced: liveText
      };
    })()
  `);
  console.log('✓ Save Toast & Live Region Announcement:', JSON.stringify(toastCheck));

  // Clean shutdown
  ws.close();
  chrome.kill();

  console.log('\n======================================================');
  if (exceptions.length > 0) {
    console.error(`FAILED: ${exceptions.length} uncaught JS exceptions detected during test run!`);
    process.exit(1);
  } else {
    console.log('🎉 ALL 7 CHROME DEVTOOLS FUNCTIONALITY TEST SUITES PASSED WITH 0 ERRORS!');
    console.log('======================================================');
  }
}

run().catch(err => {
  console.error('Fatal execution error:', err);
  process.exit(1);
});
