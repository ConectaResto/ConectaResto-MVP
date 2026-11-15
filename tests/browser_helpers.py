"""Transporte CDP compartido para pruebas con Chromium y Node existentes.

Contiene solo conexión, evaluación, espera, interacción DOM y capturas.
Los escenarios y las aserciones permanecen en cada prueba.
"""

CDP_SETUP = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const deadline = setTimeout(()=>{console.error('Browser CDP timeout');process.exit(1);},60000);
(async () => {
 const [port, base, imagePath, mode] = process.argv.slice(1);
 const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
 await new Promise((ok, fail) => { ws.onopen=ok; ws.onerror=fail; });
 let next=0; const calls=new Map();
 ws.onmessage = e => { const m=JSON.parse(e.data); const p=calls.get(m.id); if(p) { calls.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); }};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++next; calls.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const run=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true}); if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async expression=>{for(let n=0;n<150;n++){if(await run(expression))return;await new Promise(r=>setTimeout(r,50));}throw new Error('Timeout: '+expression);};
 const click=selector=>run(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const text=id=>run(`document.getElementById(${JSON.stringify(id)}).textContent`);
 const capture=async path=>{const size=(await send('Page.getLayoutMetrics')).cssContentSize;const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{...size,scale:1}});fs.writeFileSync(path,Buffer.from(shot.data,'base64'));};
"""
