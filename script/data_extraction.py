from dotenv import load_dotenv
import os

import requests
import time

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

REGION = "americas" 
PLATAFORM = "br1"

headers = {
    "X-Riot-Token": API_KEY
}

def get_chall_players(): 
    """Busca a lista de jogadores challenger para ter os ID's"""
    url = f"https://{PLATAFORM}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403:
        raise Exception("API Key inválida ou expirada. Renove em developer.riotgames.com")
    if response.status_code != 200:
        raise Exception(f"Erro inesperado: {response.status_code} - {response.json()}")
    
    return response.json()['entries']

def get_puuid_by_summoner_id(summoner_id):
    """
    Função PONTE: Converte o summonerId (da liga Challenger) 
    no puuid (necessário para buscar o histórico de partidas).
    """
    url = f"https://{PLATAFORM}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        print("Rate limit atingido na conversão de ID! Pausando...")
        time.sleep(10)
        return get_puuid_by_summoner_id(summoner_id)
        
    return response.json()['puuid']

def get_match_ids(puuid, count=20):
    """Busca os ultimos X ids de partidas de um jogador especifico."""
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_match_timeline(match_id):
    """..."""
    url =f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline" 
    response = requests.get(url, headers=headers)

    # A verificação do erro 429 entra AQUI, dentro da função
    if response.status_code == 429: 
        print(f"Rate limit atingido na partida {match_id}! Pausando...")
        time.sleep(10)
        return get_match_timeline(match_id)

    return response.json()

def get_match_details(match_id):
    """Busca o resultado final da partida."""
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        print(f"Rate limit em {match_id}! Pausando...")
        time.sleep(10)
        return get_match_details(match_id)
    
    return response.json()

# --- EXECUÇÃO DO PIPELINE ---

if __name__ == "__main__":
    from csv_builder import extract_features_from_timeline, save_to_csv, get_blue_wins

    print("Iniciando extração...")
    challenger_list = get_chall_players()
    
    rows = []  # ← acumula os dados de todas as partidas

    for player in challenger_list[:50]:  # ← limita para 50 jogadores
        puuid = player['puuid']
        match_ids = get_match_ids(puuid, count=20) 
        time.sleep(1.2)

        for match_id in match_ids:
            print(f"  > Processando: {match_id}")
            timeline = get_match_timeline(match_id)
            time.sleep(1.2)
            
            details = get_match_details(match_id)
            time.sleep(1.2)
            
            row = extract_features_from_timeline(timeline, match_id)
            row['blue_wins'] = get_blue_wins(details)  # ← nova feature
            rows.append(row)

    save_to_csv(rows)  # ← salva tudo no final
    print("Extração finalizada!")