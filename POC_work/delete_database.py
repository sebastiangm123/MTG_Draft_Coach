#!/usr/bin/env python3
"""
Delete database and all related files, ensuring connections are closed.
"""

import os
import sys
import sqlite3
from pathlib import Path
import time

def delete_database_files():
    """Delete database files, closing any connections first."""
    work_dir = Path(__file__).parent
    db_path = work_dir / "mtg_draft_coach.db"
    
    db_files = [
        db_path,
        work_dir / f"{db_path.name}-shm",
        work_dir / f"{db_path.name}-wal"
    ]
    
    print("Attempting to close any open database connections...")
    
    # Try to close any open connections by attempting to connect and close
    try:
        conn = sqlite3.connect(str(db_path), timeout=1.0)
        conn.close()
        print("Closed database connection")
    except Exception as e:
        print(f"Note: {e}")
    
    # Wait a moment for file handles to release
    time.sleep(1)
    
    print("\nDeleting database files...")
    deleted = []
    failed = []
    
    for db_file in db_files:
        if db_file.exists():
            try:
                # On Windows, we might need to retry
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        db_file.unlink()
                        deleted.append(db_file.name)
                        print(f"  Deleted: {db_file.name}")
                        break
                    except PermissionError:
                        if attempt < max_retries - 1:
                            time.sleep(0.5)
                        else:
                            raise
            except Exception as e:
                failed.append((db_file.name, str(e)))
                print(f"  Failed to delete {db_file.name}: {e}")
        else:
            print(f"  {db_file.name} not found (already deleted)")
    
    print(f"\nSummary:")
    print(f"  Deleted: {len(deleted)} file(s)")
    if deleted:
        for name in deleted:
            print(f"    - {name}")
    
    if failed:
        print(f"  Failed: {len(failed)} file(s)")
        for name, error in failed:
            print(f"    - {name}: {error}")
        print("\nWARNING: Some files could not be deleted. They may be locked by another process.")
        print("You may need to close any applications using the database and try again.")
        return False
    
    return True

if __name__ == "__main__":
    success = delete_database_files()
    sys.exit(0 if success else 1)

