// Drive the running Tauri WebView over the DevTools protocol.
//   node cdp.mjs eval "<js expression>"
//   node cdp.mjs shot <path.png>
const mode = process.argv[2];
const arg = process.argv[3];

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(t => t.type === 'page' && t.url.includes('tauri.localhost'));
if (!page) { console.error('no app page'); process.exit(1); }

const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const n = ++id;
  pending.set(n, { res, rej });
  ws.send(JSON.stringify({ id: n, method, params }));
});

await new Promise(r => ws.addEventListener('open', r));
ws.addEventListener('message', ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { res, rej } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
  }
});

await send('Runtime.enable');

if (mode === 'eval' || mode === 'file') {
  const expression = mode === 'file'
    ? (await import('node:fs')).readFileSync(arg, 'utf8')
    : arg;
  const r = await send('Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true, userGesture: true,
  });
  if (r.exceptionDetails) {
    console.log('EXCEPTION', JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails));
  } else {
    const v = r.result.value;
    console.log(typeof v === 'string' ? v : JSON.stringify(v, null, 1));
  }
} else if (mode === 'shot') {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  const { writeFileSync } = await import('node:fs');
  writeFileSync(arg, Buffer.from(r.data, 'base64'));
  console.log('wrote ' + arg);
} else {
  console.error('unknown mode');
}
ws.close();
process.exit(0);