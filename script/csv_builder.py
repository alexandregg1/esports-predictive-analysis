import json
import csv
import os
from collections import defaultdict

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def get_team(participant_id):
    """Participantes 1-5 são time azul (100), 6-10 são time vermelho (200)."""
    return 100 if participant_id <= 5 else 200

def get_blue_wins(match_details):
    """Retorna 1 se o time azul (100) venceu, 0 se perdeu."""
    teams = match_details['info']['teams']
    for team in teams:
        if team['teamId'] == 100:
            return 1 if team['win'] else 0
    return 0

def get_lane_from_participant(participant):
    """Mapeia teamPosition para lane padronizada."""
    position = participant.get('teamPosition', '')
    lane_mapping = {
        'TOP': 'top',
        'JUNGLE': 'jungle',
        'MIDDLE': 'mid',
        'BOTTOM': 'adc',
        'UTILITY': 'support'
    }
    return lane_mapping.get(position, 'unknown')

# ============================================================================
# PILAR 1: EXTRAÇÃO DE FEATURES BRUTAS (COM DIFFS POR ROTA)
# ============================================================================

def extract_raw_features(timeline, match_details, match_id):
    """
    Extrai todas as features brutas do timeline e match_details.
    Retorna dicionário com métricas por time e por rota.
    """
    frames = timeline['info']['frames']
    
    # --- Inicialização de acumuladores por time ---
    blue = {
        'kills': 0, 'towers': 0, 'dragons': 0, 'voidgrubs': 0,
        'plates': 0, 'gold': 0, 'xp': 0, 'cs': 0
    }
    red = {
        'kills': 0, 'towers': 0, 'dragons': 0, 'voidgrubs': 0,
        'plates': 0, 'gold': 0, 'xp': 0, 'cs': 0
    }
    
    # --- Inicialização por rota (gold, xp e cs) ---
    lanes = ['top', 'jungle', 'mid', 'adc', 'support']
    blue_lanes = {lane: {'gold': 0, 'xp': 0, 'cs': 0} for lane in lanes}
    red_lanes = {lane: {'gold': 0, 'xp': 0, 'cs': 0} for lane in lanes}
    
    first_blood = None
    
    # --- Mapeamento participant_id -> lane (obtido do match_details) ---
    pid_to_lane = {}
    for p in match_details['info']['participants']:
        pid_to_lane[p['participantId']] = get_lane_from_participant(p)
    
    # --- Loop pelos frames (0 a 10 minutos) ---
    for frame in frames[:11]:  # índice 0 = min 0, índice 10 = min 10
        for event in frame['events']:
            
            # --- Kills e First Blood ---
            if event['type'] == 'CHAMPION_KILL':
                killer_id = event.get('killerId', 0)
                victim_id = event.get('victimId', 0)
                
                if killer_id != 0:
                    if get_team(killer_id) == 100:
                        blue['kills'] += 1
                    else:
                        red['kills'] += 1
                
                if first_blood is None:
                    if killer_id == 0:
                        first_blood = 0 if get_team(victim_id) == 100 else 1
                    else:
                        first_blood = 1 if get_team(killer_id) == 100 else 0
            
            # --- Dragões e Vastilarvas ---
            elif event['type'] == 'ELITE_MONSTER_KILL':
                monster_type = event.get('monsterType')
                killer_team = event.get('killerTeamId', 0)
                
                if monster_type == 'DRAGON' and killer_team == 100:
                    blue['dragons'] += 1
                elif monster_type == 'DRAGON' and killer_team == 200:
                    red['dragons'] += 1
                elif monster_type == 'HORDE' and killer_team == 100:
                    blue['voidgrubs'] += 1
                elif monster_type == 'HORDE' and killer_team == 200:
                    red['voidgrubs'] += 1
            
            # --- Torres ---
            elif event['type'] == 'BUILDING_KILL':
                if event.get('buildingType') == 'TOWER_BUILDING':
                    tower_owner_team = event.get('teamId', 0)
                    
                    if tower_owner_team == 200:  # Torre vermelha destruída
                        blue['towers'] += 1
                    elif tower_owner_team == 100:  # Torre azul destruída
                        red['towers'] += 1
            
            # --- Placas (Turret Plates) ---
            elif event['type'] == 'TURRET_PLATE_DESTROYED':
                killer_team = event.get('killerTeamId', 0)
                if killer_team == 100:
                    blue['plates'] += 1
                elif killer_team == 200:
                    red['plates'] += 1
    
    # --- Snapshot do minuto 10 (gold, xp, cs por rota) ---
    frame_index = min(10, len(frames) - 1)
    frame_10 = frames[frame_index]['participantFrames']
    
    for pid_str, data in frame_10.items():
        pid = int(pid_str)
        team = get_team(pid)
        lane = pid_to_lane.get(pid, 'unknown')
        
        gold = data['totalGold']
        xp = data['xp']
        cs = data['minionsKilled'] + data['jungleMinionsKilled']
        
        if team == 100:
            blue['gold'] += gold
            blue['xp'] += xp
            blue['cs'] += cs
            if lane in blue_lanes:
                blue_lanes[lane]['gold'] += gold
                blue_lanes[lane]['xp'] += xp
                blue_lanes[lane]['cs'] += cs
        else:
            red['gold'] += gold
            red['xp'] += xp
            red['cs'] += cs
            if lane in red_lanes:
                red_lanes[lane]['gold'] += gold
                red_lanes[lane]['xp'] += xp
                red_lanes[lane]['cs'] += cs
    
    return {
        'match_id': match_id,
        'blue': blue,
        'red': red,
        'blue_lanes': blue_lanes,
        'red_lanes': red_lanes,
        'first_blood': first_blood if first_blood is not None else 0
    }

# ============================================================================
# PILAR 2: SINERGIAS (WIN RATE POR CAMPEÃO E ROTA)
# ============================================================================

class ChampionWinRateTracker:
    """Rastreia win rates por campeão e por campeão+rota."""
    
    def __init__(self):
        self.champion_games = defaultdict(int)
        self.champion_wins = defaultdict(int)
        self.champion_lane_games = defaultdict(int)
        self.champion_lane_wins = defaultdict(int)
    
    def update_from_match(self, match_details):
        """Atualiza estatísticas com uma partida."""
        blue_won = get_blue_wins(match_details)
        
        for p in match_details['info']['participants']:
            champion = p['championName']
            lane = get_lane_from_participant(p)
            team = get_team(p['participantId'])
            won = (team == 100 and blue_won == 1) or (team == 200 and blue_won == 0)
            
            self.champion_games[champion] += 1
            if won:
                self.champion_wins[champion] += 1
            
            key = f"{champion}_{lane}"
            self.champion_lane_games[key] += 1
            if won:
                self.champion_lane_wins[key] += 1
    
    def get_champion_winrate(self, champion, min_games=5):
        """Win rate global do campeão."""
        games = self.champion_games[champion]
        if games < min_games:
            return 0.5
        return self.champion_wins[champion] / games
    
    def get_champion_lane_winrate(self, champion, lane, min_games=5):
        """Win rate do campeão em uma rota específica."""
        key = f"{champion}_{lane}"
        games = self.champion_lane_games[key]
        if games < min_games:
            return 0.5
        return self.champion_lane_wins[key] / games
    
    def calculate_team_synergy(self, match_details, min_games=5):
        """Calcula win rate média do draft de cada time."""
        blue_wr_sum = 0
        red_wr_sum = 0
        blue_count = 0
        red_count = 0
        
        for p in match_details['info']['participants']:
            champion = p['championName']
            lane = get_lane_from_participant(p)
            team = get_team(p['participantId'])
            
            wr = self.get_champion_lane_winrate(champion, lane, min_games)
            
            if team == 100:
                blue_wr_sum += wr
                blue_count += 1
            else:
                red_wr_sum += wr
                red_count += 1
        
        return {
            'blue_avg_champion_wr': blue_wr_sum / blue_count if blue_count > 0 else 0.5,
            'red_avg_champion_wr': red_wr_sum / red_count if red_count > 0 else 0.5
        }

# ============================================================================
# PILAR 4: DUOS (COM CÁLCULO DE IMPACTO)
# ============================================================================

class DuoTracker:
    """Rastreia pares de jogadores que jogam juntos frequentemente."""
    
    def __init__(self, min_games_together=2):
        self.min_games_together = min_games_together
        self.pair_games = defaultdict(int)
        self.pair_wins = defaultdict(int)
        self.player_games = defaultdict(int)
        self.player_wins = defaultdict(int)
    
    def update_from_match(self, match_details):
        """Atualiza estatísticas de duos com uma partida."""
        blue_won = get_blue_wins(match_details)
        
        # Agrupa puuids por time
        blue_puuids = []
        red_puuids = []
        
        for p in match_details['info']['participants']:
            puuid = p['puuid']
            team = get_team(p['participantId'])
            won = (team == 100 and blue_won == 1) or (team == 200 and blue_won == 0)
            
            self.player_games[puuid] += 1
            if won:
                self.player_wins[puuid] += 1
            
            if team == 100:
                blue_puuids.append(puuid)
            else:
                red_puuids.append(puuid)
        
        # Atualiza pares dentro de cada time
        self._update_pairs(blue_puuids, blue_won == 1)
        self._update_pairs(red_puuids, blue_won == 0)
    
    def _update_pairs(self, puuids, team_won):
        """Atualiza estatísticas para todos os pares em um time."""
        for i in range(len(puuids)):
            for j in range(i + 1, len(puuids)):
                pair = tuple(sorted([puuids[i], puuids[j]]))
                self.pair_games[pair] += 1
                if team_won:
                    self.pair_wins[pair] += 1
    
    def is_duo(self, puuid1, puuid2):
        """Verifica se dois jogadores formam um duo (jogaram juntos >= min_games)."""
        pair = tuple(sorted([puuid1, puuid2]))
        return self.pair_games[pair] >= self.min_games_together
    
    def get_duo_impact(self, puuid1, puuid2):
        """
        Calcula o impacto real do duo:
        (win rate juntos) - (média das win rates individuais)
        """
        pair = tuple(sorted([puuid1, puuid2]))
        games_together = self.pair_games[pair]
        
        if games_together < self.min_games_together:
            return 0.0
        
        duo_wr = self.pair_wins[pair] / games_together
        
        # Win rate média individual
        solo_wr1 = self.player_wins[puuid1] / max(self.player_games[puuid1], 1)
        solo_wr2 = self.player_wins[puuid2] / max(self.player_games[puuid2], 1)
        avg_solo_wr = (solo_wr1 + solo_wr2) / 2
        
        return duo_wr - avg_solo_wr
    
    def analyze_team_duos(self, match_details):
        """Analisa duos presentes em cada time e calcula impacto médio."""
        blue_puuids = []
        red_puuids = []
        
        for p in match_details['info']['participants']:
            puuid = p['puuid']
            team = get_team(p['participantId'])
            
            if team == 100:
                blue_puuids.append(puuid)
            else:
                red_puuids.append(puuid)
        
        blue_duos = self._count_team_duos(blue_puuids)
        red_duos = self._count_team_duos(red_puuids)
        
        return {
            'blue_has_duo': 1 if blue_duos['count'] > 0 else 0,
            'red_has_duo': 1 if red_duos['count'] > 0 else 0,
            'blue_duo_impact': blue_duos['avg_impact'],
            'red_duo_impact': red_duos['avg_impact']
        }
    
    def _count_team_duos(self, puuids):
        """Conta duos em um time e calcula impacto médio."""
        duo_count = 0
        impacts = []
        
        for i in range(len(puuids)):
            for j in range(i + 1, len(puuids)):
                if self.is_duo(puuids[i], puuids[j]):
                    duo_count += 1
                    impact = self.get_duo_impact(puuids[i], puuids[j])
                    impacts.append(impact)
        
        avg_impact = sum(impacts) / len(impacts) if impacts else 0.0
        
        return {
            'count': duo_count,
            'avg_impact': avg_impact
        }

# ============================================================================
# CONSTRUÇÃO DO DATASET FINAL (4 PILARES)
# ============================================================================

def build_final_row(raw_features, match_details, wr_tracker, duo_tracker):
    """
    Constrói a linha final do dataset combinando os 4 pilares.
    """
    blue = raw_features['blue']
    red = raw_features['red']
    blue_lanes = raw_features['blue_lanes']
    red_lanes = raw_features['red_lanes']
    
    # Pilar 1: Diffs (globais e por rota)
    row = {
        'match_id': raw_features['match_id'],
        
        # Diffs globais
        'gold_diff': blue['gold'] - red['gold'],
        'xp_diff': blue['xp'] - red['xp'],
        'cs_diff': blue['cs'] - red['cs'],
        'kills_diff': blue['kills'] - red['kills'],
        'tower_diff': blue['towers'] - red['towers'],
        
        # Diffs por rota (gold e xp)
        'gold_diff_top':     blue_lanes['top']['gold']     - red_lanes['top']['gold'],
        'xp_diff_top':       blue_lanes['top']['xp']       - red_lanes['top']['xp'],
        'cs_diff_top':       blue_lanes['top']['cs']        - red_lanes['top']['cs'],

        'gold_diff_jungle':  blue_lanes['jungle']['gold']  - red_lanes['jungle']['gold'],
        'xp_diff_jungle':    blue_lanes['jungle']['xp']    - red_lanes['jungle']['xp'],
        'cs_diff_jungle':    blue_lanes['jungle']['cs']     - red_lanes['jungle']['cs'],

        'gold_diff_mid':     blue_lanes['mid']['gold']     - red_lanes['mid']['gold'],
        'xp_diff_mid':       blue_lanes['mid']['xp']       - red_lanes['mid']['xp'],
        'cs_diff_mid':       blue_lanes['mid']['cs']        - red_lanes['mid']['cs'],

        'gold_diff_adc':     blue_lanes['adc']['gold']     - red_lanes['adc']['gold'],
        'xp_diff_adc':       blue_lanes['adc']['xp']       - red_lanes['adc']['xp'],
        'cs_diff_adc':       blue_lanes['adc']['cs']        - red_lanes['adc']['cs'],

        'gold_diff_support': blue_lanes['support']['gold'] - red_lanes['support']['gold'],
        'xp_diff_support':   blue_lanes['support']['xp']   - red_lanes['support']['xp'],
        'cs_diff_support':   blue_lanes['support']['cs']    - red_lanes['support']['cs'],

        # Pilar 3: Objetivos
        'blue_dragons':  min(blue['dragons'], 1),
        'red_dragons':   min(red['dragons'], 1),
        'blue_voidgrubs': blue['voidgrubs'],
        'red_voidgrubs':  red['voidgrubs'],
        'blue_plates': blue['plates'],
        'red_plates': red['plates'],
        'plates_diff': blue['plates'] - red['plates'],
        'first_blood': raw_features['first_blood'],
    }
    
    # Pilar 2: Sinergias (win rates do draft)
    synergy = wr_tracker.calculate_team_synergy(match_details)
    row['blue_avg_champion_wr'] = synergy['blue_avg_champion_wr']
    row['red_avg_champion_wr'] = synergy['red_avg_champion_wr']
    row['synergy_diff'] = synergy['blue_avg_champion_wr'] - synergy['red_avg_champion_wr']
    
    # Pilar 4: Duos
    duos = duo_tracker.analyze_team_duos(match_details)
    row['blue_has_duo'] = duos['blue_has_duo']
    row['red_has_duo'] = duos['red_has_duo']
    row['blue_duo_impact'] = duos['blue_duo_impact']
    row['red_duo_impact'] = duos['red_duo_impact']
    row['duo_impact_diff'] = duos['blue_duo_impact'] - duos['red_duo_impact']
    
    # Target
    row['blue_wins'] = get_blue_wins(match_details)
    
    return row

# ============================================================================
# FUNÇÃO PRINCIPAL DE SAVE (MANTIDA)
# ============================================================================

def save_to_csv(rows, filepath='data/matches_10min.csv'):
    """Salva a lista de dicionários num CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    if not rows:
        print("Nenhuma linha para salvar.")
        return
    
    fieldnames = list(rows[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"CSV salvo em '{filepath}' com {len(rows)} partidas.")