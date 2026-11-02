# CardioIA, Fase 3, Ir Além 2: IA em séries temporais de saúde, regressão logística e rede neuromórfica LIF

| Campo | Valor |
|---|---|
| Aluno | Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55 (individual) |
| Curso, fase, tutor e coordenador | Inteligência Artificial, Ano 2, Fase 3 (Ir Além 2); Leonardo Ruiz Orabona; André Godoi Chiovato |
| Data e código | 31 de outubro de 2026; notebook em src/ir_alem2_ia_series do repositório FIAP_2TIAOR_2026_Ano2_Fase3 |

## 1. Objetivo e dados

O wearable das Partes 1 e 2 produz uma série de frequência cardíaca a cada 5 s, com indicador de movimento, e decide alertas por limiares fixos (acima de 120 bpm, abaixo de 50 bpm). Este estudo pergunta o que um classificador aprendido acrescenta a esses limiares e compara, sobre janelas de 2 minutos (24 amostras), um classificador tradicional, a regressão logística, com uma rede neuromórfica simples formada por codificação por taxa e neurônios LIF (leaky integrate-and-fire), o modelo de neurônio que o capítulo 3 do curso descreve nos chips TrueNorth e Loihi. A regra do firmware é a linha de base.

Os dados de treino são sintéticos e documentados no notebook: 1.200 episódios balanceados em cinco subtipos com parâmetros sorteados em faixas plausíveis. Dois subtipos foram desenhados para expor as falhas da regra fixa: atividade física (frequência de 100 a 135 bpm com movimento, fisiológica, que a regra transforma em falso alerta) e arritmia com média normal (ritmo irregular, com diferenças sucessivas de 12 a 28 bpm, que a regra não vê). Os outros são repouso normal, taquicardia em repouso e bradicardia. O rótulo vem do subtipo, não dos limiares. Cada janela gera 12 características (média, desvio, mínimo, máximo, percentis 10 e 90, inclinação, RMSSD das diferenças sucessivas, frações acima de 120 e abaixo de 50 bpm, fração com movimento e média em repouso); a divisão estratificada separa 840 janelas de treino e 360 de teste. A escolha por dados sintéticos decorre da ausência de base pública com esse passo de amostragem e rótulos de episódio, e do tratamento de dados reais de saúde exigir base legal e anonimização pela LGPD. A série real do protótipo (76 amostras extraídas dos logs do Wokwi) serve para demonstrar a inferência de ponta a ponta.

## 2. Modelos

A regressão logística usa padronização e validação cruzada de cinco dobras (scikit-learn); seus coeficientes padronizados tornam a decisão legível: a fração abaixo de 50 bpm (3,19), o RMSSD (2,33), a média em repouso (1,37) e o máximo (1,14) empurram para risco; a fração com movimento (menos 2,23) e o mínimo (menos 1,30) empurram para normal, ou seja, o modelo aprendeu que frequência alta com movimento é atividade, não risco.

A rede neuromórfica, implementada em NumPy, codifica cada característica em seis campos receptivos gaussianos (72 neurônios de entrada) que emitem trens de Poisson durante 100 passos de 1 ms; dois neurônios LIF de saída (normal e risco) integram a corrente sináptica com vazamento, disparam ao cruzar o limiar e entram em período refratário. O aprendizado é uma regra delta supervisionada sobre a contagem de disparos de cada saída, em 12 épocas (17 s de treino na máquina de teste). A decisão é do neurônio que mais dispara; uma variante antecipada decide assim que um neurônio lidera por dois disparos.

## 3. Resultados

Tabela 1. Métricas no conjunto de teste (360 janelas) e tempo de inferência por janela na máquina de teste (2 núcleos).

| Método | Acurácia | Precisão | Sensibilidade | F1 | Inferência |
|---|---|---|---|---|---|
| Regra de limiares (firmware) | 0,897 | 0,842 | 0,978 | 0,905 | desprezível |
| Regressão logística | 1,000 | 1,000 | 1,000 | 1,000 | 5 microssegundos |
| Rede LIF | 0,983 | 0,989 | 0,978 | 0,983 | 1,2 ms (100 passos) |

A regra acerta apenas 43% das janelas de atividade física e 94% das de arritmia; os dois classificadores corrigem a atividade por completo e a rede LIF mantém 94% na arritmia, com acurácia média de 0,986 (desvio 0,006) em cinco repetições da codificação estocástica. A validação cruzada da regressão logística dá 0,996 (desvio 0,003), e o acerto perfeito no teste reflete a separabilidade dos dados sintéticos, não desempenho clínico. A rede LIF processa em média 847 eventos sinápticos por janela contra 12 produtos da regressão, e sua decisão antecipada ocorre em mediana aos 19 ms dos 100 ms simulados (percentil 90 em 42 ms), com acurácia 0,992. Aplicados às janelas reais do protótipo, os três métodos concordam: repouso a 80 bpm classificado como normal (probabilidade de risco 0,002) e os trechos a 150 bpm como risco (0,998 e 0,999).

## 4. Discussão

Os classificadores superam a regra exatamente onde ela falha por construção, e a regressão logística o faz com dezenas de operações por janela, o que cabe no ESP32 e na API da Fase 6. A rede LIF alcança desempenho da mesma ordem, oferece leitura indireta pelos pesos por campo receptivo e evidência visível nos disparos, e decide antes do fim da janela, mas simulada em CPU custa ordens de grandeza mais, o que confirma a observação do capítulo 3 (e do estudo de Freitas et al., 2023, ali citado) de que redes impulsionais em arquitetura Von Neumann não rendem ganho energético: suas vantagens, processamento esparso e consumo proporcional à atividade, só se realizam em hardware orientado a eventos, como um coprocessador neuromórfico em um wearable a bateria. Limitações: dados sintéticos com cinco subtipos; rede de uma camada com regra local simplificada (gradiente substituto, como no snnTorch, alcançaria mais); codificação por taxa que descarta a ordem temporal fina; série real curta.

## 5. Conclusão

Para o CardioIA, a recomendação é adotar a regressão logística, ou modelo igualmente leve, no dispositivo e na API, mantendo os limiares fixos como rede de segurança, e reservar as redes impulsionais para um futuro coprocessador neuromórfico. O notebook, os dados e as figuras estão no repositório; o vídeo com os resultados está linkado no README principal.
