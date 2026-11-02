// Captura do editor Node-RED com a aba de integracao com a API (Ir Alem 1) e o painel de debug
const { chromium } = require('playwright');
const { spawn } = require('child_process');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
  await page.goto('http://127.0.0.1:1880/#flow/ia1aba000000001', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  const nao = await page.$('button:has-text("No, do not enable notifications")');
  if (nao && await nao.isVisible()) { await nao.click({ timeout: 3000 }).catch(()=>{}); await page.waitForTimeout(500); }
  await page.mouse.click(1713, 67); const dbg = null;
  if (dbg) await dbg.click({ timeout: 3000 }).catch(() => console.log('clique debug falhou'));
  await page.waitForTimeout(500);
  const sim = spawn('node', ['simulador_esp32.js'], { stdio: 'ignore' });
  await page.waitForTimeout(14000);
  await page.screenshot({ path: 'ia1_editor_integracao_api_debug.png', fullPage: false });
  await page.waitForTimeout(10000);
  console.log('ok');
  await browser.close();
})().catch(e => { console.error('erro', e); process.exit(1); });
