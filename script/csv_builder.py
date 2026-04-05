import json
import csv
import os

def get_team(participant_id):
    """Participantes 1-5 são time azul (100), 6-10 são time vermelho (200)."""
    return 100 if participant_id <= 5 else 200

def get_blue_wins(match_details):
    """Retorna 1 se o time azul (100) venceu, 0 se perdeu."""
    teams = match_details['info']['teams']
    for team in teams:
        if team['teamId'] == 100:
            return 1 if team['win'] else 0

def extract_features_from_timeline(timeline, match_id):
    """
    Recebe o JSON do timeline de uma partida e retorna
    um dicionário com as features calculadas até os 10 minutos.
    """
    frames = timeline['info']['frames']
    
    # --- INICIALIZAÇÃO DOS ACUMULADORES ---
    blue_kills = 0
    red_kills  = 0
    blue_dragons = 0
    first_blood = None  # None = ainda não aconteceu
    

    # --- LOOP PELOS FRAMES (0 a 10 minutos) ---
    for frame in frames[:11]:  # índice 0 = min 0, índice 10 = min 10
        for event in frame['events']:
            
            # Abates
            if event['type'] == 'CHAMPION_KILL':
                killer_id = event.get('killerId', 0)
                if killer_id == 0:
                    # killerId 0 = morte por minion/torre, sem first blood
                    pass
                elif get_team(killer_id) == 100:
                    blue_kills += 1
                else:
                    red_kills += 1
                
                # First blood (primeiro CHAMPION_KILL da partida)
                if first_blood is None:
                    if killer_id == 0:
                        # Morreu pra minion — first blood vai pro time da vítima oposto
                        victim_id = event.get('victimId', 0)
                        first_blood = 0 if get_team(victim_id) == 100 else 1
                    else:
                        first_blood = 1 if get_team(killer_id) == 100 else 0

            # Dragões
            if event['type'] == 'ELITE_MONSTER_KILL':
                if event.get('monsterType') == 'DRAGON':
                    killer_team = event.get('killerTeamId', 0)
                    if killer_team == 100:
                        blue_dragons += 1

    # --- SNAPSHOT DO MINUTO 10 ---
    frame_index = min(10, len(frames) - 1)
    frame_10 = frames[frame_index]['participantFrames']

    blue_gold = 0
    blue_xp   = 0
    blue_cs   = 0  # minions + jungle
    red_gold  = 0
    red_xp    = 0
    red_cs    = 0

    for pid_str, data in frame_10.items():
        pid = int(pid_str)
        gold = data['totalGold']
        xp   = data['xp']
        cs   = data['minionsKilled'] + data['jungleMinionsKilled']

        if get_team(pid) == 100:
            blue_gold += gold
            blue_xp   += xp
            blue_cs   += cs
        else:
            red_gold  += gold
            red_xp    += xp
            red_cs    += cs

    return {
        'match_id':        match_id,
        'blue_gold_diff':  blue_gold - red_gold,
        'blue_xp_diff':    blue_xp   - red_xp,
        'blue_cs_diff':    blue_cs   - red_cs,
        'blue_dragons':    min(blue_dragons, 1),  # 0 ou 1 conforme especificado
        'blue_kills':      blue_kills,
        'red_kills':       red_kills,
        'first_blood':     first_blood if first_blood is not None else 0,
    }


def save_to_csv(rows, filepath='data/matches_10min.csv'):
    """Salva a lista de dicionários num CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    fieldnames = [
    'match_id', 'blue_gold_diff', 'blue_xp_diff', 'blue_cs_diff',
    'blue_dragons', 'blue_kills', 'red_kills', 'first_blood', 'blue_wins'  # ← aqui
]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"CSV salvo em '{filepath}' com {len(rows)} partidas.")