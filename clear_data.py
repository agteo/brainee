#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to clear all user data from the platform.
This will reset all progress, lessons, and quiz attempts.
"""

import json
import sys
from pathlib import Path
import shutil

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DATA_DIR = Path(__file__).parent / "data"

def clear_all_data():
    """Clear all user data files."""
    print("Clearing all user data...")
    
    # Files to clear/reset
    files_to_clear = [
        "user_progress.json",
        "lesson_log.json",
        "quiz_attempts.json"
    ]
    
    # Clear JSON files (reset to empty arrays)
    for filename in files_to_clear:
        filepath = DATA_DIR / filename
        if filepath.exists():
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            print(f"  [OK] Cleared {filename}")
        else:
            print(f"  [INFO] {filename} not found (will be created on first use)")
    
    # Optionally clear parquet directories
    parquet_dirs = [
        DATA_DIR / "lesson_log.parquet",
        DATA_DIR / "quiz_attempts.parquet"
    ]
    
    for parquet_dir in parquet_dirs:
        if parquet_dir.exists() and parquet_dir.is_dir():
            shutil.rmtree(parquet_dir)
            print(f"  [OK] Removed {parquet_dir.name}/")
    
    print("\nAll user data cleared!")
    print("\nNote: To clear browser localStorage (theme preference), you can:")
    print("  1. Open browser DevTools (F12)")
    print("  2. Go to Application/Storage tab")
    print("  3. Clear Local Storage")
    print("  Or use the browser's 'Clear browsing data' option")

if __name__ == "__main__":
    try:
        clear_all_data()
    except Exception as e:
        print(f"[ERROR] Error clearing data: {e}")
        raise

