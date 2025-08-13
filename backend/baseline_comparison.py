#!/usr/bin/env python3
"""
Baseline Transition Counts for LAC

This script shows the baseline transition counts for LAC team
to compare with the adjusted counts from the CSV.
"""

import duckdb

def main():
    """Main function to show baseline data"""
    print("Baseline Transition Counts for LAC")
    print("=" * 50)
    print("Team: LAC | Baseline (no adjustments)")
    print("=" * 50)
    
    # Database connection
    DB_PATH = "/Users/baileyliao/PycharmProjects/cleannbadata/nba_clean.db"
    
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        print(f"✅ Connected to database: {DB_PATH}")
        
        # Get baseline transition counts for LAC
        print("\n1. Getting baseline transition counts...")
        baseline_query = """
        SELECT state, next_state, count
        FROM agg_team_txn_cnts 
        WHERE team = 'LAC' 
        ORDER BY count DESC
        LIMIT 20
        """
        
        baseline_data = conn.execute(baseline_query).fetchdf()
        print(f"✅ Found {len(baseline_data)} baseline transitions")
        
        # Show top baseline transitions
        print(f"\n2. Top 20 Baseline Transitions by Count:")
        print("-" * 60)
        print(baseline_data.to_string(index=False))
        
        # Get possessions per game
        poss_query = """
        SELECT poss_per_game 
        FROM agg_team_txn_cnts 
        WHERE team = 'LAC' 
        LIMIT 1
        """
        poss_result = conn.execute(poss_query).fetchdf()
        if not poss_result.empty:
            poss_per_game = poss_result.iloc[0]['poss_per_game']
            print(f"\n3. Possessions per game: {poss_per_game:.1f}")
        
        # Get team metrics
        print(f"\n4. Team Metrics (2024-25 season):")
        print("-" * 40)
        metrics_query = """
        SELECT 
            team_abbreviation,
            fg2_pct,
            fg3_pct,
            ft_pct,
            oreb_pct,
            dreb_pct,
            tov_pct
        FROM fact_team_season_box ftsb
        JOIN dim_team dt ON ftsb.team_id = dt.team_id
        WHERE team_abbreviation = 'LAC' AND season = '2024-25'
        """
        
        # Let me check what columns are actually available
        print("Checking available columns...")
        check_query = """
        SELECT * FROM fact_team_season_box ftsb
        JOIN dim_team dt ON ftsb.team_id = dt.team_id
        WHERE team_abbreviation = 'LAC' AND season = '2024-25'
        LIMIT 1
        """
        
        check_data = conn.execute(check_query).fetchdf()
        if not check_data.empty:
            print(f"Available columns: {list(check_data.columns)}")
            
            # Try to get basic shooting data
            if 'fg2_pct' in check_data.columns:
                metrics = check_data.iloc[0]
                print(f"   - 2PT FG%: {metrics['fg2_pct']:.3f}")
                print(f"   - 3PT FG%: {metrics['fg3_pct']:.3f}")
                print(f"   - FT%: {metrics['ft_pct']:.3f}")
                print(f"   - OREB%: {metrics['oreb_pct']:.3f}")
                print(f"   - DREB%: {metrics['dreb_pct']:.3f}")
                print(f"   - TOV%: {metrics['tov_pct']:.3f}")
            else:
                print("   - Basic shooting percentages not found in this table")
                print("   - Check fact_team_season_box structure")
        
        print(f"\n✅ Baseline Analysis Complete!")
        print(f"\nComparison Summary:")
        print(f"1. Baseline transition counts shown above")
        print(f"2. CSV shows 2% increase adjustments (from previous script)")
        print(f"3. Your simulation shows 56.04% 2PT FG% (with 43.37 additional 2PT made)")
        print(f"4. The CSV counts show how transitions change with theoretical 2% improvement")
        print(f"\nKey Baseline Transitions for LAC:")
        print(f"   - LAC DREB → LAC Offense Start: {baseline_data.iloc[0]['count']}")
        print(f"   - OPP DREB → OPP Offense Start: {baseline_data.iloc[1]['count']}")
        print(f"   - LAC 2pt Made → OPP Offense Start: {baseline_data.iloc[4]['count']}")
        print(f"   - LAC Offense Start → LAC 2pt Made: {baseline_data.iloc[6]['count']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print(f"\nDatabase connection closed")

if __name__ == "__main__":
    main()
