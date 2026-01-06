#!/usr/bin/env python3
"""
Full pipeline runner with automatic retry and validation.
Drops old database, runs pipeline, and validates all tables.
"""

import subprocess
import sys
import os
from pathlib import Path
import time

def run_command(cmd, cwd=None, check=True):
    """Run a command and return success status."""
    print(f"\n{'='*80}")
    print(f"Running: {cmd}")
    print('='*80)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=False)
    success = result.returncode == 0
    if check and not success:
        print(f"\nERROR: Command failed with exit code {result.returncode}")
    return success

def delete_database_files(work_dir):
    """Delete all database files."""
    db_path = work_dir / "mtg_draft_coach.db"
    db_files = [
        db_path,
        work_dir / f"{db_path.name}-shm",
        work_dir / f"{db_path.name}-wal"
    ]
    
    print("\n[STEP 1] Deleting old database files...")
    print("-" * 80)
    deleted = []
    for db_file in db_files:
        if db_file.exists():
            db_file.unlink()
            deleted.append(db_file.name)
            print(f"  Deleted: {db_file.name}")
    
    if not deleted:
        print("  No database files found to delete")
    else:
        print(f"  Deleted {len(deleted)} database file(s)")
    
    return len(deleted) > 0

def run_pipeline(set_code, draft_parquet, game_parquet, work_dir, max_attempts=5):
    """Run the pipeline with retry logic."""
    print("\n[STEP 2] Running MTG Draft Pipeline...")
    print("-" * 80)
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n  Pipeline attempt {attempt}/{max_attempts}...")
        cmd = f'python mtg_draft_pipeline.py {set_code} "{draft_parquet}" "{game_parquet}"'
        
        success = run_command(cmd, cwd=str(work_dir), check=False)
        
        if success:
            print(f"\n  SUCCESS: Pipeline completed on attempt {attempt}!")
            return True
        else:
            print(f"\n  FAILED: Pipeline attempt {attempt} failed")
            if attempt < max_attempts:
                print("  Retrying in 2 seconds...")
                time.sleep(2)
    
    print(f"\n  ERROR: Pipeline failed after {max_attempts} attempts")
    return False

def run_validation(set_code, test_card, work_dir, max_attempts=3):
    """Run validation with retry logic."""
    print("\n[STEP 3] Validating Database...")
    print("-" * 80)
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n  Validation attempt {attempt}/{max_attempts}...")
        cmd = f'python validate_database.py {set_code} "{test_card}"'
        
        success = run_command(cmd, cwd=str(work_dir), check=False)
        
        if success:
            print(f"\n  SUCCESS: Validation passed on attempt {attempt}!")
            return True
        else:
            print(f"\n  FAILED: Validation attempt {attempt} failed")
            if attempt < max_attempts:
                print("  Retrying in 2 seconds...")
                time.sleep(2)
    
    print(f"\n  ERROR: Validation failed after {max_attempts} attempts")
    return False

def run_query_card(test_card, work_dir):
    """Run query_card for detailed view."""
    print("\n[STEP 4] Running Detailed Card Query...")
    print("-" * 80)
    cmd = f'python query_card.py "{test_card}"'
    run_command(cmd, cwd=str(work_dir), check=False)

def validate_all_tables_for_rag(set_code, work_dir):
    """Comprehensive validation of all tables for RAG agent use."""
    print("\n[STEP 5] Comprehensive RAG Agent Data Validation...")
    print("-" * 80)
    
    import sqlite3
    db_path = work_dir / "mtg_draft_coach.db"
    
    if not db_path.exists():
        print(f"  ERROR: Database not found at {db_path}")
        return False
    
    issues = []
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # 1. Cards table
        print("\n  [1] Cards Table:")
        cursor.execute('SELECT COUNT(*) FROM cards WHERE "set" = ?', (set_code,))
        card_count = cursor.fetchone()[0]
        print(f"    Total cards: {card_count:,}")
        
        cursor.execute('SELECT COUNT(*) FROM cards WHERE "set" = ? AND color_identity IS NOT NULL', (set_code,))
        cards_with_colors = cursor.fetchone()[0]
        print(f"    Cards with color identity: {cards_with_colors:,} ({cards_with_colors/card_count*100:.1f}%)")
        
        if card_count == 0:
            issues.append("Cards table is empty")
        
        # 2. Card Statistics table
        print("\n  [2] Card Statistics Table:")
        cursor.execute('SELECT COUNT(*) FROM card_statistics WHERE "set" = ?', (set_code,))
        stats_count = cursor.fetchone()[0]
        print(f"    Total statistics records: {stats_count:,}")
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN gih_wr IS NOT NULL THEN 1 END) as has_gih,
                COUNT(CASE WHEN drawn_wr IS NOT NULL THEN 1 END) as has_drawn,
                COUNT(CASE WHEN overall_wr IS NOT NULL THEN 1 END) as has_overall,
                COUNT(CASE WHEN avg_pick_number IS NOT NULL THEN 1 END) as has_pick_num
            FROM card_statistics WHERE "set" = ?
        """, (set_code,))
        
        gih, drawn, overall, pick_num = cursor.fetchone()
        print(f"    Cards with GIH WR: {gih:,} ({gih/stats_count*100:.1f}%)")
        print(f"    Cards with Drawn WR: {drawn:,} ({drawn/stats_count*100:.1f}%)")
        print(f"    Cards with Overall WR: {overall:,} ({overall/stats_count*100:.1f}%)")
        print(f"    Cards with pick numbers: {pick_num:,} ({pick_num/stats_count*100:.1f}%)")
        
        if gih == 0 or drawn == 0:
            issues.append("Card statistics missing win rate data")
        
        # 3. Archetype table
        print("\n  [3] Color Archetypes Table:")
        cursor.execute('SELECT COUNT(*) FROM color_archetypes WHERE "set" = ?', (set_code,))
        arch_count = cursor.fetchone()[0]
        print(f"    Total archetypes: {arch_count:,}")
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN win_rate IS NOT NULL THEN 1 END) as has_wr,
                COUNT(CASE WHEN total_games > 0 THEN 1 END) as has_games,
                COUNT(CASE WHEN avg_num_turns IS NOT NULL THEN 1 END) as has_turns
            FROM color_archetypes WHERE "set" = ?
        """, (set_code,))
        
        has_wr, has_games, has_turns = cursor.fetchone()
        print(f"    Archetypes with win rate: {has_wr:,} ({has_wr/arch_count*100:.1f}%)")
        print(f"    Archetypes with games: {has_games:,} ({has_games/arch_count*100:.1f}%)")
        print(f"    Archetypes with avg turns: {has_turns:,} ({has_turns/arch_count*100:.1f}%)")
        
        if arch_count == 0:
            issues.append("Archetype table is empty")
        elif has_wr < arch_count * 0.5:
            issues.append(f"Only {has_wr/arch_count*100:.1f}% of archetypes have win rates")
        
        # 4. Draft Picks table
        print("\n  [4] Draft Picks Table:")
        cursor.execute('SELECT COUNT(*) FROM draft_picks WHERE "set" = ?', (set_code,))
        picks_count = cursor.fetchone()[0]
        print(f"    Total draft picks: {picks_count:,}")
        
        cursor.execute('SELECT COUNT(DISTINCT draft_id) FROM draft_picks WHERE "set" = ?', (set_code,))
        unique_drafts = cursor.fetchone()[0]
        print(f"    Unique drafts: {unique_drafts:,}")
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN pick_number IS NOT NULL THEN 1 END) as has_pick,
                COUNT(CASE WHEN pack_number IS NOT NULL THEN 1 END) as has_pack,
                COUNT(CASE WHEN maindeck_rate IS NOT NULL THEN 1 END) as has_maindeck
            FROM draft_picks WHERE "set" = ?
        """, (set_code,))
        
        has_pick, has_pack, has_maindeck = cursor.fetchone()
        print(f"    Picks with pick number: {has_pick:,} ({has_pick/picks_count*100:.1f}%)")
        print(f"    Picks with pack number: {has_pack:,} ({has_pack/picks_count*100:.1f}%)")
        print(f"    Picks with maindeck rate: {has_maindeck:,} ({has_maindeck/picks_count*100:.1f}%)")
        
        if picks_count == 0:
            issues.append("Draft picks table is empty")
        
        # 5. Game Results table
        print("\n  [5] Game Results Table:")
        cursor.execute('SELECT COUNT(*) FROM game_results WHERE "set" = ?', (set_code,))
        games_count = cursor.fetchone()[0]
        print(f"    Total games: {games_count:,}")
        
        cursor.execute('SELECT COUNT(DISTINCT draft_id) FROM game_results WHERE "set" = ?', (set_code,))
        unique_drafts_games = cursor.fetchone()[0]
        print(f"    Unique drafts with games: {unique_drafts_games:,}")
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN won IS NOT NULL THEN 1 END) as has_won,
                COUNT(CASE WHEN num_turns IS NOT NULL THEN 1 END) as has_turns,
                COUNT(CASE WHEN main_colors IS NOT NULL AND main_colors != '' THEN 1 END) as has_colors
            FROM game_results WHERE "set" = ?
        """, (set_code,))
        
        has_won, has_turns, has_colors = cursor.fetchone()
        print(f"    Games with win/loss: {has_won:,} ({has_won/games_count*100:.1f}%)")
        print(f"    Games with turn count: {has_turns:,} ({has_turns/games_count*100:.1f}%)")
        print(f"    Games with colors: {has_colors:,} ({has_colors/games_count*100:.1f}%)")
        
        if games_count == 0:
            issues.append("Game results table is empty")
        
        # 6. Game Cards table
        print("\n  [6] Game Cards Table:")
        cursor.execute("""
            SELECT COUNT(*) FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, (set_code,))
        game_cards_count = cursor.fetchone()[0]
        print(f"    Total game_cards records: {game_cards_count:,}")
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as in_hand,
                SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as drawn,
                SUM(CASE WHEN gc.in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, (set_code,))
        
        in_hand, drawn, maindeck = cursor.fetchone()
        print(f"    Cards in opening hand: {in_hand:,}")
        print(f"    Cards drawn: {drawn:,}")
        print(f"    Cards in maindeck: {maindeck:,}")
        
        if game_cards_count == 0:
            issues.append("Game cards table is empty")
        elif in_hand == 0 and drawn == 0:
            issues.append("Game cards table missing opening hand and drawn flags")
        
        # 7. Draft Summaries table
        print("\n  [7] Draft Summaries Table:")
        cursor.execute('SELECT COUNT(*) FROM draft_summaries WHERE "set" = ?', (set_code,))
        summaries_count = cursor.fetchone()[0]
        print(f"    Total draft summaries: {summaries_count:,}")
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN win_rate IS NOT NULL THEN 1 END) as has_wr,
                COUNT(CASE WHEN total_games > 0 THEN 1 END) as has_games
            FROM draft_summaries WHERE "set" = ?
        """, (set_code,))
        
        has_wr, has_games = cursor.fetchone()
        print(f"    Summaries with win rate: {has_wr:,} ({has_wr/summaries_count*100:.1f}% if > 0)")
        print(f"    Summaries with games: {has_games:,} ({has_games/summaries_count*100:.1f}% if > 0)")
    
    # Summary
    print("\n" + "-" * 80)
    print("RAG AGENT DATA VALIDATION SUMMARY")
    print("-" * 80)
    
    if issues:
        print("\n  ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
        return False
    else:
        print("\n  SUCCESS: All tables have useful data for RAG agent!")
        return True

def main():
    """Main execution."""
    if len(sys.argv) < 4:
        print("Usage: python full_pipeline_runner.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [TEST_CARD]")
        print("Example: python full_pipeline_runner.py TLA draft_data.parquet game_data.parquet 'Invasion Submersible'")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    test_card = sys.argv[4] if len(sys.argv) > 4 else "invasion submersible"
    
    work_dir = Path(__file__).parent
    
    print("=" * 80)
    print("FULL PIPELINE RUNNER WITH VALIDATION")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Draft Data: {draft_parquet}")
    print(f"Game Data: {game_parquet}")
    print(f"Test Card: {test_card}")
    print(f"Working Directory: {work_dir}")
    print("=" * 80)
    
    # Step 1: Delete old database
    delete_database_files(work_dir)
    
    # Step 2: Run pipeline
    if not run_pipeline(set_code, draft_parquet, game_parquet, work_dir):
        print("\n" + "=" * 80)
        print("PIPELINE FAILED - STOPPING")
        print("=" * 80)
        sys.exit(1)
    
    # Step 3: Run validation
    if not run_validation(set_code, test_card, work_dir):
        print("\n" + "=" * 80)
        print("VALIDATION FAILED - STOPPING")
        print("=" * 80)
        sys.exit(1)
    
    # Step 4: Run detailed card query
    run_query_card(test_card, work_dir)
    
    # Step 5: Comprehensive RAG validation
    if not validate_all_tables_for_rag(set_code, work_dir):
        print("\n" + "=" * 80)
        print("RAG VALIDATION FAILED - CHECK ISSUES ABOVE")
        print("=" * 80)
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 80)
    print("ALL STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Database: {work_dir / 'mtg_draft_coach.db'}")
    print(f"Set: {set_code}")
    print("All tables validated and ready for RAG agent use!")
    print("=" * 80)

if __name__ == "__main__":
    main()

