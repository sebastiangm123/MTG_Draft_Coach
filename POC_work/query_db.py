#!/usr/bin/env python3
"""
Simple script to query the MTG Draft Coach database.
Usage: python query_db.py
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "mtg_draft_coach.db"

def query_database(query, db_path=None):
    """Execute a query and return results."""
    if db_path is None:
        db_path = DB_PATH
    
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        return None
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def print_results(results, headers=None):
    """Pretty print query results."""
    if results is None:
        return
    
    if not results:
        print("No results found.")
        return
    
    if headers:
        # Print header
        header_str = " | ".join(headers)
        print(header_str)
        print("-" * len(header_str))
    
    # Print rows
    for row in results:
        formatted_row = []
        for x in row:
            if x is None:
                formatted_row.append("N/A")
            elif isinstance(x, float):
                formatted_row.append(f"{x:.3f}")
            else:
                formatted_row.append(str(x))
        print(" | ".join(formatted_row))

def example_queries():
    """Run example queries."""
    
    print("=" * 70)
    print("MTG Draft Coach Database - Example Queries")
    print("=" * 70)
    
    # Query 1: Top cards by overall win rate
    print("\n1. Top 10 Cards by Overall Win Rate (min 100 games):")
    print("-" * 70)
    query1 = """
        SELECT 
            c.card_name,
            cs.overall_wr,
            cs.gih_wr,
            cs.drawn_wr,
            cs.total_games
        FROM card_statistics cs
        JOIN cards c ON cs.card_id = c.card_id
        WHERE cs."set" = 'TLA'
          AND cs.total_games >= 100
          AND cs.overall_wr IS NOT NULL
        ORDER BY cs.overall_wr DESC
        LIMIT 10
    """
    results1 = query_database(query1)
    print_results(results1, ["Card Name", "Overall WR", "GIH WR", "Drawn WR", "Games"])
    
    # Query 2: Best archetypes
    print("\n2. Top 10 Color Combinations (Archetypes):")
    print("-" * 70)
    query2 = """
        SELECT 
            main_colors,
            COALESCE(splash_colors, '') AS splash,
            win_rate,
            total_games
        FROM color_archetypes
        WHERE "set" = 'TLA'
          AND total_games >= 50
        ORDER BY win_rate DESC
        LIMIT 10
    """
    results2 = query_database(query2)
    print_results(results2, ["Main Colors", "Splash", "Win Rate", "Games"])
    
    # Query 3: Database stats
    print("\n3. Database Statistics:")
    print("-" * 70)
    query3 = """
        SELECT 
            (SELECT COUNT(*) FROM cards WHERE "set" = 'TLA') AS total_cards,
            (SELECT COUNT(*) FROM card_statistics WHERE "set" = 'TLA') AS cards_with_stats,
            (SELECT COUNT(*) FROM color_archetypes WHERE "set" = 'TLA') AS total_archetypes,
            (SELECT COUNT(*) FROM draft_summaries WHERE "set" = 'TLA') AS total_drafts
    """
    results3 = query_database(query3)
    print_results(results3, ["Total Cards", "Cards w/ Stats", "Archetypes", "Drafts"])
    
    # Query 4: Cards by CMC
    print("\n4. Best 2-Drop Cards (CMC = 2):")
    print("-" * 70)
    query4 = """
        SELECT 
            c.card_name,
            c.color_identity,
            cs.overall_wr,
            cs.total_games,
            cs.avg_pick_number
        FROM card_statistics cs
        JOIN cards c ON cs.card_id = c.card_id
        WHERE cs."set" = 'TLA'
          AND c.cmc = 2
          AND cs.total_games >= 50
        ORDER BY cs.overall_wr DESC
        LIMIT 10
    """
    results4 = query_database(query4)
    print_results(results4, ["Card Name", "Colors", "Overall WR", "Games", "Avg Pick"])
    
    print("\n" + "=" * 70)
    print("Done! Check QUERY_DATABASE.md for more query examples.")
    print("=" * 70)

if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run the pipeline first to create the database.")
        sys.exit(1)
    
    example_queries()

