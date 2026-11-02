/*
 * =====================================================================
 *  Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
 *  Fase    : 3, Monitoramento Contínuo (IoT no Peito do Paciente)
 *  Parte   : 2, Transmissão para a nuvem e visualização (Fog/Cloud)
 *  Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
 *  Data    : 31/10/2026
 *  Placa   : ESP32 DevKit (simulada no Wokwi), monitor serial a 115200
 *
 *  Descrição
 *  ---------
 *  Evolução do firmware da Parte 1. Mantém a coleta (DHT22, botão de
 *  batimentos, MPU6050), a avaliação local de alertas (LED e buzzer) e o
 *  buffer circular de resiliência, e acrescenta a transmissão para a nuvem
 *  via MQTT (biblioteca PubSubClient) com Wi-Fi real do simulador
 *  (Wokwi-GUEST), relógio NTP e três tópicos:
 *     <prefixo>/sinais   : uma mensagem JSON por amostra (tempo real ou
 *                          sincronização do buffer)
 *     <prefixo>/alertas  : estado dos alertas (mensagem retida)
 *     <prefixo>/estado   : online, offline, sincronizando (mensagem retida,
 *                          com testamento "offline_inesperado")
 *
 *  A chave deslizante simula a queda do enlace: desligada, o firmware
 *  derruba a conexão e armazena localmente; ligada, reconecta e sincroniza
 *  todas as amostras pendentes pela nuvem, em ordem cronológica. A perda
 *  real de Wi-Fi ou do broker produz o mesmo comportamento.
 *
 *  Credenciais ficam em config.h (fora do versionamento); veja
 *  config.example.h. Prefixos do log: [BOOT] [SENSOR] [WIFI] [MQTT]
 *  [OFFLINE] [ONLINE] [SYNC] [ALERTA] [BUFFER] [NTP]
 * =====================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <time.h>

// Credenciais e endereços ficam em config.h (fora do versionamento; modelo em
// config.example.h). Quando o arquivo não existe, como no projeto público do
// Wokwi, usa-se o broker público de testes, que não exige segredos.
#if __has_include("config.h")
  #include "config.h"
#else
  #warning "config.h ausente: usando broker publico broker.hivemq.com sem TLS (apenas demonstracao)"
  #define WIFI_SSID        "Wokwi-GUEST"
  #define WIFI_SENHA       ""
  #define WIFI_CANAL       6
  #define MQTT_HOST        "broker.hivemq.com"
  #define MQTT_PORTA       1883
  #define MQTT_USAR_TLS    0
  #define MQTT_USUARIO     ""
  #define MQTT_SENHA       ""
  #define ID_DISPOSITIVO   "cardioia-g55-p01"
  #define PREFIXO_TOPICO   "cardioia/grupo55/paciente01"
  #define FUSO_SEGUNDOS    (-4 * 3600)
#endif

// =====================================================================
//  1. CONFIGURAÇÃO (pinos, tempos, limites e flags)
// =====================================================================
const uint8_t PINO_DHT             = 15;
const uint8_t PINO_BOTAO_BATIMENTO = 4;
const uint8_t PINO_CHAVE_WIFI      = 18;  // HIGH = enlace ativo
const uint8_t PINO_LED_ONLINE      = 25;  // verde: conectado ao broker
const uint8_t PINO_LED_ALERTA      = 26;  // vermelho: alerta local
const uint8_t PINO_BUZZER          = 27;
const uint8_t PINO_I2C_SDA         = 21;
const uint8_t PINO_I2C_SCL         = 22;

const uint32_t INTERVALO_AMOSTRA_MS = 5000;
const uint16_t CAPACIDADE_BUFFER    = 3000;   // 3.000 x 20 bytes = 60 KB

const uint16_t LIMITE_BPM_TAQUICARDIA   = 120;
const uint16_t LIMITE_BPM_BRADICARDIA   = 50;
const float    LIMITE_TEMP_FEBRE_C      = 38.0;
const float    LIMITE_TEMP_HIPOTERMIA_C = 35.0;
#define MODO_DEMONSTRACAO 1
#if MODO_DEMONSTRACAO
const uint32_t LIMITE_SEM_MOVIMENTO_MS = 60UL * 1000UL;        // 60 s na demonstração
#else
const uint32_t LIMITE_SEM_MOVIMENTO_MS = 10UL * 60UL * 1000UL; // 10 min em produção
#endif

const uint32_t DEBOUNCE_BATIMENTO_MS = 150;
const uint32_t TEMPO_ZERAR_BPM_MS    = 5000;
const uint8_t  N_INTERVALOS_MEDIA    = 4;
const float    LIMIAR_DELTA_MOVIMENTO_G     = 0.10;
const float    LIMIAR_MAGNITUDE_MOVIMENTO_G = 0.30;

const uint32_t INTERVALO_TENTATIVA_MQTT_MS = 5000;   // reconexão não bloqueante
const uint32_t TEMPO_MAX_ASSOCIACAO_MS     = 30000;  // sem associação Wi-Fi neste prazo, reinicia o rádio e tenta de novo
const uint32_t INTERVALO_HEARTBEAT_MS      = 30000;  // estado periódico
const uint32_t PAUSA_ENTRE_SYNC_MS         = 20;     // evita inundar o broker
const uint32_t DURACAO_BIP_MS              = 200;
const uint16_t TAMANHO_BUFFER_MQTT         = 512;    // PubSubClient (padrão 256)

// =====================================================================
//  2. TIPOS E ESTADO GLOBAL
// =====================================================================
const uint8_t ALERTA_TAQUICARDIA   = 0x01;
const uint8_t ALERTA_BRADICARDIA   = 0x02;
const uint8_t ALERTA_FEBRE         = 0x04;
const uint8_t ALERTA_HIPOTERMIA    = 0x08;
const uint8_t ALERTA_SEM_MOVIMENTO = 0x10;

// Amostra com 20 bytes: acrescenta o número de sequência e a origem do
// carimbo de tempo (NTP ou relativo ao boot) em relação à Parte 1.
struct __attribute__((packed)) Amostra {
  uint32_t ts;          // época Unix (s) se NTP sincronizado; senão segundos desde o boot
  uint32_t seq;         // sequência crescente (detecção de lacunas no dashboard)
  float    temperatura;
  float    umidade;
  uint16_t bpm;
  uint8_t  movimento;
  uint8_t  alertas;     // bit 7 = carimbo relativo (sem NTP)
};
static_assert(sizeof(Amostra) == 20, "Amostra deve ocupar 20 bytes");
const uint8_t FLAG_TS_RELATIVO = 0x80;

enum EstadoConexao { OFFLINE, ONLINE };

Amostra  buffer[CAPACIDADE_BUFFER];
uint16_t bufferInicio = 0, bufferQtd = 0;
uint32_t totalArmazenadas = 0, totalDescartadas = 0, totalSincronizadas = 0, totalPublicadas = 0;
uint32_t sequencia = 0;

DHT dht(PINO_DHT, DHT22);
Adafruit_MPU6050 mpu;
bool  mpuDisponivel = false;
float ultimaTemperatura = NAN, ultimaUmidade = NAN;
float accAnterior[3] = {0, 0, 1.0};
uint32_t ultimoMovimentoMs = 0;

volatile uint32_t ultimoBatimentoMs = 0;
volatile uint32_t intervalosMs[N_INTERVALOS_MEDIA];
volatile uint8_t  idxIntervalo = 0, nIntervalos = 0;
volatile uint32_t totalBatimentos = 0;

#if MQTT_USAR_TLS
WiFiClientSecure clienteRede;
#else
WiFiClient clienteRede;
#endif
PubSubClient mqtt(clienteRede);

char topicoSinais[96], topicoAlertas[96], topicoEstado[96];
EstadoConexao estado = OFFLINE;
bool     ntpSincronizado = false;
uint8_t  ultimaMascaraAlertas = 0;
uint32_t proximaAmostraMs = 0, proximoHeartbeatMs = 0, proximaTentativaMqttMs = 0, buzzerAteMs = 0;
bool     wifiIniciado = false;
uint32_t inicioTentativaWifiMs = 0;   // marca o início da associação Wi-Fi (vigia de reconexão)

// =====================================================================
//  3. BATIMENTOS (ISR do botão) E SENSORES (iguais à Parte 1)
// =====================================================================
void IRAM_ATTR isrBatimento() {
  uint32_t agora = millis();
  if (agora - ultimoBatimentoMs < DEBOUNCE_BATIMENTO_MS) return;
  if (ultimoBatimentoMs != 0) {
    intervalosMs[idxIntervalo] = agora - ultimoBatimentoMs;
    idxIntervalo = (idxIntervalo + 1) % N_INTERVALOS_MEDIA;
    if (nIntervalos < N_INTERVALOS_MEDIA) nIntervalos++;
  }
  ultimoBatimentoMs = agora;
  totalBatimentos++;
}

uint16_t calcularBpm() {
  uint32_t copia[N_INTERVALOS_MEDIA]; uint8_t n; uint32_t ultimo;
  noInterrupts();
  n = nIntervalos; ultimo = ultimoBatimentoMs;
  for (uint8_t i = 0; i < N_INTERVALOS_MEDIA; i++) copia[i] = intervalosMs[i];
  interrupts();
  if (n == 0 || ultimo == 0) return 0;
  if (millis() - ultimo > TEMPO_ZERAR_BPM_MS) {
    noInterrupts(); nIntervalos = 0; idxIntervalo = 0; ultimoBatimentoMs = 0; interrupts();
    return 0;
  }
  uint32_t soma = 0;
  for (uint8_t i = 0; i < n; i++) soma += copia[i];
  uint32_t media = soma / n;
  return media ? (uint16_t)(60000UL / media) : 0;
}

void lerDht(float &temperatura, float &umidade) {
  float t = dht.readTemperature(), u = dht.readHumidity();
  if (isnan(t) || isnan(u)) {
    Serial.println("[SENSOR] falha de leitura do DHT22; mantendo ultimo valor valido");
    temperatura = ultimaTemperatura; umidade = ultimaUmidade; return;
  }
  ultimaTemperatura = temperatura = t;
  ultimaUmidade = umidade = u;
}

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
  bool movimento = (delta > LIMIAR_DELTA_MOVIMENTO_G) || (fabsf(magnitudeG - 1.0f) > LIMIAR_MAGNITUDE_MOVIMENTO_G);
  if (movimento) ultimoMovimentoMs = millis();
  return movimento;
}

// =====================================================================
//  4. ALERTAS LOCAIS (Edge): avaliação e atuação independem da nuvem
// =====================================================================
uint8_t avaliarAlertas(const Amostra &a) {
  uint8_t al = 0;
  if (a.bpm > LIMITE_BPM_TAQUICARDIA) al |= ALERTA_TAQUICARDIA;
  if (a.bpm > 0 && a.bpm < LIMITE_BPM_BRADICARDIA) al |= ALERTA_BRADICARDIA;
  if (!isnan(a.temperatura)) {
    if (a.temperatura > LIMITE_TEMP_FEBRE_C) al |= ALERTA_FEBRE;
    if (a.temperatura < LIMITE_TEMP_HIPOTERMIA_C) al |= ALERTA_HIPOTERMIA;
  }
  if (mpuDisponivel && ultimoMovimentoMs > 0 && (millis() - ultimoMovimentoMs) > LIMITE_SEM_MOVIMENTO_MS) al |= ALERTA_SEM_MOVIMENTO;
  return al;
}

// Nomes curtos, usados no JSON e no log (sem acentos para simplificar o transporte).
void nomesAlertas(uint8_t mascara, char *saida, size_t tam) {
  saida[0] = '\0';
  const char* nomes[5] = {"taquicardia", "bradicardia", "febre", "hipotermia", "sem_movimento"};
  for (uint8_t i = 0; i < 5; i++) {
    if (mascara & (1 << i)) {
      if (saida[0]) strncat(saida, ",", tam - strlen(saida) - 1);
      strncat(saida, nomes[i], tam - strlen(saida) - 1);
    }
  }
}

void atuarAlertas(uint8_t mascara) {
  digitalWrite(PINO_LED_ALERTA, mascara ? HIGH : LOW);
  if (mascara) { digitalWrite(PINO_BUZZER, HIGH); buzzerAteMs = millis() + DURACAO_BIP_MS; }
}

void atualizarBuzzer() {
  if (buzzerAteMs != 0 && (int32_t)(millis() - buzzerAteMs) >= 0) { digitalWrite(PINO_BUZZER, LOW); buzzerAteMs = 0; }
}

// =====================================================================
//  5. RELÓGIO: NTP quando há rede; carimbo relativo antes da sincronização
// =====================================================================
uint32_t agoraSegundos(bool &relativo) {
  time_t t = time(nullptr);
  if (t > 1700000000) { ntpSincronizado = true; relativo = false; return (uint32_t)t; }
  relativo = true;
  return millis() / 1000UL;
}

// =====================================================================
//  6. SERIALIZAÇÃO JSON (compacta, sem biblioteca externa)
// =====================================================================
void amostraParaJson(const Amostra &a, const char *origem, char *saida, size_t tam) {
  bool relativo = a.alertas & FLAG_TS_RELATIVO;
  uint8_t mascara = a.alertas & 0x7F;
  snprintf(saida, tam,
           "{\"disp\":\"%s\",\"seq\":%lu,\"ts\":%lu,\"tsrel\":%d,\"temp\":%.2f,\"umid\":%.1f,"
           "\"bpm\":%u,\"mov\":%u,\"alertas\":%u,\"origem\":\"%s\"}",
           ID_DISPOSITIVO, (unsigned long)a.seq, (unsigned long)a.ts, relativo ? 1 : 0,
           a.temperatura, a.umidade, a.bpm, a.movimento, mascara, origem);
}

void alertasParaJson(const Amostra &a, char *saida, size_t tam) {
  char nomes[96];
  uint8_t mascara = a.alertas & 0x7F;
  nomesAlertas(mascara, nomes, sizeof(nomes));
  snprintf(saida, tam,
           "{\"disp\":\"%s\",\"ts\":%lu,\"ativo\":%d,\"mascara\":%u,\"tipos\":\"%s\",\"bpm\":%u,\"temp\":%.2f,\"seq\":%lu}",
           ID_DISPOSITIVO, (unsigned long)a.ts, mascara ? 1 : 0, mascara, nomes, a.bpm, a.temperatura, (unsigned long)a.seq);
}

void estadoParaJson(const char *nomeEstado, char *saida, size_t tam) {
  bool rel; uint32_t ts = agoraSegundos(rel);
  snprintf(saida, tam,
           "{\"disp\":\"%s\",\"estado\":\"%s\",\"pendentes\":%u,\"capacidade\":%u,\"descartadas\":%lu,"
           "\"publicadas\":%lu,\"ts\":%lu,\"heap\":%u,\"rssi\":%d}",
           ID_DISPOSITIVO, nomeEstado, bufferQtd, CAPACIDADE_BUFFER, (unsigned long)totalDescartadas,
           (unsigned long)totalPublicadas, (unsigned long)ts, (unsigned)ESP.getFreeHeap(), WiFi.RSSI());
}

// =====================================================================
//  7. BUFFER CIRCULAR (resiliência offline, igual à Parte 1)
// =====================================================================
void bufferArmazenar(const Amostra &a) {
  if (bufferQtd == CAPACIDADE_BUFFER) {
    bufferInicio = (bufferInicio + 1) % CAPACIDADE_BUFFER; bufferQtd--; totalDescartadas++;
    Serial.printf("[BUFFER] cheio: amostra mais antiga descartada (total descartadas=%lu)\n", (unsigned long)totalDescartadas);
  }
  buffer[(bufferInicio + bufferQtd) % CAPACIDADE_BUFFER] = a;
  bufferQtd++; totalArmazenadas++;
}

// =====================================================================
//  8. REDE: Wi-Fi, MQTT e máquina de estados
// =====================================================================
bool publicar(const char *topico, const char *payload, bool retido) {
  bool ok = mqtt.publish(topico, payload, retido);
  if (ok) totalPublicadas++;
  return ok;
}

void publicarEstado(const char *nomeEstado) {
  char json[256];
  estadoParaJson(nomeEstado, json, sizeof(json));
  if (publicar(topicoEstado, json, true)) Serial.printf("[MQTT] %s <- %s\n", topicoEstado, json);
}

// Envia o buffer em ordem cronológica. Cada amostra só sai do buffer depois
// de publicada; se a conexão cair no meio, o restante permanece pendente.
void sincronizarPendentes() {
  char json[256];
  uint16_t enviadas = 0, total = bufferQtd;
  Serial.printf("[SYNC] iniciando sincronizacao de %u amostras pendentes via MQTT\n", total);
  publicarEstado("sincronizando");
  while (bufferQtd > 0 && mqtt.connected()) {
    const Amostra &a = buffer[bufferInicio];
    amostraParaJson(a, "sync", json, sizeof(json));
    if (!publicar(topicoSinais, json, false)) {
      Serial.println("[SYNC] falha de publicacao; restante permanece no buffer");
      break;
    }
    bufferInicio = (bufferInicio + 1) % CAPACIDADE_BUFFER; bufferQtd--; enviadas++;
    totalSincronizadas++;
    if ((enviadas % 10) == 0) Serial.printf("[SYNC] %u/%u enviadas (seq %lu)\n", enviadas, total, (unsigned long)a.seq);
    mqtt.loop();
    delay(PAUSA_ENTRE_SYNC_MS);
  }
  Serial.printf("[SYNC] concluida: %u de %u enviadas; pendentes=%u (total sincronizadas=%lu)\n",
                enviadas, total, bufferQtd, (unsigned long)totalSincronizadas);
}

void iniciarWifi() {
  Serial.printf("[WIFI] conectando a \"%s\" (canal %d)...\n", WIFI_SSID, WIFI_CANAL);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);              // o controlador tenta reassociar sozinho se a rede cair
  WiFi.begin(WIFI_SSID, WIFI_SENHA, WIFI_CANAL);
  wifiIniciado = true;
  inicioTentativaWifiMs = millis();
}

// Vigia da associação: se WiFi.begin não concluir em TEMPO_MAX_ASSOCIACAO_MS, o rádio é
// desligado e religado e a associação recomeça. Evita o dispositivo ficar preso em
// "conectando" depois de uma queda longa; o custo é apenas uma linha no log.
void vigiarAssociacaoWifi() {
  if ((millis() - inicioTentativaWifiMs) < TEMPO_MAX_ASSOCIACAO_MS) return;
  Serial.printf("[WIFI] sem associacao em %lu s; reiniciando o radio e tentando de novo\n",
                (unsigned long)(TEMPO_MAX_ASSOCIACAO_MS / 1000UL));
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  delay(200);
  wifiIniciado = false;
  iniciarWifi();
}

void desligarRede(const char *motivo) {
  if (mqtt.connected()) { publicarEstado("offline"); mqtt.disconnect(); }
  if (wifiIniciado) { WiFi.disconnect(true); WiFi.mode(WIFI_OFF); wifiIniciado = false; }
  if (estado == ONLINE) {
    estado = OFFLINE;
    digitalWrite(PINO_LED_ONLINE, LOW);
    Serial.printf("[OFFLINE] %s em t=%lu s; armazenando localmente\n", motivo, (unsigned long)(millis() / 1000UL));
  }
}

bool conectarMqtt() {
  char testamento[160];
  snprintf(testamento, sizeof(testamento), "{\"disp\":\"%s\",\"estado\":\"offline_inesperado\"}", ID_DISPOSITIVO);
  Serial.printf("[MQTT] conectando a %s:%d (TLS=%d) como %s...\n", MQTT_HOST, MQTT_PORTA, MQTT_USAR_TLS, ID_DISPOSITIVO);
  bool ok;
  if (strlen(MQTT_USUARIO) > 0) ok = mqtt.connect(ID_DISPOSITIVO, MQTT_USUARIO, MQTT_SENHA, topicoEstado, 1, true, testamento);
  else                          ok = mqtt.connect(ID_DISPOSITIVO, topicoEstado, 1, true, testamento);
  if (!ok) { Serial.printf("[MQTT] falha, rc=%d; nova tentativa em %lu s\n", mqtt.state(), (unsigned long)(INTERVALO_TENTATIVA_MQTT_MS / 1000)); }
  return ok;
}

void atualizarRede() {
  bool chaveLigada = digitalRead(PINO_CHAVE_WIFI) == HIGH;

  if (!chaveLigada) { desligarRede("enlace desligado pela chave"); return; }

  if (!wifiIniciado) iniciarWifi();

  if (WiFi.status() != WL_CONNECTED) {
    if (estado == ONLINE) desligarRede("Wi-Fi perdido");
    if (!wifiIniciado) iniciarWifi();
    else vigiarAssociacaoWifi();
    return;
  }

  // Wi-Fi ativo: garante NTP e MQTT
  static bool ntpConfigurado = false;
  if (!ntpConfigurado) {
    configTime(FUSO_SEGUNDOS, 0, "pool.ntp.org", "time.google.com");
    ntpConfigurado = true;
    Serial.printf("[WIFI] conectado, IP %s, RSSI %d dBm; NTP solicitado\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  }
  static bool ntpAnunciado = false;
  if (!ntpAnunciado) {
    bool rel; agoraSegundos(rel);
    if (!rel) { ntpAnunciado = true; Serial.printf("[NTP] relogio sincronizado: %lu (epoca Unix)\n", (unsigned long)time(nullptr)); }
  }

  if (!mqtt.connected()) {
    if (estado == ONLINE) { estado = OFFLINE; digitalWrite(PINO_LED_ONLINE, LOW); Serial.println("[OFFLINE] conexao MQTT perdida; armazenando localmente"); }
    if ((int32_t)(millis() - proximaTentativaMqttMs) >= 0) {
      proximaTentativaMqttMs = millis() + INTERVALO_TENTATIVA_MQTT_MS;
      if (conectarMqtt()) {
        estado = ONLINE;
        digitalWrite(PINO_LED_ONLINE, HIGH);
        Serial.printf("[ONLINE] conectado ao broker em t=%lu s; %u amostras pendentes\n", (unsigned long)(millis() / 1000UL), bufferQtd);
        if (bufferQtd > 0) sincronizarPendentes();
        publicarEstado("online");
        proximoHeartbeatMs = millis() + INTERVALO_HEARTBEAT_MS;
      }
    }
    return;
  }

  mqtt.loop();
  if ((int32_t)(millis() - proximoHeartbeatMs) >= 0) {
    proximoHeartbeatMs += INTERVALO_HEARTBEAT_MS;
    publicarEstado("online");
  }
}

// =====================================================================
//  9. CICLO DE AMOSTRAGEM
// =====================================================================
void coletarAmostra() {
  Amostra a;
  bool relativo;
  a.ts = agoraSegundos(relativo);
  a.seq = ++sequencia;
  float temperatura, umidade;
  lerDht(temperatura, umidade);
  a.temperatura = temperatura; a.umidade = umidade;
  a.bpm = calcularBpm();
  float magnitudeG;
  a.movimento = lerMovimento(magnitudeG) ? 1 : 0;
  uint8_t mascara = avaliarAlertas(a);
  a.alertas = mascara | (relativo ? FLAG_TS_RELATIVO : 0);

  atuarAlertas(mascara);  // atuação local sempre, antes de qualquer envio
  if (mascara) {
    char nomes[96]; nomesAlertas(mascara, nomes, sizeof(nomes));
    Serial.printf("[ALERTA] %s (bpm=%u, temp=%.1f C); LED vermelho e buzzer acionados localmente\n", nomes, a.bpm, a.temperatura);
  }

  char json[256];
  if (estado == ONLINE && mqtt.connected()) {
    amostraParaJson(a, "rt", json, sizeof(json));
    if (publicar(topicoSinais, json, false)) {
      Serial.printf("[ONLINE] %s <- %s\n", topicoSinais, json);
    } else {
      Serial.println("[MQTT] falha ao publicar; amostra enviada ao buffer");
      bufferArmazenar(a);
    }
    // Estado dos alertas: publica quando muda (retido) e reforça enquanto ativo.
    if (mascara != ultimaMascaraAlertas || mascara != 0) {
      alertasParaJson(a, json, sizeof(json));
      if (publicar(topicoAlertas, json, true)) Serial.printf("[MQTT] %s <- %s\n", topicoAlertas, json);
    }
    ultimaMascaraAlertas = mascara;
  } else {
    bufferArmazenar(a);
    Serial.printf("[OFFLINE] seq=%lu ts=%lu temp=%.2f umid=%.1f bpm=%u mov=%u alertas=%u | armazenada (%u/%u)\n",
                  (unsigned long)a.seq, (unsigned long)a.ts, a.temperatura, a.umidade, a.bpm, a.movimento,
                  mascara, bufferQtd, CAPACIDADE_BUFFER);
  }
}

// =====================================================================
// 10. SETUP E LOOP
// =====================================================================
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("[BOOT] CardioIA Fase 3, Parte 2 (Fog/Cloud): wearable cardiaco com MQTT");
  Serial.printf("[BOOT] amostragem=%lu ms, buffer=%u amostras x %u bytes = %u bytes\n",
                (unsigned long)INTERVALO_AMOSTRA_MS, CAPACIDADE_BUFFER, (unsigned)sizeof(Amostra), (unsigned)sizeof(buffer));
  Serial.printf("[BOOT] limites: bpm>%u, bpm<%u, temp>%.1f, temp<%.1f, sem movimento>%lu s\n",
                LIMITE_BPM_TAQUICARDIA, LIMITE_BPM_BRADICARDIA, LIMITE_TEMP_FEBRE_C, LIMITE_TEMP_HIPOTERMIA_C,
                (unsigned long)(LIMITE_SEM_MOVIMENTO_MS / 1000UL));
  Serial.println("[BOOT] dica: no Wokwi, ajuste o DHT22 para ~36.5 C (temperatura cutanea normal); 24 C gera alerta de hipotermia");

  snprintf(topicoSinais, sizeof(topicoSinais), "%s/sinais", PREFIXO_TOPICO);
  snprintf(topicoAlertas, sizeof(topicoAlertas), "%s/alertas", PREFIXO_TOPICO);
  snprintf(topicoEstado, sizeof(topicoEstado), "%s/estado", PREFIXO_TOPICO);
  Serial.printf("[BOOT] topicos: %s | %s | %s\n", topicoSinais, topicoAlertas, topicoEstado);

  pinMode(PINO_LED_ONLINE, OUTPUT); pinMode(PINO_LED_ALERTA, OUTPUT); pinMode(PINO_BUZZER, OUTPUT);
  pinMode(PINO_CHAVE_WIFI, INPUT_PULLDOWN);
  pinMode(PINO_BOTAO_BATIMENTO, INPUT_PULLUP);
  digitalWrite(PINO_LED_ONLINE, LOW); digitalWrite(PINO_LED_ALERTA, LOW); digitalWrite(PINO_BUZZER, LOW);

  dht.begin();
  Wire.begin(PINO_I2C_SDA, PINO_I2C_SCL);
  mpuDisponivel = mpu.begin();
  if (mpuDisponivel) { mpu.setAccelerometerRange(MPU6050_RANGE_4_G); mpu.setFilterBandwidth(MPU6050_BAND_21_HZ); Serial.println("[SENSOR] MPU6050 iniciado"); }
  else Serial.println("[SENSOR] MPU6050 nao encontrado; movimento desabilitado");
  attachInterrupt(digitalPinToInterrupt(PINO_BOTAO_BATIMENTO), isrBatimento, FALLING);

#if MQTT_USAR_TLS
  // No simulador não há armazenamento de certificados raiz; a conexão é
  // cifrada, mas o certificado do servidor não é validado. Em produção:
  // clienteRede.setCACert(CERTIFICADO_CA_PEM);
  clienteRede.setInsecure();
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORTA);
  mqtt.setBufferSize(TAMANHO_BUFFER_MQTT);
  mqtt.setKeepAlive(30);

  Serial.printf("[BOOT] heap livre=%u bytes\n", (unsigned)ESP.getFreeHeap());
  Serial.println(digitalRead(PINO_CHAVE_WIFI) == HIGH ? "[BOOT] chave ligada: iniciando conexao" : "[OFFLINE] chave desligada: coleta local ate o enlace voltar");
  proximaAmostraMs = millis() + 2000;
}

void loop() {
  atualizarRede();
  atualizarBuzzer();
  uint32_t agora = millis();
  if ((int32_t)(agora - proximaAmostraMs) >= 0) {
    proximaAmostraMs += INTERVALO_AMOSTRA_MS;
    coletarAmostra();
  }
  delay(5);
}
