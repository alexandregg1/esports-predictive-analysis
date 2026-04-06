# Predictive Analysis in e-Sports: LoL Win Prediction 🎮📊

Este projeto utiliza **Machine Learning** para prever o desfecho de partidas de *League of Legends* com base em dados de desempenho dos primeiros 10 minutos de jogo (*Early Game*).

> **Status do Projeto:** 🚧 Em desenvolvimento (WIP)

---

## 🚀 Objetivo

O foco é identificar o impacto real do **"efeito bola de neve"** (*snowball*) no cenário de alto nível (Challenger), respondendo se estatísticas de ouro, experiência e objetivos aos 10 minutos são preditores precisos de vitória.

---

## 🛠️ Tecnologias e Ferramentas

- **Python** – Extração de dados e integração com a Riot Games API (Match-V5 e Timeline)
- **R** – Processamento estatístico, análise exploratória (EDA) e treinamento de modelos de Machine Learning
- **SQL** – Estruturação e armazenamento temporário de dados brutos (opcional)

---

## 📂 Estrutura Atual
├── data_extraction.py # Script para coleta de dados via API
├── data_processing.R # Script (em breve) para tratamento e modelagem em R
└── /data # Repositório dos datasets gerados em CSV


---

## 📝 Próximos Passos

- [ ] Realizar a limpeza e normalização dos dados no R
- [ ] Treinar e comparar modelos de classificação (Random Forest, XGBoost)
- [ ] Documentar resultados finais e métricas de acurácia

