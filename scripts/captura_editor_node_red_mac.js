// CardioIA Fase 3, Parte 2: captura do editor Node-RED (fluxo e painel de debug) no Mac,
// com o ESP32 do Wokwi publicando no broker publico. Usa o Google Chrome instalado via playwright-core.
const { chromium } = require('playwright-core');
const destino = process.argv[2];
const espera = parseInt(process.argv[3] || '30000', 10);
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
  await page.goto('http://127.0.0.1:1880/#flow/cardioia_f3_tab', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);
  // fecha o tour de boas-vindas do Node-RED (aparece em perfis novos do navegador)
  for (let i = 0; i < 3; i++) {
    const fechar = await page.$('.red-ui-tourGuide-popover button.red-ui-tourGuide-close, .red-ui-tourGuide-popover [class*="close"], .red-ui-tourGuide-popover button:has-text("\u00d7")');
    if (fechar && await fechar.isVisible()) { await fechar.click({ timeout: 2000 }).catch(() => {}); console.log('tour fechado'); await page.waitForTimeout(800); }
    else { const n = await page.$$eval('[class*="tourGuide"]', e => e.length); console.log('elementos do tour: ' + n); if (!n) break; await page.keyboard.press('Escape'); await page.waitForTimeout(800); }
  }
  // fluxo completo na tela
  await page.keyboard.press('Control+Shift+Space').catch(() => {});
  await page.screenshot({ path: destino + '/p2_14_editor_fluxo_mac.png', fullPage: false });
  // abre a aba de debug da barra lateral e acumula mensagens do dispositivo
  await page.mouse.click(1713, 67);
  await page.waitForTimeout(1000);
  let visivel = await page.$eval('#red-ui-sidebar-debug, .red-ui-sidebar-debug, #red-ui-tab-debug', e => !!(e.offsetWidth || e.offsetHeight)).catch(() => false);
  if (!visivel) { await page.keyboard.press('Control+g'); await page.keyboard.press('d'); await page.waitForTimeout(1000); }
  visivel = await page.$eval('.red-ui-debug-content, .red-ui-sidebar-debug', e => !!(e.offsetWidth || e.offsetHeight)).catch(() => false);
  console.log('painel de debug visivel: ' + visivel);
  await page.waitForTimeout(espera);
  await page.screenshot({ path: destino + '/p2_15_editor_debug_mac.png', fullPage: false });
  console.log('capturas gravadas em ' + destino);
  await browser.close();
})().catch(e => { console.error('erro', e); process.exit(1); });
