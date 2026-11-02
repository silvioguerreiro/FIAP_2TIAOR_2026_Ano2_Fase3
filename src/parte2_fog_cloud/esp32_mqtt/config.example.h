/*
 * CardioIA Fase 3, Parte 2 (Fog/Cloud): modelo de configuração de rede e MQTT.
 *
 * Copie este arquivo para "config.h" (mesma pasta) e preencha os valores.
 * O arquivo config.h está no .gitignore e nunca deve ser versionado nem
 * colado em projetos públicos com credenciais reais.
 *
 * Dois perfis de broker:
 *   1) HiveMQ Cloud (recomendado): TLS na porta 8883, usuário e senha criados
 *      em Access Management do cluster. No simulador o certificado do servidor
 *      não é validado (setInsecure); em produção use setCACert com a cadeia
 *      da autoridade certificadora.
 *   2) Broker público de testes broker.hivemq.com, porta 1883, sem autenticação
 *      e sem criptografia. Use apenas para demonstração; qualquer pessoa pode
 *      ler e publicar nos tópicos.
 */
#pragma once

// ---- Wi-Fi ---------------------------------------------------------------
// No Wokwi a rede é "Wokwi-GUEST", sem senha; o canal 6 acelera a conexão.
#define WIFI_SSID        "Wokwi-GUEST"
#define WIFI_SENHA       ""
#define WIFI_CANAL       6

// ---- Broker MQTT ---------------------------------------------------------
// Perfil 1 (HiveMQ Cloud, TLS):
#define MQTT_HOST        "SEU-CLUSTER.s1.eu.hivemq.cloud"
#define MQTT_PORTA       8883
#define MQTT_USAR_TLS    1
#define MQTT_USUARIO     "usuario-do-dispositivo"
#define MQTT_SENHA       "senha-do-dispositivo"

// Perfil 2 (broker público, sem TLS): descomente estas linhas e comente as de cima.
// #define MQTT_HOST     "broker.hivemq.com"
// #define MQTT_PORTA    1883
// #define MQTT_USAR_TLS 0
// #define MQTT_USUARIO  ""
// #define MQTT_SENHA    ""

// ---- Identificação e tópicos ----------------------------------------------
// O identificador do paciente é um pseudônimo: nenhum dado pessoal trafega.
#define ID_DISPOSITIVO   "cardioia-g55-p01"
#define PREFIXO_TOPICO   "cardioia/grupo55/paciente01"

// ---- Fuso horário para o relógio NTP (Cuiabá, UTC-4) ------------------------
#define FUSO_SEGUNDOS    (-4 * 3600)
