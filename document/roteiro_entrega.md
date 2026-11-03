# Roteiro de entrega: publicação do repositório e envio no portal

Projeto CardioIA, Fase 3, Grupo 55. Repositório: `FIAP_2TIAOR_2026_Ano2_Fase3`, conta GitHub `silvioguerreiro`. Pasta local que espelha o repositório: `Fase 3/03_entrega`. Prazo: 04/11/2026 (horário de Brasília; Cuiabá tem uma hora a menos).

## 1. Antes de publicar

| Verificação | Como fazer |
|---|---|
| Links do Wokwi | Feito em 30/10/2026: Parte 1 em https://wokwi.com/projects/479362553804308481 e Parte 2 em https://wokwi.com/projects/479362979389911041, inseridos no README, nos relatórios e no documento de entrega. Antes de publicar, abrir os dois links em janela anônima e confirmar que a simulação inicia |
| Evidências do Node-RED com o ESP32 real | Feito em 30/10/2026 com o Node-RED instalado em `~/cardioia-nodered` no Mac: capturas `p2_10` a `p2_15` e logs em `assets/evidencias/parte2/`; relatório da Parte 2 atualizado (Figuras 3 a 5, 7 e 8 e seção 4.2). As capturas de validação com simulador foram movidas para `Fase 3/_to_delete/evidencias_parte2_TESTE/` e não entram no repositório |
| Vídeo do Ir Além 2 | Publicado no YouTube como não listado em 02/11/2026 (https://youtu.be/PfXksf7mLBU) e linkado no README (tabela de links, tabela Ir Além e critérios) e no documento de entrega |
| Credenciais | Nenhum `config.h` na pasta; `config.example.h` apenas com placeholders; nenhuma senha em `flows.json` (o nó de broker não tem usuário nem senha) |
| Auditoria | Conferir `document/checklist_rubrica.md`; todos os itens de repositório atendidos |
| Pastas de material do curso e de trabalho | Ficam fora do repositório (material do curso com credenciais de terceiros e arquivos de trabalho); só `03_entrega` é versionada |

## 2. Regenerar os relatórios depois de inserir os links

Na pasta `03_entrega` (requer Node.js e o pacote `docx`: `cd config && npm install`, ou `npm install docx` na raiz):

```bash
node scripts/md_para_docx.js document/md/relatorio_parte1.md document/relatorio_parte1.docx "CardioIA, Fase 3, Parte 1: Edge Computing"
node scripts/md_para_docx.js document/md/relatorio_parte2.md document/relatorio_parte2.docx "CardioIA, Fase 3, Parte 2: Fog e Cloud Computing"
node scripts/md_para_docx.js document/md/documento_entrega.md document/documento_entrega.docx "CardioIA, Fase 3: Documento de entrega"
```

Alternativa sem Node.js: pedir a KARDIA que regenere os três arquivos após os links serem informados no chat.

## 3. Inicialização do repositório local

Executar no Terminal, a partir da pasta `03_entrega`. Observação importante desta fase: o OneDrive e o Cowork podem criar um lock órfão em `.git/index.lock`; por isso todos os comandos usam `--no-optional-locks`, e, se algum comando falhar com "index.lock exists", basta remover o arquivo `.git/index.lock` e repetir.

```bash
git --no-optional-locks init -b main
git --no-optional-locks config user.name "Silvio Prestes Guerreiro Junior"
git --no-optional-locks config user.email "<e-mail da conta GitHub>"
git --no-optional-locks status      # conferir que config.h, node_modules e .DS_Store nao aparecem
```

## 4. Commits por módulo

```bash
git --no-optional-locks add .gitignore .gitattributes .github/problem-report.md LICENSE assets/logo-fiap.png config/
git --no-optional-locks commit -m "Estrutura inicial do repositorio da Fase 3 (modelo FIAP)"

git --no-optional-locks add src/parte1_edge/
git --no-optional-locks commit -m "Parte 1: firmware Edge com sensores, alertas locais e buffer de resiliencia offline"

git --no-optional-locks add assets/evidencias/parte1/
git --no-optional-locks commit -m "Parte 1: evidencias de execucao no Wokwi (log serial e capturas)"

git --no-optional-locks add src/parte2_fog_cloud/esp32_mqtt/
git --no-optional-locks commit -m "Parte 2: firmware MQTT com Wi-Fi, NTP, topicos, testamento e sincronizacao do buffer"

git --no-optional-locks add src/parte2_fog_cloud/node_red/ scripts/gerar_flows_node_red.py scripts/simulador_mqtt_esp32.js scripts/captura_editor_node_red_mac.js
git --no-optional-locks commit -m "Parte 2: fluxo Node-RED com Dashboard 2.0, gerador, simulador de mensagens e captura do editor"

git --no-optional-locks add assets/evidencias/parte2/
git --no-optional-locks commit -m "Parte 2: evidencias MQTT (serial e broker) e capturas do dashboard com o ESP32 real"

git --no-optional-locks add src/ir_alem1_rest_email/ scripts/gerar_flow_integracao_api.py scripts/captura_integracao_api_playwright.js assets/evidencias/ir_alem1/
git --no-optional-locks commit -m "Ir Alem 1: API REST em Python com verificacao de risco, e-mail automatizado, cliente, ponte MQTT e testes"

git --no-optional-locks add src/ir_alem2_ia_series/ scripts/extrair_series_prototipo.py assets/figuras/ir_alem2/
git --no-optional-locks commit -m "Ir Alem 2: notebook comparativo (regressao logistica e rede LIF) sobre series de frequencia cardiaca"

git --no-optional-locks add assets/figuras/ scripts/desenhar_figuras_relatorios.py scripts/fig_p2_sequencia_mqtt.mmd scripts/md_para_docx.js document/
git --no-optional-locks commit -m "Documentacao: relatorios das Partes 1 e 2 e dos Ir Alem, documento de entrega, checklist e roteiro"

git --no-optional-locks add README.md
git --no-optional-locks commit -m "README com identificacao, links e matriz de rastreabilidade"
```

## 5. Publicação no GitHub

1. No GitHub, criar o repositório `FIAP_2TIAOR_2026_Ano2_Fase3` como **público**, sem README, sem .gitignore e sem licença (os arquivos já existem localmente).
2. Conectar e enviar:

```bash
git --no-optional-locks remote add origin https://github.com/silvioguerreiro/FIAP_2TIAOR_2026_Ano2_Fase3.git
git --no-optional-locks push -u origin main
```

3. Conferir, em uma janela anônima do navegador, que `https://github.com/silvioguerreiro/FIAP_2TIAOR_2026_Ano2_Fase3` abre sem login, que o README é renderizado com o logo, as figuras e as capturas, que os links do Wokwi abrem e iniciam a simulação, e que os DOCX podem ser baixados.

## 6. Ajustes finais e commit de fechamento

Depois de qualquer alteração (links, evidências reais do Node-RED):

```bash
git --no-optional-locks add -A
git --no-optional-locks commit -m "Ajustes finais da entrega da Fase 3"
git --no-optional-locks push
```

Repetir a auditoria de `document/checklist_rubrica.md` após o push.

## 7. Arquivo de upload na plataforma

O formato exigido deve ser conferido na própria tela de envio da atividade (PDF, .txt ou .zip). O arquivo foi preparado fora do repositório, na pasta de trabalho `04_upload/`: `CardioIA_Fase3_Grupo55_RM567958_entrega_completa.pdf` reúne o documento de entrega (identificação, links clicáveis do repositório, dos projetos no Wokwi e do vídeo, resumo, roteiro de avaliação e declaração LGPD) e os quatro relatórios (Parte 1, Parte 2, Ir Além 1 e Ir Além 2), em 33 páginas; `CardioIA_Fase3_Grupo55_RM567958_documento_entrega.pdf` é a versão curta, só com o documento de entrega. Se a plataforma exigir .zip, compactar o PDF escolhido. Abrir o arquivo final e testar cada link antes de enviar. Não é possível substituir o arquivo depois do fechamento da entrega ou da correção.

## 8. Recomendações expressas da FIAP nas fases anteriores

| Recomendação | Providência |
|---|---|
| Verificar se o arquivo do upload está correto; não é possível enviar outro após o fechamento | Conferir o arquivo aberto, com os links testados, antes do envio |
| Não deixar a entrega para os últimos minutos do prazo; entregas apenas pela plataforma | Publicar o repositório em 03/11 e fazer o upload na manhã de 04/11 |
| Não compartilhar a resposta em grupos de mensagens (plágio pode zerar a atividade) | Não divulgar links nem arquivos da entrega em grupos |
| Período de 15 dias após a publicação da nota para solicitar revisão | Anotar a data de publicação da nota |
