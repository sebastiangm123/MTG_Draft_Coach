#!/usr/bin/env python3
"""
Run the pipeline and validate the database, looping until successful.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"\n{'='*80}")
    print(f"Running: {cmd}")
    print('='*80)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=False)
    return result.returncode == 0

def main():
    if len(sys.argv) < 4:
        print("Usage: python run_pipeline_with_validation.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [TEST_CARD]")
        print("Example: python run_pipeline_with_validation.py TLA draft_data.parquet game_data.parquet 'Invasion Submersible'")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    test_card = sys.argv[4] if len(sys.argv) > 4 else "invasion submersible"
    
    work_dir = Path(__file__).parent
    db_path = work_dir / "mtg_draft_coach.db"
    
    print("=" * 80)
    print("PIPELINE RUNNER WITH VALIDATION")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Draft Data: {draft_parquet}")
    print(f"Game Data: {game_parquet}")
    print(f"Test Card: {test_card}")
    print("=" * 80)
    
    # Step 1: Delete old database
    print("\n[STEP 1] Deleting old database...")
    if db_path.exists():
        db_path.unlink()
        print(f"  Deleted {db_path}")
    if (db_path.parent / f"{db_path.name}-shm").exists():
        (db_path.parent / f"{db_path.name}-shm").unlink()
    if (db_path.parent / f"{db_path.name}-wal").exists():
        (db_path.parent / f"{db_path.name}-wal").unlink()
    print("  Old database files removed")
    
    # Step 2: Run pipeline (loop until successful)
    print("\n[STEP 2] Running pipeline...")
    pipeline_success = False
    attempt = 1
    
    while not pipeline_success:
        print(f"\n  Attempt {attempt}...")
        cmd = f'python mtg_draft_pipeline.py {set_code} "{draft_parquet}" "{game_parquet}"'
        pipeline_success = run_command(cmd, cwd=str(work_dir))
        
        if not pipeline_success:
            print(f"\n  Pipeline failed on attempt {attempt}. Retrying...")
            attempt += 1
            if attempt > 5:
                print("\n  ERROR: Pipeline failed 5 times. Stopping.")
                sys.exit(1)
        else:
            print(f"\n  Pipeline completed successfully on attempt {attempt}!")
    
    # Step 3: Validate database
    print("\n[STEP 3] Validating database...")
    validation_success = False
    attempt = 1
    
    while not validation_success:
        print(f"\n  Validation attempt {attempt}...")
        cmd = f'python validate_database.py {set_code} "{test_card}"'
        validation_success = run_command(cmd, cwd=str(work_dir))
        
        if not validation_success:
            print(f"\n  Validation failed on attempt {attempt}.")
            print("  Checking what needs to be fixed...")
            
            # Run query_card to see the issue
            print("\n  Running query_card for detailed view...")
            cmd = f'python query_card.py "{test_card}"'
            run_command(cmd, cwd=str(work_dir))
            
            # Automatically rerun pipeline if validation fails
            print("\n  Validation failed. Rerunning pipeline...")
            if db_path.exists():
                db_path.unlink()
                if (db_path.parent / f"{db_path.name}-shm").exists():
                    (db_path.parent / f"{db_path.name}-shm").unlink()
                if (db_path.parent / f"{db_path.name}-wal").exists():
                    (db_path.parent / f"{db_path.name}-wal").unlink()
            
            pipeline_success = False
            pipeline_attempt = 1
            while not pipeline_success:
                print(f"\n  Pipeline retry attempt {pipeline_attempt}...")
                cmd = f'python mtg_draft_pipeline.py {set_code} "{draft_parquet}" "{game_parquet}"'
                pipeline_success = run_command(cmd, cwd=str(work_dir))
                if not pipeline_success:
                    pipeline_attempt += 1
                    if pipeline_attempt > 5:
                        print("\n  ERROR: Pipeline failed 5 times. Stopping.")
                        sys.exit(1)
            
            # Reset validation attempt counter
            attempt = 1
        else:
            print(f"\n  Validation passed on attempt {attempt}!")
    
    # Step 4: Final query_card check
    print("\n[STEP 4] Final detailed card query...")
    cmd = f'python query_card.py "{test_card}"'
    run_command(cmd, cwd=str(work_dir))
    
    print("\n" + "=" * 80)
    print("ALL STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Set: {set_code}")
    print("=" * 80)

if __name__ == "__main__":
    main()

