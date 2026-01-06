#!/usr/bin/env python3
"""
Agent Loop Pipeline Runner with Comprehensive Validation and CSV Export
Runs the pipeline, validates all tables, and exports summaries to CSV for manual validation.
"""

import subprocess
import sys
import os
from pathlib import Path
import time
import sqlite3
import pandas as pd
from datetime import datetime

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

def verify_database_exists(work_dir):
    """Verify database was created successfully."""
    print("\n[STEP 3] Verifying Database Creation...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    
    if not db_path.exists():
        print(f"  ERROR: Database not found at {db_path}")
        return False
    
    # Check database is accessible
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['cards', 'card_statistics', 'color_archetypes', 
                             'draft_picks', 'draft_summaries', 'game_results', 'game_cards']
            
            print(f"  Database found: {db_path}")
            print(f"  Tables found: {len(tables)}")
            
            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"  WARNING: Missing tables: {missing}")
                return False
            
            print(f"  [OK] All {len(expected_tables)} tables exist")
            return True
    except Exception as e:
        print(f"  ERROR: Could not access database: {e}")
        return False

def validate_table_data(set_code, work_dir):
    """Validate that all tables have data."""
    print("\n[STEP 4] Validating Table Data...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    
    if not db_path.exists():
        print(f"  ERROR: Database not found at {db_path}")
        return False
    
    validation_results = {}
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check each table
        tables_to_check = [
            ('cards', 'card_id'),
            ('card_statistics', 'card_stat_id'),
            ('color_archetypes', 'archetype_id'),
            ('draft_picks', 'pick_id'),
            ('draft_summaries', 'draft_summary_id'),
            ('game_results', 'game_id'),
            ('game_cards', 'game_card_id')
        ]
        
        for table_name, id_column in tables_to_check:
            # game_cards doesn't have a set column, need to join with game_results
            if table_name == 'game_cards':
                cursor.execute("""
                    SELECT COUNT(*) FROM game_cards gc
                    JOIN game_results gr ON gc.game_id = gr.game_id
                    WHERE gr."set" = ?
                """, (set_code,))
            else:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE "set" = ?', (set_code,))
            count = cursor.fetchone()[0]
            validation_results[table_name] = count
            status = "[OK]" if count > 0 else "[FAIL]"
            print(f"  {status} {table_name}: {count:,} records")
    
    all_valid = all(count > 0 for count in validation_results.values())
    
    if all_valid:
        print(f"\n  [OK] All tables have data for set {set_code}")
    else:
        print(f"\n  [FAIL] Some tables are empty for set {set_code}")
    
    return all_valid, validation_results

def validate_example_card(card_name, set_code, work_dir):
    """Validate example card data."""
    print(f"\n[STEP 5] Validating Example Card: {card_name}...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check card exists
        cursor.execute("""
            SELECT card_id, card_name, "set", color_identity, card_type, cmc, rarity
            FROM cards
            WHERE card_name = ? AND "set" = ?
        """, (card_name.lower(), set_code))
        
        card = cursor.fetchone()
        if not card:
            print(f"  [FAIL] Card '{card_name}' not found in database")
            return False
        
        card_id, name, set_code_db, color_identity, card_type, cmc, rarity = card
        print(f"  [OK] Card found:")
        print(f"    ID: {card_id}")
        print(f"    Name: {name}")
        print(f"    Set: {set_code_db}")
        print(f"    Color Identity: {color_identity or 'N/A'}")
        print(f"    Type: {card_type or 'N/A'}")
        print(f"    CMC: {cmc if cmc is not None else 'N/A'}")
        print(f"    Rarity: {rarity or 'N/A'}")
        
        # Check statistics
        cursor.execute("""
            SELECT gih_wr, gih_games, drawn_wr, drawn_games, overall_wr, total_games, avg_pick_number
            FROM card_statistics
            WHERE card_id = ? AND "set" = ?
        """, (card_id, set_code))
        
        stats = cursor.fetchone()
        if stats:
            gih_wr, gih_games, drawn_wr, drawn_games, overall_wr, total_games, avg_pick = stats
            print(f"\n  [OK] Statistics found:")
            gih_wr_str = f"{gih_wr:.4f}" if gih_wr is not None else "N/A"
            drawn_wr_str = f"{drawn_wr:.4f}" if drawn_wr is not None else "N/A"
            overall_wr_str = f"{overall_wr:.4f}" if overall_wr is not None else "N/A"
            avg_pick_str = f"{avg_pick:.2f}" if avg_pick is not None else "N/A"
            print(f"    GIH WR: {gih_wr_str} ({gih_games or 0} games)")
            print(f"    Drawn WR: {drawn_wr_str} ({drawn_games or 0} games)")
            print(f"    Overall WR: {overall_wr_str}")
            print(f"    Total Games: {total_games or 0}")
            print(f"    Avg Pick: {avg_pick_str}")
        else:
            print(f"  [FAIL] No statistics found for card")
            return False
        
        return True

def validate_example_archetype(archetype, set_code, work_dir):
    """Validate example archetype data."""
    print(f"\n[STEP 6] Validating Example Archetype: {archetype}...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check archetype exists
        cursor.execute("""
            SELECT archetype_id, main_colors, splash_colors, win_rate, total_games, 
                   total_wins, total_losses, avg_num_turns
            FROM color_archetypes
            WHERE main_colors = ? AND "set" = ?
        """, (archetype.upper(), set_code))
        
        arch = cursor.fetchone()
        if not arch:
            print(f"  [FAIL] Archetype '{archetype}' not found in database")
            return False
        
        arch_id, main_colors, splash_colors, win_rate, total_games, total_wins, total_losses, avg_turns = arch
        print(f"  [OK] Archetype found:")
        print(f"    ID: {arch_id}")
        print(f"    Main Colors: {main_colors}")
        print(f"    Splash Colors: {splash_colors or 'None'}")
        win_rate_str = f"{win_rate:.4f}" if win_rate is not None else "N/A"
        avg_turns_str = f"{avg_turns:.2f}" if avg_turns is not None else "N/A"
        print(f"    Win Rate: {win_rate_str}")
        print(f"    Total Games: {total_games or 0}")
        print(f"    Wins: {total_wins or 0}")
        print(f"    Losses: {total_losses or 0}")
        print(f"    Avg Turns: {avg_turns_str}")
        
        return True

def generate_table_summaries(set_code, work_dir, output_dir):
    """Generate summaries for each table and export to CSV."""
    print("\n[STEP 7] Generating Table Summaries and CSV Exports...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    output_dir.mkdir(exist_ok=True)
    
    summaries = {}
    
    with sqlite3.connect(str(db_path)) as conn:
        # 1. Cards Summary
        print("\n  [1] Cards Table Summary...")
        cards_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_cards,
                COUNT(DISTINCT color_identity) as unique_colors,
                COUNT(CASE WHEN color_identity IS NOT NULL THEN 1 END) as cards_with_colors,
                COUNT(CASE WHEN cmc IS NOT NULL THEN 1 END) as cards_with_cmc,
                AVG(cmc) as avg_cmc,
                COUNT(CASE WHEN rarity = 'Common' THEN 1 END) as commons,
                COUNT(CASE WHEN rarity = 'Uncommon' THEN 1 END) as uncommons,
                COUNT(CASE WHEN rarity = 'Rare' THEN 1 END) as rares,
                COUNT(CASE WHEN rarity = 'Mythic' THEN 1 END) as mythics
            FROM cards
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['cards'] = cards_df
        print(f"    Total Cards: {cards_df.iloc[0]['total_cards']}")
        
        # Export sample cards
        sample_cards = pd.read_sql_query("""
            SELECT card_name, color_identity, card_type, cmc, rarity
            FROM cards
            WHERE "set" = ?
            ORDER BY card_name
            LIMIT 100
        """, conn, params=(set_code,))
        sample_cards.to_csv(output_dir / "sample_cards.csv", index=False)
        print(f"    Exported {len(sample_cards)} sample cards to CSV")
        
        # 2. Card Statistics Summary
        print("\n  [2] Card Statistics Summary...")
        stats_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_stats,
                COUNT(CASE WHEN gih_wr IS NOT NULL THEN 1 END) as cards_with_gih_wr,
                COUNT(CASE WHEN drawn_wr IS NOT NULL THEN 1 END) as cards_with_drawn_wr,
                COUNT(CASE WHEN overall_wr IS NOT NULL THEN 1 END) as cards_with_overall_wr,
                AVG(gih_wr) as avg_gih_wr,
                AVG(drawn_wr) as avg_drawn_wr,
                AVG(overall_wr) as avg_overall_wr,
                SUM(total_games) as total_games_all_cards,
                SUM(total_picks) as total_picks_all_cards
            FROM card_statistics
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['card_statistics'] = stats_df
        print(f"    Total Statistics Records: {stats_df.iloc[0]['total_stats']}")
        
        # Export top cards by win rate
        top_cards = pd.read_sql_query("""
            SELECT 
                c.card_name,
                cs.gih_wr,
                cs.drawn_wr,
                cs.overall_wr,
                cs.total_games,
                cs.total_picks,
                cs.avg_pick_number,
                cs.maindeck_rate
            FROM card_statistics cs
            JOIN cards c ON cs.card_id = c.card_id
            WHERE cs."set" = ? AND cs.overall_wr IS NOT NULL AND cs.total_games >= 50
            ORDER BY cs.overall_wr DESC
            LIMIT 100
        """, conn, params=(set_code,))
        top_cards.to_csv(output_dir / "top_cards_by_wr.csv", index=False)
        print(f"    Exported {len(top_cards)} top cards to CSV")
        
        # 3. Color Archetypes Summary
        print("\n  [3] Color Archetypes Summary...")
        arch_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_archetypes,
                COUNT(CASE WHEN win_rate IS NOT NULL THEN 1 END) as archetypes_with_wr,
                AVG(win_rate) as avg_win_rate,
                SUM(total_games) as total_games_all_archetypes,
                AVG(avg_num_turns) as avg_game_length
            FROM color_archetypes
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['color_archetypes'] = arch_df
        print(f"    Total Archetypes: {arch_df.iloc[0]['total_archetypes']}")
        
        # Export all archetypes
        all_archetypes = pd.read_sql_query("""
            SELECT 
                main_colors,
                splash_colors,
                win_rate,
                total_games,
                total_wins,
                total_losses,
                avg_num_turns
            FROM color_archetypes
            WHERE "set" = ?
            ORDER BY win_rate DESC
        """, conn, params=(set_code,))
        all_archetypes.to_csv(output_dir / "all_archetypes.csv", index=False)
        print(f"    Exported {len(all_archetypes)} archetypes to CSV")
        
        # 4. Draft Picks Summary
        print("\n  [4] Draft Picks Summary...")
        picks_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_picks,
                COUNT(DISTINCT draft_id) as unique_drafts,
                COUNT(DISTINCT card_id) as unique_cards_picked,
                AVG(pack_number) as avg_pack_number,
                AVG(pick_number) as avg_pick_number,
                COUNT(CASE WHEN maindeck_rate IS NOT NULL THEN 1 END) as picks_with_maindeck_rate
            FROM draft_picks
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['draft_picks'] = picks_df
        print(f"    Total Picks: {picks_df.iloc[0]['total_picks']}")
        print(f"    Unique Drafts: {picks_df.iloc[0]['unique_drafts']}")
        
        # Export pick distribution
        pick_dist = pd.read_sql_query("""
            SELECT 
                pack_number,
                pick_number,
                COUNT(*) as pick_count
            FROM draft_picks
            WHERE "set" = ?
            GROUP BY pack_number, pick_number
            ORDER BY pack_number, pick_number
        """, conn, params=(set_code,))
        pick_dist.to_csv(output_dir / "pick_distribution.csv", index=False)
        print(f"    Exported pick distribution to CSV")
        
        # 5. Draft Summaries Summary
        print("\n  [5] Draft Summaries Summary...")
        draft_sum_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_drafts,
                AVG(win_rate) as avg_draft_win_rate,
                AVG(total_games) as avg_games_per_draft,
                SUM(total_wins) as total_wins_all_drafts,
                SUM(total_losses) as total_losses_all_drafts,
                COUNT(DISTINCT final_colors) as unique_color_combos
            FROM draft_summaries
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['draft_summaries'] = draft_sum_df
        print(f"    Total Drafts: {draft_sum_df.iloc[0]['total_drafts']}")
        
        # Export draft summaries sample
        sample_drafts = pd.read_sql_query("""
            SELECT 
                draft_id,
                final_colors,
                splash_colors,
                win_rate,
                total_games,
                total_wins,
                total_losses,
                avg_game_length,
                rank
            FROM draft_summaries
            WHERE "set" = ?
            ORDER BY win_rate DESC
            LIMIT 100
        """, conn, params=(set_code,))
        sample_drafts.to_csv(output_dir / "sample_draft_summaries.csv", index=False)
        print(f"    Exported {len(sample_drafts)} draft summaries to CSV")
        
        # 6. Game Results Summary
        print("\n  [6] Game Results Summary...")
        games_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_games,
                COUNT(DISTINCT draft_id) as unique_drafts_with_games,
                SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as total_wins,
                SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) as total_losses,
                AVG(num_turns) as avg_turns,
                COUNT(DISTINCT main_colors) as unique_color_combos
            FROM game_results
            WHERE "set" = ?
        """, conn, params=(set_code,))
        
        summaries['game_results'] = games_df
        print(f"    Total Games: {games_df.iloc[0]['total_games']}")
        
        # Export game results sample
        sample_games = pd.read_sql_query("""
            SELECT 
                game_id,
                draft_id,
                won,
                num_turns,
                main_colors,
                opp_colors,
                on_play,
                rank
            FROM game_results
            WHERE "set" = ?
            LIMIT 1000
        """, conn, params=(set_code,))
        sample_games.to_csv(output_dir / "sample_game_results.csv", index=False)
        print(f"    Exported {len(sample_games)} game results to CSV")
        
        # 7. Game Cards Summary
        print("\n  [7] Game Cards Summary...")
        game_cards_df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_game_card_records,
                SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as cards_in_opening_hand,
                SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as cards_drawn,
                SUM(CASE WHEN gc.in_maindeck = 1 THEN 1 ELSE 0 END) as cards_in_maindeck,
                COUNT(DISTINCT gc.card_id) as unique_cards_in_games,
                COUNT(DISTINCT gc.game_id) as unique_games_with_cards
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, conn, params=(set_code,))
        
        summaries['game_cards'] = game_cards_df
        print(f"    Total Game Card Records: {game_cards_df.iloc[0]['total_game_card_records']}")
        
        # Export game cards sample
        sample_game_cards = pd.read_sql_query("""
            SELECT 
                gc.game_id,
                c.card_name,
                gc.in_opening_hand,
                gc.was_drawn,
                gc.in_maindeck,
                gr.won
            FROM game_cards gc
            JOIN cards c ON gc.card_id = c.card_id
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
            LIMIT 1000
        """, conn, params=(set_code,))
        sample_game_cards.to_csv(output_dir / "sample_game_cards.csv", index=False)
        print(f"    Exported {len(sample_game_cards)} game card records to CSV")
    
    # Export all summaries to a single CSV
    all_summaries = pd.concat([df.assign(table=name) for name, df in summaries.items()], ignore_index=True)
    all_summaries.to_csv(output_dir / "table_summaries.csv", index=False)
    print(f"\n    [OK] All summaries exported to {output_dir / 'table_summaries.csv'}")
    
    return summaries

def validate_rag_readiness(set_code, work_dir):
    """Validate that data is ready for RAG agent use."""
    print("\n[STEP 8] Validating RAG Agent Readiness...")
    print("-" * 80)
    
    db_path = work_dir / "mtg_draft_coach.db"
    issues = []
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check cards have metadata
        cursor.execute("""
            SELECT COUNT(*) FROM cards WHERE "set" = ? AND color_identity IS NULL
        """, (set_code,))
        cards_no_color = cursor.fetchone()[0]
        if cards_no_color > 0:
            issues.append(f"{cards_no_color} cards missing color identity")
        
        # Check statistics have win rates (allow up to 5% missing as some cards may never be played)
        cursor.execute("""
            SELECT COUNT(*) FROM card_statistics 
            WHERE "set" = ? AND (gih_wr IS NULL AND drawn_wr IS NULL)
        """, (set_code,))
        stats_no_wr = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM card_statistics WHERE "set" = ?', (set_code,))
        total_stats = cursor.fetchone()[0]
        if stats_no_wr > 0 and total_stats > 0:
            missing_pct = (stats_no_wr / total_stats) * 100
            if missing_pct > 5.0:  # More than 5% missing is a problem
                issues.append(f"{stats_no_wr} card statistics missing win rates ({missing_pct:.1f}%)")
            else:
                print(f"  [INFO] {stats_no_wr} card statistics missing win rates ({missing_pct:.1f}%) - acceptable")
        
        # Check archetypes have win rates
        cursor.execute("""
            SELECT COUNT(*) FROM color_archetypes 
            WHERE "set" = ? AND win_rate IS NULL
        """, (set_code,))
        arch_no_wr = cursor.fetchone()[0]
        if arch_no_wr > 0:
            issues.append(f"{arch_no_wr} archetypes missing win rates")
        
        # Check game cards have data
        cursor.execute("""
            SELECT COUNT(*) FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, (set_code,))
        game_cards_count = cursor.fetchone()[0]
        if game_cards_count == 0:
            issues.append("No game cards data found")
    
    if issues:
        print("  [WARNING] Issues found:")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("  [OK] All RAG readiness checks passed!")
        print("    - Cards have metadata")
        print("    - Statistics have win rates")
        print("    - Archetypes have win rates")
        print("    - Game cards data present")
        return True

def main():
    """Main execution."""
    if len(sys.argv) < 4:
        print("Usage: python agent_pipeline_runner.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [TEST_CARD] [ARCHETYPE]")
        print("Example: python agent_pipeline_runner.py TLA draft_data.parquet game_data.parquet 'Invasion Submersible' WU")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    test_card = sys.argv[4] if len(sys.argv) > 4 else "invasion submersible"
    test_archetype = sys.argv[5] if len(sys.argv) > 5 else "WU"
    
    work_dir = Path(__file__).parent
    output_dir = work_dir / "validation_outputs"
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("AGENT PIPELINE RUNNER WITH COMPREHENSIVE VALIDATION")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Draft Data: {draft_parquet}")
    print(f"Game Data: {game_parquet}")
    print(f"Test Card: {test_card}")
    print(f"Test Archetype: {test_archetype}")
    print(f"Working Directory: {work_dir}")
    print(f"Output Directory: {output_dir}")
    print("=" * 80)
    
    # Step 1: Check if database exists, if not delete and run pipeline
    db_path = work_dir / "mtg_draft_coach.db"
    if not db_path.exists():
        print("\n[INFO] Database not found, running pipeline...")
        delete_database_files(work_dir)
        
        # Step 2: Run pipeline
        if not run_pipeline(set_code, draft_parquet, game_parquet, work_dir):
            print("\n" + "=" * 80)
            print("PIPELINE FAILED - STOPPING")
            print("=" * 80)
            sys.exit(1)
    else:
        print("\n[INFO] Database already exists, skipping pipeline step...")
    
    # Step 3: Verify database exists
    if not verify_database_exists(work_dir):
        print("\n" + "=" * 80)
        print("DATABASE VERIFICATION FAILED - STOPPING")
        print("=" * 80)
        sys.exit(1)
    
    # Step 4: Validate table data
    all_valid, validation_results = validate_table_data(set_code, work_dir)
    if not all_valid:
        # Check if game_cards is empty and try to fix it
        if validation_results.get('game_cards', 0) == 0:
            print("\n[INFO] game_cards table is empty, attempting to fix...")
            print("-" * 80)
            try:
                from mtg_draft_pipeline import MTGDraftPipeline
                pipeline = MTGDraftPipeline(db_path=str(work_dir / "mtg_draft_coach.db"), use_scryfall=False)
                pipeline.connect_db()
                
                # Delete existing game_cards and card_statistics for this set
                pipeline.cursor.execute("""
                    DELETE FROM game_cards
                    WHERE game_id IN (
                        SELECT game_id FROM game_results WHERE "set" = ?
                    )
                """, (set_code,))
                pipeline.cursor.execute('DELETE FROM card_statistics WHERE "set" = ?', (set_code,))
                pipeline.conn.commit()
                
                # Reprocess game data
                print("  Reprocessing game data...")
                pipeline.process_game_data(game_parquet, set_code)
                
                # Recalculate statistics
                print("  Recalculating card statistics...")
                pipeline.calculate_card_statistics(set_code)
                
                pipeline.close_db()
                print("  [OK] game_cards table fixed, re-validating...")
                
                # Re-validate
                all_valid, validation_results = validate_table_data(set_code, work_dir)
            except Exception as e:
                print(f"  [FAIL] Could not fix game_cards: {e}")
        
        if not all_valid:
            print("\n" + "=" * 80)
            print("TABLE VALIDATION FAILED - CHECK ISSUES ABOVE")
            print("=" * 80)
            sys.exit(1)
    
    # Step 5: Validate example card
    if not validate_example_card(test_card, set_code, work_dir):
        print("\n" + "=" * 80)
        print("CARD VALIDATION FAILED - CHECK ISSUES ABOVE")
        print("=" * 80)
        sys.exit(1)
    
    # Step 6: Validate example archetype
    if not validate_example_archetype(test_archetype, set_code, work_dir):
        print("\n" + "=" * 80)
        print("ARCHETYPE VALIDATION FAILED - CHECK ISSUES ABOVE")
        print("=" * 80)
        sys.exit(1)
    
    # Step 7: Generate summaries and CSV exports
    summaries = generate_table_summaries(set_code, work_dir, output_dir)
    
    # Step 8: Validate RAG readiness
    if not validate_rag_readiness(set_code, work_dir):
        print("\n" + "=" * 80)
        print("RAG READINESS CHECK FAILED - CHECK ISSUES ABOVE")
        print("=" * 80)
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 80)
    print("ALL STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Database: {work_dir / 'mtg_draft_coach.db'}")
    print(f"Set: {set_code}")
    print(f"Validation Outputs: {output_dir}")
    print("\nGenerated CSV Files:")
    for csv_file in sorted(output_dir.glob("*.csv")):
        print(f"  - {csv_file.name}")
    print("\nAll tables validated and ready for RAG agent use!")
    print("=" * 80)

if __name__ == "__main__":
    main()

