#!/usr/bin/env python3
"""
Simple Transition Matrix Comparison

This script reads the CSV data and shows the 2PT FG% adjustments for LAC
to help verify against live simulation results.
"""

import pandas as pd
import duckdb

def main():
    """Main function to show CSV data for comparison"""
    print("Transition Matrix Adjustment Comparison")
    print("=" * 60)
    print("Team: LAC | Focus: 2PT FG% +2% adjustments")
    print("=" * 60)
    
    try:
        # Read the CSV we generated
        print("\n1. Loading CSV data...")
        df = pd.read_csv("transition_matrix_2percent_adjustments.csv")
        print(f"✅ Loaded CSV with {len(df)} total rows")
        
        # Filter for LAC team and 2PT FG% +2% adjustment
        lac_2pt = df[
            (df['team'] == 'LAC') & 
            (df['adjustment_type'] == '2PT FG% +2%')
        ].copy()
        
        print(f"✅ Found {len(lac_2pt)} rows for LAC 2PT FG% +2%")
        
        # Show summary stats
        print(f"\n2. Summary Statistics:")
        print(f"   - Total state combinations: {len(lac_2pt)}")
        print(f"   - Unique states: {lac_2pt['state'].nunique()}")
        print(f"   - Unique next states: {lac_2pt['next_state'].nunique()}")
        print(f"   - Possessions per game: {lac_2pt['poss_per_game'].iloc[0]:.1f}")
        
        # Show sample data
        print(f"\n3. Sample Data (first 10 rows):")
        print("-" * 80)
        sample_cols = ['state', 'next_state', 'counts', 'poss_per_game']
        print(lac_2pt[sample_cols].head(10).to_string(index=False))
        
        # Show counts distribution
        print(f"\n4. Counts Distribution:")
        print("-" * 40)
        counts_stats = lac_2pt['counts'].describe()
        print(f"   - Min: {counts_stats['min']:.2f}")
        print(f"   - 25%: {counts_stats['25%']:.2f}")
        print(f"   - 50%: {counts_stats['50%']:.2f}")
        print(f"   - 75%: {counts_stats['75%']:.2f}")
        print(f"   - Max: {counts_stats['max']:.2f}")
        print(f"   - Mean: {counts_stats['mean']:.2f}")
        print(f"   - Std: {counts_stats['std']:.2f}")
        
        # Show top transitions by count
        print(f"\n5. Top 10 Transitions by Count:")
        print("-" * 50)
        top_transitions = lac_2pt.nlargest(10, 'counts')[['state', 'next_state', 'counts']]
        print(top_transitions.to_string(index=False))
        
        # Show bottom transitions by count
        print(f"\n6. Bottom 10 Transitions by Count:")
        print("-" * 50)
        bottom_transitions = lac_2pt.nsmallest(10, 'counts')[['state', 'next_state', 'counts']]
        print(bottom_transitions.to_string(index=False))
        
        print(f"\n✅ CSV Analysis Complete!")
        print(f"\nTo compare with live simulation:")
        print(f"1. Your LAC simulation shows 56.04% 2PT FG%")
        print(f"2. This CSV shows theoretical 2% increase adjustments")
        print(f"3. The counts above show how transitions change with 2% better 2PT FG%")
        
    except FileNotFoundError:
        print("❌ CSV file not found. Please run generate_transition_adjustments.py first.")
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
