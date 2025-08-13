import duckdb
import pandas as pd
from typing import Dict, List, Any

def get_baseline_data(conn, team: str, season: str) -> Dict[str, Any]:
    """Step 1: Get baseline data from database"""
    print(f"📊 Getting baseline data for {team}...")
    
    # Get transition counts
    transitions_query = """
    SELECT state, next_state, count 
    FROM agg_team_txn_cnts 
    WHERE team = ? AND season = ?
    ORDER BY count DESC
    """
    transitions = conn.execute(transitions_query, [team, season]).fetchdf()
    print(f"    ✅ Got {len(transitions)} transition counts")
    
    # Get transition metrics from the rates table
    rates_query = """
    SELECT * FROM team_transition_matrix_adjustments_rates 
    WHERE season = ?
    """
    rates = conn.execute(rates_query, [season]).fetchdf()
    print(f"    ✅ Got adjustment rates")
    
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
        print(f"    ✅ Got team metrics")
        print(f"    🔍 Available columns: {list(metrics.columns)}")
        print(f"    📊 First row: {dict(metrics.iloc[0])}")
        
        # Extract the 12 key metrics - using actual column names from database
        team_metrics = {
            'fg2_pct': metrics.iloc[0]['fg2_pct'],
            'fg3_pct': metrics.iloc[0]['FG3_PCT'], 
            'ft_pct': metrics.iloc[0]['FT_PCT'],
            'oreb_pct': metrics.iloc[0]['OREB_PCT'],
            'dreb_pct': metrics.iloc[0]['dreb_pct'],
            'tov_pct': metrics.iloc[0]['TM_TOV_PCT'],
            'opp_fg2_pct': metrics.iloc[0]['opp_fg2_pct'],
            'opp_fg3_pct': metrics.iloc[0]['OPP_FG3_PCT'],
            'opp_ft_pct': metrics.iloc[0]['OPP_FT_PCT'],
            'opp_oreb_pct': metrics.iloc[0]['OPP_OREB_PCT'],
            'opp_dreb_pct': metrics.iloc[0]['opp_dreb_pct'],
            'opp_tov_pct': metrics.iloc[0]['OPP_TOV_PCT'],
            'POSS': metrics.iloc[0]['POSS']
        }
        
        # Create team_attempts from the metrics data
        team_attempts = {
            'fg2_attempts': int(metrics.iloc[0]['fg2a']),
            'fg3_attempts': int(metrics.iloc[0]['FG3A']),
            'ft_attempts': int(metrics.iloc[0]['FTA']),
            'turnovers': int(metrics.iloc[0]['TOV']),
            'dreb_attempts': int(metrics.iloc[0]['DREB']),
            'oreb_attempts': int(metrics.iloc[0]['OREB'])
        }
    else:
        print(f"    ❌ No metrics found - cannot proceed without data")
        raise ValueError("No team metrics found in database")
    
    # Convert rates DataFrame to dictionary for transition_metrics
    if not rates.empty:
        transition_metrics = rates.iloc[0].to_dict()
        print(f"    ✅ Got transition metrics from rates table")
        print(f"    🔍 Available transition metrics: {list(transition_metrics.keys())}")
    else:
        print(f"    ❌ No transition metrics found - cannot proceed without data")
        raise ValueError("No transition metrics found in database")
    
    return {
        'transitions': transitions,
        'rates': rates,
        'metrics': team_metrics,
        'team_attempts': team_attempts,
        'transition_metrics': transition_metrics
    }

def calculate_improved_metrics(team_metrics: Dict[str, float]) -> Dict[str, float]:
    """Step 2: Calculate 5% improvements for all 12 metrics"""
    print(f"📈 Calculating 5% improvements...")
    
    improved_metrics = {}
    
    # Team metrics: increase by 5% (except TOV% which decreases by 5%)
    improved_metrics['fg2_pct'] = team_metrics['fg2_pct'] * 1.05
    improved_metrics['fg3_pct'] = team_metrics['fg3_pct'] * 1.05
    improved_metrics['ft_pct'] = team_metrics['ft_pct'] * 1.05
    improved_metrics['oreb_pct'] = team_metrics['oreb_pct'] * 1.05
    improved_metrics['dreb_pct'] = team_metrics['dreb_pct'] * 1.05
    improved_metrics['tov_pct'] = team_metrics['tov_pct'] * 0.95  # Decrease TOV%
    
    # Opponent metrics: decrease by 5% (except TOV% which increases by 5%)
    improved_metrics['opp_fg2_pct'] = team_metrics['opp_fg2_pct'] * 0.95
    improved_metrics['opp_fg3_pct'] = team_metrics['opp_fg3_pct'] * 0.95
    improved_metrics['opp_ft_pct'] = team_metrics['opp_ft_pct'] * 0.95
    improved_metrics['opp_oreb_pct'] = team_metrics['opp_oreb_pct'] * 0.95
    improved_metrics['opp_dreb_pct'] = team_metrics['opp_dreb_pct'] * 0.95
    improved_metrics['opp_tov_pct'] = team_metrics['opp_tov_pct'] * 1.05  # Increase opp TOV%
    
    print(f"    ✅ Calculated 5% improvements for all 12 metrics")
    return improved_metrics

def calculate_additional_variables(team_metrics: Dict[str, float], improved_metrics: Dict[str, float], team_attempts: Dict[str, int]) -> Dict[str, float]:
    """Step 3: Calculate additional variables using existing formulas from frontend"""
    print(f"🧮 Calculating additional variables...")
    
    # Helper function to check if metric is at default (returns 0 if so)
    def get_additional(adjusted_value: float, original_value: float, formula: callable) -> float:
        if abs(adjusted_value - original_value) < 0.0001:  # At default
            return 0.0
        return formula()
    
    # Get original values from team_attempts (these are the raw counts)
    original = {
        'fg2a': team_attempts['fg2_attempts'],
        'fg2m': team_attempts['fg2_attempts'] * team_metrics['fg2_pct'],
        'FG3A': team_attempts['fg3_attempts'],
        'FGM3': team_attempts['fg3_attempts'] * team_metrics['fg3_pct'],
        'FTA': team_attempts['ft_attempts'],
        'FTM': team_attempts['ft_attempts'] * team_metrics['ft_pct'],
        'POSS': team_metrics['POSS'],
        'TOV': team_attempts['turnovers'],
        'DREB': team_attempts['dreb_attempts'],
        'OREB': team_attempts['oreb_attempts'],
        'opp_fg2a': team_attempts['fg2_attempts'],  # Approximate - using team attempts as proxy
        'opp_fg2m': team_attempts['fg2_attempts'] * team_metrics['opp_fg2_pct'],
        'OPP_FG3A': team_attempts['fg3_attempts'],  # Approximate
        'OPP_FGM3': team_attempts['fg3_attempts'] * team_metrics['opp_fg3_pct'],
        'OPP_FTA': team_attempts['ft_attempts'],  # Approximate
        'OPP_FTM': team_attempts['ft_attempts'] * team_metrics['opp_ft_pct'],
        'OPP_TOV': team_attempts['turnovers'],  # Approximate
        'OPP_DREB': team_attempts['dreb_attempts'],  # Approximate
        'OPP_OREB': team_attempts['oreb_attempts']  # Approximate
    }
    
    additional_vars = {
        # Team additional variables
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
        
        # Opponent additional variables
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
    
    print(f"    ✅ Calculated additional variables:")
    for key, value in additional_vars.items():
        if abs(value) > 0.01:  # Only show non-zero values
            print(f"      {key}: {value:.2f}")
    
    return additional_vars

def calculate_transition_metrics(transitions: pd.DataFrame, team: str) -> Dict[str, float]:
    """Calculate transition metrics needed for adjustments from actual transition data"""
    print(f"    📊 Calculating transition metrics from data...")
    
    # Get total counts for key transitions
    total_2pt_made = transitions[
        (transitions['next_state'] == f'{team} 2pt Made')
    ]['count'].sum()
    
    total_3pt_made = transitions[
        (transitions['next_state'] == f'{team} 3pt Made')
    ]['count'].sum()
    
    total_ft_made = transitions[
        (transitions['next_state'] == f'{team} FT Made')
    ]['count'].sum()
    
    # Calculate percentages from different starting states
    per_2pt_from_oreb = 0
    per_2pt_from_offense_start = 0
    per_3pt_from_oreb = 0
    per_3pt_from_offense_start = 0
    per_ft_from_oreb = 0
    per_ft_from_offense_start = 0
    per_ft_from_ft_made = 0
    
    if total_2pt_made > 0:
        per_2pt_from_oreb = transitions[
            (transitions['state'] == f'{team} OREB') & 
            (transitions['next_state'] == f'{team} 2pt Made')
        ]['count'].sum() / total_2pt_made
        
        per_2pt_from_offense_start = transitions[
            (transitions['state'] == f'{team} Offense Start') & 
            (transitions['next_state'] == f'{team} 2pt Made')
        ]['count'].sum() / total_2pt_made
    
    if total_3pt_made > 0:
        per_3pt_from_oreb = transitions[
            (transitions['state'] == f'{team} OREB') & 
            (transitions['next_state'] == f'{team} 3pt Made')
        ]['count'].sum() / total_3pt_made
        
        per_3pt_from_offense_start = transitions[
            (transitions['state'] == f'{team} Offense Start') & 
            (transitions['next_state'] == f'{team} 3pt Made')
        ]['count'].sum() / total_3pt_made
    
    if total_ft_made > 0:
        per_ft_from_oreb = transitions[
            (transitions['state'] == f'{team} OREB') & 
            (transitions['next_state'] == f'{team} FT Made')
        ]['count'].sum() / total_ft_made
        
        per_ft_from_offense_start = transitions[
            (transitions['state'] == f'{team} Offense Start') & 
            (transitions['next_state'] == f'{team} FT Made')
        ]['count'].sum() / total_ft_made
        
        per_ft_from_ft_made = transitions[
            (transitions['state'] == f'{team} FT Made') & 
            (transitions['next_state'] == f'{team} FT Made')
        ]['count'].sum() / total_ft_made
    
    transition_metrics = {
        'per_2pt_made_from_oreb': per_2pt_from_oreb,
        'per_2pt_made_from_offense_start_tov': per_2pt_from_offense_start,
        'per_3pt_made_from_oreb': per_3pt_from_oreb,
        'per_3pt_made_from_offense_start_tov': per_3pt_from_offense_start,
        'per_ft_made_from_oreb': per_ft_from_oreb,
        'per_ft_made_from_offense_start': per_ft_from_offense_start,
        'per_ft_made_from_ft_made': per_ft_from_ft_made
    }
    
    print(f"    ✅ Calculated transition metrics:")
    for key, value in transition_metrics.items():
        print(f"      {key}: {value:.3f}")
    
    return transition_metrics

def calculate_all_adjustments(team: str, additional_vars: dict, 
                            transition_metrics: dict, adjusted_metrics: dict) -> List[Dict]:
    """Calculate all transition adjustments based on user formulas - copied from simulation.py"""
    print(f"    Starting calculate_all_adjustments for team: {team}")

    adjustments = []
    
    # Get all the required variables
    oreb_per = adjusted_metrics['oreb_pct']
    opp_oreb_per = adjusted_metrics['opp_oreb_pct']
    print(f"    Got adjusted metrics - oreb_per: {oreb_per}, opp_oreb_per: {opp_oreb_per}")
    
    # Team 2pt adjustments
    if 'additional_shots_made_2' in additional_vars:
        print("    Processing 2pt adjustments")
        adj_2pt = additional_vars['additional_shots_made_2']
        per_2pt_oreb = transition_metrics['per_2pt_made_from_oreb']
        per_2pt_offense = transition_metrics['per_2pt_made_from_offense_start_tov']
        
        # Debug output for LAC OREB → LAC 2pt Made
        if team == 'LAC':
            print(f"    🔍 DEBUG 2PT: adj_2pt={adj_2pt:.2f}, per_2pt_oreb={per_2pt_oreb:.4f}")
            print(f"    🔍 DEBUG 2PT: LAC OREB → LAC 2pt Made adjustment = {adj_2pt * per_2pt_oreb:.2f}")
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} 2pt Made', 
             'adjustment': adj_2pt * (1 - per_2pt_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} 2pt Made', 
             'adjustment': adj_2pt * per_2pt_oreb},
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': -adj_2pt * (1 - per_2pt_oreb) * oreb_per},
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': -adj_2pt * (1 - per_2pt_oreb) * (1 - oreb_per)},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': -adj_2pt * per_2pt_oreb * oreb_per},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': -adj_2pt * per_2pt_oreb * (1 - oreb_per)}
        ])
    
    # Team 3pt adjustments
    if 'additional_shots_made_3' in additional_vars:
        print("    Processing 3pt adjustments")
        adj_3pt = additional_vars['additional_shots_made_3']
        per_3pt_oreb = transition_metrics['per_3pt_made_from_oreb']
        per_3pt_offense = transition_metrics['per_3pt_made_from_offense_start_tov']
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} 3pt Made', 
             'adjustment': adj_3pt * (1 - per_3pt_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} 3pt Made', 
             'adjustment': adj_3pt * per_3pt_oreb},
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': -adj_3pt * (1 - per_3pt_oreb) * oreb_per},
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': -adj_3pt * (1 - per_3pt_oreb) * (1 - oreb_per)},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': -adj_3pt * per_3pt_oreb * oreb_per},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': -adj_3pt * per_3pt_oreb * (1 - oreb_per)}
        ])
    
    # Team FT adjustments
    if 'additional_shots_made_ft' in additional_vars:
        print("    Processing FT adjustments")
        adj_ft = additional_vars['additional_shots_made_ft']
        per_ft_oreb = transition_metrics['per_ft_made_from_oreb']
        per_ft_offense = transition_metrics['per_ft_made_from_offense_start']
        per_ft_made = transition_metrics['per_ft_made_from_ft_made']
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} FT Made', 
             'adjustment': adj_ft * per_ft_offense},
            {'state': f'{team} FT Made', 'next_state': f'{team} FT Made', 
             'adjustment': adj_ft * per_ft_made},
            {'state': f'{team} OREB', 'next_state': f'{team} FT Made', 
             'adjustment': adj_ft * per_ft_oreb},
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': -adj_ft * per_ft_offense * oreb_per},
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': -adj_ft * per_ft_offense * (1 - oreb_per)},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': -adj_ft * per_ft_oreb * oreb_per},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': -adj_ft * per_ft_oreb * (1 - oreb_per)},
            {'state': f'{team} FT Made', 'next_state': f'{team} OREB', 
             'adjustment': -adj_ft * per_ft_made * oreb_per},
            {'state': f'{team} FT Made', 'next_state': 'OPP DREB', 
             'adjustment': -adj_ft * per_ft_made * (1 - oreb_per)}
        ])
    
    # Team turnover adjustments
    if 'additional_turnovers' in additional_vars:
        print("    Processing turnover adjustments")
        adj_tov = additional_vars['additional_turnovers']
        per_tov_oreb = transition_metrics['per_turnover_from_oreb']
        per_2pt_tov = transition_metrics['per_2pt_made_from_offense_start_tov']
        per_3pt_tov = transition_metrics['per_3pt_made_from_offense_start_tov']
        per_ft_tov = transition_metrics['per_ft_made_from_offense_start_tov']
        per_oreb_tov = transition_metrics['per_oreb_from_offense_start_tov']
        per_opp_dreb_tov = transition_metrics['per_opp_dreb_from_offense_start_tov']
        per_2pt_oreb_tov = transition_metrics['per_2pt_made_from_oreb_tov']
        per_3pt_oreb_tov = transition_metrics['per_3pt_made_from_oreb_tov']
        per_ft_oreb_tov = transition_metrics['per_ft_made_from_oreb_tov']
        per_oreb_oreb_tov = transition_metrics['per_oreb_from_oreb_tov']
        per_opp_dreb_oreb_tov = transition_metrics['per_opp_dreb_from_oreb_tov']
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} Turnover', 
             'adjustment': adj_tov * (1 - per_tov_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} Turnover', 
             'adjustment': adj_tov * per_tov_oreb},
            {'state': f'{team} Offense Start', 'next_state': f'{team} 2pt Made', 
             'adjustment': -adj_tov * (1 - per_tov_oreb) * per_2pt_tov},
            {'state': f'{team} Offense Start', 'next_state': f'{team} 3pt Made', 
             'adjustment': -adj_tov * (1 - per_tov_oreb) * per_3pt_tov},
            {'state': f'{team} Offense Start', 'next_state': f'{team} FT Made', 
             'adjustment': -adj_tov * (1 - per_tov_oreb) * per_ft_tov},
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': -adj_tov * (1 - per_tov_oreb) * per_oreb_tov},
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': -adj_tov * (1 - per_tov_oreb) * per_opp_dreb_tov},
            {'state': f'{team} OREB', 'next_state': f'{team} 2pt Made', 
             'adjustment': -adj_tov * per_tov_oreb * per_2pt_oreb_tov},
            {'state': f'{team} OREB', 'next_state': f'{team} 3pt Made', 
             'adjustment': -adj_tov * per_tov_oreb * per_3pt_oreb_tov},
            {'state': f'{team} OREB', 'next_state': f'{team} FT Made', 
             'adjustment': -adj_tov * per_tov_oreb * per_ft_oreb_tov},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': -adj_tov * per_tov_oreb * per_oreb_oreb_tov},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': -adj_tov * per_tov_oreb * per_opp_dreb_oreb_tov}
        ])
    
    # Team DREB adjustments
    if 'additional_dreb' in additional_vars:
        adj_dreb = additional_vars['additional_dreb']
        per_dreb_opp_oreb = transition_metrics['per_dreb_from_opp_oreb']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': adj_dreb * (1 - per_dreb_opp_oreb)},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': adj_dreb * per_dreb_opp_oreb},
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': -adj_dreb * (1 - per_dreb_opp_oreb)},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': -adj_dreb * per_dreb_opp_oreb}
        ])
    
    # Team OREB adjustments
    if 'additional_oreb' in additional_vars:
        adj_oreb = additional_vars['additional_oreb']
        per_oreb_from_oreb = transition_metrics['per_oreb_from_oreb']
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': adj_oreb * (1 - per_oreb_from_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': adj_oreb * per_oreb_from_oreb},
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': -adj_oreb * (1 - per_oreb_from_oreb)},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': -adj_oreb * per_oreb_from_oreb}
        ])
    
    # Opponent 2pt adjustments
    if 'opp_additional_shots_made_2' in additional_vars:
        adj_opp_2pt = additional_vars['opp_additional_shots_made_2']
        per_2pt_oreb_opp = transition_metrics['per_2pt_made_from_oreb_opp']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': 'OPP 2pt Made', 
             'adjustment': adj_opp_2pt * (1 - per_2pt_oreb_opp)},
            {'state': 'OPP OREB', 'next_state': 'OPP 2pt Made', 
             'adjustment': adj_opp_2pt * per_2pt_oreb_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_2pt * (1 - per_2pt_oreb_opp) * opp_oreb_per},
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_2pt * (1 - per_2pt_oreb_opp) * (1 - opp_oreb_per)},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_2pt * per_2pt_oreb_opp * opp_oreb_per},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_2pt * per_2pt_oreb_opp * (1 - opp_oreb_per)}
        ])
    
    # Opponent 3pt adjustments
    if 'opp_additional_shots_made_3' in additional_vars:
        adj_opp_3pt = additional_vars['opp_additional_shots_made_3']
        per_3pt_oreb_opp = transition_metrics['per_3pt_made_from_oreb_opp']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': 'OPP 3pt Made', 
             'adjustment': adj_opp_3pt * (1 - per_3pt_oreb_opp)},
            {'state': 'OPP OREB', 'next_state': 'OPP 3pt Made', 
             'adjustment': adj_opp_3pt * per_3pt_oreb_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_3pt * (1 - per_3pt_oreb_opp) * opp_oreb_per},
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_3pt * (1 - per_3pt_oreb_opp) * (1 - opp_oreb_per)},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_3pt * per_3pt_oreb_opp * opp_oreb_per},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_3pt * per_3pt_oreb_opp * (1 - opp_oreb_per)}
        ])
    
    # Opponent FT adjustments
    if 'opp_additional_shots_made_ft' in additional_vars:
        adj_opp_ft = additional_vars['opp_additional_shots_made_ft']
        per_ft_offense_opp = transition_metrics['per_ft_made_from_offense_start_opp']
        per_ft_oreb_opp = transition_metrics['per_ft_made_from_oreb_opp']
        per_ft_made_opp = transition_metrics['per_ft_made_from_ft_made_opp']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': 'OPP FT Made', 
             'adjustment': adj_opp_ft * per_ft_offense_opp},
            {'state': 'OPP OREB', 'next_state': 'OPP FT Made', 
             'adjustment': adj_opp_ft * per_ft_oreb_opp},
            {'state': 'OPP FT Made', 'next_state': 'OPP FT Made', 
             'adjustment': adj_opp_ft * per_ft_made_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_ft * per_ft_offense_opp * opp_oreb_per},
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_ft * per_ft_offense_opp * (1 - opp_oreb_per)},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_ft * per_ft_oreb_opp * opp_oreb_per},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_ft * per_ft_oreb_opp * (1 - opp_oreb_per)},
            {'state': 'OPP FT Made', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_ft * per_ft_made_opp * opp_oreb_per},
            {'state': 'OPP FT Made', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_ft * per_ft_made_opp * (1 - opp_oreb_per)}
        ])
    
    # Opponent turnover adjustments
    if 'opp_additional_turnovers' in additional_vars:
        print("    Processing opponent turnover adjustments")
        adj_opp_tov = additional_vars['opp_additional_turnovers']
        per_tov_oreb_opp = transition_metrics['per_turnover_from_oreb_opp']
        per_2pt_offense_tov_opp = transition_metrics['per_2pt_made_from_offense_start_tov_opp']
        per_3pt_offense_tov_opp = transition_metrics['per_3pt_made_from_offense_start_tov_opp']
        per_ft_offense_tov_opp = transition_metrics['per_ft_made_from_offense_start_tov_opp']
        per_oreb_offense_tov_opp = transition_metrics['per_oreb_from_offense_start_tov_opp']
        per_dreb_offense_tov_opp = transition_metrics['per_dreb_from_offense_start_tov_opp']
        per_2pt_oreb_tov_opp = transition_metrics['per_2pt_made_from_oreb_tov_opp']
        per_3pt_oreb_tov_opp = transition_metrics['per_3pt_made_from_oreb_tov_opp']
        per_ft_oreb_tov_opp = transition_metrics['per_ft_made_from_oreb_tov_opp']
        per_oreb_oreb_tov_opp = transition_metrics['per_oreb_from_oreb_tov_opp']
        per_dreb_oreb_tov_opp = transition_metrics['per_dreb_from_oreb_tov_opp']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': 'OPP Turnover', 
             'adjustment': adj_opp_tov * (1 - per_tov_oreb_opp)},
            {'state': 'OPP OREB', 'next_state': 'OPP Turnover', 
             'adjustment': adj_opp_tov * per_tov_oreb_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP 2pt Made', 
             'adjustment': -adj_opp_tov * (1 - per_tov_oreb_opp) * per_2pt_offense_tov_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP 3pt Made', 
             'adjustment': -adj_opp_tov * (1 - per_tov_oreb_opp) * per_3pt_offense_tov_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP FT Made', 
             'adjustment': -adj_opp_tov * (1 - per_tov_oreb_opp) * per_ft_offense_tov_opp},
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_tov * (1 - per_tov_oreb_opp) * per_oreb_offense_tov_opp},
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_tov * (1 - per_tov_oreb_opp) * per_dreb_offense_tov_opp},
            {'state': 'OPP OREB', 'next_state': 'OPP 2pt Made', 
             'adjustment': -adj_opp_tov * per_tov_oreb_opp * per_2pt_oreb_tov_opp},
            {'state': 'OPP OREB', 'next_state': 'OPP 3pt Made', 
             'adjustment': -adj_opp_tov * per_tov_oreb_opp * per_3pt_oreb_tov_opp},
            {'state': 'OPP OREB', 'next_state': 'OPP FT Made', 
             'adjustment': -adj_opp_tov * per_tov_oreb_opp * per_ft_oreb_tov_opp},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': -adj_opp_tov * per_tov_oreb_opp * per_oreb_oreb_tov_opp},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_tov * per_tov_oreb_opp * per_dreb_oreb_tov_opp}
        ])
    
    # Opponent DREB adjustments
    if 'opp_additional_dreb' in additional_vars:
        adj_opp_dreb = additional_vars['opp_additional_dreb']
        per_opp_dreb_from_oreb = transition_metrics['per_opp_dreb_from_oreb']
        
        adjustments.extend([
            {'state': f'{team} Offense Start', 'next_state': 'OPP DREB', 
             'adjustment': adj_opp_dreb * (1 - per_opp_dreb_from_oreb)},
            {'state': f'{team} OREB', 'next_state': 'OPP DREB', 
             'adjustment': adj_opp_dreb * per_opp_dreb_from_oreb},
            {'state': f'{team} Offense Start', 'next_state': f'{team} OREB', 
             'adjustment': -adj_opp_dreb * (1 - per_opp_dreb_from_oreb)},
            {'state': f'{team} OREB', 'next_state': f'{team} OREB', 
             'adjustment': -adj_opp_dreb * per_opp_dreb_from_oreb}
        ])
    
    # Opponent OREB adjustments
    if 'opp_additional_oreb' in additional_vars:
        adj_opp_oreb = additional_vars['opp_additional_oreb']
        per_opp_oreb_from_oreb_opp = transition_metrics['per_opp_oreb_from_oreb_opp']
        
        adjustments.extend([
            {'state': 'OPP Offense Start', 'next_state': 'OPP OREB', 
             'adjustment': adj_opp_oreb * (1 - per_opp_oreb_from_oreb_opp)},
            {'state': 'OPP OREB', 'next_state': 'OPP OREB', 
             'adjustment': adj_opp_oreb * per_opp_oreb_from_oreb_opp},
            {'state': 'OPP Offense Start', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_oreb * (1 - per_opp_oreb_from_oreb_opp)},
            {'state': 'OPP OREB', 'next_state': f'{team} DREB', 
             'adjustment': -adj_opp_oreb * per_opp_oreb_from_oreb_opp}
        ])
    
    print(f"    calculate_all_adjustments completed, returning {len(adjustments)} adjustments")
    return adjustments

def apply_adjustments_for_metric(transitions: pd.DataFrame, adjustments: List[Dict], team: str, transition_metrics: Dict[str, float], adjusted_metrics: Dict[str, float], poss_per_game: float, adjustment_type: str) -> List[Dict[str, Any]]:
    """Step 4: Apply adjustments to get final output for a specific metric"""
    print(f"🔧 Applying {adjustment_type} adjustments to transitions...")
    
    results = []
    
    # Apply the adjustments to get final adjusted counts
    adjusted_counts = transitions.copy()
    
    for adj in adjustments:
        state = adj['state']
        next_state = adj['next_state']
        adjustment = adj['adjustment']
        
        # Debug output for LAC OREB → LAC 2pt Made
        if state == 'LAC OREB' and next_state == 'LAC 2pt Made':
            print(f"    🔍 DEBUG APPLY: {state} → {next_state}: adjustment = {adjustment:.2f}")
        
        # Find the row in transitions that matches this state and next_state
        mask = (adjusted_counts['state'] == state) & (adjusted_counts['next_state'] == next_state)
        if mask.any():
            # Apply the adjustment to the raw count
            adjusted_counts.loc[mask, 'count'] += adjustment
            
            # Debug output for LAC OREB → LAC 2pt Made
            if state == 'LAC OREB' and next_state == 'LAC 2pt Made':
                old_count = adjusted_counts.loc[mask, 'count'].iloc[0] - adjustment
                new_count = adjusted_counts.loc[mask, 'count'].iloc[0]
                print(f"    🔍 DEBUG APPLY: {state} → {next_state}: {old_count:.2f} → {new_count:.2f}")
    
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
    
    print(f"    ✅ Generated {len(results)} result rows for {adjustment_type}")
    return results

def main():
    """Main function to generate transition adjustment analysis"""
    print("🚀 Starting Transition Matrix Adjustment Analysis...")
    print("=" * 70)
    
    # Database connection
    DB_PATH = "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db"
    
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        print(f"✅ Connected to database: {DB_PATH}")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return
    
    try:
        # Get all teams from the database
        teams_query = "SELECT DISTINCT team FROM agg_team_txn_cnts WHERE season = '2024-25' ORDER BY team"
        teams_df = conn.execute(teams_query).fetchdf()
        all_teams = teams_df['team'].tolist()
        
        print(f"📊 Found {len(all_teams)} teams to analyze")
        
        # Process each team
        all_results = []
        season = '2024-25'
        
        for team in all_teams:
            print(f"\n🎯 Analyzing team: {team}")
            print("-" * 50)
            
            # Step 1: Get baseline data
            baseline_data = get_baseline_data(conn, team, season)
            
            # Step 2: Calculate 5% improvements
            improved_metrics = calculate_improved_metrics(baseline_data['metrics'])
            
            # Step 3: Calculate additional variables
            additional_vars = calculate_additional_variables(baseline_data['metrics'], improved_metrics, baseline_data['team_attempts'])
            
            # Step 4: Calculate transition metrics from actual data
            transition_metrics = baseline_data['transition_metrics']
            
                # Add team and season columns to transitions DataFrame
    baseline_data['transitions']['team'] = team
    baseline_data['transitions']['season'] = season
            
            # Step 5: Process each adjustment type separately
            team_results = []
            
            # Define the 12 adjustment types (now with 5% instead of 2%)
            adjustment_types = [
                '2PT FG% +5%', '3PT FG% +5%', 'FT% +5%', 'OREB% +5%', 'DREB% +5%', 'TOV% -5%',
                'OPP 2PT FG% -5%', 'OPP 3PT FG% -5%', 'OPP FT% -5%', 'OPP OREB% -5%', 'OPP DREB% -5%', 'OPP TOV% +5%'
            ]
            
            for adjustment_type in adjustment_types:
                print(f"    Processing {adjustment_type}")
                
                # Create a filtered additional_vars for this specific metric
                filtered_vars = {}
                if 'OPP 2PT FG%' in adjustment_type:
                    filtered_vars = {'opp_additional_shots_made_2': additional_vars['opp_additional_shots_made_2']}
                elif 'OPP 3PT FG%' in adjustment_type:
                    filtered_vars = {'opp_additional_shots_made_3': additional_vars['opp_additional_shots_made_3']}
                elif 'OPP FT%' in adjustment_type:
                    filtered_vars = {'opp_additional_shots_made_ft': additional_vars['opp_additional_shots_made_ft']}
                elif 'OPP OREB%' in adjustment_type:
                    filtered_vars = {'opp_additional_oreb': additional_vars['opp_additional_oreb']}
                elif 'OPP DREB%' in adjustment_type:
                    filtered_vars = {'opp_additional_dreb': additional_vars['opp_additional_dreb']}
                elif 'OPP TOV%' in adjustment_type:
                    filtered_vars = {'opp_additional_turnovers': additional_vars['opp_additional_turnovers']}
                elif '2PT FG%' in adjustment_type:
                    filtered_vars = {'additional_shots_made_2': additional_vars['additional_shots_made_2']}
                elif '3PT FG%' in adjustment_type:
                    filtered_vars = {'additional_shots_made_3': additional_vars['additional_shots_made_3']}
                elif 'FT%' in adjustment_type:
                    filtered_vars = {'additional_shots_made_ft': additional_vars['additional_shots_made_ft']}
                elif 'OREB%' in adjustment_type:
                    filtered_vars = {'additional_oreb': additional_vars['additional_oreb']}
                elif 'DREB%' in adjustment_type:
                    filtered_vars = {'additional_dreb': additional_vars['additional_dreb']}
                elif 'TOV%' in adjustment_type:
                    filtered_vars = {'additional_turnovers': additional_vars['additional_turnovers']}
                
                # Get adjustments for this specific metric only
                adjustments = calculate_all_adjustments(team, filtered_vars, transition_metrics, improved_metrics)
                
                # Apply adjustments for this metric only
                poss_per_game = baseline_data['metrics'].get('POSS', 98.8)
                results = apply_adjustments_for_metric(baseline_data['transitions'], adjustments, team, transition_metrics, improved_metrics, poss_per_game, adjustment_type)
                team_results.extend(results)
            
            all_results.extend(team_results)
            print(f"✅ Completed analysis for {team}")
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(all_results)
        
        # Save to CSV
        output_file = "transition_matrix_5percent_adjustments.csv"
        df.to_csv(output_file, index=False)
        
        print("\n" + "=" * 70)
        print(f"🎉 Analysis complete! Results saved to: {output_file}")
        print(f"📊 Total rows generated: {len(df):,}")
        
        # Display summary
        if not df.empty:
            print("\n📋 SUMMARY:")
            print("-" * 20)
            print(f"Teams processed: {df['team'].nunique()}")
            print(f"Adjustment types: {df['adjustment_type'].nunique()}")
            print(f"State combinations: {df.groupby(['state', 'next_state']).size().shape[0]}")
            print(f"Columns in output: {list(df.columns)}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print(f"\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
