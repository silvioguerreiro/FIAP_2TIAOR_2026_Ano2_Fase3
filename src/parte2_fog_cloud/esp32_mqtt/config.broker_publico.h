/*
 * CardioIA Fase 3, Parte 2: configuração para o broker público de testes.
 * Conteúdo usado como "config.h" no projeto público do Wokwi, porque não
 * contém segredos: broker.hivemq.com, porta 1883, sem autenticação e sem
 * criptografia (limitação registrada no relatório). Para o HiveMQ Cloud
 * com TLS e credenciais, use config.example.h como modelo e mantenha o
 * config.h resultante fora do versionamento.
 */
#pragma once

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
