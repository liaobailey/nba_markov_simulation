import numpy as np
import pandas as pd
from typing import List, Dict, Any

class MarkovSimulator:
    def __init__(self, db_connection):
        self.conn = db_connection
        
        # Cache for performance optimization
        self._transition_matrix_cache = {}
        self._metrics_cache = {}
        self._last_cache_key = None
        self._debug_mode = False  # Disable verbose logging by default
    
    def get_scoring_states(self, team: str) -> Dict[str, int]:
        """Define scoring states and their point values"""
        return {
            f"{team} 2pt Made": 2,
            f"{team} 3pt Made": 3,
            f"{team} FT Made": 1,
            f"OPP 2pt Made": 2,
            f"OPP 3pt Made": 3,
            f"OPP FT Made": 1,
        }
    
    def _get_cache_key(self, team: str, additional_vars: dict, transition_metrics: dict, adjusted_metrics: dict) -> str:
        """Generate a cache key for the transition matrix"""
        if not additional_vars or not transition_metrics or not adjusted_metrics:
            return f"{team}_base"
        
        # Create a hash of the key parameters
        import hashlib
        key_data = f"{team}_{str(sorted(additional_vars.items()))}_{str(sorted(transition_metrics.items()))}_{str(sorted(adjusted_metrics.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def build_transition_matrix(self, agg_team: pd.DataFrame, team: str, additional_vars: dict = None, 
                               transition_metrics: dict = None, adjusted_metrics: dict = None) -> pd.DataFrame:
        """Build transition matrix from aggregated team data with optional adjustments"""
        # Check cache first
        cache_key = self._get_cache_key(team, additional_vars, transition_metrics, adjusted_metrics)
        if cache_key in self._transition_matrix_cache:
            print(f"  Using cached transition matrix for {team}")
            return self._transition_matrix_cache[cache_key]
        
        print(f"  Building new transition matrix for {team}")
        
        # Filter for the selected team
        transition_df = agg_team[agg_team['team'] == team]
        
        # Build transition counts
        counts = transition_df.pivot_table(
            index="state",
            columns="next_state",
            values="count",
            aggfunc="sum",
            fill_value=0
        )
        
        # Apply adjustments if provided (check if dictionaries have content)
        if additional_vars and transition_metrics and adjusted_metrics and len(additional_vars) > 0:
            counts = self.apply_transition_adjustments(counts, team, additional_vars, transition_metrics, adjusted_metrics)
        
        # Normalize to create transition probabilities
        transition_matrix = counts.div(counts.sum(axis=1), axis=0).fillna(0)
        
        # Enforce basketball logic for specific states
        forced_transitions = {
            f"{team} 2pt Made": "OPP Offense Start",
            f"{team} 3pt Made": "OPP Offense Start",
            f"OPP 2pt Made": f"{team} Offense Start",
            f"OPP 3pt Made": f"{team} Offense Start",
            f"{team} Defensive Rebound": f"{team} Offense Start",
            "OPP Defensive Rebound": "OPP Offense Start"
        }
        
        for state, forced_next in forced_transitions.items():
            if state in transition_matrix.index and forced_next in transition_matrix.columns:
                # Zero out existing row and force 100% probability to forced_next
                transition_matrix.loc[state] = 0.0
                transition_matrix.at[state, forced_next] = 1.0
        
        # Cache the result
        self._transition_matrix_cache[cache_key] = transition_matrix
        
        return transition_matrix
    
    def apply_transition_adjustments(self, counts: pd.DataFrame, team: str, additional_vars: dict, 
                                   transition_metrics: dict, adjusted_metrics: dict) -> pd.DataFrame:
        """Apply comprehensive transition matrix adjustments based on user formulas"""
        # Create a copy to avoid modifying original
        adjusted_counts = counts.copy()
        
        # Get adjusted metrics with fallbacks
        oreb_per = adjusted_metrics.get('oreb_pct', 0)
        opp_oreb_per = adjusted_metrics.get('opp_oreb_pct', 0)
        
        # Apply all adjustments
        adjustments = self.calculate_all_adjustments(team, additional_vars, transition_metrics, adjusted_metrics)
        
        # Group adjustments by state for vectorized operations
        adjustment_groups = {}
        for adj in adjustments:
            state = adj['state']
            if state not in adjustment_groups:
                adjustment_groups[state] = []
            adjustment_groups[state].append(adj)
        
        # Apply adjustments vectorized by state
        for state, state_adjustments in adjustment_groups.items():
            if state in adjusted_counts.index:
                # Create adjustment vector for this state
                adjustment_vector = pd.Series(0.0, index=adjusted_counts.columns)
                
                for adj in state_adjustments:
                    next_state = adj['next_state']
                    if next_state in adjusted_counts.columns:
                        adjustment_vector[next_state] += adj['adjustment']
                
                # Apply all adjustments for this state at once
                adjusted_counts.loc[state] += adjustment_vector
                
                # Log non-zero adjustments (only in debug mode)
                if hasattr(self, '_debug_mode') and self._debug_mode:
                    non_zero_adjustments = adjustment_vector[abs(adjustment_vector) > 0.01]
                    for next_state, adj_value in non_zero_adjustments.items():
                        print(f"  ADJUSTMENT: {state} -> {next_state}")
                        print(f"    Adjustment: {adj_value:.2f}")
        
        # Force any negative counts to 0 AFTER all adjustments are complete
        for state in adjusted_counts.index:
            for next_state in adjusted_counts.columns:
                if adjusted_counts.at[state, next_state] < 0:
                    print(f"  FORCING TO 0: {state} -> {next_state} (was: {adjusted_counts.at[state, next_state]:.2f})")
                    adjusted_counts.at[state, next_state] = 0
        
        # Validate adjustments AFTER all adjustments are complete
        self.validate_adjustments(adjusted_counts, counts)
        
        # Print summary of row total changes
        print(f"\nSUMMARY OF ROW TOTAL CHANGES:")
        for state in adjusted_counts.index:
            if state in counts.index:
                original_total = counts.loc[state].sum()
                adjusted_total = adjusted_counts.loc[state].sum()
                if abs(adjusted_total - original_total) > 0.01:  # Only show significant changes
                    print(f"  {state}: {original_total:.1f} -> {adjusted_total:.1f} (change: {adjusted_total - original_total:+.1f})")
        
        return adjusted_counts
    
    def calculate_all_adjustments(self, team: str, additional_vars: dict, 
                                transition_metrics: dict, adjusted_metrics: dict) -> List[Dict]:
        """Calculate all transition adjustments based on user formulas"""
        print(f"Starting calculate_all_adjustments for team: {team}")
        adjustments = []
        
        # Get all the required variables
        oreb_per = adjusted_metrics.get('oreb_pct', 0)
        opp_oreb_per = adjusted_metrics.get('opp_oreb_pct', 0)
        print(f"Got adjusted metrics - oreb_per: {oreb_per}, opp_oreb_per: {opp_oreb_per}")
        
        # Team 2pt adjustments
        if 'additional_shots_made_2' in additional_vars:
            print("Processing 2pt adjustments")
            adj_2pt = additional_vars['additional_shots_made_2']
            per_2pt_oreb = transition_metrics.get('per_2pt_made_from_oreb', 0)
            per_2pt_offense = transition_metrics.get('per_2pt_made_from_offense_start_tov', 0)
            
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
            print("Processing 3pt adjustments")
            adj_3pt = additional_vars['additional_shots_made_3']
            per_3pt_oreb = transition_metrics.get('per_3pt_made_from_oreb', 0)
            per_3pt_offense = transition_metrics.get('per_3pt_made_from_offense_start_tov', 0)
            
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
            print("Processing FT adjustments")
            adj_ft = additional_vars['additional_shots_made_ft']
            per_ft_oreb = transition_metrics.get('per_ft_made_from_oreb', 0)
            per_ft_offense = transition_metrics.get('per_ft_made_from_offense_start', 0)
            per_ft_made = transition_metrics.get('per_ft_made_from_ft_made', 0)
            
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
            print("Processing turnover adjustments")
            adj_tov = additional_vars['additional_turnovers']
            per_tov_oreb = transition_metrics.get('per_turnover_from_oreb', 0)
            per_2pt_tov = transition_metrics.get('per_2pt_made_from_offense_start_tov', 0)
            per_3pt_tov = transition_metrics.get('per_3pt_made_from_offense_start_tov', 0)
            per_ft_tov = transition_metrics.get('per_ft_made_from_offense_start_tov', 0)
            per_oreb_tov = transition_metrics.get('per_oreb_from_offense_start_tov', 0)
            per_opp_dreb_tov = transition_metrics.get('per_opp_dreb_from_offense_start_tov', 0)
            per_2pt_oreb_tov = transition_metrics.get('per_2pt_made_from_oreb_tov', 0)
            per_3pt_oreb_tov = transition_metrics.get('per_3pt_made_from_oreb_tov', 0)
            per_ft_oreb_tov = transition_metrics.get('per_ft_made_from_oreb_tov', 0)
            per_oreb_oreb_tov = transition_metrics.get('per_oreb_from_oreb_tov', 0)
            per_opp_dreb_oreb_tov = transition_metrics.get('per_opp_dreb_from_oreb_tov', 0)
            
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
            per_dreb_opp_oreb = transition_metrics.get('per_dreb_from_opp_oreb', 0)
            
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
            per_oreb_from_oreb = transition_metrics.get('per_oreb_from_oreb', 0)
            
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
            per_2pt_oreb_opp = transition_metrics.get('per_2pt_made_from_oreb_opp', 0)
            
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
            per_3pt_oreb_opp = transition_metrics.get('per_3pt_made_from_oreb_opp', 0)
            
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
            per_ft_offense_opp = transition_metrics.get('per_ft_made_from_offense_start_opp', 0)
            per_ft_oreb_opp = transition_metrics.get('per_ft_made_from_oreb_opp', 0)
            per_ft_made_opp = transition_metrics.get('per_ft_made_from_ft_made_opp', 0)
            
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
            adj_opp_tov = additional_vars['opp_additional_turnovers']
            per_tov_oreb_opp = transition_metrics.get('per_turnover_from_oreb_opp', 0)
            per_2pt_offense_tov_opp = transition_metrics.get('per_2pt_made_from_offense_start_tov_opp', 0)
            per_3pt_offense_tov_opp = transition_metrics.get('per_3pt_made_from_offense_start_tov_opp', 0)
            per_ft_offense_tov_opp = transition_metrics.get('per_ft_made_from_offense_start_tov_opp', 0)
            per_oreb_offense_tov_opp = transition_metrics.get('per_oreb_from_offense_start_tov_opp', 0)
            per_dreb_offense_tov_opp = transition_metrics.get('per_dreb_from_offense_start_tov_opp', 0)
            per_2pt_oreb_tov_opp = transition_metrics.get('per_2pt_made_from_oreb_tov_opp', 0)
            per_3pt_oreb_tov_opp = transition_metrics.get('per_3pt_made_from_oreb_tov_opp', 0)
            per_ft_oreb_tov_opp = transition_metrics.get('per_ft_made_from_oreb_tov_opp', 0)
            per_oreb_oreb_tov_opp = transition_metrics.get('per_oreb_from_oreb_tov_opp', 0)
            per_dreb_oreb_tov_opp = transition_metrics.get('per_dreb_from_oreb_tov_opp', 0)
            
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
            per_opp_dreb_from_oreb = transition_metrics.get('per_opp_dreb_from_oreb', 0)
            
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
            per_opp_oreb_from_oreb_opp = transition_metrics.get('per_opp_oreb_from_oreb_opp', 0)
            
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
        
        print(f"calculate_all_adjustments completed, returning {len(adjustments)} adjustments")
        return adjustments
    
    def validate_adjustments(self, adjusted_counts: pd.DataFrame, original_counts: pd.DataFrame):
        """Validate that adjustments maintain proper constraints after all adjustments are complete"""
        for state in adjusted_counts.index:
            if state in original_counts.index:
                # Check that no counts are negative
                negative_counts = adjusted_counts.loc[state][adjusted_counts.loc[state] < 0]
                if not negative_counts.empty:
                    raise ValueError(f"Negative counts found for {state}: {negative_counts.to_dict()}")
                
                # Check that the row has some positive counts (can't have all zeros)
                row_sum = adjusted_counts.loc[state].sum()
                if row_sum <= 0:
                    raise ValueError(f"Row {state} has no positive counts after adjustments")
                
                # Check that probabilities sum to 1 (after normalization)
                probabilities = adjusted_counts.loc[state] / row_sum
                prob_sum = probabilities.sum()
                if abs(prob_sum - 1.0) > 0.01:
                    raise ValueError(f"Probabilities for {state} don't sum to 1: {prob_sum}")
                
                # Log the adjustment impact for debugging
                original_total = original_counts.loc[state].sum()
                adjusted_total = adjusted_counts.loc[state].sum()
                if abs(adjusted_total - original_total) > 0.1:  # Log significant changes
                    print(f"Info: Row {state} total changed from {original_total:.1f} to {adjusted_total:.1f}")
    
    def simulate_possession(self, start_state: str, transition_matrix: pd.DataFrame, team: str) -> int:
        """Simulate a single possession - optimized version"""
        state = start_state
        points = 0
        scoring_states = self.get_scoring_states(team)
        max_steps = 50  # prevent infinite loops
        steps = 0
        
        # Pre-convert to numpy arrays for faster access
        if not hasattr(self, '_transition_matrix_np'):
            self._transition_matrix_np = transition_matrix.values
            self._state_to_idx = {state: i for i, state in enumerate(transition_matrix.index)}
            self._idx_to_state = {i: state for i, state in enumerate(transition_matrix.index)}
            self._col_to_idx = {col: i for i, col in enumerate(transition_matrix.columns)}
        
        while steps < max_steps:
            steps += 1
            if state not in self._state_to_idx:
                break
            
            # Use pre-computed numpy arrays
            state_idx = self._state_to_idx[state]
            probs = self._transition_matrix_np[state_idx]
            next_state_idx = np.random.choice(len(probs), p=probs)
            next_state = self._idx_to_state[next_state_idx]
            
            if next_state in scoring_states:
                points += scoring_states[next_state]
            
            if start_state.startswith(team) and next_state == "OPP Offense Start":
                break
            if start_state.startswith("OPP") and next_state == f"{team} Offense Start":
                break
            
            state = next_state
        
        return points
    
    def simulate_game(self, transition_matrix: pd.DataFrame, team: str, possessions_per_team: int) -> tuple:
        """Simulate one full game - optimized version"""
        # Vectorize multiple possessions for better performance
        team_score = sum(self.simulate_possession(f"{team} Offense Start", transition_matrix, team) 
                        for _ in range(possessions_per_team))
        opp_score = sum(self.simulate_possession("OPP Offense Start", transition_matrix, team) 
                       for _ in range(possessions_per_team))
        
        return team_score, opp_score
    
    def simulate_season(self, team: str, additional_vars: dict = None, 
                        transition_metrics: dict = None, adjusted_metrics: dict = None) -> Dict[str, Any]:
        """Simulate one full season (82 games) and return results"""
        # Get team data from database
        agg_team = self.conn.execute(
            "SELECT * FROM agg_team_txn_cnts WHERE team = ?", 
            [team]
        ).fetchdf()
        
        if agg_team.empty:
            raise ValueError(f"No data found for team: {team}")
        
        # Build transition matrix with optional adjustments
        transition_matrix = self.build_transition_matrix(
            agg_team, team, additional_vars, transition_metrics, adjusted_metrics
        )
        
        # Get possessions per game
        team_poss = agg_team.loc[agg_team['team'] == team, 'poss_per_game'].values
        if len(team_poss) == 0:
            raise ValueError(f"No 'poss_per_game' found for team: {team}")
        possessions_per_team = int(round(team_poss[0]))
        
        # Simulate 82 games
        wins = 0
        games_data = []
        
        for game in range(1, 83):
            team_score, opp_score = self.simulate_game(transition_matrix, team, possessions_per_team)
            if team_score > opp_score:
                wins += 1
            
            # Calculate expected wins after this game
            win_pct = wins / game
            expected_wins = win_pct * 82
            
            games_data.append({
                "game": game,
                "expected_wins": round(expected_wins, 2),
                "team_score": team_score,
                "opp_score": opp_score,
                "is_win": team_score > opp_score
            })
        
        return {
            "games": games_data,
            "final_expected_wins": round((wins / 82) * 82, 2),
            "total_wins": wins,
            "win_percentage": round(wins / 82, 3)
        }
    
    def simulate_multiple_seasons(self, team: str, num_seasons: int = 10, 
                                additional_vars: dict = None, transition_metrics: dict = None, 
                                adjusted_metrics: dict = None) -> Dict[str, Any]:
        """Simulate multiple seasons and return all results - optimized version"""
        # Build transition matrix once and reuse for all seasons - optimized query
        agg_team = self.conn.execute(
            "SELECT state, next_state, count, poss_per_game FROM agg_team_txn_cnts WHERE team = ?", 
            [team]
        ).fetchdf()
        
        if agg_team.empty:
            raise ValueError(f"No data found for team: {team}")
        
        transition_matrix = self.build_transition_matrix(
            agg_team, team, additional_vars, transition_metrics, adjusted_metrics
        )
        
        # Get possessions per game once
        team_poss = agg_team.loc[agg_team['team'] == team, 'poss_per_game'].values
        if len(team_poss) == 0:
            raise ValueError(f"No 'poss_per_game' found for team: {team}")
        possessions_per_team = int(round(team_poss[0]))
        
        seasons_data = []
        all_expected_wins = []
        
        # Pre-allocate arrays for better performance
        seasons_data = []
        all_expected_wins = []
        
        for season in range(num_seasons):
            # Simulate 82 games directly without rebuilding transition matrix
            wins = 0
            
            # Vectorized game simulation for better performance
            for game in range(82):  # 0-81 instead of 1-83
                team_score, opp_score = self.simulate_game(transition_matrix, team, possessions_per_team)
                if team_score > opp_score:
                    wins += 1
            
            final_wins = round((wins / 82) * 82, 2)
            win_pct = round(wins / 82, 3)
            
            seasons_data.append({
                "season": season + 1,
                "final_expected_wins": final_wins,
                "total_wins": wins,
                "win_percentage": win_pct
            })
            
            all_expected_wins.append(final_wins)
        
        # Calculate statistics
        avg_wins = np.mean(all_expected_wins)
        std_wins = np.std(all_expected_wins)
        confidence_interval_95 = 1.96 * std_wins / np.sqrt(num_seasons)
        
        return {
            "seasons": seasons_data,
            "statistics": {
                "average_expected_wins": round(avg_wins, 2),
                "standard_deviation": round(std_wins, 2),
                "confidence_interval_95": round(confidence_interval_95, 2),
                "min_wins": round(min(all_expected_wins), 2),
                "max_wins": round(max(all_expected_wins), 2)
            }
        }
