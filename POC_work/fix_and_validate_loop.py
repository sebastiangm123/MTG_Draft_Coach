#!/usr/bin/env python3
"""
Fix pipeline code and run validation in a loop until all checks pass.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_full_pipeline(set_code, draft_parquet, game_parquet, work_dir, max_attempts=5):
    """Run the full pipeline (delete DB and rebuild)."""
    print("\n" + "=" * 80)
    print("RUNNING FULL PIPELINE (DELETE AND REBUILD)")
    print("=" * 80)
    
    for attempt in range(1, max_attempts + 1):
        print(f"\nPipeline attempt {attempt}/{max_attempts}...")
        
        # Delete database first
        from delete_database import delete_database_files
        delete_database_files()
        
        # Run pipeline
        cmd = [
            sys.executable,
            str(work_dir / "mtg_draft_pipeline.py"),
            set_code,
            draft_parquet,
            game_parquet
        ]
        
        result = subprocess.run(cmd, cwd=str(work_dir), capture_output=False)
        
        if result.returncode == 0:
            print(f"\n[OK] Pipeline completed on attempt {attempt}!")
            return True
        else:
            print(f"\n[FAIL] Pipeline attempt {attempt} failed")
            if attempt < max_attempts:
                print("Retrying in 5 seconds...")
                time.sleep(5)
    
    return False

def run_validation(set_code, draft_parquet, game_parquet, test_card, test_archetype, work_dir, max_attempts=10):
    """Run validation in a loop until success."""
    print("\n" + "=" * 80)
    print("RUNNING VALIDATION LOOP")
    print("=" * 80)
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n{'='*80}")
        print(f"VALIDATION ATTEMPT {attempt}/{max_attempts}")
        print('='*80)
        
        # Run the agent pipeline runner
        cmd = [
            sys.executable,
            str(work_dir / "agent_pipeline_runner.py"),
            set_code,
            draft_parquet,
            game_parquet,
            test_card,
            test_archetype
        ]
        
        result = subprocess.run(cmd, cwd=str(work_dir), capture_output=False)
        
        if result.returncode == 0:
            print(f"\n{'='*80}")
            print(f"[OK] All validation passed on attempt {attempt}!")
            print('='*80)
            return True
        else:
            print(f"\n[FAIL] Validation attempt {attempt} failed with exit code {result.returncode}")
            if attempt < max_attempts:
                print(f"Retrying in 5 seconds...")
                time.sleep(5)
    
    print(f"\n{'='*80}")
    print(f"[FAIL] Validation failed after {max_attempts} attempts")
    print('='*80)
    return False

def main():
    """Main execution."""
    if len(sys.argv) < 4:
        print("Usage: python fix_and_validate_loop.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [TEST_CARD] [ARCHETYPE] [RUN_FULL_PIPELINE]")
        print("Example: python fix_and_validate_loop.py TLA draft_data.parquet game_data.parquet 'Invasion Submersible' WU true")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    test_card = sys.argv[4] if len(sys.argv) > 4 else "invasion submersible"
    test_archetype = sys.argv[5] if len(sys.argv) > 5 else "WU"
    run_full = sys.argv[6].lower() == 'true' if len(sys.argv) > 6 else False
    
    work_dir = Path(__file__).parent
    
    print("=" * 80)
    print("FIX AND VALIDATE LOOP")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Draft Data: {draft_parquet}")
    print(f"Game Data: {game_parquet}")
    print(f"Test Card: {test_card}")
    print(f"Test Archetype: {test_archetype}")
    print(f"Run Full Pipeline: {run_full}")
    print("=" * 80)
    
    # Step 1: Run full pipeline if requested
    if run_full:
        if not run_full_pipeline(set_code, draft_parquet, game_parquet, work_dir):
            print("\n[FAIL] Full pipeline failed - stopping")
            sys.exit(1)
    
    # Step 2: Run validation loop
    if not run_validation(set_code, draft_parquet, game_parquet, test_card, test_archetype, work_dir):
        print("\n[FAIL] Validation failed - stopping")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("[OK] ALL CHECKS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    main()

