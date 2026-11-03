# Ir Além 2: IA em séries temporais de saúde

Projeto CardioIA, Fase 3, Grupo 55. Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR.

Notebook Python que compara um classificador tradicional (regressão logística) com uma rede neuromórfica simples (codificação por taxa e neurônios LIF, implementada em NumPy) na classificação de episódios de risco em séries temporais de frequência cardíaca com o mesmo formato produzido pelo wearable das Partes 1 e 2 (uma amostra a cada 5 s, com indicador de movimento). A regra de limiares do firmware (acima de 120 bpm, abaixo de 50 bpm) entra como linha de base.

## Estrutura

```
src/ir_alem2_ia_series/
├── cardioia_fase3_ir_alem2_series_lif.ipynb   # notebook comentado e executado (saidas gravadas)
├── dados/
│   ├── prototipo_parte1_2026-10-30.csv        # serie real do prototipo (log da Parte 1, 53 amostras)
│   └── prototipo_parte2_2026-10-30.csv        # serie real do prototipo (log da Parte 2, 23 amostras)
├── requirements.txt
└── README.md
```

As figuras geradas pelo notebook ficam em `assets/figuras/ir_alem2/` (exemplos de episódios, matrizes de confusão, raster e potencial de membrana da rede LIF, janelas do protótipo). Os CSVs de `dados/` são extraídos dos logs do monitor serial em `assets/evidencias/` por `scripts/extrair_series_prototipo.py`.

## O que o notebook faz

1. Carrega a série real do protótipo e descreve o formato dos dados.
2. Gera 1.200 episódios sintéticos de 2 minutos (24 amostras) em cinco subtipos documentados: repouso normal, atividade física (frequência alta com movimento, fisiológica), taquicardia em repouso, bradicardia e arritmia com média normal (ritmo irregular). O rótulo vem do subtipo, não dos limiares, para que os casos em que a regra fixa erra sejam medidos.
3. Extrai 12 características por janela (média, desvio, mínimo, máximo, percentis, inclinação, RMSSD das diferenças sucessivas, frações acima de 120 e abaixo de 50 bpm, fração com movimento, média em repouso) e divide em treino (840) e teste (360), estratificado.
4. Avalia a regra de limiares do firmware como linha de base.
5. Treina a regressão logística (scikit-learn, padronização e validação cruzada de 5 dobras) e lê os coeficientes.
6. Implementa a rede neuromórfica: codificação por taxa com 6 campos receptivos gaussianos por característica (72 neurônios de entrada, trens de Poisson em 100 passos de 1 ms), dois neurônios LIF de saída (normal e risco) e regra delta supervisionada sobre as contagens de disparos; mede acurácia em 5 repetições da codificação estocástica.
7. Compara os métodos: acurácia, precisão, sensibilidade, F1, matrizes de confusão, acerto por subtipo, custo computacional (operações por janela, tempo de treino e de inferência) e latência de decisão da rede LIF (decisão antecipada quando um neurônio lidera por dois disparos).
8. Aplica os três métodos às janelas da série real do protótipo (repouso a 80 bpm e trechos a 150 bpm).

## Resultados (conjunto de teste, 360 janelas)

| Método | Acurácia | Precisão | Sensibilidade | F1 | Inferência por janela |
|---|---|---|---|---|---|
| Regra de limiares (firmware) | 0,897 | 0,842 | 0,978 | 0,905 | desprezível |
| Regressão logística | 1,000 | 1,000 | 1,000 | 1,000 | cerca de 1 microssegundo |
| Rede LIF (NumPy) | 0,983 (0,986 mais ou menos 0,006 em 5 repetições) | 0,989 | 0,978 | 0,983 | cerca de 0,3 ms (simulação de 100 passos) |

A regra erra por construção na atividade física (falso alerta, 43% de acerto nesse subtipo) e na arritmia com média normal (94%); a regressão logística corrige os dois casos, e a rede LIF corrige a atividade física (96% de acerto) mas mantém o mesmo acerto da regra na arritmia (94%). A rede LIF decide antes do fim da janela em mediana 19 ms de 100 ms simulados, com acurácia 0,992 na decisão antecipada, mas custa ordens de grandeza mais por janela em CPU convencional, como discute o capítulo 3 do curso sobre redes impulsionais em arquitetura Von Neumann. Os números vêm de dados sintéticos e devem ser lidos como demonstração de método, não como desempenho clínico.

## Como executar

```bash
cd src/ir_alem2_ia_series
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab cardioia_fase3_ir_alem2_series_lif.ipynb   # ou: jupyter nbconvert --to notebook --execute cardioia_fase3_ir_alem2_series_lif.ipynb
```

O notebook executa em menos de um minuto em um computador comum (sementes fixas; a rede LIF treina 12 épocas em cerca de 3 s no computador do aluno, com Apple Silicon, e levou 17 s no ambiente de trabalho da primeira execução; os tempos variam com o processador, as métricas não). As figuras são gravadas em `assets/figuras/ir_alem2/` quando a pasta do repositório é detectada; caso contrário, apenas exibidas.

## Entregáveis do Ir Além 2

Notebook comentado (este diretório), repositório público (este repositório), relatório comparativo de duas páginas em `document/relatorio_ir_alem2.docx` e vídeo de até 4 minutos com os resultados, publicado como não listado no YouTube e linkado no README principal. O vídeo foi gravado com a execução de 31/10 no ambiente de trabalho (treino da rede LIF em 17 s e inferência em 1,2 ms por janela); a execução gravada neste notebook, no computador do aluno, tem as mesmas métricas e tempos menores (3 s e 0,3 ms).
