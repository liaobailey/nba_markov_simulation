import pandas as pd
import duckdb
from typing import Dict, List, Any

def get_baseline_data(conn, team: str, season: str) -> Dict[str, Any]:
    """Get baseline data from database"""
    # Get transition counts
    transitions_query = """
    SELECT state, next_state, count 
    FROM agg_team_txn_cnts 
    WHERE team = ? AND season = ?
    ORDER BY count DESC
    """
    transitions = conn.execute(transitions_query, [team, season]).fetchdf()
    
    # Get transition metrics from the rates table
    rates_query = """
    SELECT * FROM team_transition_matrix_adjustments_rates 
    WHERE season = ?
    """
    rates = conn.execute(rates_query, [season]).fetchdf()
    
    # Get team metrics
    metrics_query = """
    with cte_box as (
    select season, team_abbreviation, fga-fg3a as fg2a, fgm-fg3m as fg2m, fg2m/fg2a as fg2_pct, fg3a, fg3m, fg3_pct, fta, ftm, ft_pct, dreb, oreb, tov
    from fact_team_season_box ftsb
    join dim_team dt on ftsb.team_id = dt.team_id
    ),
    cte_opp_box as (
    select season, team_abbreviation, opp_fga-opp_fg3a as opp_fg2a, opp_fgm-opp_fg3m as opp_fg2m, opp_fg2m/opp_fg2a as opp_fg2_pct, opp_fg3a, opp_fg3m, opp_fg3_pct, opp_fta, opp_ftm, opp_ft_pct, opp_dreb, opp_oreb, opp_tov
    from fact_team_season_opponent_box ftsob
    join dim_team dt on ftsob.team_id = dt.team_id
    ),
    cte_ff as (
    select ftsff.season, team_abbreviation, ftsff.oreb_pct, ftsff.tm_tov_pct, 1-opp_oreb_pct as dreb_pct, opp_oreb_pct, opp_tov_pct, 1-ftsff.oreb_pct as opp_dreb_pct, poss
    from fact_team_season_four_factor ftsff
    join dim_team dt on dt.team_id = ftsff.team_id
    join fact_team_season_advanced ftsa on ftsff.team_id = ftsa.team_id and ftsff.season = ftsa.season
    )
    select cb.*
        , cob.* EXCLUDE (team_abbreviation, season)
        , cf.* EXCLUDE (team_abbreviation, season)
    from cte_box cb
    left join cte_opp_box cob on cb.season = cob.season and cb.team_abbreviation = cob.team_abbreviation
    left join cte_ff cf on cb.season = cf.season and cb.team_abbreviation = cb.team_abbreviation
    where cb.season = ?
    """
    
    metrics = conn.execute(metrics_query, [season]).fetchdf()
    
    if not metrics.empty:
        team_metrics = {
            'fg2_pct': metrics.iloc[0].get('fg2_pct', 0.54),
            'fg3_pct': metrics.iloc[0].get('fg3_pct', 0.36), 
            'ft_pct': metrics.iloc[0].get('ft_pct', 0.78),
            'oreb_pct': metrics.iloc[0].get('oreb_pct', 0.28),
            'dreb_pct': metrics.iloc[0].get('dreb_pct', 0.72),
            'tov_pct': metrics.iloc[0].get('tm_tov_pct', 0.14),
            'opp_fg2_pct': metrics.iloc[0].get('opp_fg2_pct', 0.54),
            'opp_fg3_pct': metrics.iloc[0].get('opp_fg3_pct', 0.36),
            'opp_ft_pct': metrics.iloc[0].get('opp_ft_pct', 0.78),
            'opp_oreb_pct': metrics.iloc[0].get('opp_oreb_pct', 0.28),
            'opp_dreb_pct': metrics.iloc[0].get('opp_dreb_pct', 0.72),
            'opp_tov_pct': metrics.iloc[0].get('opp_tov_pct', 0.14)
        }
        
        team_attempts = {
            'fg2_attempts': int(metrics.iloc[0].get('fg2a', 2000)),
            'fg3_attempts': int(metrics.iloc[0].get('fg3a', 900)),
            'ft_attempts': int(metrics.iloc[0].get('fta', 800)),
            'turnovers': int(metrics.iloc[0].get('tov', 300)),
            'dreb_attempts': int(metrics.iloc[0].get('dreb', 1200)),
            'oreb_attempts': int(metrics.iloc[0].get('oreb', 400))
        }
    else:
        team_metrics = {
            'fg2_pct': 0.54, 'fg3_pct': 0.36, 'ft_pct': 0.78,
            'oreb_pct': 0.28, 'dreb_pct': 0.72, 'tov_pct': 0.14,
            'opp_fg2_pct': 0.54, 'opp_fg3_pct': 0.36, 'opp_ft_pct': 0.78,
            'opp_oreb_pct': 0.28, 'opp_dreb_pct': 0.72, 'opp_tov_pct': 0.14
        }
        team_attempts = {
            'fg2_attempts': 2000, 'fg3_attempts': 900, 'ft_attempts': 800,
            'turnovers': 300, 'dreb_attempts': 1200, 'oreb_attempts': 400
        }
    
    # Convert rates DataFrame to dictionary for transition_metrics
    if not rates.empty:
        transition_metrics = rates.iloc[0].to_dict()
    else:
        transition_metrics = {
            'per_2pt_made_from_oreb': 0.13,
            'per_2pt_made_from_offense_start_tov': 0.87,
            'per_3pt_made_from_oreb': 0.05,
            'per_3pt_made_from_offense_start_tov': 0.95,
            'per_ft_made_from_oreb': 0.02,
            'per_ft_made_from_offense_start': 0.98,
            'per_ft_made_from_ft_made': 0.0
        }
    
    return {
        'transitions': transitions,
        'rates': rates,
        'metrics': team_metrics,
        'team_attempts': team_attempts,
        'transition_metrics': transition_metrics
    }

def calculate_improved_metrics(team_metrics: Dict[str, float], improvement_factor: float) -> Dict[str, float]:
    """Calculate improvements for all metrics"""
    improved_metrics = {}
    
    # Team metrics: increase by improvement factor
    improved_metrics['fg2_pct'] = team_metrics['fg2_pct'] * improvement_factor
    improved_metrics['fg3_pct'] = team_metrics['fg3_pct'] * improvement_factor
    improved_metrics['ft_pct'] = team_metrics['ft_pct'] * improvement_factor
    improved_metrics['oreb_pct'] = team_metrics['oreb_pct'] * improvement_factor
    improved_metrics['dreb_pct'] = team_metrics['dreb_pct'] * improvement_factor
    improved_metrics['tov_pct'] = team_metrics['tov_pct'] * (2 - improvement_factor)  # Decrease TOV%
    
    # Opponent metrics: decrease by improvement factor
    improved_metrics['opp_fg2_pct'] = team_metrics['opp_fg2_pct'] * (2 - improvement_factor)
    improved_metrics['opp_fg3_pct'] = team_metrics['opp_fg3_pct'] * (2 - improvement_factor)
    improved_metrics['opp_ft_pct'] = team_metrics['opp_ft_pct'] * (2 - improvement_factor)
    improved_metrics['opp_oreb_pct'] = team_metrics['opp_oreb_pct'] * (2 - improvement_factor)
    improved_metrics['opp_dreb_pct'] = team_metrics['opp_dreb_pct'] * (2 - improvement_factor)
    improved_metrics['opp_tov_pct'] = team_metrics['opp_tov_pct'] * improvement_factor  # Increase opp TOV%
    
    return improved_metrics

def calculate_additional_variables(team_metrics: Dict[str, float], improved_metrics: Dict[str, float], team_attempts: Dict[str, int]) -> Dict[str, float]:
    """Calculate additional variables using existing formulas"""
    def get_additional(adjusted_value: float, original_value: float, formula: callable) -> float:
        if abs(adjusted_value - original_value) < 0.0001:
            return 0.0
        return formula()
    
    original = {
        'fg2a': team_attempts['fg2_attempts'],
        'fg2m': team_attempts['fg2_attempts'] * team_metrics['fg2_pct'],
        'FG3A': team_attempts['fg3_attempts'],
        'FGM3': team_attempts['fg3_attempts'] * team_metrics['fg3_pct'],
        'FTA': team_attempts['ft_attempts'],
        'FTM': team_attempts['ft_attempts'] * team_metrics['ft_pct'],
        'POSS': team_attempts['fg2_attempts'] + team_attempts['fg3_attempts'] + team_attempts['turnovers'],
        'TOV': team_attempts['turnovers'],
        'DREB': team_attempts['dreb_attempts'],
        'OREB': team_attempts['oreb_attempts'],
        'opp_fg2a': team_attempts['fg2_attempts'],
        'opp_fg2m': team_attempts['fg2_attempts'] * team_metrics['opp_fg2_pct'],
        'OPP_FG3A': team_attempts['fg3_attempts'],
        'OPP_FGM3': team_attempts['fg3_attempts'] * team_metrics['opp_fg3_pct'],
        'OPP_FTA': team_attempts['ft_attempts'],
        'OPP_FTM': team_attempts['ft_attempts'] * team_metrics['opp_ft_pct'],
        'OPP_TOV': team_attempts['turnovers'],
        'OPP_DREB': team_attempts['dreb_attempts'],
        'OPP_OREB': team_attempts['oreb_attempts']
    }
    
    additional_vars = {
        'additional_shots_made_2': get_additional(
            improved_metrics['fg2_pct'], team_metrics['fg2_pct'],
            lambda: (improved_metrics['fg2_pct'] * original['fg2a']) - original['fg2m']
        ),
        'additional_shots_made_3': get_additional(
            improved_metrics['fg3_pct'], team_metrics['fg3_pct'],
            lambda: (improved_metrics['fg3_pct'] * original['FG3A']) - original['FGM3']
        ),
        'additional_shots_made_ft': get_additional(
            improved_metrics['ft_pct'], team_metrics['ft_pct'],
            lambda: (improved_metrics['ft_pct'] * original['FTA']) - original['FTM']
        ),
        'additional_turnovers': get_additional(
            improved_metrics['tov_pct'], team_metrics['tov_pct'],
            lambda: (improved_metrics['tov_pct'] * original['POSS']) - original['TOV']
        ),
        'additional_dreb': get_additional(
            improved_metrics['dreb_pct'], team_metrics['dreb_pct'],
            lambda: (original['DREB'] / team_metrics['dreb_pct']) * improved_metrics['dreb_pct'] - original['DREB']
        ),
        'additional_oreb': get_additional(
            improved_metrics['oreb_pct'], team_metrics['oreb_pct'],
            lambda: (original['OREB'] / team_metrics['oreb_pct']) * improved_metrics['oreb_pct'] - original['OREB']
        ),
        'opp_additional_shots_made_2': get_additional(
            improved_metrics['opp_fg2_pct'], team_metrics['opp_fg2_pct'],
            lambda: (improved_metrics['opp_fg2_pct'] * original['opp_fg2a']) - original['opp_fg2m']
        ),
        'opp_additional_shots_made_3': get_additional(
            improved_metrics['opp_fg3_pct'], team_metrics['opp_fg3_pct'],
            lambda: (improved_metrics['opp_fg3_pct'] * original['OPP_FG3A']) - original['OPP_FGM3']
        ),
        'opp_additional_shots_made_ft': get_additional(
            improved_metrics['opp_ft_pct'], team_metrics['opp_ft_pct'],
            lambda: (improved_metrics['opp_ft_pct'] * original['OPP_FTA']) - original['OPP_FTM']
        ),
        'opp_additional_turnovers': get_additional(
            improved_metrics['opp_tov_pct'], team_metrics['opp_tov_pct'],
            lambda: (improved_metrics['opp_tov_pct'] * original['POSS']) - original['OPP_TOV']
        ),
        'opp_additional_dreb': get_additional(
            improved_metrics['opp_dreb_pct'], team_metrics['opp_dreb_pct'],
            lambda: (original['OPP_DREB'] / team_metrics['opp_dreb_pct']) * improved_metrics['opp_dreb_pct'] - original['OPP_DREB']
        ),
        'opp_additional_oreb': get_additional(
            improved_metrics['opp_oreb_pct'], team_metrics['opp_oreb_pct'],
            lambda: (original['OPP_OREB'] / team_metrics['opp_oreb_pct']) * improved_metrics['opp_oreb_pct'] - original['OPP_OREB']
        )
    }
    
    return additional_vars

def get_filtered_vars(adjustment_type: str, additional_vars: Dict[str, float]) -> Dict[str, float]:
    """Get filtered variables for a specific adjustment type"""
    if '2PT FG%' in adjustment_type:
        return {'additional_shots_made_2': additional_vars['additional_shots_made_2']}
    elif '3PT FG%' in adjustment_type:
        return {'additional_shots_made_3': additional_vars['additional_shots_made_3']}
    elif 'FT%' in adjustment_type:
        return {'additional_shots_made_ft': additional_vars['additional_shots_made_ft']}
    elif 'OREB%' in adjustment_type:
        return {'additional_oreb': additional_vars['additional_oreb']}
    elif 'DREB%' in adjustment_type:
        return {'additional_dreb': additional_vars['additional_dreb']}
    elif 'TOV%' in adjustment_type:
        return {'additional_turnovers': additional_vars['additional_turnovers']}
    elif 'OPP 2PT FG%' in adjustment_type:
        return {'opp_additional_shots_made_2': additional_vars['opp_additional_shots_made_2']}
    elif 'OPP 3PT FG%' in adjustment_type:
        return {'opp_additional_shots_made_3': additional_vars['opp_additional_shots_made_3']}
    elif 'OPP FT%' in adjustment_type:
        return {'opp_additional_shots_made_ft': additional_vars['opp_additional_shots_made_ft']}
    elif 'OPP OREB%' in adjustment_type:
        return {'opp_additional_oreb': additional_vars['opp_additional_oreb']}
    elif 'OPP DREB%' in adjustment_type:
        return {'opp_additional_dreb': additional_vars['opp_additional_dreb']}
    elif 'OPP TOV%' in adjustment_type:
        return {'opp_additional_turnovers': additional_vars['opp_additional_turnovers']}
    return {}

def calculate_all_adjustments(team: str, additional_vars: dict, transition_metrics: dict, adjusted_metrics: dict) -> List[Dict]:
    """Calculate all transition adjustments"""
    adjustments = []
    
    # Get required variables
    oreb_per = adjusted_metrics.get('oreb_pct', 0)
    opp_oreb_per = adjusted_metrics.get('opp_oreb_pct', 0)
    
    # Team 2pt adjustments
    if 'additional_shots_made_2' in additional_vars:
        adj_2pt = additional_vars['additional_shots_made_2']
        per_2pt_oreb = transition_metrics.get('per_2pt_made_from_oreb', 0)
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} 2pt Made', 
             'adjustment': adj_2pt * (1 - per_2pt_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} 2pt Made', 
             'adjustment': adj_2pt * per_2pt_oreb}
        ])
    
    # Team 3pt adjustments
    if 'additional_shots_made_3' in additional_vars:
        adj_3pt = additional_vars['additional_shots_made_3']
        per_3pt_oreb = transition_metrics.get('per_3pt_made_from_oreb', 0)
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} 3pt Made', 
             'adjustment': adj_3pt * (1 - per_3pt_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} 3pt Made', 
             'adjustment': adj_3pt * per_3pt_oreb}
        ])
    
    # Team FT adjustments
    if 'additional_shots_made_ft' in additional_vars:
        adj_ft = additional_vars['additional_shots_made_ft']
        per_ft_oreb = transition_metrics.get('per_ft_made_from_oreb', 0)
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} FT Made', 
             'adjustment': adj_ft * (1 - per_ft_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} FT Made', 
             'adjustment': adj_ft * per_ft_oreb}
        ])
    
    return adjustments

def apply_adjustments_for_metric(transitions: pd.DataFrame, adjustments: List[Dict], team: str, transition_metrics: Dict[str, float], adjusted_metrics: Dict[str, float], poss_per_game: float, adjustment_type: str) -> List[Dict[str, Any]]:
    """Apply adjustments to get final output for a specific metric"""
    results = []
    
    # Apply the adjustments to get final adjusted counts
    adjusted_counts = transitions.copy()
    
    for adj in adjustments:
        state = adj['state']
        next_state = adj['next_state']
        adjustment = adj['adjustment']
        
        # Find the row in transitions that matches this state and next_state
        mask = (adjusted_counts['state'] == state) & (adjusted_counts['next_state'] == next_state)
        if mask.any():
            # Apply the adjustment to the raw count
            adjusted_counts.loc[mask, 'count'] += adjustment
    
    # Ensure no negative counts
    adjusted_counts['count'] = adjusted_counts['count'].clip(lower=0)
    
    # Now output all the adjusted counts
    for _, row in adjusted_counts.iterrows():
        results.append({
            'team': row['team'],
            'season': row['season'],
            'state': row['state'],
            'next_state': row['next_state'],
            'count': round(row['count'], 2),
            'adjustment_type': adjustment_type,
            'poss_per_game': poss_per_game
        })
    
    return results
