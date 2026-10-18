// QAAfterHours · Screenshot → Bug Reporter UI. Posts to /api/report, which proxies to the n8n webhook.
const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_UPLOAD = 3.8 * 1024 * 1024; // leaves room for logs under Vercel's 4.5 MB body limit
const RECENT_KEY = 'qaah-bug-reports';

const $ = (id) => document.getElementById(id);
const form = $('form'), drop = $('drop'), fileInput = $('file');
const submitBtn = $('submit'), progress = $('progress'), errorBox = $('error');
let screenshot = null;
let stepTimers = [];

$('year').textContent = new Date().getFullYear();

// ---------- connection status ----------
fetch('/api/report')
  .then((r) => r.json())
  .then((d) => setStatus(d.configured ? 'online' : 'offline', d.configured ? 'Connected to n8n' : 'n8n not configured'))
  .catch(() => setStatus('offline', 'API unreachable'));
function setStatus(state, text) {
  $('status').dataset.state = state;
  $('status').querySelector('span').textContent = text;
}

// ---------- file selection: click, drag & drop, paste ----------
drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); } });
fileInput.addEventListener('change', () => fileInput.files[0] && setFile(fileInput.files[0]));
['dragenter', 'dragover'].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add('drag'); }));
['dragleave', 'drop'].forEach((t) => drop.addEventListener(t, () => drop.classList.remove('drag')));
drop.addEventListener('drop', (e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f); });
document.addEventListener('paste', (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith('image/'));
  if (!item) return;
  e.preventDefault();
  const blob = item.getAsFile();
  setFile(new File([blob], `pasted-screenshot-${Date.now()}.png`, { type: blob.type || 'image/png' }));
});
$('file-clear').addEventListener('click', (e) => { e.stopPropagation(); clearFile(); });

function setFile(file) {
  hideError();
  if (!ACCEPTED.includes(file.type)) {
    drop.classList.add('invalid');
    return showError('Unsupported file', `"${file.name}" is not a PNG, JPG or WEBP image.`);
  }
  drop.classList.remove('invalid');
  screenshot = file;
  $('preview-img').src = URL.createObjectURL(file);
  $('file-name').textContent = file.name;
  $('file-size').textContent = formatBytes(file.size) + (file.size > MAX_UPLOAD ? ' · will be compressed' : '');
  $('drop-empty').hidden = true;
  $('drop-preview').hidden = false;
}
function clearFile() {
  screenshot = null;
  fileInput.value = '';
  $('drop-empty').hidden = false;
  $('drop-preview').hidden = true;
}

// ---------- helpers ----------
$('logs').addEventListener('input', (e) => { $('logs-count').textContent = e.target.value.length.toLocaleString() + ' chars'; });
$('detect-env').addEventListener('click', () => { $('environment').value = detectEnvironment(); });

function detectEnvironment() {
  const ua = navigator.userAgent;
  const browser = (ua.match(/(Edg|OPR|Chrome|Firefox|Version)\/(\d+)/) || []);
  const name = { Edg: 'Edge', OPR: 'Opera', Version: 'Safari' }[browser[1]] || browser[1] || 'Browser';
  const os = /Windows NT 10/.test(ua) ? 'Windows 10/11' : /Mac OS X/.test(ua) ? 'macOS' : /Android/.test(ua) ? 'Android'
    : /iPhone|iPad/.test(ua) ? 'iOS' : /Linux/.test(ua) ? 'Linux' : 'Unknown OS';
  return `${name} ${browser[2] || ''} / ${os} / ${screen.width}x${screen.height} @${devicePixelRatio}x`.replace(/\s+\//g, ' /');
}

function formatBytes(n) { return n < 1024 * 1024 ? Math.round(n / 1024) + ' KB' : (n / 1024 / 1024).toFixed(1) + ' MB'; }

// Large screenshots are downscaled/re-encoded so the upload fits through the Vercel function.
async function shrink(file) {
  if (file.size <= MAX_UPLOAD) return file;
  const bmp = await createImageBitmap(file);
  for (const [maxW, q] of [[2560, 0.9], [1920, 0.85], [1440, 0.8], [1280, 0.7]]) {
    const scale = Math.min(1, maxW / bmp.width);
    const c = document.createElement('canvas');
    c.width = Math.round(bmp.width * scale);
    c.height = Math.round(bmp.height * scale);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    const blob = await new Promise((res) => c.toBlob(res, 'image/webp', q));
    if (blob && blob.size <= MAX_UPLOAD) return new File([blob], file.name.replace(/\.\w+$/, '') + '.webp', { type: 'image/webp' });
  }
  throw new Error('This screenshot is too large even after compression. Crop it and try again.');
}

// ---------- submit ----------
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideError();
  if (!screenshot) {
    drop.classList.add('invalid');
    drop.focus();
    return showError('Screenshot missing', 'Add a screenshot of the bug first.');
  }

  setBusy(true);
  try {
    const file = await shrink(screenshot);
    const body = new FormData();
    body.append('screenshot', file, file.name);
    body.append('notes', $('notes').value.trim());
    body.append('logs', $('logs').value);
    body.append('environment', $('environment').value.trim());

    const res = await fetch('/api/report', { method: 'POST', body });
    const data = await res.json().catch(() => ({ ok: false, error: `Unexpected response (HTTP ${res.status}).` }));
    if (!res.ok || !data.ok) throw new Error(data.error || 'Bug could not be created.');

    finishSteps();
    showResult(data);
    saveRecent(data);
  } catch (err) {
    showError('Bug could not be created', err.message +
      (/rate|limit|429/i.test(err.message) ? ' The free AI tier allows about 2–3 bugs a minute. Wait a minute and try again.' : ''));
  } finally {
    setBusy(false);
  }
});

function setBusy(busy) {
  submitBtn.disabled = busy;
  submitBtn.classList.toggle('busy', busy);
  submitBtn.querySelector('.btn-label').textContent = busy ? 'Creating bug…' : 'Create bug in Jira';
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  if (busy) {
    progress.hidden = false;
    $('result').hidden = true;
    // The webhook answers once at the end, so the stages are paced to typical timings.
    [0, 2500, 14000, 24000].forEach((ms, i) => stepTimers.push(setTimeout(() => markStep(i), ms)));
  } else if (!progress.dataset.done) {
    progress.hidden = true;
  }
  delete progress.dataset.done;
}
function markStep(i) {
  progress.querySelectorAll('li').forEach((li, j) => {
    li.classList.toggle('done', j < i);
    li.classList.toggle('active', j === i);
  });
}
function finishSteps() {
  progress.querySelectorAll('li').forEach((li) => { li.classList.remove('active'); li.classList.add('done'); });
  progress.dataset.done = '1';
}

function showResult(d) {
  $('r-key').textContent = d.key;
  $('r-title').textContent = d.title || '';
  $('r-link').href = d.url;
  const chips = $('r-chips');
  chips.replaceChildren();
  const chip = (text, cls = '') => { const s = document.createElement('span'); s.className = 'chip ' + cls; s.textContent = text; chips.append(s); };
  if (d.severity) chip(d.severity + ' severity', 'sev-' + String(d.severity).toLowerCase());
  if (d.confidence) chip('AI confidence: ' + d.confidence);
  (d.labels || []).filter((l) => !/^(ai-bug-report|from-screenshot|severity-)/.test(l)).forEach((l) => chip(l));
  $('r-attach').textContent = d.screenshotAttached === false
    ? 'The issue was created, but the screenshot could not be attached. Add it manually in Jira.'
    : 'Screenshot attached to the issue.';
  $('result').hidden = false;
  if (matchMedia('(max-width: 880px)').matches) $('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

$('again').addEventListener('click', () => {
  form.reset();
  clearFile();
  $('logs-count').textContent = '0 chars';
  $('result').hidden = true;
  progress.hidden = true;
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

function showError(title, msg) {
  errorBox.replaceChildren();
  const b = document.createElement('b');
  b.textContent = title;
  errorBox.append(b, document.createTextNode(msg));
  errorBox.hidden = false;
}
function hideError() { errorBox.hidden = true; drop.classList.remove('invalid'); }

// ---------- recent reports (this browser only) ----------
function loadRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY)) || []; } catch { return []; }
}
function saveRecent(d) {
  const list = [{ key: d.key, url: d.url, title: d.title, at: Date.now() }, ...loadRecent().filter((r) => r.key !== d.key)].slice(0, 6);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch {}
  renderRecent();
}
function renderRecent() {
  const list = loadRecent();
  $('recent-card').hidden = !list.length;
  $('recent').replaceChildren(...list.map((r) => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = r.url; a.target = '_blank'; a.rel = 'noopener';
    const k = document.createElement('span'); k.className = 'k'; k.textContent = r.key;
    const t = document.createElement('span'); t.className = 't'; t.textContent = r.title || '';
    const time = document.createElement('time'); time.textContent = new Date(r.at).toLocaleString();
    a.append(k, t, time);
    li.append(a);
    return li;
  }));
}
$('recent-clear').addEventListener('click', () => { try { localStorage.removeItem(RECENT_KEY); } catch {} renderRecent(); });
renderRecent();
