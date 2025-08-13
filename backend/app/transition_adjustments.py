from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import duckdb
import tempfile
import os
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI(title="NBA Transition Matrix Adjustments API")

class AdjustmentRequest(BaseModel):
    team: str
    season: str = "2024-25"
    adjustment_percentage: float = 5.0

@app.get("/")
async def root():
    return {"message": "NBA Transition Matrix Adjustments API", "version": "1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/generate-adjustments")
async def generate_adjustments(request: AdjustmentRequest):
    """Generate transition matrix adjustments for a specific team"""
    try:
        # Connect to database
        DB_PATH = os.getenv("DB_PATH", "nba_clean.db")
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
        DB_PATH = os.getenv("DB_PATH", "nba_clean.db")
        conn = duckdb.connect(DB_PATH, read_only=True)
        
        teams_query = "SELECT DISTINCT team FROM agg_team_txn_cnts WHERE season = ? ORDER BY team"
        teams_df = conn.execute(teams_query, [season]).fetchdf()
        teams = teams_df['team'].tolist()
        
        conn.close()
        return {"teams": teams, "season": season}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting teams: {str(e)}")

# Import the functions from the existing script
# Note: You'll need to copy the helper functions from generate_transition_adjustments.py
