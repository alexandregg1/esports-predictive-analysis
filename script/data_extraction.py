# ============================================================================
# IMPORTAÇÕES E CONFIGURAÇÕES INICIAIS
# ============================================================================
from dotenv import load_dotenv
import os
import json
import requests
import time

# Carrega a chave da API do arquivo .env
load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

# Define as regioes da API da Riot
REGION    = "americas"  # Regiao para endpoints de partidas (Match v5)
PLATAFORM = "br1"       # Plataforma para endpoints de jogadores (Summoner v4)

# Headers padrao para todas as requisicoes
headers = {
    "X-Riot-Token": API_KEY
}

# Diretórios de persistência
MATCHES_DIR   = 'data/matches/'
TIMELINES_DIR = 'data/timelines/'

# ============================================================================
# FUNCOES DE INTERACAO COM A API DA RIOT
# ============================================================================

def get_chall_players():
    """
    Busca a lista completa de jogadores Challenger no servidor brasileiro.
    Retorna uma lista de dicionarios com summonerId, summonerName, etc.
    """
    url = f"https://{PLATAFORM}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    response = requests.get(url, headers=headers)
    
    # Verifica se a chave da API e valida
    if response.status_code == 403:
        raise Exception("API Key invalida ou expirada. Renove em developer.riotgames.com")
    if response.status_code != 200:
        raise Exception(f"Erro inesperado: {response.status_code} - {response.json()}")
    
    return response.json()['entries']


def get_puuid_by_summoner_id(summoner_id):
    """
    Converte o summonerId (identificador antigo) no puuid (identificador universal).
    O puuid e necessario para buscar o historico de partidas.
    """
    url = f"https://{PLATAFORM}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
    response = requests.get(url, headers=headers)
    
    # Tratamento de rate limit (limite de requisicoes por minuto)
    if response.status_code == 429:
        print("Rate limit atingido na conversao de ID! Pausando...")
        time.sleep(10)
        return get_puuid_by_summoner_id(summoner_id)
        
    return response.json()['puuid']


def get_match_ids(puuid, count=20):
    """
    Busca os IDs das ultimas 'count' partidas de um jogador especifico.
    Retorna uma lista de strings com os matchIds.
    """
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        print("Rate limit em match_ids! Pausando...")
        time.sleep(10)
        return get_match_ids(puuid, count)
        
    return response.json()


def get_match_timeline(match_id):
    """
    Busca o timeline completo de uma partida.
    Contem dados frame a frame (minuto a minuto) de gold, xp, eventos, etc.
    """
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline" 
    response = requests.get(url, headers=headers)

    if response.status_code == 429: 
        print(f"Rate limit atingido na partida {match_id}! Pausando...")
        time.sleep(10)
        return get_match_timeline(match_id)

    return response.json()


def get_match_details(match_id):
    """
    Busca os detalhes finais de uma partida.
    Contem informacoes de vencedor, campeoes escolhidos, rotas, etc.
    """
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        print(f"Rate limit em {match_id}! Pausando...")
        time.sleep(10)
        return get_match_details(match_id)
    
    return response.json()


# ============================================================================
# EXECUCAO PRINCIPAL DO PIPELINE DE EXTRACAO
# ============================================================================

# ============================================================================
# EXECUCAO PRINCIPAL DO PIPELINE DE EXTRACAO
# ============================================================================

if __name__ == "__main__":
    from csv_builder import (
        extract_raw_features, 
        build_final_row, 
        save_to_csv, 
        ChampionWinRateTracker, 
        DuoTracker
    )

    print("Iniciando extracao...")
    
    os.makedirs(MATCHES_DIR,   exist_ok=True)
    os.makedirs(TIMELINES_DIR, exist_ok=True)

    # Obtem a lista de jogadores Challenger
    challenger_list = get_chall_players()

    seen_match_ids = set()
    total_saved    = 0
    NUM_PLAYERS    = 100

    print(f"Processando {NUM_PLAYERS} jogadores Challenger...")

    for idx, player in enumerate(challenger_list[:NUM_PLAYERS]):
        # O endpoint de Challenger agora retorna diretamente o puuid
        puuid = player.get('puuid')
        
        if not puuid:
            print(f"\n[{idx+1}/{NUM_PLAYERS}] ERRO: jogador sem puuid. Chaves: {list(player.keys())}")
            continue
            
        # Nome do jogador nao vem mais no endpoint de Challenger
        # Vamos usar o proprio puuid como identificador (ou buscar o nome depois)
        print(f"\n[{idx+1}/{NUM_PLAYERS}] Processando jogador (puuid: {puuid[:20]}...)")

        try:
            # NAO PRECISA MAIS CONVERTER summonerId -> puuid
            match_ids = get_match_ids(puuid, count=50)
            time.sleep(1.2)
            
            print(f"  -> {len(match_ids)} partidas encontradas")

            for match_id in match_ids:
                if match_id in seen_match_ids:
                    continue
                seen_match_ids.add(match_id)

                match_path    = os.path.join(MATCHES_DIR,   f'{match_id}.json')
                timeline_path = os.path.join(TIMELINES_DIR, f'{match_id}_timeline.json')

                if os.path.exists(match_path) and os.path.exists(timeline_path):
                    print(f"  > Ja salvo, pulando: {match_id}")
                    continue

                print(f"  > Baixando: {match_id}")
                try:
                    details  = get_match_details(match_id)
                    time.sleep(1.2)
                    timeline = get_match_timeline(match_id)
                    time.sleep(1.2)

                    with open(match_path,    'w', encoding='utf-8') as f:
                        json.dump(details,  f)
                    with open(timeline_path, 'w', encoding='utf-8') as f:
                        json.dump(timeline, f)
                    total_saved += 1

                except Exception as e:
                    print(f"  Aviso: Erro na partida {match_id}: {e}")

        except Exception as e:
            print(f"  Erro no jogador {puuid[:20]}...: {e}")

    print(f"\nColeta finalizada! {total_saved} partidas novas salvas em disco.")
    
    # ========================================================================
    # FASE 2: PROCESSAMENTO — lê os JSONs do disco e constrói o dataset
    # Os trackers precisam ver TODAS as partidas antes de calcular features,
    # por isso a leitura acontece em duas passagens.
    # ========================================================================

    print("\nCarregando partidas do disco para os trackers...")

    match_files = sorted(f for f in os.listdir(MATCHES_DIR) if f.endswith('.json'))

    wr_tracker  = ChampionWinRateTracker()
    duo_tracker = DuoTracker(min_games_together=2)

    for fname in match_files:
        with open(os.path.join(MATCHES_DIR, fname), encoding='utf-8') as f:
            details = json.load(f)
        wr_tracker.update_from_match(details)
        duo_tracker.update_from_match(details)

    print(f"Trackers populados com {len(match_files)} partidas.")
    print("\nGerando features e construindo dataset...")

    rows    = []
    skipped = 0

    for fname in match_files:
        match_id      = fname.replace('.json', '')
        timeline_path = os.path.join(TIMELINES_DIR, f'{match_id}_timeline.json')

        if not os.path.exists(timeline_path):
            print(f"  [AVISO] Timeline ausente para {match_id}, pulando.")
            skipped += 1
            continue

        try:
            with open(os.path.join(MATCHES_DIR, fname), encoding='utf-8') as f:
                details = json.load(f)
            with open(timeline_path, encoding='utf-8') as f:
                timeline = json.load(f)

            raw_features = extract_raw_features(timeline, details, match_id)
            row          = build_final_row(raw_features, details, wr_tracker, duo_tracker)
            rows.append(row)

        except Exception as e:
            print(f"  Aviso: Erro ao processar {match_id}: {e}")

    # ========================================================================
    # FASE 3: SALVAMENTO
    # ========================================================================

    if rows:
        save_to_csv(rows)
        print(f"\nDataset salvo com {len(rows)} partidas. ({skipped} puladas)")
    else:
        print("Erro: nenhuma partida processada com sucesso.")