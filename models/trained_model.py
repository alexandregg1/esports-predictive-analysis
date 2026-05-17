# Importação das Bibliotecas
# %%
import joblib
import pandas as pd

# %% 
# Carregar o modelo
modelo = joblib.load('modelo_lol_xgboost.pkl')

# Features de uma nova partida (10 min)
nova_partida = {
    # Básicas
    'gold_diff': -12200,
    'xp_diff': -1500,
    'cs_diff': -1500,
    'kills_diff': -20,
    'gold_diff_top': -3300,
    'xp_diff_top': -4000,
    'cs_diff_top': -45,
    'gold_diff_jungle': -1220,
    'xp_diff_jungle': -1100,
    'cs_diff_jungle': -21,
    'gold_diff_mid': -4030,
    'xp_diff_mid': -3400,
    'cs_diff_mid': -100,
    'gold_diff_adc': -3250,
    'xp_diff_adc': -1530,
    'cs_diff_adc': -80,
    'gold_diff_support': -2100,
    'xp_diff_support': -502,
    'cs_diff_support': -50,
    'blue_dragons': 1,
    'red_dragons': 4,
    'blue_voidgrubs': 1,
    'red_voidgrubs': 3,
    'first_blood': 0,
    'blue_avg_champion_wr': 0.48,
    'red_avg_champion_wr': 0.52,
    'synergy_diff': 0.01,
    'blue_has_duo': 0,
    'red_has_duo': 2,
    'blue_duo_impact': -0.15,
    'red_duo_impact': 0.30,
    'duo_impact_diff': 0.20   
}

# %%
def prever_partida(dados_partida, caminho_modelo='modelo_lol_xgboost.pkl'):
    modelo = joblib.load(caminho_modelo)
    
    # --- Recalcular TODAS as derivadas que o modelo espera ---
    dados_partida['dragon_diff'] = dados_partida['blue_dragons'] - dados_partida['red_dragons']
    dados_partida['voidgrubs_diff'] = dados_partida['blue_voidgrubs'] - dados_partida['red_voidgrubs']
    dados_partida['gold_sum_lanes'] = (
        dados_partida['gold_diff_top'] + dados_partida['gold_diff_jungle'] +
        dados_partida['gold_diff_mid'] + dados_partida['gold_diff_adc'] + dados_partida['gold_diff_support']
    )
    # duo_impact_diff já existe, mas recalculei por segurança
    dados_partida['duo_impact_diff'] = dados_partida['blue_duo_impact'] - dados_partida['red_duo_impact']
    
    
    
    # --- DataFrame na ordem do modelo ---
    X = pd.DataFrame([dados_partida])
    X = X[modelo.feature_names_in_]
    
    # Previsão
    prob = modelo.predict_proba(X)[0]
    pred = modelo.predict(X)[0]
    
    print("\n--- PREVISÃO DA PARTIDA ---")
    print(f"Probabilidade Azul vencer:   {prob[1]*100:.1f}%")
    print(f"Probabilidade Vermelho vencer: {prob[0]*100:.1f}%")
    print(f"Confiança do modelo:          {max(prob)*100:.1f}%")
    print(f"\n>>> Resultado previsto: {'TIME AZUL VENCE' if pred == 1 else 'TIME VERMELHO VENCE'} <<<\n")
    
    return {
        'previsao': 'Azul vence' if pred == 1 else 'Vermelho vence',
        'probabilidade_azul': float(prob[1]),
        'confianca': float(max(prob))
    }

# Resultado após definição de parametros e recalculos pelas funções
resultado = prever_partida(nova_partida)
