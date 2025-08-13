#!/usr/bin/env python3
"""
Compare Transition Matrix Adjustments

This script compares the theoretical 2% adjustments from the CSV
with the actual live simulation adjustments for LAC team and 2PT FG%.
"""

import pandas as pd
import duckdb
import sys
import os
from typing import Dict, Any

# Add the app directory to the path so we can import the simulator
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from simulation import MarkovSimulator

def get_csv_2pt_adjustments() -> pd.DataFrame:
    """Get 2PT FG% +2% adjustments from the CSV for LAC"""
    try:
        # Read the CSV we generated
        df = pd.read_csv("transition_matrix_2percent_adjustments.csv")
        
        # Filter for LAC team and 2PT FG% +2% adjustment
        lac_2pt = df[
            (df['team'] == 'LAC') & 
            (df['adjustment_type'] == '2PT FG% +2%')
        ].copy()
        
        print(f"Found {len(lac_2pt)} rows for LAC 2PT FG% +2% in CSV")
        return lac_2pt
        
    except FileNotFoundError:
        print("❌ CSV file not found. Please run generate_transition_adjustments.py first.")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return pd.DataFrame()

def get_live_simulation_adjustments(conn, team: str = 'LAC') -> pd.DataFrame:
    """Get the actual adjusted transition counts from live simulation"""
    try:
        # Initialize simulator
        simulator = MarkovSimulator(conn)
        
        # Get team data
        agg_team = conn.execute(
            "SELECT * FROM agg_team_txn_cnts WHERE team = ?", 
            [team]
        ).fetchdf()
        
        # Get transition metrics
        transition_metrics = conn.execute(
            "SELECT * FROM team_transition_matrix_adjustments_rates WHERE team = ?", 
            [team]
        ).fetchdf()
        
        # Get season metrics
        season_metrics = get_team_season_metrics(conn, team)
        
        # Build transition matrix with NO adjustments (baseline)
        baseline_matrix = simulator.build_transition_matrix(
            agg_team, team, 
            additional_vars={},  # No additional vars
            transition_metrics=transition_metrics,
            adjusted_metrics=season_metrics
        )
        
        # Build transition matrix with 43.37 additional 2PT made
        additional_vars = {
            'additional_shots_made_2': 43.37,
            'additional_shots_made_3': 0,
            'additional_shots_made_ft': 0,
            'additional_turnovers': 0,
            'additional_dreb': 0,
            'additional_oreb': 0,
            'opp_additional_shots_made_2': 0,
            'opp_additional_shots_made_3': 0,
            'opp_additional_shots_made_ft': 0,
            'opp_additional_turnovers': 0,
            'opp_additional_dreb': 0,
            'opp_additional_oreb': 0
        }
        
        adjusted_matrix = simulator.build_transition_matrix(
            agg_team, team, 
            additional_vars=additional_vars,
            transition_metrics=transition_metrics,
            adjusted_metrics=season_metrics
        )
        
        # Get the raw counts before and after adjustments
        # We need to access the adjusted_counts from the simulator
        # This is a bit tricky since the simulator normalizes to probabilities
        
        print("✅ Successfully built transition matrices for comparison")
        
        # For now, let's return the baseline and adjusted matrices
        # We'll need to extract the actual adjusted counts
        return {
            'baseline': baseline_matrix,
            'adjusted': adjusted_matrix,
            'transition_metrics': transition_metrics,
            'season_metrics': season_metrics
        }
        
    except Exception as e:
        print(f"❌ Error getting live simulation adjustments: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_team_season_metrics(conn, team: str) -> Dict[str, float]:
    """Get current season metrics for a team"""
    season_metrics_query = """
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
    where cb.season = '2024-25' AND cb.team_abbreviation = ?
    """
    
    season_metrics = conn.execute(season_metrics_query, [team]).fetchdf()
    
    if season_metrics.empty:
        return {}
    
    team_data = season_metrics.iloc[0]
    
    # Calculate the 12 metrics we need
    metrics = {}
    
    # Team metrics
    metrics['fg2_pct'] = team_data.get('fg2_pct', 0)
    metrics['fg3_pct'] = team_data.get('fg3_pct', 0)
    metrics['ft_pct'] = team_data.get('ft_pct', 0)
    metrics['oreb_pct'] = team_data.get('OREB_PCT', 0)
    metrics['dreb_pct'] = team_data.get('dreb_pct', 0)
    metrics['tov_pct'] = team_data.get('TM_TOV_PCT', 0)
    
    # Opponent metrics
    metrics['opp_fg2_pct'] = team_data.get('opp_fg2_pct', 0)
    metrics['opp_fg3_pct'] = team_data.get('OPP_FG3_PCT', 0)
    metrics['opp_ft_pct'] = team_data.get('OPP_FT_PCT', 0)
    metrics['opp_oreb_pct'] = team_data.get('OPP_OREB_PCT', 0)
    metrics['opp_dreb_pct'] = team_data.get('opp_dreb_pct', 0)
    metrics['opp_tov_pct'] = team_data.get('OPP_TOV_PCT', 0)
    
    return metrics

def main():
    """Main function to compare adjustments"""
    print("Starting Transition Matrix Adjustment Comparison...")
    print("=" * 70)
    print("Comparing CSV 2% adjustments vs Live Simulation adjustments")
    print("Team: LAC | Focus: 2PT FG% adjustments")
    print("=" * 70)
    
    # Database connection
    DB_PATH = "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db"
    
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        print(f"Connected to database: {DB_PATH}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
    
    try:
        # Get CSV data
        print("\n1. Loading CSV data...")
        csv_data = get_csv_2pt_adjustments()
        
        if csv_data.empty:
            print("❌ No CSV data found. Exiting.")
            return
        
        # Get live simulation data
        print("\n2. Getting live simulation adjustments...")
        live_data = get_live_simulation_adjustments(conn, 'LAC')
        
        if not live_data:
            print("❌ No live simulation data found. Exiting.")
            return
        
        # Display comparison
        print("\n3. Comparison Results:")
        print("-" * 50)
        
        print(f"CSV 2PT FG% +2% adjustments: {len(csv_data)} rows")
        print(f"Live simulation matrices built successfully")
        
        # Show some sample data from CSV
        print("\nSample CSV data (first 5 rows):")
        print(csv_data[['state', 'next_state', 'counts']].head())
        
        # Show matrix info
        print(f"\nBaseline matrix shape: {live_data['baseline'].shape}")
        print(f"Adjusted matrix shape: {live_data['adjusted'].shape}")
        
        # Show key metrics
        print(f"\nKey Metrics for LAC:")
        print(f"Original 2PT FG%: {live_data['season_metrics'].get('fg2_pct', 0):.3f}")
        print(f"With 43.37 additional 2PT made: ~56.04% (from logs)")
        
        print("\n✅ Comparison complete!")
        print("\nNote: To see exact adjusted counts, we need to access the")
        print("simulator's internal adjusted_counts before normalization.")
        
    except Exception as e:
        print(f"Error during comparison: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print(f"\nDatabase connection closed")

if __name__ == "__main__":
    main()
