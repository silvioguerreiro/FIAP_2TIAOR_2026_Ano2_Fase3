# Documento de entrega. CardioIA, Fase 3: Monitoramento Contínuo (IoT no Peito do Paciente)

![FIAP](../../assets/logo-fiap.png)

| Campo | Valor |
|---|---|
| Instituição | FIAP, Faculdade de Informática e Administração Paulista |
| Curso | Inteligência Artificial, Ano 2 |
| Turma | 2TIAOR |
| Grupo | 55 (formato individual) |
| Aluno | Silvio Prestes Guerreiro Junior, RM 567958 |
| Fase | 3, Monitoramento Contínuo: IoT no Peito do Paciente (Edge, Fog e Cloud Computing) |
| Tutor | Leonardo Ruiz Orabona |
| Coordenador | André Godoi Chiovato |
| Data da entrega | 02 de novembro de 2026 |
| Repositório público no GitHub | https://github.com/silvioguerreiro/FIAP_2TIAOR_2026_Ano2_Fase3 |
| Projeto da Parte 1 no Wokwi | https://wokwi.com/projects/479362553804308481 |
| Projeto da Parte 2 no Wokwi | https://wokwi.com/projects/479362979389911041 |
| Ir Além 1 (REST e e-mail) | Concluído: src/ir_alem1_rest_email (API FastAPI, verificação de risco, e-mail simulado, cliente, ponte MQTT, 35 testes) e document/relatorio_ir_alem1.docx |
| Ir Além 2 (IA em séries temporais) | Concluído: src/ir_alem2_ia_series (notebook comparativo entre a regra de limiares, regressão logística e rede neuromórfica LIF sobre séries de frequência cardíaca), document/relatorio_ir_alem2.docx e vídeo com legendas explicativas: https://youtu.be/PfXksf7mLBU |

## 1. Resumo do conteúdo entregue

A entrega resolve integralmente as duas partes obrigatórias da Fase 3. Na Parte 1, um wearable cardíaco simulado no Wokwi com ESP32 lê três sensores (DHT22 para temperatura e umidade, botão de pressão como sensor de batimentos e MPU6050 para movimento), avalia no próprio dispositivo cinco regras de alerta (taquicardia, bradicardia, febre, hipotermia e ausência de movimento), aciona LED e buzzer mesmo sem conexão, simula a conectividade por uma chave deslizante, armazena as amostras em um buffer circular de 3.000 posições durante a perda de conexão e as sincroniza em ordem cronológica, em CSV pela serial, quando a conexão volta. A camada SPIFFS, não pontuada por limitação dos simuladores, está implementada e pronta para chip real sob uma flag de compilação. Na Parte 2, o firmware evolui para Wi-Fi, NTP e MQTT, publicando sinais, alertas e estado em três tópicos de um broker (HiveMQ Cloud com TLS no perfil de produção; broker público para a demonstração), com mensagens retidas, testamento, reconexão automática e sincronização do buffer pela nuvem; um fluxo do Node-RED com Dashboard 2.0 recebe as mensagens, reavalia os limites e exibe gráficos de frequência cardíaca e temperatura, medidores, painel de alerta com cor, notificação, tabela e estado do dispositivo.

O desafio Ir Além 1 também foi realizado: uma API REST em Python (FastAPI) recebe os mesmos sinais publicados pelo dispositivo, aplica regras de risco explícitas e testáveis e aciona uma automação de e-mail (simulada por padrão, com modos SMTP local e real), com cliente REST, ponte MQTT, aba de integração no Node-RED e 35 testes automatizados. O desafio Ir Além 2 compara, em um notebook executado, a regra de limiares do firmware, uma regressão logística e uma rede neuromórfica simples de neurônios LIF na classificação de episódios de risco em janelas de dois minutos de frequência cardíaca, com dados sintéticos documentados e aplicação à série real do protótipo; o relatório comparativo e o vídeo com legendas explicativas acompanham o notebook. Todos os entregáveis pedidos pelo enunciado estão no repositório, organizado no modelo de repositório da FIAP, e a Tabela 1 relaciona cada um deles ao seu local. Na versão em PDF enviada na plataforma, os quatro relatórios seguem anexos a este documento, na ordem Parte 1, Parte 2, Ir Além 1 e Ir Além 2.

Tabela 1. Entregáveis da Fase 3 e localização no repositório.

| Entregável exigido | Localização |
|---|---|
| Parte 1: link do projeto no Wokwi | Tabela de identificação acima e seção "Links da entrega" do README |
| Parte 1: código em C++ comentado | src/parte1_edge/wokwi/sketch.ino, com diagram.json, libraries.txt, wokwi.toml e platformio.ini |
| Parte 1: relatório (mínimo de uma página) sobre o fluxo de funcionamento e a lógica de resiliência | document/relatorio_parte1.docx (8 páginas, com diagrama de blocos, máquina de estados, dimensionamento numérico e evidências) |
| Parte 2: código do ESP32 (Arduino IDE/Wokwi) | src/parte2_fog_cloud/esp32_mqtt/sketch.ino, com config.example.h (credenciais fora do código), diagram.json, libraries.txt, wokwi.toml e platformio.ini |
| Parte 2: prints da aplicação ou export do dashboard no Node-RED | src/parte2_fog_cloud/node_red/flows.json (export completo) e assets/evidencias/parte2/ (capturas do dashboard, do editor, do debug e do broker; logs do monitor serial e do assinante do broker) |
| Parte 2: relatório (mínimo de duas páginas) sobre o fluxo MQTT e a configuração do dashboard | document/relatorio_parte2.docx (18 páginas, com arquitetura, sequência MQTT, configuração do Node-RED, evidências e seção de segurança e boas práticas) |
| Documentação | README.md com matriz de rastreabilidade dos cinco critérios de avaliação; src/parte2_fog_cloud/node_red/README.md; document/checklist_rubrica.md; document/roteiro_entrega.md |
| Ir Além 1: código Python (cliente REST, verificação de risco, e-mail automatizado) e relatório curto | src/ir_alem1_rest_email (api/, cliente/, tests/, node_red/); document/relatorio_ir_alem1.docx (2 páginas); evidências em assets/evidencias/ir_alem1 |
| Ir Além 2: notebook comentado, repositório público, relatório comparativo e vídeo | src/ir_alem2_ia_series (notebook executado, dados do protótipo, README); document/relatorio_ir_alem2.docx (2 páginas); assets/figuras/ir_alem2; vídeo: https://youtu.be/PfXksf7mLBU |

## 2. Roteiro sugerido de avaliação

Para verificar a Parte 1, abra o link do projeto no Wokwi, inicie a simulação e observe no monitor serial as linhas [BOOT] com o dimensionamento do buffer e os limites de alerta. Mova a chave deslizante para a posição desligada: as amostras passam a ser armazenadas ([OFFLINE] ... armazenada (n/3000)). Clique no DHT22 e ajuste a temperatura para 36,5 C para encerrar o alerta de hipotermia do valor padrão; pressione o botão vermelho várias vezes em sequência para gerar batimentos e, em ritmo rápido, o alerta de taquicardia com LED vermelho e buzzer; mova um eixo do MPU6050 para registrar movimento. Ao religar a chave, as amostras pendentes são enviadas em CSV com o prefixo [SYNC], em ordem cronológica, e o buffer é limpo.

Para verificar a Parte 2, abra o link do projeto da Parte 2 e inicie a simulação com a chave ligada: o monitor serial mostra a conexão à rede Wokwi-GUEST, a sincronização do relógio por NTP e a conexão ao broker, seguidas de uma publicação JSON a cada 5 s. As mensagens podem ser acompanhadas por qualquer cliente MQTT assinando cardioia/grupo55/# no broker público (por exemplo, o HiveMQ Websocket Client), ou pelo dashboard: instale o Node-RED com o Dashboard 2.0 conforme src/parte2_fog_cloud/node_red/README.md, importe flows.json, faça o deploy e abra http://localhost:1880/dashboard/paciente01. Desligue e religue a chave para ver o estado passar por offline, sincronizando e online, com as amostras atrasadas posicionadas no gráfico pelo carimbo de tempo original.

Para os desafios Ir Além, a API do Ir Além 1 sobe com uvicorn api.main:app na pasta src/ir_alem1_rest_email, o cliente simulado em python -m cliente.cliente_rest exercita os quatro cenários e os 35 testes rodam com python -m pytest; o notebook do Ir Além 2 abre no JupyterLab ou no VS Code com as saídas já gravadas e executa em menos de um minuto, e o vídeo de 3 minutos resume os resultados com legendas explicativas.

## 3. Declaração de uso responsável de dados (LGPD)

Declaro que nenhum dado pessoal real foi coletado, tratado ou armazenado nesta entrega. Todos os sinais vitais são simulados no Wokwi (sensores virtuais e interação manual), o paciente é identificado exclusivamente por um pseudônimo (paciente01, dispositivo cardioia-g55-p01) e nenhum nome, documento, data de nascimento, contato ou localização trafega nas mensagens, nos logs ou nas capturas de tela. Dados de saúde são dados pessoais sensíveis nos termos do art. 5º, inciso II, da Lei nº 13.709/2018 (LGPD); por isso o projeto aplica, desde o protótipo, as práticas que um sistema real exigiria: minimização dos campos transmitidos, pseudonimização, credenciais fora do código versionado, hierarquia de tópicos que permite controle de acesso por dispositivo, perfil de comunicação cifrada (MQTT sobre TLS) com validação de certificado prevista para produção e trilha de auditoria por carimbo de tempo e número de sequência. O broker público utilizado na demonstração não oferece autenticação nem criptografia e é inadequado para dados reais, o que está documentado no relatório da Parte 2. Nenhum artefato desta entrega é dispositivo médico nem ferramenta de monitoramento clínico; os alertas gerados têm finalidade exclusivamente acadêmica e não substituem a avaliação de um profissional de saúde.

Silvio Prestes Guerreiro Junior, RM 567958. Cuiabá, 02 de novembro de 2026.
