# Node-RED: fluxo e dashboard da Parte 2 (Fog/Cloud)

Projeto CardioIA, Fase 3, Grupo 55. Este diretório contém o fluxo completo do Node-RED (`flows.json`) com o dashboard do paciente, a lista de pacotes (`pacotes.txt`) e estas instruções de instalação e importação.

## O que o fluxo faz

O fluxo assina três tópicos do broker MQTT publicados pelo ESP32 (`cardioia/grupo55/paciente01/sinais`, `/alertas` e `/estado`), converte o JSON, normaliza cada amostra, avalia os limites de alerta na camada Fog (combinando com a avaliação feita no próprio dispositivo) e alimenta a página `Paciente 01 - Monitoramento continuo` do Dashboard 2.0, com gráficos de série temporal de frequência cardíaca e temperatura (eixo do tempo pelo carimbo da amostra, o que posiciona corretamente as amostras sincronizadas do buffer), medidores de temperatura, umidade e frequência cardíaca, painel de alerta com cor, notificação, textos com a última avaliação e uma tabela com as últimas 12 amostras.

Limites de alerta (definidos no nó `Definir limites de alerta`, executado no deploy): frequência cardíaca acima de 120 bpm ou abaixo de 50 bpm (quando houver batimentos), temperatura acima de 38,0 C ou abaixo de 35,0 C, ausência de movimento por mais de 600 s.

## Instalação no computador (macOS, Windows ou Linux)

Pré-requisito: Node.js 18 ou superior (testado com 22 no ambiente de trabalho e com 24.16 no computador do aluno).

Opção A, instalação global:

```bash
npm install -g --unsafe-perm node-red
cd ~/.node-red          # no Windows: cd %USERPROFILE%\.node-red
npm install @flowfuse/node-red-dashboard
node-red
```

Opção B, instalação local em uma pasta, sem privilégios de administrador (foi a usada na execução de 30/10/2026 no macOS, porque o cache global do npm pertencia ao root):

```bash
mkdir -p ~/cardioia-nodered/userdir && cd ~/cardioia-nodered
npm install --cache ./.npm-cache --no-audit --no-fund node-red@4 @flowfuse/node-red-dashboard
cp <repositorio>/src/parte2_fog_cloud/node_red/flows.json userdir/flows.json
node node_modules/node-red/red.js -u ~/cardioia-nodered/userdir -p 1880
```

Editor em http://localhost:1880 e dashboard em http://localhost:1880/dashboard/paciente01. Na opção B o fluxo já é carregado na partida (o arquivo `flows.json` foi copiado para o diretório de usuário), e o passo de importação abaixo pode ser pulado.

## Importação do fluxo

1. No editor, menu (canto superior direito), `Import`, `select a file to import`, escolha `flows.json` desta pasta e clique em `Import`.
2. Abra o nó de configuração `Broker MQTT (HiveMQ publico)` (duplo clique em qualquer nó `MQTT ...`, ícone de lápis) para conferir o broker. O arquivo vem configurado para `broker.hivemq.com`, porta 1883, sem autenticação, o mesmo perfil do projeto público do Wokwi. Para o HiveMQ Cloud: altere o servidor para o endereço do cluster, porta 8883, marque `Use TLS` e preencha usuário e senha na aba `Security`. As credenciais ficam criptografadas no arquivo de credenciais do Node-RED e não entram no `flows.json`.
3. Clique em `Deploy`. Os nós `MQTT ...` devem exibir `connected`.
4. Abra o dashboard. Com o ESP32 publicando (projeto do Wokwi da Parte 2 em execução), o painel de estado mostra `ONLINE` e os gráficos começam a receber pontos a cada 5 s.

## Execução com o ESP32 real e capturas

Em 30/10/2026 o fluxo foi executado no computador do aluno (opção B) com o projeto da Parte 2 em execução no Wokwi (https://wokwi.com/projects/479362979389911041), ambos ligados ao broker público. As capturas `p2_10` a `p2_15` em `assets/evidencias/parte2/` vêm dessa execução: dashboard em estado normal, com alerta, offline e após a sincronização do buffer, editor com o fluxo e painel de depuração. As capturas do dashboard foram feitas com o Google Chrome em modo sem interface (`--headless=new --screenshot --window-size=1600,1750 --timeout=14000 http://127.0.0.1:1880/dashboard/paciente01`) e as do editor com `scripts/captura_editor_node_red_mac.js` (playwright-core sobre o Chrome instalado: `npm install playwright-core` e `node captura_editor_node_red_mac.js <pasta_destino>`). O log do Node-RED dessa sessão está em `assets/evidencias/parte2/log_node_red_mac_2026-10-30.txt`.

## Teste sem o ESP32

`scripts/simulador_mqtt_esp32.js` publica mensagens no mesmo formato do firmware (incluindo uma rajada de sincronização e cenários de taquicardia e febre). Uso: `node scripts/simulador_mqtt_esp32.js mqtt://broker.hivemq.com:1883` (requer `npm install mqtt`). Foi com esse simulador e um broker local (aedes) que o fluxo foi construído e validado no ambiente de trabalho, antes da execução com o dispositivo real.

## Regeneração do flows.json

O arquivo é gerado por `scripts/gerar_flows_node_red.py` (Python 3, sem dependências), que mantém IDs estáveis e documenta cada nó. Edite o script e execute `python3 scripts/gerar_flows_node_red.py src/parte2_fog_cloud/node_red/flows.json`.
