#!/usr/bin/env python3
"""
Fix the game_cards table by reprocessing game data with corrected logic.
This will fix the opening_hand and drawn flags that were being overwritten.
"""

import sys
from pathlib import Path
from mtg_draft_pipeline import MTGDraftPipeline

def fix_database(set_code, draft_parquet, game_parquet, db_path="mtg_draft_coach.db"):
    """Fix game_cards and card_statistics for a given set."""
    
    print("=" * 80)
    print(f"FIXING DATABASE FOR SET: {set_code}")
    print("=" * 80)
    print()
    
    # Initialize pipeline
    pipeline = MTGDraftPipeline(db_path=db_path, use_scryfall=False)
    pipeline.connect_db()
    
    try:
        # Step 1: Delete existing game_cards and card_statistics for this set
        print("[STEP 1] Deleting existing game_cards and card_statistics...")
        print("-" * 80)
        
        # Delete game_cards via game_results join
        pipeline.cursor.execute("""
            DELETE FROM game_cards
            WHERE game_id IN (
                SELECT game_id FROM game_results WHERE "set" = ?
            )
        """, (set_code,))
        game_cards_deleted = pipeline.cursor.rowcount
        
        # Delete card_statistics
        pipeline.cursor.execute('DELETE FROM card_statistics WHERE "set" = ?', (set_code,))
        card_stats_deleted = pipeline.cursor.rowcount
        
        pipeline.conn.commit()
        
        print(f"  Deleted {game_cards_deleted:,} game_cards records")
        print(f"  Deleted {card_stats_deleted:,} card_statistics records")
        print()
        
        # Step 2: Reprocess game data
        print("[STEP 2] Reprocessing game data with fixed logic...")
        print("-" * 80)
        pipeline.process_game_data(game_parquet, set_code)
        print()
        
        # Step 3: Recalculate card statistics
        print("[STEP 3] Recalculating card statistics...")
        print("-" * 80)
        pipeline.calculate_card_statistics(set_code)
        print()
        
        # Step 4: Verify the fix
        print("[STEP 4] Verifying the fix...")
        print("-" * 80)
        pipeline.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN in_opening_hand = 1 THEN 1 ELSE 0 END) as in_hand,
                SUM(CASE WHEN was_drawn = 1 THEN 1 ELSE 0 END) as drawn,
                SUM(CASE WHEN in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, (set_code,))
        
        result = pipeline.cursor.fetchone()
        total, in_hand, drawn, maindeck = result
        
        print(f"  Total game_cards records: {total:,}")
        print(f"  Cards in opening hand: {in_hand:,}")
        print(f"  Cards drawn: {drawn:,}")
        print(f"  Cards in maindeck: {maindeck:,}")
        print()
        
        # Check card_statistics
        pipeline.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN gih_wr IS NOT NULL THEN 1 END) as has_gih_wr,
                COUNT(CASE WHEN drawn_wr IS NOT NULL THEN 1 END) as has_drawn_wr,
                COUNT(CASE WHEN overall_wr IS NOT NULL THEN 1 END) as has_overall_wr
            FROM card_statistics
            WHERE "set" = ?
        """, (set_code,))
        
        result = pipeline.cursor.fetchone()
        total_stats, has_gih, has_drawn, has_overall = result
        
        print(f"  Total card_statistics records: {total_stats:,}")
        print(f"  Cards with GIH WR: {has_gih:,}")
        print(f"  Cards with Drawn WR: {has_drawn:,}")
        print(f"  Cards with Overall WR: {has_overall:,}")
        print()
        
        if in_hand > 0 and drawn > 0:
            print("✓ SUCCESS: Opening hand and drawn flags are now populated!")
        else:
            print("⚠ WARNING: Still no opening hand or drawn data. Check the Parquet file columns.")
        
        if has_gih > 0 and has_drawn > 0:
            print("✓ SUCCESS: Win rates are now calculated!")
        else:
            print("⚠ WARNING: Win rates still not calculated.")
        
        print()
        print("=" * 80)
        print("Database fix completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        pipeline.close_db()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python fix_game_cards.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [DB_PATH]")
        print("Example: python fix_game_cards.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    db_path = sys.argv[4] if len(sys.argv) > 4 else "mtg_draft_coach.db"
    
    # Check files exist
    if not Path(draft_parquet).exists():
        print(f"Error: Draft Parquet file not found: {draft_parquet}")
        sys.exit(1)
    
    if not Path(game_parquet).exists():
        print(f"Error: Game Parquet file not found: {game_parquet}")
        sys.exit(1)
    
    fix_database(set_code, draft_parquet, game_parquet, db_path)


