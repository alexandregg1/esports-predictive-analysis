# Predictive Analysis in e-Sports: LoL Win Prediction 🎮📊

Este projeto utiliza **Machine Learning** para prever o desfecho de partidas de *League of Legends* com base em dados de desempenho dos primeiros 10 minutos de jogo (*Early Game*).

> **Status do Projeto:** ✅ Concluído – modelo operacional com acurácia de ~89%

---

## 🚀 Objetivo

O foco é identificar o impacto real do **"efeito bola de neve"** (*snowball*) no cenário de alto nível (Challenger), respondendo se estatísticas de ouro, experiência e objetivos aos 10 minutos são preditores precisos de vitória.  
Com base em dados da API oficial da Riot Games, foi construído um modelo de classificação capaz de antecipar o vencedor com alta confiabilidade, mesmo em cenários de desvantagem extrema.

---

## 🛠️ Tecnologias e Ferramentas

| Etapa | Tecnologia | Descrição |
|-------|------------|-----------|
| Extração de dados | Python (RiotWatcher) | Coleta de partidas Challenger via Riot API (Match-V5) |
| Tratamento e feature engineering | R (tidyverse, janitor) | Limpeza, remoção de outliers, criação de variáveis derivadas |
| Modelagem | Python (XGBoost, scikit-learn) | Treinamento do classificador, regularização e avaliação |
| Visualização | Matriz de confusão, importância de features, curva de gold_diff |

---

## 📂 Estrutura do Projeto
├── data/
│   ├── matches_10min.csv          # Dados brutos extraídos (10 min)
│   └── matches_processed.csv      # Dados tratados e enriquecidos
├── scripts/
│   ├── data_extraction.py         # Coleta de dados via Riot API
│   ├── data_processing.Rmd        # Limpeza e feature engineering (R)
│   └── csv_builder.py             # Cria dataset usado no modelo
├── models/
│   ├── model_machine.py           # Treinamento, avaliação e previsão
│   ├── trained_model.py           # Script para testes com modelo treinado
│   └── modelo_lol_xgboost.pkl     # Modelo XGBoost salvo
└── README.md

---

## 📊 Pipeline de Dados

### 1. Extração
O script `data_extraction.py` consulta a Riot API e repassa para o script `csv_builder` que gera o arquivo `matches_10min.csv` com estatísticas dos 10 minutos iniciais de partidas Challenger (temporada 2026).

### 2. Tratamento (R)
O script `data_processing.Rmd` realiza:
- Padronização de nomes com `janitor::clean_names()`
- Remoção de colunas sem variância (`blue_plates`, `red_plates`, `plates_diff`, `tower_diff`)
- Remoção de **252 linhas corrompidas** (gold_diff fisicamente impossível)
- Criação da variável alvo `resultado` ("Azul vence" / "Vermelho vence")
- Criação de features derivadas:
  - `dragon_diff` e `voidgrubs_diff` (controle de objetivos)
  - `gold_sum_lanes` (soma do ouro por rota)
  - Recalcula `duo_impact_diff` para consistência numérica
- Verificação de duplicatas e integridade
- Exportação de `matches_processed.csv`

### 3. Modelagem (Python)
O script `model_machine.py` executa:
- Carregamento do CSV processado
- Remoção de colunas não preditivas (`match_id`, `blue_wins`, `red_wins`, `gold_advantage`)
- Criação do target binário (0 = Vermelho vence, 1 = Azul vence)
- **Split temporal** (70% treino, 15% validação, 15% teste)
- Treinamento com **XGBoost** e regularização:
  ```python
  XGBClassifier(
      n_estimators=300, max_depth=4, learning_rate=0.03,
      subsample=0.7, colsample_bytree=0.7,
      min_child_weight=5, gamma=0.2, reg_alpha=0.5, reg_lambda=1.0,
      early_stopping_rounds=20
  )

* Avaliação no conjunto de teste

* Salvamento do modelo em models/modelo_lol_xgboost.pkl

## 📈 Resultados
Métricas de classificação
Conjunto	Acurácia
Treino	90.3%
Validação	86.1%
Teste	89.1%

---

## Conclusão 

### O early-game é altamente preditivo
O modelo de Machine Learning conseguiu atingir 89% de acurácia usando apenas os dados dos primeiros 10 minutos de jogo. Isso confirma que, no cenário brasileiro de mais  alto nivel o Challenger, o desempenho inicial no começo das partidas tem um peso decisivo pro resultado final da partida, com o efeito de snowball (bola de neve) sendo real e possivel de mensurar.

### As features mais importantes 
| Features | Significado | Impacto |
|-------|------------|-----------|
| gold_diff | Diferença de ouro Total | Quanto maior a vantagem de ouro do time azul, maior a probabilidade de vitória |
| gold_sum_lanes | Soma de ouro nas 5 rotas | Reforça a importância da vantagem econômica distribuída |
| dragon_diff | Diferença de dragões abatidos | Dragões conferem bónus permanentes e indicam controle do rio, que resulta em um controle do mapa |
| voidgrubs_diff | Diferença de vastilarvas(voidgrubs) abatidos | Afeta a pressão nas torres e o ritmo de jogo |
| kills_diff | Diferença de abates | Abates geram ouro e experiência, alimentando o snowball |

Interpretação:

* Ouro > Objetivos > Abates – a vantagem económica é o fator isolado mais forte, mas o controle de dragões e voidgrubs mostra-se quase tão relevante.

* Um time que chega aos 10 minutos com vantagem de ouro e controle de objetivos tem uma probabilidade de vitória muito superior.

### O modelo é confiável e generalizável 
* O gap entre treino e teste é pequno (1.8 pontos percentuais), indicando que o modelo não sofre com overfitting.
* Em cenários extremos (ex: desvantagem de 8k de ouro), a confiança da previsão atinge > 99%, mostrando coerencia  com a realidade do jogo.
* A validação com partidas reais do dataset confirmou que o modelo capturou corretamente a relação entre as variáveis.

### Limitações e possivéis atualizações
* O modelo foi treinado com dados de um patch específico do game (2026 S2). Mudanças no meta podem exigir um re-treino.
* A inclusão de informações como composição de campeões (ex: winrate individual e sinergias) ou dados de visão poderiam aumentar ainda mais a acurácia.
* Uma análise de drift ao longo dos patches ajudaria a determinar a frequência ideal de atualizações do modelo.

### Resumo
O projeto demonstra que é possivel prever com alta precisão o desfecho de uma partida de LoL usando apenas estatísticas iniciais. O modelo desenvolvido server como base para análises mais aprofundadas ou para construção de ferramentas de apoio à decisão em cenários competitvos como o CBLOL (Campeonato Brasileiro de League of Legends). 
