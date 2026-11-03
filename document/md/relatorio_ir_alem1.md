# CardioIA, Fase 3, Ir Além 1: comunicação automatizada com REST e e-mail

| Campo | Valor |
|---|---|
| Aluno | Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55 (individual) |
| Curso, fase, tutor e coordenador | Inteligência Artificial, Ano 2, Fase 3 (Ir Além 1); Leonardo Ruiz Orabona; André Godoi Chiovato |
| Data e código | 31 de outubro de 2026; pasta src/ir_alem1_rest_email do repositório FIAP_2TIAOR_2026_Ano2_Fase3 |

## 1. Objetivo e fluxo implementado

O desafio pede um sistema que consuma e envie sinais vitais por uma API REST em Python, verifique riscos e acione uma automação de e-mail em caso de alerta, aplicando os conceitos de RPA do capítulo 2 do curso (REST e e-mail como motores de processos). A solução estende as Partes 1 e 2: o mesmo JSON que o ESP32 publica via MQTT é aceito, sem conversão, por uma API FastAPI, que se torna o ponto de automação da plataforma CardioIA.

O fluxo tem quatro passos. Uma amostra chega por POST /sinais, vinda do cliente REST que simula o wearable (cliente/cliente_rest.py), da ponte MQTT que assina o tópico do ESP32 (cliente/ponte_mqtt_api.py) ou do Node-RED, por um nó http request em uma aba de integração (node_red/flows_integracao_api.json). A API valida o payload com Pydantic, determina o instante efetivo da amostra (carimbo NTP ou hora de chegada), atualiza o último movimento do paciente e aplica as regras de risco. Havendo alerta, a automação monta o e-mail e o envia ou simula, respeitando uma política anti-spam. A amostra é armazenada com a avaliação e consultada em GET /sinais, GET /sinais/ultimo, GET /alertas, GET /pacientes/{disp}/resumo e GET /notificacoes; a documentação OpenAPI fica em /docs.

## 2. Lógica de verificação de risco

As regras ficam em api/risco.py como funções puras, uma por condição, com os mesmos limites do firmware e do Node-RED (Tabela 1), parametrizáveis por variáveis de ambiente. A função avaliar() aplica todas as regras e acrescenta os alertas que o dispositivo já sinalizou na máscara de bits, de modo que a decisão tomada na borda nunca se perde na nuvem. A ausência de movimento é avaliada pelo histórico do paciente (instante do último movimento conhecido) e só dispara depois de existir ao menos um movimento registrado, evitando falso alerta no início. Uma regra de supervisão adicional, sem_dados, sinaliza no resumo do paciente quando o dispositivo está em silêncio há mais de 5 minutos, o que cobre a falha do próprio sensor ou do enlace. A suíte de testes (tests/, 35 casos aprovados) verifica cada limite nas fronteiras exatas (120 e 121 bpm, 50 e 49 bpm, 38,0 e 38,1 C, 35,0 e 34,9 C, 600 e 601 s), a combinação de alertas, a máscara do dispositivo sem duplicatas, a política anti-spam e os endpoints de ponta a ponta.

Tabela 1. Regras de risco e limites.

| Regra | Condição | Gravidade |
|---|---|---|
| taquicardia | bpm acima de 120 | alta |
| bradicardia | bpm entre 1 e 49 (zero é ausência de leitura) | alta |
| febre | temperatura acima de 38,0 C | média |
| hipotermia | temperatura abaixo de 35,0 C | alta |
| sem_movimento | mais de 600 s desde o último movimento | alta |
| sem_dados | nenhuma amostra há mais de 300 s (resumo do paciente) | média |

## 3. Automação de e-mail

O módulo api/notificacao.py monta a mensagem com a biblioteca padrão (email.message): assunto com gravidade e tipos de alerta; corpo com o pseudônimo do paciente, instante, sequência, descrição de cada alerta, sinais da amostra e aviso de uso acadêmico. Três modos são escolhidos no .env: simulado (padrão), que registra a mensagem completa em logs/emails_simulados.log sem nada sair pela rede; local, que entrega a um servidor SMTP de depuração na própria máquina (aiosmtpd); e smtp, que envia por um servidor real com STARTTLS e autenticação, com credenciais lidas apenas do .env. A política anti-spam não repete o mesmo tipo de alerta para o mesmo paciente antes de 10 minutos, mas deixa passar imediatamente um tipo novo, como um sistema de alarme clínico que evita a fadiga de alarmes sem atrasar informação nova. Falhas de rede ou de autenticação não derrubam a API: o registro fica como não entregue em GET /notificacoes.

## 4. Evidências e resultados

A execução de 31/10/2026 está documentada em assets/evidencias/ir_alem1. O cliente REST enviou 151 amostras em quatro cenários encadeados (repouso, taquicardia, febre e imobilidade); a API detectou 20 amostras com alerta e disparou exatamente três e-mails, um por tipo novo (taquicardia na amostra 8, febre na 17 e ausência de movimento na 142, após 605 s sem movimento), suprimindo as repetições pelo intervalo mínimo; as consultas devolveram as 151 amostras, os 20 alertas, o resumo com o alerta ativo e os três e-mails. A ponte MQTT, com um broker local e o simulador de mensagens no formato exato do firmware, encaminhou 16 amostras e produziu os e-mails de taquicardia e febre; a mesma sequência passou pelo Node-RED, cujo nó http request recebeu as respostas 201 da API com os alertas (captura ia1_01). Os 35 testes automatizados passaram.

Limitações declaradas: a validação usou o cliente simulado, o simulador MQTT e um broker local, porque o ambiente de trabalho não alcança o broker público (com o ESP32 no Wokwi basta apontar a ponte ou o Node-RED para broker.hivemq.com); o envio real por SMTP não foi executado, para não depender de credenciais.

## 5. Conclusão

O Ir Além 1 fecha a automação do monitoramento: o sinal captado na borda, transmitido pela nuvem e exibido na névoa passa a gerar uma ação automática, o e-mail para a equipe clínica, com regras explícitas, testadas e parametrizáveis, dados simulados e credenciais fora do código. A API é o ponto de entrada das próximas fases, que consumirão o histórico por GET /sinais (previsão de crises na Fase 6, assistente na Fase 5).
