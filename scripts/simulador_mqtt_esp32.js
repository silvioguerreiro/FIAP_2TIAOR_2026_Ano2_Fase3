// Simulador de teste do fluxo Node-RED: publica mensagens no mesmo formato do firmware da Parte 2
// (apenas para validar o fluxo no ambiente de trabalho; nao substitui o dispositivo).
const mqtt = require('mqtt');
const host = process.argv[2] || 'mqtt://127.0.0.1:1883';
const prefixo = 'cardioia/grupo55/paciente01';
const c = mqtt.connect(host, { clientId: 'cardioia-g55-p01-sim' });
let seq = 0;
const cen = [ // cenarios: [bpm, temp, umid, mov, mascara, origem]
  [72, 36.5, 45, 1, 0, 'rt'], [75, 36.6, 45, 0, 0, 'rt'], [78, 36.6, 46, 1, 0, 'rt'],
  [135, 36.7, 46, 1, 1, 'rt'], [142, 36.8, 46, 0, 1, 'rt'], [128, 36.8, 47, 1, 1, 'rt'],
  [80, 38.4, 47, 0, 4, 'rt'], [82, 38.6, 47, 1, 4, 'rt'], [76, 37.2, 46, 1, 0, 'rt'], [74, 36.9, 45, 1, 0, 'rt'],
];
function pub(topic, obj, retain) { c.publish(topic, JSON.stringify(obj), { retain: !!retain }); }
c.on('connect', () => {
  console.log('simulador conectado a', host);
  const ts0 = Math.floor(Date.now() / 1000);
  pub(prefixo + '/estado', { disp: 'cardioia-g55-p01', estado: 'online', pendentes: 0, capacidade: 3000, descartadas: 0, publicadas: 0, ts: ts0, heap: 160000, rssi: -70 }, true);
  // 1) rajada de sincronizacao de 6 amostras antigas (origem sync, 5 s de intervalo)
  pub(prefixo + '/estado', { disp: 'cardioia-g55-p01', estado: 'sincronizando', pendentes: 6, capacidade: 3000, descartadas: 0, publicadas: 0, ts: ts0, heap: 160000, rssi: -70 }, true);
  for (let i = 0; i < 6; i++) {
    seq++;
    pub(prefixo + '/sinais', { disp: 'cardioia-g55-p01', seq, ts: ts0 - (6 - i) * 5 - 60, tsrel: 0, temp: 36.4, umid: 44, bpm: 70 + i, mov: 1, alertas: 0, origem: 'sync' });
  }
  pub(prefixo + '/estado', { disp: 'cardioia-g55-p01', estado: 'online', pendentes: 0, capacidade: 3000, descartadas: 0, publicadas: 6, ts: ts0, heap: 160000, rssi: -70 }, true);
  // 2) tempo real: um cenario a cada 2 s
  let i = 0;
  const t = setInterval(() => {
    if (i >= cen.length) { clearInterval(t); setTimeout(() => { c.end(); process.exit(0); }, 500); return; }
    const [bpm, temp, umid, mov, mascara, origem] = cen[i++];
    seq++;
    const ts = Math.floor(Date.now() / 1000);
    pub(prefixo + '/sinais', { disp: 'cardioia-g55-p01', seq, ts, tsrel: 0, temp, umid, bpm, mov, alertas: mascara, origem });
    const nomes = ['taquicardia', 'bradicardia', 'febre', 'hipotermia', 'sem_movimento'];
    const tipos = nomes.filter((n, k) => mascara & (1 << k)).join(',');
    pub(prefixo + '/alertas', { disp: 'cardioia-g55-p01', ts, ativo: mascara ? 1 : 0, mascara, tipos, bpm, temp, seq }, true);
    console.log('publicado seq', seq, bpm, temp, tipos || '-');
  }, 2000);
});
