# Checklist de auditoria contra os critérios de avaliação

Projeto CardioIA, Fase 3, Grupo 55. Auditoria executada em 31/10/2026 sobre os arquivos de `03_entrega` (varredura por script de travessões, emojis fora dos cabeçalhos do modelo FIAP e padrões de credenciais; contagem de páginas dos DOCX após conversão para PDF; leitura dos logs de evidência). Atualizada em 31/10/2026 (madrugada, horário de Cuiabá) após o salvamento dos projetos no Wokwi e a execução de ponta a ponta com o Node-RED no computador do aluno. Itens pendentes dependem de ações externas (publicação no GitHub, upload) e devem ser refeitos antes do envio.

## 1. Critérios oficiais (10 pontos)

| Critério | Pontos | Status | Evidência |
|---|---|---|---|
| Leitura de sensores | 2 | atendido | Três sensores (DHT22, botão de batimentos com interrupção, MPU6050) lidos a cada 5 s em `src/parte1_edge/wokwi/sketch.ino` e `src/parte2_fog_cloud/esp32_mqtt/sketch.ino`; log da Parte 1 com temperatura de 24,0 e 36,5 C, 80 e 150 bpm e `mov=sim`; SPIFFS implementado sob flag (não pontuado) |
| Implementação de resiliência offline (Edge Computing) | 2 | atendido | Buffer circular de 3.000 amostras com sobrescrita e contador de descartes, camada SPIFFS opcional, chave de conectividade simulada, sincronização em ordem cronológica e limpeza do buffer; log com 41 amostras armazenadas e `[SYNC] concluida: 41 enviadas, buffer limpo`; alertas locais (LED e buzzer) durante o período offline; dimensionamento numérico no relatório da Parte 1 |
| Envio via MQTT e integração com broker | 2 | atendido | PubSubClient, Wi-Fi Wokwi-GUEST, NTP, três tópicos, JSON, retidos, testamento, reconexão; executado no Wokwi contra `broker.hivemq.com` em 30/10/2026 e confirmado por assinante independente (HiveMQ Websocket Client), incluindo nove amostras sincronizadas com origem `sync`; perfil HiveMQ Cloud com TLS pronto em `config.example.h` (não executado) |
| Dashboard funcional e alertas automáticos | 2 | atendido | `flows.json` importa sem erro e funciona com Node-RED 4.1.17 e Dashboard 2.0 1.34.1: gráficos de bpm e temperatura, três medidores, painel de alerta com cor, notificação, tabela e estado; executado no computador do aluno com o ESP32 do Wokwi publicando no broker público em 30/10/2026 (capturas `p2_10` a `p2_15`: normal, alerta de taquicardia, febre e ausência de movimento, offline, pós-sincronização, editor e debug; logs `log_node_red_mac_2026-10-30.txt` e `log_serial_parte2_wokwi_2026-10-30_nodered_mac.txt`) |
| Documentação clara (código e relatórios) | 2 | atendido | Código com cabeçalho, seção única de configuração, comentários em português e log por prefixos; `document/relatorio_parte1.docx` (8 páginas) e `document/relatorio_parte2.docx` (18 páginas) com figuras legendadas, evidências e referências; README com matriz de rastreabilidade; README do Node-RED |

## 2. Verificações obrigatórias

| Verificação | Status | Evidência |
|---|---|---|
| Parte 1: link do projeto no Wokwi funcionando | atendido | https://wokwi.com/projects/479362553804308481 (público, salvo na conta do aluno em 30/10/2026; simulação iniciada após o salvamento e `[ONLINE]` observado no monitor serial); link no README, no relatório e no documento de entrega |
| Parte 1: código C++ comentado que compila | atendido | Compilado e executado pelo Wokwi (web) em 30/10/2026 |
| Parte 1: relatório com uma página ou mais, fluxo de funcionamento e lógica de resiliência | atendido | 8 páginas; seções 3 (fluxo, diagrama de blocos e máquina de estados) e 4 (resiliência) |
| Parte 1: evidências do monitor serial (coleta offline, retorno da conexão, sincronização) | atendido | `assets/evidencias/parte1/log_serial_parte1_wokwi_2026-10-30.txt` e capturas `p1_01` a `p1_04` |
| Parte 1: justificativa numérica da capacidade do buffer | atendido | Tabela 2 do relatório da Parte 1: 5 s, 16 bytes, 3.000 amostras, 48 KB, 4 h 10 min, heap medido, SPIFFS com cerca de 35 mil amostras |
| Parte 2: link do projeto no Wokwi | atendido | https://wokwi.com/projects/479362979389911041 (público; recarregado após o salvamento com `sketch.ino`, `diagram.json` e `libraries.txt` íntegros; simulação conectou ao broker em 5 s) |
| Parte 2: código do ESP32 com MQTT | atendido | `src/parte2_fog_cloud/esp32_mqtt/sketch.ino`, `config.example.h`, `.gitignore` com `config.h` |
| Parte 2: `flows.json` importando sem erros | atendido | Importado e executado no Node-RED 4.1.17 em 30/10/2026 |
| Parte 2: prints do dashboard (normal e em alerta), do editor, do debug e do broker | atendido | Broker: `p2_01` a `p2_03` (HiveMQ Websocket Client). Dashboard normal `p2_10`, em alerta `p2_11`, offline `p2_12`, após sincronização `p2_13`, editor `p2_14` e debug `p2_15`, todos com o ESP32 real publicando; as capturas de validação com simulador foram retiradas da entrega (movidas para `_to_delete/`) |
| Parte 2: relatório com duas páginas ou mais, fluxo MQTT e configuração do dashboard | atendido | 18 páginas; seções 2 (MQTT), 3 (Node-RED) e 4 (evidências, incluindo a execução de ponta a ponta) |
| Parte 2: seção de eficiência, segurança e boas práticas em IoT médico | atendido | Seção 5 do relatório da Parte 2 (minimização, pseudonimização, LGPD, credenciais, controle de acesso por tópico, TLS, taxa, energia) |
| Matriz de rastreabilidade com os cinco critérios | atendido | README, seção "Matriz de rastreabilidade" |
| Identificação correta (aluno, RM, turma, grupo, tutor da Fase 3, coordenação) | atendido | Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55, tutor Leonardo Ruiz Orabona (confirmado por Silvio em 30/10/2026), coordenador André Godoi Chiovato, em README, relatórios e documento de entrega |
| Documento de entrega em DOCX (capa, links, resumo, declaração LGPD) | atendido | `document/documento_entrega.docx` com os links do GitHub e dos dois projetos do Wokwi; situação do Ir Além 2 a confirmar antes do envio |
| Nenhum arquivo com credenciais | atendido | Varredura por padrões de senha, e-mail, CPF e telefone: apenas os placeholders de `config.example.h`; `config.h` ausente; nó de broker do `flows.json` sem usuário e senha; o material do curso (com credenciais de terceiros) fica fora do repositório |
| Nenhum travessão nem emoji fora dos cabeçalhos do modelo FIAP | atendido | 0 ocorrências em .md, .ino, .py, .js, .json, .txt, .h, .toml, .ini e .mmd (os emojis do README são os cabeçalhos do modelo de repositório da FIAP, mantidos como na Fase 2) |
| Repositório público com README completo, `.gitignore`, licença e `.github` | pendente | Arquivos prontos em `03_entrega`; publicação conforme `document/roteiro_entrega.md` |
| Ir Além 1 e 2 (se feitos) com todos os entregáveis | Ir Além 1 e Ir Além 2 atendidos | Ir Além 1: código Python (`src/ir_alem1_rest_email`: cliente REST, módulo de risco, e-mail automatizado simulado, 35 testes aprovados), relatório `document/relatorio_ir_alem1.docx` (2 páginas), evidências em `assets/evidencias/ir_alem1/`. Ir Além 2: notebook executado (`src/ir_alem2_ia_series`), README e `requirements.txt` do módulo, relatório `document/relatorio_ir_alem2.docx` (2 páginas), figuras em `assets/figuras/ir_alem2/`, vídeo de 3 min 02 s com legendas explicativas gerado em 31/10/2026 (pasta de trabalho `video_ir_alem2/`, fora do repositório, publicado no YouTube como não listado em 02/11/2026: https://youtu.be/PfXksf7mLBU, linkado no README e no documento de entrega); tabelas de critérios no README |
| Arquivo de upload no formato exigido pela plataforma | pendente | Formato a conferir na tela de envio; conteúdo mínimo listado no roteiro |

## 3. Pendências para fechar a entrega

1. Projetos salvos no Wokwi em 30/10/2026 e links inseridos no README, nos relatórios e no documento de entrega (concluído).
2. Capturas do dashboard, do editor e do debug com o ESP32 real feitas em 30/10/2026 no computador do aluno; capturas de validação retiradas (concluído).
3. Ir Além 1 concluído em 31/10/2026. Ir Além 2 concluído em 31/10/2026 (notebook, relatório, README, vídeo com legendas); vídeo publicado no YouTube como não listado em 02/11/2026 e link inserido no README e no documento de entrega.
4. Publicar o repositório conforme `document/roteiro_entrega.md` e testar em janela anônima.
5. Preparar o arquivo de upload, conferir os links e enviar no portal com folga em relação ao prazo de 04/11/2026.
6. Repetir esta auditoria após as alterações finais.
