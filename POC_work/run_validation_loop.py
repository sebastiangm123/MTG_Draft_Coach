#!/usr/bin/env python3
"""
Run validation in a loop until all checks pass.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_validation(set_code, draft_parquet, game_parquet, test_card, test_archetype, max_attempts=10):
    """Run validation in a loop until success."""
    work_dir = Path(__file__).parent
    
    print("=" * 80)
    print("VALIDATION LOOP RUNNER")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Max Attempts: {max_attempts}")
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
            print(f"SUCCESS! All validation passed on attempt {attempt}")
            print('='*80)
            return True
        else:
            print(f"\n[FAIL] Validation attempt {attempt} failed with exit code {result.returncode}")
            if attempt < max_attempts:
                print(f"Retrying in 5 seconds...")
                time.sleep(5)
    
    print(f"\n{'='*80}")
    print(f"FAILED: Validation failed after {max_attempts} attempts")
    print('='*80)
    return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_validation_loop.py <SET_CODE> <DRAFT_PARQUET> <GAME_PARQUET> [TEST_CARD] [ARCHETYPE] [MAX_ATTEMPTS]")
        print("Example: python run_validation_loop.py TLA draft_data.parquet game_data.parquet 'Invasion Submersible' WU 10")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    draft_parquet = sys.argv[2]
    game_parquet = sys.argv[3]
    test_card = sys.argv[4] if len(sys.argv) > 4 else "invasion submersible"
    test_archetype = sys.argv[5] if len(sys.argv) > 5 else "WU"
    max_attempts = int(sys.argv[6]) if len(sys.argv) > 6 else 10
    
    success = run_validation(set_code, draft_parquet, game_parquet, test_card, test_archetype, max_attempts)
    sys.exit(0 if success else 1)

