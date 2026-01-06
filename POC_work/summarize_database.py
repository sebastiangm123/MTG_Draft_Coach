#!/usr/bin/env python3
"""
Database Summary Script for MTG Draft Coach
Provides high-level validation and summary statistics for each table.
Outputs to CSV and prints to terminal.
"""

import sqlite3
import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Database path
DB_PATH = Path(__file__).parent / "mtg_draft_coach.db"

def get_table_summary(cursor, table_name, set_code):
    """Get summary statistics for a table."""
    summary = {
        'table_name': table_name,
        'set_code': set_code,
        'total_rows': 0,
        'rows_for_set': 0,
        'statistics': {}
    }
    
    # Get total row count
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        summary['total_rows'] = cursor.fetchone()[0]
    except sqlite3.Error as e:
        summary['error'] = str(e)
        return summary
    
    # Get row count for this set
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE "set" = ?', (set_code,))
        summary['rows_for_set'] = cursor.fetchone()[0]
    except sqlite3.Error:
        # Table might not have a "set" column
        summary['rows_for_set'] = summary['total_rows']
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Get statistics for numeric columns
    numeric_stats = {}
    for col in columns:
        if col in ['card_id', 'pick_id', 'game_id', 'draft_id', 'archetype_id', 
                   'card_stat_id', 'draft_summary_id', 'game_card_id', 'created_at', 
                   'last_updated', 'draft_time', 'game_time']:
            continue
        
        try:
            # Check if column has numeric data
            if 'set' in columns:
                query = f'SELECT MIN({col}), MAX({col}), AVG({col}), COUNT(*) FROM {table_name} WHERE "set" = ? AND {col} IS NOT NULL'
                cursor.execute(query, (set_code,))
            else:
                query = f'SELECT MIN({col}), MAX({col}), AVG({col}), COUNT(*) FROM {table_name} WHERE {col} IS NOT NULL'
                cursor.execute(query)
            
            result = cursor.fetchone()
            if result and result[3] > 0:  # If there are non-null values
                numeric_stats[col] = {
                    'min': result[0],
                    'max': result[1],
                    'avg': result[2],
                    'non_null_count': result[3]
                }
        except (sqlite3.Error, sqlite3.OperationalError):
            # Column might not be numeric or doesn't exist
            pass
    
    summary['statistics'] = numeric_stats
    
    # Get null counts for key columns
    null_counts = {}
    key_columns = ['card_name', 'color_identity', 'gih_wr', 'drawn_wr', 'overall_wr', 
                   'win_rate', 'main_colors', 'final_colors', 'won', 'rank']
    
    for col in key_columns:
        if col in columns:
            try:
                if 'set' in columns:
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE "set" = ? AND {col} IS NULL', (set_code,))
                else:
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL')
                null_counts[col] = cursor.fetchone()[0]
            except (sqlite3.Error, sqlite3.OperationalError):
                pass
    
    summary['null_counts'] = null_counts
    
    return summary

def get_detailed_statistics(cursor, set_code):
    """Get detailed statistics for each table."""
    stats = {}
    
    # 1. Cards table
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT color_identity) as unique_colors,
            COUNT(DISTINCT cmc) as unique_cmc,
            COUNT(CASE WHEN color_identity IS NULL THEN 1 END) as null_colors,
            COUNT(CASE WHEN cmc IS NULL THEN 1 END) as null_cmc
        FROM cards
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['cards'] = {
        'total_cards': row[0],
        'unique_color_identities': row[1],
        'unique_cmc_values': row[2],
        'null_color_identity': row[3],
        'null_cmc': row[4]
    }
    
    # 2. Card Statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN gih_wr IS NOT NULL THEN 1 END) as has_gih_wr,
            COUNT(CASE WHEN drawn_wr IS NOT NULL THEN 1 END) as has_drawn_wr,
            COUNT(CASE WHEN overall_wr IS NOT NULL THEN 1 END) as has_overall_wr,
            AVG(gih_wr) as avg_gih_wr,
            AVG(drawn_wr) as avg_drawn_wr,
            AVG(overall_wr) as avg_overall_wr,
            COUNT(CASE WHEN total_games >= 100 THEN 1 END) as cards_100_plus_games,
            COUNT(CASE WHEN total_games >= 50 THEN 1 END) as cards_50_plus_games
        FROM card_statistics
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['card_statistics'] = {
        'total_records': row[0],
        'has_gih_wr': row[1],
        'has_drawn_wr': row[2],
        'has_overall_wr': row[3],
        'avg_gih_wr': row[4],
        'avg_drawn_wr': row[5],
        'avg_overall_wr': row[6],
        'cards_100_plus_games': row[7],
        'cards_50_plus_games': row[8]
    }
    
    # 3. Color Archetypes
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT main_colors) as unique_main_colors,
            AVG(win_rate) as avg_win_rate,
            MIN(win_rate) as min_win_rate,
            MAX(win_rate) as max_win_rate,
            COUNT(CASE WHEN total_games >= 50 THEN 1 END) as archetypes_50_plus_games
        FROM color_archetypes
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['color_archetypes'] = {
        'total_archetypes': row[0],
        'unique_main_color_combos': row[1],
        'avg_win_rate': row[2],
        'min_win_rate': row[3],
        'max_win_rate': row[4],
        'archetypes_50_plus_games': row[5]
    }
    
    # 4. Draft Picks
    cursor.execute("""
        SELECT 
            COUNT(*) as total_picks,
            COUNT(DISTINCT draft_id) as unique_drafts,
            AVG(pick_number) as avg_pick_number,
            AVG(pack_number) as avg_pack_number,
            COUNT(CASE WHEN maindeck_rate IS NOT NULL THEN 1 END) as has_maindeck_rate
        FROM draft_picks
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['draft_picks'] = {
        'total_picks': row[0],
        'unique_drafts': row[1],
        'avg_pick_number': row[2],
        'avg_pack_number': row[3],
        'has_maindeck_rate': row[4]
    }
    
    # 5. Draft Summaries
    cursor.execute("""
        SELECT 
            COUNT(*) as total_drafts,
            AVG(win_rate) as avg_win_rate,
            AVG(total_games) as avg_games_per_draft,
            AVG(total_picks) as avg_picks_per_draft,
            COUNT(DISTINCT final_colors) as unique_color_combos,
            COUNT(CASE WHEN rank IS NOT NULL THEN 1 END) as has_rank
        FROM draft_summaries
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['draft_summaries'] = {
        'total_drafts': row[0],
        'avg_win_rate': row[1],
        'avg_games_per_draft': row[2],
        'avg_picks_per_draft': row[3],
        'unique_color_combos': row[4],
        'has_rank': row[5]
    }
    
    # 6. Game Results
    cursor.execute("""
        SELECT 
            COUNT(*) as total_games,
            COUNT(DISTINCT draft_id) as unique_drafts,
            SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as total_wins,
            SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) as total_losses,
            AVG(num_turns) as avg_turns,
            AVG(num_mulligans) as avg_mulligans,
            COUNT(DISTINCT main_colors) as unique_main_colors
        FROM game_results
        WHERE "set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    total_games = row[0] or 0
    total_wins = row[2] or 0
    stats['game_results'] = {
        'total_games': total_games,
        'unique_drafts': row[1],
        'total_wins': total_wins,
        'total_losses': row[3] or 0,
        'overall_win_rate': (total_wins / total_games) if total_games > 0 else 0,
        'avg_turns': row[4],
        'avg_mulligans': row[5],
        'unique_main_colors': row[6]
    }
    
    # 7. Game Cards
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT gc.game_id) as unique_games,
            COUNT(DISTINCT gc.card_id) as unique_cards,
            SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as in_opening_hand_count,
            SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as was_drawn_count
        FROM game_cards gc
        JOIN game_results gr ON gc.game_id = gr.game_id
        WHERE gr."set" = ?
    """, (set_code,))
    row = cursor.fetchone()
    stats['game_cards'] = {
        'total_records': row[0],
        'unique_games': row[1],
        'unique_cards': row[2],
        'in_opening_hand_count': row[3],
        'was_drawn_count': row[4]
    }
    
    return stats

def print_summary(detailed_stats, set_code):
    """Print summary to terminal."""
    print("=" * 80)
    print(f"MTG Draft Coach Database Summary - Set: {set_code}")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Cards
    print("[CARDS TABLE]")
    print("-" * 80)
    cs = detailed_stats['cards']
    print(f"  Total Cards: {cs['total_cards']:,}")
    print(f"  Unique Color Identities: {cs['unique_color_identities']}")
    print(f"  Unique CMC Values: {cs['unique_cmc_values']}")
    print(f"  Cards with NULL color_identity: {cs['null_color_identity']}")
    print(f"  Cards with NULL cmc: {cs['null_cmc']}")
    print()
    
    # Card Statistics
    print("[CARD STATISTICS TABLE]")
    print("-" * 80)
    cst = detailed_stats['card_statistics']
    print(f"  Total Records: {cst['total_records']:,}")
    print(f"  Cards with GIH WR: {cst['has_gih_wr']:,}")
    print(f"  Cards with Drawn WR: {cst['has_drawn_wr']:,}")
    print(f"  Cards with Overall WR: {cst['has_overall_wr']:,}")
    if cst['avg_gih_wr']:
        print(f"  Average GIH WR: {cst['avg_gih_wr']:.3f}")
    if cst['avg_drawn_wr']:
        print(f"  Average Drawn WR: {cst['avg_drawn_wr']:.3f}")
    if cst['avg_overall_wr']:
        print(f"  Average Overall WR: {cst['avg_overall_wr']:.3f}")
    print(f"  Cards with 100+ games: {cst['cards_100_plus_games']:,}")
    print(f"  Cards with 50+ games: {cst['cards_50_plus_games']:,}")
    print()
    
    # Color Archetypes
    print("[COLOR ARCHETYPES TABLE]")
    print("-" * 80)
    ca = detailed_stats['color_archetypes']
    print(f"  Total Archetypes: {ca['total_archetypes']:,}")
    print(f"  Unique Main Color Combinations: {ca['unique_main_color_combos']}")
    if ca['avg_win_rate']:
        print(f"  Average Win Rate: {ca['avg_win_rate']:.3f}")
        print(f"  Min Win Rate: {ca['min_win_rate']:.3f}")
        print(f"  Max Win Rate: {ca['max_win_rate']:.3f}")
    print(f"  Archetypes with 50+ games: {ca['archetypes_50_plus_games']:,}")
    print()
    
    # Draft Picks
    print("[DRAFT PICKS TABLE]")
    print("-" * 80)
    dp = detailed_stats['draft_picks']
    print(f"  Total Picks: {dp['total_picks']:,}")
    print(f"  Unique Drafts: {dp['unique_drafts']:,}")
    if dp['avg_pick_number']:
        print(f"  Average Pick Number: {dp['avg_pick_number']:.2f}")
    if dp['avg_pack_number']:
        print(f"  Average Pack Number: {dp['avg_pack_number']:.2f}")
    print(f"  Picks with Maindeck Rate: {dp['has_maindeck_rate']:,}")
    print()
    
    # Draft Summaries
    print("[DRAFT SUMMARIES TABLE]")
    print("-" * 80)
    ds = detailed_stats['draft_summaries']
    print(f"  Total Drafts: {ds['total_drafts']:,}")
    if ds['avg_win_rate']:
        print(f"  Average Win Rate: {ds['avg_win_rate']:.3f}")
    if ds['avg_games_per_draft']:
        print(f"  Average Games per Draft: {ds['avg_games_per_draft']:.2f}")
    if ds['avg_picks_per_draft']:
        print(f"  Average Picks per Draft: {ds['avg_picks_per_draft']:.2f}")
    print(f"  Unique Color Combinations: {ds['unique_color_combos']}")
    print(f"  Drafts with Rank: {ds['has_rank']:,}")
    print()
    
    # Game Results
    print("[GAME RESULTS TABLE]")
    print("-" * 80)
    gr = detailed_stats['game_results']
    print(f"  Total Games: {gr['total_games']:,}")
    print(f"  Unique Drafts: {gr['unique_drafts']:,}")
    print(f"  Total Wins: {gr['total_wins']:,}")
    print(f"  Total Losses: {gr['total_losses']:,}")
    print(f"  Overall Win Rate: {gr['overall_win_rate']:.3f}")
    if gr['avg_turns']:
        print(f"  Average Turns: {gr['avg_turns']:.2f}")
    if gr['avg_mulligans']:
        print(f"  Average Mulligans: {gr['avg_mulligans']:.2f}")
    print(f"  Unique Main Color Combinations: {gr['unique_main_colors']}")
    print()
    
    # Game Cards
    print("[GAME CARDS TABLE]")
    print("-" * 80)
    gc = detailed_stats['game_cards']
    print(f"  Total Records: {gc['total_records']:,}")
    print(f"  Unique Games: {gc['unique_games']:,}")
    print(f"  Unique Cards: {gc['unique_cards']:,}")
    print(f"  Cards in Opening Hand: {gc['in_opening_hand_count']:,}")
    print(f"  Cards Drawn: {gc['was_drawn_count']:,}")
    print()
    
    # Data Quality Checks
    print("[DATA QUALITY CHECKS]")
    print("-" * 80)
    issues = []
    
    if cst['has_overall_wr'] < cst['total_records'] * 0.9:
        issues.append(f"WARNING: Only {cst['has_overall_wr']}/{cst['total_records']} cards have overall_wr")
    
    if ca['archetypes_50_plus_games'] < ca['total_archetypes'] * 0.5:
        issues.append(f"WARNING: Only {ca['archetypes_50_plus_games']}/{ca['total_archetypes']} archetypes have 50+ games")
    
    if cs['null_color_identity'] > 0:
        issues.append(f"WARNING: {cs['null_color_identity']} cards have NULL color_identity")
    
    if cs['null_cmc'] > 0:
        issues.append(f"WARNING: {cs['null_cmc']} cards have NULL cmc")
    
    if not issues:
        print("  OK: No major data quality issues detected")
    else:
        for issue in issues:
            print(f"  {issue}")
    
    print()
    print("=" * 80)

def export_to_csv(detailed_stats, set_code, output_file):
    """Export summary to CSV."""
    rows = []
    
    # Flatten the statistics into rows
    for table_name, stats in detailed_stats.items():
        row = {'table': table_name, 'set': set_code}
        row.update(stats)
        rows.append(row)
    
    # Write to CSV
    if rows:
        fieldnames = set()
        for row in rows:
            fieldnames.update(row.keys())
        fieldnames = sorted(fieldnames)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                # Fill missing keys with None
                full_row = {k: row.get(k, None) for k in fieldnames}
                writer.writerow(full_row)
        
        print(f"OK: Summary exported to: {output_file}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python summarize_database.py <SET_CODE> [output_csv]")
        print("Example: python summarize_database.py TLA")
        print("Example: python summarize_database.py TLA summary.csv")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    output_csv = sys.argv[2] if len(sys.argv) > 2 else f"database_summary_{set_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            
            # Check if set exists
            cursor.execute('SELECT COUNT(*) FROM cards WHERE "set" = ?', (set_code,))
            if cursor.fetchone()[0] == 0:
                print(f"Error: No data found for set '{set_code}'")
                print("Available sets:")
                cursor.execute('SELECT DISTINCT "set" FROM cards')
                sets = [row[0] for row in cursor.fetchall()]
                for s in sets:
                    print(f"  - {s}")
                sys.exit(1)
            
            # Get detailed statistics
            print("Generating database summary...")
            detailed_stats = get_detailed_statistics(cursor, set_code)
            
            # Print to terminal
            print_summary(detailed_stats, set_code)
            
            # Export to CSV
            output_path = Path(__file__).parent / output_csv
            export_to_csv(detailed_stats, set_code, output_path)
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

