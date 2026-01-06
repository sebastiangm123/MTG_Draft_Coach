"""
Example script showing how to run the MTG Draft Pipeline.

This is a simple example that processes TLA (The Last Airbender) set data.
"""

from mtg_draft_pipeline import MTGDraftPipeline
import os

def main():
    # Configuration
    SET_CODE = "TLA"
    DRAFT_PARQUET = "draft_data_public.TLA.PremierDraft.parquet"
    GAME_PARQUET = "game_data_public.TLA.PremierDraft.parquet"
    DB_PATH = "mtg_draft_coach.db"
    
    # Check if Parquet files exist
    if not os.path.exists(DRAFT_PARQUET):
        print(f"Error: {DRAFT_PARQUET} not found!")
        print("Please ensure the Parquet files are in the current directory.")
        return
    
    if not os.path.exists(GAME_PARQUET):
        print(f"Error: {GAME_PARQUET} not found!")
        print("Please ensure the Parquet files are in the current directory.")
        return
    
    # Initialize pipeline
    print("Initializing MTG Draft Pipeline...")
    pipeline = MTGDraftPipeline(db_path=DB_PATH, use_scryfall=True)
    
    # Run pipeline
    try:
        pipeline.run_pipeline(
            set_name=SET_CODE,
            draft_data=DRAFT_PARQUET,
            game_data=GAME_PARQUET
        )
        
        print("\n" + "="*60)
        print("Pipeline completed successfully!")
        print(f"Database created at: {DB_PATH}")
        print("="*60)
        
        # Example: Query some statistics
        print("\nExample query: Top 10 cards by overall win rate")
        pipeline.connect_db()
        cursor = pipeline.cursor
        
        cursor.execute("""
            SELECT 
                c.card_name,
                cs.overall_wr,
                cs.gih_wr,
                cs.drawn_wr,
                cs.total_games
            FROM card_statistics cs
            JOIN cards c ON cs.card_id = c.card_id
            WHERE cs.set = ?
              AND cs.overall_wr IS NOT NULL
              AND cs.total_games >= 100
            ORDER BY cs.overall_wr DESC
            LIMIT 10
        """, (SET_CODE,))
        
        results = cursor.fetchall()
        print("\nCard Name | Overall WR | GIH WR | Drawn WR | Games")
        print("-" * 60)
        for row in results:
            name, overall, gih, drawn, games = row
            print(f"{name[:30]:30} | {overall:.3f} | {gih:.3f if gih else 'N/A':>6} | {drawn:.3f if drawn else 'N/A':>7} | {games:>5}")
        
        pipeline.close_db()
        
    except Exception as e:
        print(f"\nError running pipeline: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

