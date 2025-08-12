from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import duckdb
import pandas as pd
import json
import traceback
# Import existing functions from simulation.py
from .simulation import *

# Import transition adjustment functions
from .transition_utils import *
import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
import os
import tempfile

app = FastAPI(title="NBA Markov Simulation API")

# Global cache for metrics to avoid refetching
_metrics_cache = {}

# Global cancellation tracking
_active_simulations = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DuckDB connection to the existing database
DB_PATH = "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db"

try:
    conn = duckdb.connect(DB_PATH, read_only=True)
except Exception as e:
    print(f"Error connecting to database: {e}")
    raise

# Initialize simulator
simulator = MarkovSimulator(conn)

class AdjustmentRequest(BaseModel):
    team: str
    season: str = "2024-25"
    adjustment_percentage: float = 5.0

@app.get("/")
async def root():
    return {"message": "Welcome to NBA Markov Simulation API"}

@app.get("/health")
async def health_check():
    try:
        # Test the database connection
        conn.execute("SELECT 1").fetchone()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.post("/api/simulate/cancel")
async def cancel_simulation(request: dict):
    """Cancel an active simulation"""
    try:
        team = request.get('team')
        if not team:
            raise HTTPException(status_code=400, detail="Team is required")
        
        if team in _active_simulations:
            _active_simulations[team] = True  # Mark as cancelled
            print(f"Simulation cancelled for team: {team}")
            return {"message": f"Simulation cancelled for team: {team}"}
        else:
            return {"message": f"No active simulation found for team: {team}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling simulation: {str(e)}")

@app.get("/api/teams")
async def get_teams():
    """Get list of available teams"""
    try:
        teams = conn.execute("SELECT DISTINCT team FROM agg_team_txn_cnts ORDER BY team").fetchdf()
        return {"teams": teams['team'].tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")

@app.get("/api/baseline-wins")
async def get_baseline_wins(season: str = '2024-25'):
    """Get baseline simulated wins for all teams from database for a specific season"""
    try:
        query = "SELECT team, wins FROM estimated_wins_simulated WHERE season = ? ORDER BY team"
        result = conn.execute(query, [season]).fetchdf()
        
        # Convert to dictionary format
        baseline_wins = {}
        for _, row in result.iterrows():
            baseline_wins[row['team']] = float(row['wins'])
        
        return {"baseline_wins": baseline_wins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching baseline wins: {str(e)}")

@app.get("/api/seasons")
async def get_available_seasons():
    """Get all available seasons from the database"""
    try:
        query = "SELECT DISTINCT season FROM agg_team_txn_cnts ORDER BY season"
        result = conn.execute(query).fetchdf()
        
        seasons = result['season'].tolist() if not result.empty else []
        return {"seasons": seasons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching seasons: {str(e)}")

@app.get("/api/season-metrics")
async def get_season_metrics(season: str = '2024-25'):
    """Get season-end team metrics for a specific season"""
    try:
        query = """
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
        
        result = conn.execute(query, [season]).fetchdf()
        
        # Calculate min, median, max for each metric
        metrics_stats = {}
        numeric_columns = ['fg2_pct', 'FG3_PCT', 'FT_PCT', 'OREB_PCT', 'dreb_pct', 'TM_TOV_PCT',
                          'opp_fg2_pct', 'OPP_FG3_PCT', 'OPP_FT_PCT', 'OPP_OREB_PCT', 'opp_dreb_pct', 'OPP_TOV_PCT']
        
        for col in numeric_columns:
            if col in result.columns:
                values = result[col].dropna()
                if len(values) > 0:
                    metrics_stats[col] = {
                        'min': float(values.min()),
                        'median': float(values.median()),
                        'max': float(values.max())
                    }
        
        return {
            "metrics": result.to_dict('records'),
            "stats": metrics_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching season metrics: {str(e)}")

@app.get("/api/transition-matrix-adjustment-metrics/{team}")
async def get_transition_matrix_adjustment_metrics(team: str, season: str = '2024-25'):
    """Get transition matrix adjustment metrics for a specific team and season"""
    try:
        query = "SELECT * FROM team_transition_matrix_adjustments_rates WHERE team = ? AND season = ?"
        result = conn.execute(query, [team, season]).fetchdf()
        
        if result.empty:
            raise HTTPException(status_code=404, detail=f"No data found for team: {team} and season: {season}")
        
        return {"metrics": result.to_dict('records')[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transition matrix adjustment metrics: {str(e)}")

@app.post("/api/simulate")
async def simulate_season(request: dict):
    """Simulate multiple seasons for a team"""
    try:
        team = request.get("team")
        num_seasons = request.get("num_seasons", 10)
        season = request.get("season", "2024-25")
        
        if not team:
            raise HTTPException(status_code=400, detail="Team parameter is required")
        
        # Validate team exists
        team_check = conn.execute("SELECT COUNT(*) FROM agg_team_txn_cnts WHERE team = ? AND season = ?", [team, season]).fetchone()
        if team_check[0] == 0:
            raise HTTPException(status_code=404, detail=f"Team {team} not found in database for season {season}")
        
        # Get transition matrix adjustment metrics
        transition_metrics_response = await get_transition_matrix_adjustment_metrics(team, season)
        transition_metrics = transition_metrics_response.get('metrics', {})
        
        # Get season metrics for additional variables calculation
        season_metrics_response = await get_season_metrics(season)
        team_metrics = None
        for metric in season_metrics_response.get('metrics', []):
            if metric['team_abbreviation'] == team:
                team_metrics = metric
                break
        
        if not team_metrics:
            raise HTTPException(status_code=404, detail=f"No season metrics found for team: {team}")
        
        # Get adjusted metrics (this would come from frontend)
        # For now, we'll use original values
        adjusted_metrics = {
            'oreb_pct': team_metrics.get('OREB_PCT', 0),
            'opp_oreb_pct': team_metrics.get('OPP_OREB_PCT', 0)
        }
        
        # Calculate additional variables based on user adjustments
        # These would normally come from the frontend, but for now let's calculate them
        # based on the difference between adjusted and original metrics
        original_metrics = {
            'fg2_pct': team_metrics.get('fg2_pct', 0),
            'FG3_PCT': team_metrics.get('FG3_PCT', 0),
            'FT_PCT': team_metrics.get('FT_PCT', 0),
            'OREB_PCT': team_metrics.get('OREB_PCT', 0),
            'dreb_pct': team_metrics.get('dreb_pct', 0),
            'TM_TOV_PCT': team_metrics.get('TM_TOV_PCT', 0),
            'opp_fg2_pct': team_metrics.get('opp_fg2_pct', 0),
            'OPP_FG3_PCT': team_metrics.get('OPP_FG3_PCT', 0),
            'OPP_FT_PCT': team_metrics.get('OPP_FT_PCT', 0),
            'OPP_OREB_PCT': team_metrics.get('OPP_OREB_PCT', 0),
            'opp_dreb_pct': team_metrics.get('opp_dreb_pct', 0),
            'OPP_TOV_PCT': team_metrics.get('OPP_TOV_PCT', 0)
        }
        
        # Default to no adjustments (all values set to 0)
        additional_vars = {
            'additional_shots_made_2': 0,  # No change to 2pt shots
            'additional_shots_made_3': 0,  # No change to 3pt shots
            'additional_shots_made_ft': 0, # No change to FT
            'additional_turnovers': 0,     # No change to turnovers
            'additional_dreb': 0,          # No change to defensive rebounds
            'additional_oreb': 0,          # No change to offensive rebounds
            'opp_additional_shots_made_2': 0,  # No change to opponent 2pt shots
            'opp_additional_shots_made_3': 0,  # No change to opponent 3pt shots
            'opp_additional_shots_made_ft': 0, # No change to opponent FT
            'opp_additional_turnovers': 0,     # No change to opponent turnovers
            'opp_additional_dreb': 0,          # No change to opponent defensive rebounds
            'opp_additional_oreb': 0           # No change to opponent offensive rebounds
        }
        
        # Initialize simulator and run simulation
        simulator = MarkovSimulator(conn)
        results = simulator.simulate_multiple_seasons(
            team, num_seasons, additional_vars, transition_metrics, adjusted_metrics
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Simulation error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")

@app.post("/api/simulate/stream")
async def simulate_season_stream(request: dict):
    """Stream simulation results using Server-Sent Events"""
    try:
        print(f"Starting simulation for request: {request}")
        team = request.get('team')
        num_seasons = request.get('num_seasons', 10)
        season = request.get('season', '2024-25')
        
        if not team:
            raise HTTPException(status_code=400, detail="Team is required")
        
        # Check cache for transition metrics
        cache_key = f"{team}_{season}_transition_metrics"
        if cache_key not in _metrics_cache:
            print(f"Fetching transition matrix adjustment metrics for team: {team}")
            transition_metrics_response = await get_transition_matrix_adjustment_metrics(team, season)
            _metrics_cache[cache_key] = transition_metrics_response.get('metrics', {})
        else:
            print(f"Using cached transition metrics for team: {team}")
        
        transition_metrics = _metrics_cache[cache_key]
        print(f"Got transition metrics: {list(transition_metrics.keys())}")
        
        # Check cache for season metrics
        season_cache_key = f"season_metrics_{season}"
        if season_cache_key not in _metrics_cache:
            print(f"Fetching season metrics for team: {team}")
            season_metrics_response = await get_season_metrics(season)
            _metrics_cache[season_cache_key] = season_metrics_response
        else:
            print(f"Using cached season metrics")
        
        season_metrics_response = _metrics_cache[season_cache_key]
        team_metrics = None
        for metric in season_metrics_response.get('metrics', []):
            if metric['team_abbreviation'] == team:
                team_metrics = metric
                break
        
        if not team_metrics:
            raise HTTPException(status_code=404, detail=f"No season metrics found for team: {team}")
        print(f"Got team metrics for: {team}")
        
        # Get adjusted metrics (this would come from frontend)
        # For now, we'll use original values
        adjusted_metrics = {
            'oreb_pct': team_metrics.get('OREB_PCT', 0),
            'opp_oreb_pct': team_metrics.get('OPP_OREB_PCT', 0)
        }
        
        # Get additional variables and adjusted metrics from frontend request
        additional_vars = request.get('additional_vars', {})
        frontend_adjusted_metrics = request.get('adjusted_metrics', {})
        
        # Merge frontend adjusted metrics with our base metrics
        if frontend_adjusted_metrics:
            adjusted_metrics.update({
                'oreb_pct': frontend_adjusted_metrics.get('oreb_pct', adjusted_metrics['oreb_pct']),
                'opp_oreb_pct': frontend_adjusted_metrics.get('opp_oreb_pct', adjusted_metrics['opp_oreb_pct'])
            })
        
        # If no additional vars from frontend, default to no adjustments
        if not additional_vars:
            additional_vars = {
                'additional_shots_made_2': 0,  # No change to 2pt shots
                'additional_shots_made_3': 0,  # No change to 3pt shots
                'additional_shots_made_ft': 0, # No change to FT
                'additional_turnovers': 0,     # No change to turnovers
                'additional_dreb': 0,          # No change to defensive rebounds
                'additional_oreb': 0,          # No change to offensive rebounds
                'opp_additional_shots_made_2': 0,  # No change to opponent 2pt shots
                'opp_additional_shots_made_3': 0,  # No change to opponent 3pt shots
                'opp_additional_shots_made_ft': 0, # No change to opponent FT
                'opp_additional_turnovers': 0,     # No change to opponent turnovers
                'opp_additional_dreb': 0,          # No change to opponent defensive rebounds
                'opp_additional_oreb': 0           # No change to opponent offensive rebounds
            }
        
        print(f"Initializing simulator for team: {team}")
        # Initialize simulator
        simulator = MarkovSimulator(conn)
        
        # Track active simulation
        _active_simulations[team] = False
        
        print(f"Starting simulation with {num_seasons} seasons")
        
        # Helper function to calculate running statistics
        def calculate_running_statistics(expected_wins_list):
            """Calculate running statistics for the seasons completed so far"""
            if not expected_wins_list:
                return {
                    "average_expected_wins": 0,
                    "standard_deviation": 0,
                    "confidence_interval_95": 0,
                    "min_wins": 0,
                    "max_wins": 0,
                    "seasons_completed": 0
                }
            
            num_completed = len(expected_wins_list)
            avg_wins = np.mean(expected_wins_list)
            std_wins = np.std(expected_wins_list) if num_completed > 1 else 0
            confidence_interval_95 = 1.96 * std_wins / np.sqrt(num_completed) if num_completed > 1 else 0
            
            return {
                "average_expected_wins": round(avg_wins, 2),
                "standard_deviation": round(std_wins, 2),
                "confidence_interval_95": round(confidence_interval_95, 2),
                "min_wins": round(min(expected_wins_list), 2),
                "max_wins": round(max(expected_wins_list), 2),
                "seasons_completed": num_completed
            }
        
        # Simulate seasons with adjustments - stream as they complete
        def generate_results():
            all_expected_wins = []
            
            for season_num in range(1, num_seasons + 1):
                # Check for cancellation before starting each season
                if _active_simulations.get(team, False):
                    print(f"Simulation cancelled for team: {team}")
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Simulation cancelled by user'})}\n\n"
                    break
                
                print(f"Starting season {season_num}")
                # Simulate one season at a time
                season_result = simulator.simulate_season(
                    team, additional_vars, transition_metrics, adjusted_metrics
                )
                season_result["season"] = season_num
                season_result['transition_metrics_used'] = list(transition_metrics.keys())
                season_result['additional_vars_used'] = list(additional_vars.keys())
                
                # Add this season's expected wins to our running total
                all_expected_wins.append(season_result["final_expected_wins"])
                
                # Calculate running statistics for all seasons completed so far
                running_stats = calculate_running_statistics(all_expected_wins)
                season_result['running_statistics'] = running_stats
                
                print(f"Season {season_num} completed, streaming results with running stats")
                yield f"data: {json.dumps(season_result)}\n\n"
            
            # Send final statistics (same as before, but now also sent after each season)
            if not _active_simulations.get(team, False):  # Only if not cancelled
                print("Sending final statistics")
                final_stats = {
                    'type': 'final_statistics',
                    'statistics': running_stats  # Use the final running stats
                }
                yield f"data: {json.dumps(final_stats)}\n\n"
            
            # Clean up
            if team in _active_simulations:
                del _active_simulations[team]
        
        return StreamingResponse(generate_results(), media_type="text/plain")
        
    except Exception as e:
        print(f"Error in simulate_season_stream: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        error_data = {"error": str(e)}
        return HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/with-adjustments")
async def simulate_with_adjustments(request: dict):
    """Simulate multiple seasons with custom adjustments from frontend"""
    try:
        team = request.get("team")
        num_seasons = request.get("num_seasons", 10)
        season = request.get("season", "2024-25")
        additional_vars = request.get("additional_vars", {})
        adjusted_metrics = request.get("adjusted_metrics", {})
        
        if not team:
            raise HTTPException(status_code=400, detail="Team parameter is required")
        
        # Validate team exists
        team_check = conn.execute("SELECT COUNT(*) FROM agg_team_txn_cnts WHERE team = ? AND season = ?", [team, season]).fetchone()
        if team_check[0] == 0:
            raise HTTPException(status_code=404, detail=f"Team {team} not found in database for season {season}")
        
        # Check cache for transition metrics
        cache_key = f"{team}_{season}_transition_metrics"
        if cache_key not in _metrics_cache:
            transition_metrics_response = await get_transition_matrix_adjustment_metrics(team, season)
            _metrics_cache[cache_key] = transition_metrics_response.get('metrics', {})
        transition_metrics = _metrics_cache[cache_key]
        
        # Initialize simulator and run simulation with adjustments
        simulator = MarkovSimulator(conn)
        results = simulator.simulate_multiple_seasons(
            team, num_seasons, additional_vars, transition_metrics, adjusted_metrics
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Simulation error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")

@app.post("/api/simulate/with-adjustments/stream")
async def simulate_with_adjustments_stream(request: dict):
    """Stream simulation results with custom adjustments using Server-Sent Events"""
    try:
        team = request.get('team')
        num_seasons = request.get('num_seasons', 10)
        season = request.get('season', '2024-25')
        additional_vars = request.get('additional_vars', {})
        adjusted_metrics = request.get('adjusted_metrics', {})
        
        if not team:
            raise HTTPException(status_code=400, detail="Team is required")
        
        # Check cache for transition metrics
        cache_key = f"{team}_{season}_transition_metrics"
        if cache_key not in _metrics_cache:
            transition_metrics_response = await get_transition_matrix_adjustment_metrics(team, season)
            _metrics_cache[cache_key] = transition_metrics_response.get('metrics', {})
        transition_metrics = _metrics_cache[cache_key]
        
        # Track active simulation
        _active_simulations[team] = False
        
        # Initialize simulator
        simulator = MarkovSimulator(conn)
        
        # Simulate seasons with adjustments
        results = simulator.simulate_multiple_seasons(
            team, num_seasons, additional_vars, transition_metrics, adjusted_metrics
        )
        
        def generate_results():
            # Stream results
            for season_data in results['seasons']:
                # Check for cancellation before streaming each season
                if _active_simulations.get(team, False):
                    print(f"Simulation cancelled for team: {team}")
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Simulation cancelled by user'})}\n\n"
                    break
                
                season_data['transition_metrics_used'] = list(transition_metrics.keys())
                season_data['additional_vars_used'] = list(additional_vars.keys())
                season_data['adjusted_metrics_used'] = list(adjusted_metrics.keys())
                yield f"data: {json.dumps(season_data)}\n\n"
            
            # Send final statistics only if not cancelled
            if not _active_simulations.get(team, False):
                final_stats = {
                    'type': 'final_statistics',
                    'statistics': results['statistics']
                }
                yield f"data: {json.dumps(final_stats)}\n\n"
            
            # Clean up
            if team in _active_simulations:
                del _active_simulations[team]
        
        return StreamingResponse(generate_results(), media_type="text/plain")
        
    except Exception as e:
        error_data = {"error": str(e)}
        return HTTPException(status_code=500, detail=str(e))

@app.post("/generate-adjustments")
async def generate_adjustments(request: AdjustmentRequest):
    """Generate transition matrix adjustments for a specific team"""
    try:
        # Connect to database
        DB_PATH = os.getenv("DB_PATH", "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db")
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        # Get baseline data
        baseline_data = get_baseline_data(conn, request.team, request.season)
        
        # Calculate improvements based on percentage
        improvement_factor = 1 + (request.adjustment_percentage / 100)
        improved_metrics = calculate_improved_metrics(baseline_data['metrics'], improvement_factor)
        
        # Calculate additional variables
        additional_vars = calculate_additional_variables(baseline_data['metrics'], improved_metrics, baseline_data['team_attempts'])
        
        # Get transition metrics
        transition_metrics = baseline_data['transition_metrics']
        
        # Add team and season columns
        baseline_data['transitions']['team'] = request.team
        baseline_data['transitions']['season'] = request.season
        
        # Process adjustments
        all_results = []
        adjustment_types = [
            f'2PT FG% +{request.adjustment_percentage}%', f'3PT FG% +{request.adjustment_percentage}%', 
            f'FT% +{request.adjustment_percentage}%', f'OREB% +{request.adjustment_percentage}%', 
            f'DREB% +{request.adjustment_percentage}%', f'TOV% -{request.adjustment_percentage}%',
            f'OPP 2PT FG% -{request.adjustment_percentage}%', f'OPP 3PT FG% -{request.adjustment_percentage}%', 
            f'OPP FT% -{request.adjustment_percentage}%', f'OPP OREB% -{request.adjustment_percentage}%', 
            f'OPP DREB% -{request.adjustment_percentage}%', f'OPP TOV% +{request.adjustment_percentage}%'
        ]
        
        for adjustment_type in adjustment_types:
            # Create filtered variables for this metric
            filtered_vars = get_filtered_vars(adjustment_type, additional_vars)
            
            # Get adjustments
            adjustments = calculate_all_adjustments(request.team, filtered_vars, transition_metrics, improved_metrics)
            
            # Apply adjustments
            poss_per_game = baseline_data['metrics'].get('POSS', 98.8)
            results = apply_adjustments_for_metric(
                baseline_data['transitions'], adjustments, request.team, 
                transition_metrics, improved_metrics, poss_per_game, adjustment_type
            )
            all_results.extend(results)
        
        # Create DataFrame
        df = pd.DataFrame(all_results)
        
        # Save to temporary CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            df.to_csv(tmp_file.name, index=False)
            tmp_path = tmp_file.name
        
        conn.close()
        
        # Return file
        return FileResponse(
            tmp_path, 
            media_type='text/csv',
            filename=f"{request.team}_{request.season}_{request.adjustment_percentage}percent_adjustments.csv"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating adjustments: {str(e)}")

@app.get("/teams")
async def get_teams(season: str = "2024-25"):
    """Get list of available teams"""
    try:
        DB_PATH = os.getenv("DB_PATH", "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db")
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        teams_query = "SELECT DISTINCT team FROM agg_team_txn_cnts WHERE season = ? ORDER BY team"
        teams_df = conn.execute(teams_query, [season]).fetchdf()
        teams = teams_df['team'].tolist()
        
        conn.close()
        return {"teams": teams, "season": season}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting teams: {str(e)}")

