/*
 * =====================================================================
 *  Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
 *  Fase    : 3, Monitoramento Contínuo (IoT no Peito do Paciente)
 *  Parte   : 1, Armazenamento e processamento local (Edge Computing)
 *  Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
 *  Data    : 31/10/2026
 *  Placa   : ESP32 DevKit (simulada no Wokwi), monitor serial a 115200
 *
 *  Descrição
 *  ---------
 *  Firmware de um wearable cardíaco simulado. A cada INTERVALO_AMOSTRA_MS
 *  o dispositivo gera uma amostra com carimbo de tempo, temperatura e
 *  umidade (DHT22), frequência cardíaca (botão: cada pressão é um
 *  batimento) e indicador de movimento (MPU6050). A avaliação dos limites
 *  de alerta acontece no próprio ESP32, que aciona LED e buzzer mesmo sem
 *  conexão: este é o argumento central de Edge Computing em saúde.
 *
 *  A conectividade Wi-Fi é simulada por uma variável booleana controlada
 *  por uma chave deslizante no diagrama. Offline, as amostras ficam em um
 *  buffer circular na RAM (e, opcionalmente, em arquivo CSV no SPIFFS).
 *  Ao voltar a ficar online, todas as amostras pendentes são enviadas para
 *  a "nuvem" via Serial.println em CSV, em ordem cronológica, e o
 *  armazenamento local é limpo. A coleta nunca para.
 *
 *  Prefixos do log serial: [BOOT] [SENSOR] [OFFLINE] [ONLINE] [SYNC]
 *  [ALERTA] [BUFFER] [SPIFFS]
 * =====================================================================
 */

#include <Wire.h>
#include <DHT.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// =====================================================================
//  1. CONFIGURAÇÃO (única seção que precisa ser alterada para ajustes)
// =====================================================================

// ---- Pinos -----------------------------------------------------------
const uint8_t PINO_DHT            = 15;  // dado do DHT22
const uint8_t PINO_BOTAO_BATIMENTO = 4;  // botão: cada pressão é um batimento
const uint8_t PINO_CHAVE_WIFI     = 18;  // chave deslizante: HIGH = conectado
const uint8_t PINO_LED_ONLINE     = 25;  // LED verde: estado online
const uint8_t PINO_LED_ALERTA     = 26;  // LED vermelho: alerta local ativo
const uint8_t PINO_BUZZER         = 27;  // buzzer: aviso sonoro de alerta
const uint8_t PINO_I2C_SDA        = 21;  // MPU6050
const uint8_t PINO_I2C_SCL        = 22;  // MPU6050

// ---- Amostragem e armazenamento ---------------------------------------
// 5 s respeita o mínimo de 2 s do DHT22 e gera 720 amostras por hora.
const uint32_t INTERVALO_AMOSTRA_MS = 5000;
// 3.000 amostras x 16 bytes = 48 KB de RAM, cerca de 4 h 10 min offline.
// Dimensionamento justificado no relatório da Parte 1.
const uint16_t CAPACIDADE_BUFFER    = 3000;

// ---- Limites de alerta (avaliados localmente, no dispositivo) ---------
const uint16_t LIMITE_BPM_TAQUICARDIA = 120;  // acima: taquicardia
const uint16_t LIMITE_BPM_BRADICARDIA = 50;   // abaixo (com bpm > 0): bradicardia
const float    LIMITE_TEMP_FEBRE_C    = 38.0; // acima: febre
const float    LIMITE_TEMP_HIPOTERMIA_C = 35.0; // abaixo: hipotermia
// Ausência de movimento: 10 min em produção. No modo de demonstração o
// limite cai para 60 s para que o alerta possa ser observado na simulação.
#define MODO_DEMONSTRACAO 1
#if MODO_DEMONSTRACAO
const uint32_t LIMITE_SEM_MOVIMENTO_MS = 60UL * 1000UL;
#else
const uint32_t LIMITE_SEM_MOVIMENTO_MS = 10UL * 60UL * 1000UL;
#endif

// ---- Detecção de batimentos e movimento -------------------------------
const uint32_t DEBOUNCE_BATIMENTO_MS = 150;  // limita a 400 bpm e filtra ruído do botão
const uint32_t TEMPO_ZERAR_BPM_MS    = 5000; // sem pressão por 5 s, bpm volta a 0
const uint8_t  N_INTERVALOS_MEDIA    = 4;    // média móvel dos últimos intervalos
const float    LIMIAR_DELTA_MOVIMENTO_G = 0.10; // variação do vetor entre leituras
const float    LIMIAR_MAGNITUDE_MOVIMENTO_G = 0.30; // afastamento de 1 g

// ---- Flags de compilação ----------------------------------------------
// USAR_SPIFFS 1 grava as amostras offline em /pendentes.csv. Funciona em
// chip real; no Wokwi funciona apenas durante a sessão (dados perdidos ao
// encerrar a simulação). Com 0, apenas o buffer em RAM é usado.
#define USAR_SPIFFS 0
// DEMO_AUTOMATICO 1 ignora a chave e alterna offline/online a cada
// PERIODO_DEMO_MS, útil para gerar evidências sem intervenção.
#define DEMO_AUTOMATICO 0
const uint32_t PERIODO_DEMO_MS = 60000;

// ---- Outros ------------------------------------------------------------
const uint32_t INTERVALO_STATUS_BUFFER_MS = 30000; // linha [BUFFER] periódica
const uint32_t DURACAO_BIP_MS = 200;               // duração do bip de alerta
const size_t   LIMITE_ARQUIVO_SPIFFS_BYTES = 1024UL * 1024UL; // 1 MB

// =====================================================================
//  2. TIPOS E ESTADO GLOBAL
// =====================================================================

// Bits do campo "alertas" de cada amostra.
const uint8_t ALERTA_TAQUICARDIA  = 0x01;
const uint8_t ALERTA_BRADICARDIA  = 0x02;
const uint8_t ALERTA_FEBRE        = 0x04;
const uint8_t ALERTA_HIPOTERMIA   = 0x08;
const uint8_t ALERTA_SEM_MOVIMENTO = 0x10;

// Uma amostra ocupa 16 bytes. O static_assert garante o dimensionamento
// usado no relatório (3.000 x 16 bytes = 48.000 bytes).
struct __attribute__((packed)) Amostra {
  uint32_t ts;          // segundos desde o início (Parte 1 não tem RTC)
  float    temperatura; // graus Celsius
  float    umidade;     // por cento
  uint16_t bpm;         // batimentos por minuto (0 = sem batimentos)
  uint8_t  movimento;   // 1 = movimento detectado na janela
  uint8_t  alertas;     // bitmask dos alertas avaliados no dispositivo
};
static_assert(sizeof(Amostra) == 16, "Amostra deve ocupar 16 bytes");

enum EstadoConexao { OFFLINE, ONLINE };

// Buffer circular em RAM (alocação estática: tamanho conhecido em compilação).
Amostra  buffer[CAPACIDADE_BUFFER];
uint16_t bufferInicio = 0;   // índice da amostra mais antiga
uint16_t bufferQtd    = 0;   // quantidade pendente
uint32_t totalArmazenadas  = 0;
uint32_t totalDescartadas  = 0;  // sobrescritas por falta de espaço
uint32_t totalSincronizadas = 0;

// Sensores
DHT dht(PINO_DHT, DHT22);
Adafruit_MPU6050 mpu;
bool  mpuDisponivel = false;
float ultimaTemperatura = NAN;
float ultimaUmidade = NAN;
float accAnterior[3] = {0, 0, 1.0};  // vetor de aceleração anterior, em g
uint32_t ultimoMovimentoMs = 0;

// Batimentos (compartilhado com a ISR, por isso volatile)
volatile uint32_t ultimoBatimentoMs = 0;
volatile uint32_t intervalosMs[N_INTERVALOS_MEDIA];
volatile uint8_t  idxIntervalo = 0;
volatile uint8_t  nIntervalos  = 0;
volatile uint32_t totalBatimentos = 0;

// Conexão e temporização
EstadoConexao estado = OFFLINE;
uint32_t proximaAmostraMs = 0;
uint32_t proximoStatusMs  = 0;
uint32_t buzzerAteMs      = 0;

#if USAR_SPIFFS
#include <SPIFFS.h>
const char* ARQUIVO_PENDENTES = "/pendentes.csv";
bool spiffsOk = false;
#endif

// =====================================================================
//  3. INTERRUPÇÃO DO BOTÃO (um batimento por pressão)
// =====================================================================
// A ISR faz o mínimo: registra o instante e o intervalo desde o batimento
// anterior. O cálculo de bpm fica no loop principal.
void IRAM_ATTR isrBatimento() {
  uint32_t agora = millis();
  if (agora - ultimoBatimentoMs < DEBOUNCE_BATIMENTO_MS) return;  // ruído
  if (ultimoBatimentoMs != 0) {
    intervalosMs[idxIntervalo] = agora - ultimoBatimentoMs;
    idxIntervalo = (idxIntervalo + 1) % N_INTERVALOS_MEDIA;
    if (nIntervalos < N_INTERVALOS_MEDIA) nIntervalos++;
  }
  ultimoBatimentoMs = agora;
  totalBatimentos++;
}

// Frequência cardíaca pela média móvel dos últimos intervalos entre
// pressões. Sem pressão por TEMPO_ZERAR_BPM_MS, considera-se que não há
// batimentos registrados (bpm = 0, tratado como "sem leitura").
uint16_t calcularBpm() {
  uint32_t copiaIntervalos[N_INTERVALOS_MEDIA];
  uint8_t  n;
  uint32_t ultimo;
  noInterrupts();
  n = nIntervalos;
  ultimo = ultimoBatimentoMs;
  for (uint8_t i = 0; i < N_INTERVALOS_MEDIA; i++) copiaIntervalos[i] = intervalosMs[i];
  interrupts();

  if (n == 0 || ultimo == 0) return 0;
  if (millis() - ultimo > TEMPO_ZERAR_BPM_MS) {
    // Zera o histórico para que a próxima sequência comece limpa.
    noInterrupts();
    nIntervalos = 0;
    idxIntervalo = 0;
    ultimoBatimentoMs = 0;
    interrupts();
    return 0;
  }
  uint32_t soma = 0;
  for (uint8_t i = 0; i < n; i++) soma += copiaIntervalos[i];
  uint32_t media = soma / n;
  if (media == 0) return 0;
  return (uint16_t)(60000UL / media);
}

// =====================================================================
//  4. LEITURA DOS SENSORES
// =====================================================================
void lerDht(float &temperatura, float &umidade) {
  float t = dht.readTemperature();
  float u = dht.readHumidity();
  if (isnan(t) || isnan(u)) {
    // Mantém o último valor válido para não interromper a série; o fato
    // fica registrado no log para auditoria.
    Serial.println("[SENSOR] falha de leitura do DHT22; mantendo ultimo valor valido");
    temperatura = ultimaTemperatura;
    umidade = ultimaUmidade;
    return;
  }
  ultimaTemperatura = t;
  ultimaUmidade = u;
  temperatura = t;
  umidade = u;
}

// Movimento: compara o vetor de aceleração (em g) com a leitura anterior e
// com a gravidade. Paciente parado produz vetor constante de módulo 1 g.
bool lerMovimento(float &magnitudeG) {
  if (!mpuDisponivel) { magnitudeG = NAN; return false; }
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  float ax = a.acceleration.x / SENSORS_GRAVITY_STANDARD;
  float ay = a.acceleration.y / SENSORS_GRAVITY_STANDARD;
  float az = a.acceleration.z / SENSORS_GRAVITY_STANDARD;
  magnitudeG = sqrtf(ax * ax + ay * ay + az * az);
  float dx = ax - accAnterior[0], dy = ay - accAnterior[1], dz = az - accAnterior[2];
  float delta = sqrtf(dx * dx + dy * dy + dz * dz);
  accAnterior[0] = ax; accAnterior[1] = ay; accAnterior[2] = az;
  bool movimento = (delta > LIMIAR_DELTA_MOVIMENTO_G) ||
                   (fabsf(magnitudeG - 1.0f) > LIMIAR_MAGNITUDE_MOVIMENTO_G);
  if (movimento) ultimoMovimentoMs = millis();
  return movimento;
}

// =====================================================================
//  5. AVALIAÇÃO LOCAL DE ALERTAS (Edge)
// =====================================================================
uint8_t avaliarAlertas(const Amostra &a) {
  uint8_t alertas = 0;
  if (a.bpm > LIMITE_BPM_TAQUICARDIA) alertas |= ALERTA_TAQUICARDIA;
  if (a.bpm > 0 && a.bpm < LIMITE_BPM_BRADICARDIA) alertas |= ALERTA_BRADICARDIA;
  if (!isnan(a.temperatura)) {
    if (a.temperatura > LIMITE_TEMP_FEBRE_C) alertas |= ALERTA_FEBRE;
    if (a.temperatura < LIMITE_TEMP_HIPOTERMIA_C) alertas |= ALERTA_HIPOTERMIA;
  }
  // Só avalia ausência de movimento quando o sensor existe e já houve
  // movimento alguma vez (evita falso alerta nos primeiros segundos).
  if (mpuDisponivel && ultimoMovimentoMs > 0 &&
      (millis() - ultimoMovimentoMs) > LIMITE_SEM_MOVIMENTO_MS) {
    alertas |= ALERTA_SEM_MOVIMENTO;
  }
  return alertas;
}

void descreverAlertas(uint8_t alertas, const Amostra &a, char *saida, size_t tam) {
  saida[0] = '\0';
  if (alertas & ALERTA_TAQUICARDIA) snprintf(saida + strlen(saida), tam - strlen(saida), "taquicardia (%u bpm > %u); ", a.bpm, LIMITE_BPM_TAQUICARDIA);
  if (alertas & ALERTA_BRADICARDIA) snprintf(saida + strlen(saida), tam - strlen(saida), "bradicardia (%u bpm < %u); ", a.bpm, LIMITE_BPM_BRADICARDIA);
  if (alertas & ALERTA_FEBRE)       snprintf(saida + strlen(saida), tam - strlen(saida), "febre (%.1f C > %.1f); ", a.temperatura, LIMITE_TEMP_FEBRE_C);
  if (alertas & ALERTA_HIPOTERMIA)  snprintf(saida + strlen(saida), tam - strlen(saida), "hipotermia (%.1f C < %.1f); ", a.temperatura, LIMITE_TEMP_HIPOTERMIA_C);
  if (alertas & ALERTA_SEM_MOVIMENTO) snprintf(saida + strlen(saida), tam - strlen(saida), "sem movimento ha %lu s; ", (unsigned long)((millis() - ultimoMovimentoMs) / 1000UL));
}

// Atuação local: LED vermelho aceso enquanto houver alerta e bip curto a
// cada amostra em alerta. Funciona offline, sem depender da nuvem.
void atuarAlertas(uint8_t alertas) {
  digitalWrite(PINO_LED_ALERTA, alertas ? HIGH : LOW);
  if (alertas) {
    digitalWrite(PINO_BUZZER, HIGH);
    buzzerAteMs = millis() + DURACAO_BIP_MS;
  }
}

void atualizarBuzzer() {
  if (buzzerAteMs != 0 && (int32_t)(millis() - buzzerAteMs) >= 0) {
    digitalWrite(PINO_BUZZER, LOW);
    buzzerAteMs = 0;
  }
}

// =====================================================================
//  6. FORMATO CSV ("nuvem" da Parte 1 = monitor serial)
// =====================================================================
const char* CSV_CABECALHO = "ts_s,temp_c,umid_pct,bpm,mov,alertas";

void formatarCsv(const Amostra &a, char *linha, size_t tam) {
  snprintf(linha, tam, "%lu,%.2f,%.2f,%u,%u,%u",
           (unsigned long)a.ts, a.temperatura, a.umidade, a.bpm, a.movimento, a.alertas);
}

// =====================================================================
//  7. BUFFER CIRCULAR EM RAM
// =====================================================================
void bufferArmazenar(const Amostra &a) {
  if (bufferQtd == CAPACIDADE_BUFFER) {
    // Política: sobrescrever a amostra mais antiga e contabilizar o descarte.
    bufferInicio = (bufferInicio + 1) % CAPACIDADE_BUFFER;
    bufferQtd--;
    totalDescartadas++;
    Serial.printf("[BUFFER] cheio: amostra mais antiga descartada (total descartadas=%lu)\n",
                  (unsigned long)totalDescartadas);
  }
  uint16_t pos = (bufferInicio + bufferQtd) % CAPACIDADE_BUFFER;
  buffer[pos] = a;
  bufferQtd++;
  totalArmazenadas++;
}

void bufferLimpar() {
  bufferInicio = 0;
  bufferQtd = 0;
}

// Envia as amostras pendentes em ordem cronológica (da mais antiga à mais
// recente) e limpa o buffer.
void sincronizarDaRam() {
  char linha[64];
  Serial.printf("[SYNC] iniciando sincronizacao de %u amostras pendentes (RAM)\n", bufferQtd);
  Serial.print("[SYNC] ");
  Serial.println(CSV_CABECALHO);
  for (uint16_t i = 0; i < bufferQtd; i++) {
    const Amostra &a = buffer[(bufferInicio + i) % CAPACIDADE_BUFFER];
    formatarCsv(a, linha, sizeof(linha));
    Serial.print("[SYNC] ");
    Serial.println(linha);
    if ((i & 0x3F) == 0x3F) delay(1);  // cede tempo ao sistema em lotes grandes
  }
  totalSincronizadas += bufferQtd;
  Serial.printf("[SYNC] concluida: %u enviadas, buffer limpo (total sincronizadas=%lu, descartadas=%lu)\n",
                bufferQtd, (unsigned long)totalSincronizadas, (unsigned long)totalDescartadas);
  bufferLimpar();
}

// =====================================================================
//  8. CAMADA OPCIONAL: SPIFFS (ativada por USAR_SPIFFS)
// =====================================================================
#if USAR_SPIFFS
void spiffsIniciar() {
  spiffsOk = SPIFFS.begin(true);  // formata na primeira vez
  if (!spiffsOk) {
    Serial.println("[SPIFFS] falha ao montar; usando apenas RAM");
    return;
  }
  Serial.printf("[SPIFFS] montado: total=%u bytes, usado=%u bytes\n",
                (unsigned)SPIFFS.totalBytes(), (unsigned)SPIFFS.usedBytes());
  if (SPIFFS.exists(ARQUIVO_PENDENTES)) {
    File f = SPIFFS.open(ARQUIVO_PENDENTES, FILE_READ);
    Serial.printf("[SPIFFS] %s existente com %u bytes (pendentes de execucao anterior)\n",
                  ARQUIVO_PENDENTES, (unsigned)f.size());
    f.close();
  }
}

void spiffsGravar(const Amostra &a) {
  if (!spiffsOk) return;
  File f = SPIFFS.open(ARQUIVO_PENDENTES, FILE_APPEND);
  if (!f) { Serial.println("[SPIFFS] erro ao abrir arquivo para escrita"); return; }
  if (f.size() > LIMITE_ARQUIVO_SPIFFS_BYTES) {
    // Em chip real, a política é manter o arquivo abaixo de 1 MB; as
    // amostras continuam na RAM e o descarte fica registrado.
    f.close();
    Serial.println("[SPIFFS] limite de 1 MB atingido; amostra nao gravada em arquivo");
    return;
  }
  char linha[64];
  formatarCsv(a, linha, sizeof(linha));
  f.println(linha);
  f.close();
}

void sincronizarDoSpiffs() {
  File f = SPIFFS.open(ARQUIVO_PENDENTES, FILE_READ);
  if (!f) { Serial.println("[SYNC] nenhum arquivo pendente no SPIFFS"); return; }
  uint32_t linhas = 0;
  Serial.printf("[SYNC] iniciando sincronizacao a partir de %s (%u bytes)\n",
                ARQUIVO_PENDENTES, (unsigned)f.size());
  Serial.print("[SYNC] ");
  Serial.println(CSV_CABECALHO);
  while (f.available()) {
    String l = f.readStringUntil('\n');
    l.trim();
    if (l.length() == 0) continue;
    Serial.print("[SYNC] ");
    Serial.println(l);
    linhas++;
    if ((linhas & 0x3F) == 0) delay(1);
  }
  f.close();
  SPIFFS.remove(ARQUIVO_PENDENTES);  // "apaga o arquivo local" após o envio
  totalSincronizadas += linhas;
  Serial.printf("[SYNC] concluida: %lu linhas enviadas, arquivo removido\n", (unsigned long)linhas);
}
#endif

// =====================================================================
//  9. CONECTIVIDADE SIMULADA E MÁQUINA DE ESTADOS
// =====================================================================
bool lerConectividade() {
#if DEMO_AUTOMATICO
  return ((millis() / PERIODO_DEMO_MS) % 2) == 1;  // alterna a cada período
#else
  return digitalRead(PINO_CHAVE_WIFI) == HIGH;      // chave deslizante
#endif
}

void sincronizarPendentes() {
#if USAR_SPIFFS
  if (spiffsOk) {
    sincronizarDoSpiffs();  // arquivo é a fonte de verdade quando existe
    bufferLimpar();
    return;
  }
#endif
  sincronizarDaRam();
}

void atualizarEstadoConexao() {
  bool conectado = lerConectividade();
  if (conectado && estado == OFFLINE) {
    estado = ONLINE;
    digitalWrite(PINO_LED_ONLINE, HIGH);
    Serial.printf("[ONLINE] conexao restabelecida em t=%lu s; %u amostras pendentes\n",
                  (unsigned long)(millis() / 1000UL), bufferQtd);
    if (bufferQtd > 0) sincronizarPendentes();
    Serial.print("[ONLINE] envio em tempo real: ");
    Serial.println(CSV_CABECALHO);
  } else if (!conectado && estado == ONLINE) {
    estado = OFFLINE;
    digitalWrite(PINO_LED_ONLINE, LOW);
    Serial.printf("[OFFLINE] conexao perdida em t=%lu s; armazenando localmente\n",
                  (unsigned long)(millis() / 1000UL));
  }
}

// =====================================================================
// 10. CICLO DE AMOSTRAGEM
// =====================================================================
void coletarAmostra() {
  Amostra a;
  a.ts = millis() / 1000UL;
  // Campos de struct "packed" não podem ser passados por referência;
  // por isso a leitura usa variáveis locais e depois copia.
  float temperatura, umidade;
  lerDht(temperatura, umidade);
  a.temperatura = temperatura;
  a.umidade = umidade;
  a.bpm = calcularBpm();
  float magnitudeG;
  a.movimento = lerMovimento(magnitudeG) ? 1 : 0;
  a.alertas = avaliarAlertas(a);

  // Atuação local acontece antes de qualquer decisão de envio.
  atuarAlertas(a.alertas);
  if (a.alertas) {
    char texto[160];
    descreverAlertas(a.alertas, a, texto, sizeof(texto));
    Serial.printf("[ALERTA] %s(LED vermelho e buzzer acionados localmente)\n", texto);
  }

  char linha[64];
  formatarCsv(a, linha, sizeof(linha));
  if (estado == ONLINE) {
    Serial.print("[ONLINE] ");
    Serial.println(linha);
  } else {
    bufferArmazenar(a);
#if USAR_SPIFFS
    spiffsGravar(a);
#endif
    Serial.printf("[OFFLINE] %s | armazenada (%u/%u, mov=%s, |a|=%.2f g)\n",
                  linha, bufferQtd, CAPACIDADE_BUFFER, a.movimento ? "sim" : "nao",
                  isnan(magnitudeG) ? 0.0f : magnitudeG);
  }
}

void imprimirStatusBuffer() {
  Serial.printf("[BUFFER] pendentes=%u/%u armazenadas=%lu sincronizadas=%lu descartadas=%lu batimentos=%lu heap_livre=%u\n",
                bufferQtd, CAPACIDADE_BUFFER, (unsigned long)totalArmazenadas,
                (unsigned long)totalSincronizadas, (unsigned long)totalDescartadas,
                (unsigned long)totalBatimentos, (unsigned)ESP.getFreeHeap());
}

// =====================================================================
// 11. SETUP E LOOP
// =====================================================================
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("[BOOT] CardioIA Fase 3, Parte 1 (Edge): wearable cardiaco simulado");
  Serial.printf("[BOOT] amostragem=%lu ms, buffer=%u amostras x %u bytes = %u bytes\n",
                (unsigned long)INTERVALO_AMOSTRA_MS, CAPACIDADE_BUFFER,
                (unsigned)sizeof(Amostra), (unsigned)sizeof(buffer));
  Serial.printf("[BOOT] autonomia offline estimada=%lu s (%.1f h)\n",
                (unsigned long)(CAPACIDADE_BUFFER * (INTERVALO_AMOSTRA_MS / 1000UL)),
                CAPACIDADE_BUFFER * (INTERVALO_AMOSTRA_MS / 1000.0f) / 3600.0f);
  Serial.printf("[BOOT] limites: bpm>%u taquicardia, bpm<%u bradicardia, temp>%.1f febre, temp<%.1f hipotermia, sem movimento>%lu s\n",
                LIMITE_BPM_TAQUICARDIA, LIMITE_BPM_BRADICARDIA, LIMITE_TEMP_FEBRE_C,
                LIMITE_TEMP_HIPOTERMIA_C, (unsigned long)(LIMITE_SEM_MOVIMENTO_MS / 1000UL));
  Serial.printf("[BOOT] heap livre antes dos sensores=%u bytes\n", (unsigned)ESP.getFreeHeap());
  Serial.println("[BOOT] dica: no Wokwi, ajuste o DHT22 para ~36.5 C (temperatura cutanea normal); o padrao de 24 C gera alerta de hipotermia");

  pinMode(PINO_LED_ONLINE, OUTPUT);
  pinMode(PINO_LED_ALERTA, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  pinMode(PINO_CHAVE_WIFI, INPUT_PULLDOWN);   // chave liga a 3V3 quando "conectado"
  pinMode(PINO_BOTAO_BATIMENTO, INPUT_PULLUP); // botão liga ao GND quando pressionado
  digitalWrite(PINO_LED_ONLINE, LOW);
  digitalWrite(PINO_LED_ALERTA, LOW);
  digitalWrite(PINO_BUZZER, LOW);

  dht.begin();
  Wire.begin(PINO_I2C_SDA, PINO_I2C_SCL);
  mpuDisponivel = mpu.begin();
  if (mpuDisponivel) {
    mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("[SENSOR] MPU6050 iniciado (acelerometro, faixa 4 g)");
  } else {
    Serial.println("[SENSOR] MPU6050 nao encontrado; movimento desabilitado");
  }
  Serial.println("[SENSOR] DHT22 iniciado; botao de batimento com interrupcao");

  attachInterrupt(digitalPinToInterrupt(PINO_BOTAO_BATIMENTO), isrBatimento, FALLING);

#if USAR_SPIFFS
  spiffsIniciar();
#else
  Serial.println("[SPIFFS] desativado por compilacao (USAR_SPIFFS 0); resiliencia via buffer em RAM");
#endif

  // Estado inicial coerente com a chave.
  estado = lerConectividade() ? ONLINE : OFFLINE;
  digitalWrite(PINO_LED_ONLINE, estado == ONLINE ? HIGH : LOW);
  Serial.printf("[%s] estado inicial definido pela chave Wi-Fi simulada\n",
                estado == ONLINE ? "ONLINE" : "OFFLINE");
  if (estado == ONLINE) {
    Serial.print("[ONLINE] envio em tempo real: ");
    Serial.println(CSV_CABECALHO);
  }
  proximaAmostraMs = millis() + 2000;  // aguarda o DHT22 estabilizar
  proximoStatusMs  = millis() + INTERVALO_STATUS_BUFFER_MS;
}

void loop() {
  atualizarEstadoConexao();
  atualizarBuzzer();

  uint32_t agora = millis();
  if ((int32_t)(agora - proximaAmostraMs) >= 0) {
    proximaAmostraMs += INTERVALO_AMOSTRA_MS;
    coletarAmostra();
  }
  if ((int32_t)(agora - proximoStatusMs) >= 0) {
    proximoStatusMs += INTERVALO_STATUS_BUFFER_MS;
    imprimirStatusBuffer();
  }
  delay(5);  // loop leve; a lógica é temporizada por millis()
}
