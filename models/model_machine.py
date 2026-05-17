# %%
import pandas as pd
from sklearn.metrics import accuracy_score
import xgboost as xgb
import joblib

# %%
# 1. Carregar o CSV processado pelo R
df = pd.read_csv('../data/matches_processed.csv')
#%%
# 2. Criar target
df['target'] = df['resultado'].map({'Azul vence': 1, 'Vermelho vence': 0})
#%%
# 3. Remover colunas que não são features
colunas_remover = ['match_id', 'resultado', 'blue_wins', 'red_wins', 'gold_advantage']
df.drop(columns=colunas_remover, inplace=True, errors='ignore')
#%%
# 4. Separar X e Y
feature_cols = [col for col in df.columns if col != 'target']
X = df[feature_cols]
y = df['target']
#%%
# 5. Split temporal
n = len(df)
X_train, y_train = X.iloc[:int(n*0.7)], y.iloc[:int(n*0.7)]
X_val, y_val     = X.iloc[int(n*0.7):int(n*0.85)], y.iloc[int(n*0.7):int(n*0.85)]
X_test, y_test   = X.iloc[int(n*0.85):], y.iloc[int(n*0.85):]
#%%
# 6. Modelo (parâmetros que já funcionaram)
modelo = xgb.XGBClassifier(
    n_estimators=300, max_depth=4, learning_rate=0.03,
    subsample=0.7, colsample_bytree=0.7,
    min_child_weight=5, gamma=0.2, reg_alpha=0.5, reg_lambda=1.0,
    random_state=42, eval_metric='logloss',
    early_stopping_rounds=20
)
modelo.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
#%%
# 7. Avaliação rápida
y_pred_test = modelo.predict(X_test)
print("Acurácia Teste:", accuracy_score(y_test, y_pred_test))
#%%
# 8. Salvar modelo novo
joblib.dump(modelo, 'modelo_lol_xgboost.pkl')
# %%
