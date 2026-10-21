// Optional development QA. Requires Playwright; the app itself has no npm dependency.
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'output', 'web-qa');
const temp = path.join(root, 'tmp', 'browser-qa', randomUUID());
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync(temp, { recursive: true });
const child = spawn(process.env.MEMORY_PYTHON || 'python', ['-X', 'utf8', '-u', path.join(root, 'webapp.py'), '--port', '0', '--db', path.join(temp, 'chat.sqlite3')], {
  cwd: root, windowsHide: true, env: { ...process.env, OPENAI_API_KEY: '' }, stdio: ['ignore', 'pipe', 'pipe'],
});
let log = '', browser;
const checks = {};
child.stderr.on('data', chunk => { log += chunk; });
const address = new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error('Test server did not start')), 10000);
  child.stdout.on('data', chunk => {
    log += chunk;
    const match = log.match(/running at (http:\/\/127\.0\.0\.1:\d+)/);
    if (match) { clearTimeout(timer); resolve(match[1]); }
  });
  child.once('error', reject);
  child.once('exit', code => { clearTimeout(timer); reject(new Error('Server exit ' + code + '\n' + log)); });
});

(async () => {
  const url = await address;
  const executable = process.env.MEMORY_BROWSER_PATH || [
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ].find(file => fs.existsSync(file));
  browser = await chromium.launch({ headless: true, executablePath: executable, args: ['--no-first-run'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.locator('#projectSelect option').first().waitFor({ state: 'attached' });
  await page.screenshot({ path: path.join(output, '01-welcome.png'), fullPage: true });
  checks.initial_page_loaded = await page.locator('#welcome').isVisible();

  async function send(text) {
    const before = await page.locator('.message.assistant').count();
    await page.locator('#messageInput').fill(text);
    await page.locator('#messageInput').press('Enter');
    await page.waitForFunction(expected => document.querySelectorAll('.message.assistant').length === expected && !document.getElementById('messageInput').disabled, before + 1);
  }
  await send('Dự án dùng TypeScript, PostgreSQL và JWT. Chúng ta chọn API REST /api/v1 với JSON snake_case.');
  assert.equal(await page.locator('.memory-card').count(), 4);
  checks.natural_decisions_saved = true;
  await page.locator('#newChat').click();
  await page.locator('#welcome').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.message').count(), 0);
  assert.equal(await page.locator('.memory-card').count(), 4);
  await send('Bạn đang nhớ quy ước nào của dự án?');
  const remembered = await page.locator('.message.assistant').innerText();
  assert(remembered.includes('TypeScript') && remembered.includes('PostgreSQL') && remembered.includes('JWT'));
  checks.new_chat_recalls_memory = true;
  await page.screenshot({ path: path.join(output, '02-new-chat-memory.png'), fullPage: true });

  await send('Chuyển authentication từ JWT sang session cookie.');
  await page.locator('#newChat').click();
  await page.locator('#welcome').waitFor({ state: 'visible' });
  await send('Hãy lập kế hoạch middleware đăng nhập theo quy ước dự án.');
  assert((await page.locator('.message.assistant').innerText()).includes('session cookie'));
  await page.locator('#openTrace').click();
  const trace = JSON.parse(await page.locator('#traceContent').innerText());
  assert.equal(trace.request.input.length, 2);
  assert(!JSON.stringify(trace.request).toLowerCase().includes('jwt'));
  checks.new_chat_uses_updated_cookie_without_stale_jwt = true;
  await page.screenshot({ path: path.join(output, '03-injected-context.png'), fullPage: true });
  await page.locator('[data-close="traceDialog"]').click();
  await page.locator('#historyTab').click();
  assert.equal(await page.locator('.memory-card.superseded').count(), 1);
  assert.equal(await page.locator('.memory-card').count(), 5);
  checks.superseded_history_visible = true;
  await page.screenshot({ path: path.join(output, '04-history.png'), fullPage: true });

  const downloaded = page.waitForEvent('download');
  await page.locator('#exportEvidence').click();
  const download = await downloaded;
  await download.saveAs(path.join(output, 'browser-export.json'));
  const exported = JSON.parse(fs.readFileSync(path.join(output, 'browser-export.json'), 'utf8'));
  assert.equal(exported.memory.history.length, 5);
  checks.export_evidence_downloaded = true;

  await send('<img src=x onerror=alert(1)>');
  assert.equal(await page.locator('.message.user img').count(), 0);
  checks.message_html_rendered_as_text = true;
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.querySelectorAll('.message.user').length === 2);
  checks.reload_retains_conversation = true;

  await page.locator('#addProject').click();
  await page.locator('#projectInput').fill('Dự án kiểm tra độc lập');
  await page.locator('#projectForm button[type=submit]').click();
  await page.waitForFunction(() => document.getElementById('projectTitle').textContent === 'Dự án kiểm tra độc lập');
  assert.equal(await page.locator('.memory-card').count(), 0);
  checks.separate_project_has_empty_memory = true;

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, '05-mobile.png'), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  checks.mobile_has_no_horizontal_overflow = true;
  await page.locator('#messageInput').fill('Dòng một');
  await page.locator('#messageInput').press('Shift+Enter');
  await page.locator('#messageInput').press('a');
  assert.equal(await page.locator('.message').count(), 0);
  assert((await page.locator('#messageInput').inputValue()).includes('\n'));
  checks.shift_enter_inserts_newline = true;

  await page.locator('#modeBadge').click();
  await page.locator('#providerInput').selectOption('openai');
  await page.locator('#apiFields').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#apiKeyInput').getAttribute('type'), 'password');
  await page.screenshot({ path: path.join(output, '06-ai-settings.png'), fullPage: true });
  checks.ai_settings_available = true;
  assert.equal(errors.length, 0, errors.join('\n'));
  checks.no_browser_javascript_errors = true;
  const verification = { passed: true, checks, screenshots: 6, provider: 'demo', real_llm_called: false, tested_at: new Date().toISOString(), note: 'Separate temporary server/database/profile; did not modify the user server on port 8765.' };
  fs.writeFileSync(path.join(output, 'verification.json'), JSON.stringify(verification, null, 2));
  console.log('PASS: ' + Object.keys(checks).length + ' browser checks. Screenshots and evidence: ' + output);
})().catch(error => {
  console.error(error);
  fs.writeFileSync(path.join(output, 'failure.txt'), String(error.stack || error));
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  child.kill();
  fs.writeFileSync(path.join(output, 'server.log'), log);
});
