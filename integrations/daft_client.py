"""Daft Client for structured data storage in LearnAI.

Uses Daft DataFrames for efficient structured data handling and querying.
Falls back to JSON storage if Daft is not available.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Try to import Daft, fallback to pandas/JSON if not available
try:
    import daft
    DAFT_AVAILABLE = True
except ImportError:
    DAFT_AVAILABLE = False

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)


class DaftStorage:
    """Structured storage using Daft DataFrames."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(exist_ok=True)

        # Initialize usage stats
        self._usage_stats = {
            'parquet_reads': 0,
            'parquet_writes': 0,
            'json_reads': 0,
            'json_writes': 0,
            'quiz_attempts_logged': 0,
            'lesson_events_logged': 0,
            'last_used': None,
            'using_daft': DAFT_AVAILABLE
        }

        # Initialize storage files
        self.quiz_attempts_path = self.data_dir / "quiz_attempts.parquet"
        self.lesson_log_path = self.data_dir / "lesson_log.parquet"
        self.user_progress_path = self.data_dir / "user_progress.parquet"

        # JSON fallback paths
        self.quiz_attempts_json = self.data_dir / "quiz_attempts.json"
        self.lesson_log_json = self.data_dir / "lesson_log.json"
        self.user_progress_json = self.data_dir / "user_progress.json"
        
        # Check for directory conflicts and remove them
        self._cleanup_directory_conflicts()

    def _load_or_create_df(self, parquet_path: Path, json_path: Path, schema: Dict) -> 'daft.DataFrame':
        """Load existing Daft DataFrame or create new one."""
        if not DAFT_AVAILABLE:
            # Fallback: load from JSON
            if json_path.exists():
                self._usage_stats['json_reads'] += 1
                self._usage_stats['last_used'] = datetime.now().isoformat()
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return pd.DataFrame(data) if data else pd.DataFrame(columns=list(schema.keys()))
            return pd.DataFrame(columns=list(schema.keys()))

        # Try to load from parquet (Daft format)
        if parquet_path.exists() and parquet_path.is_file():
            try:
                self._usage_stats['parquet_reads'] += 1
                self._usage_stats['last_used'] = datetime.now().isoformat()
                df = daft.read_parquet(str(parquet_path))
                # Verify it's a valid DataFrame
                if df is not None:
                    return df
            except Exception as e:
                # If parquet file is corrupted or invalid, try JSON fallback
                print(f"Warning: Could not read parquet file {parquet_path}: {e}")
                pass

        # Try to load from JSON and convert to Daft
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    return daft.from_pydict(self._list_to_dict(data))
            except Exception:
                pass

        # Create empty DataFrame with proper schema types
        # Use default values that match schema types to ensure correct inference
        # Create an empty list for each column to avoid lazy evaluation issues
        empty_data = {key: [] for key in schema.keys()}
        
        # Create DataFrame directly from empty dict - this avoids lazy evaluation
        # that might try to read non-existent parquet files
        try:
            df = daft.from_pydict(empty_data)
            # Materialize immediately to avoid lazy evaluation issues
            # Use a simple operation that forces materialization without reading files
            return df
        except Exception as e:
            # If Daft fails, return None and let the caller handle JSON fallback
            print(f"Warning: Could not create empty Daft DataFrame: {e}")
            return None

    def _list_to_dict(self, data: List[Dict]) -> Dict[str, List]:
        """Convert list of dicts to dict of lists for Daft."""
        if not data:
            return {}

        result = {k: [] for k in data[0].keys()}
        for item in data:
            for key in result.keys():
                result[key].append(item.get(key))
        return result

    def _cleanup_directory_conflicts(self):
        """Remove directory conflicts with parquet file names."""
        parquet_files = [
            self.quiz_attempts_path,
            self.lesson_log_path,
            self.user_progress_path
        ]
        
        for parquet_path in parquet_files:
            # Check if path exists and is a directory
            if parquet_path.exists() and parquet_path.is_dir():
                import shutil
                try:
                    # Remove the directory
                    shutil.rmtree(parquet_path)
                    print(f"Removed directory conflict: {parquet_path}")
                except Exception as e:
                    print(f"Warning: Could not remove directory {parquet_path}: {e}")

    def _save_df(self, df, parquet_path: Path, json_path: Path):
        """Save DataFrame to both parquet and JSON."""
        # Check if parquet_path is a directory and remove it
        if parquet_path.exists() and parquet_path.is_dir():
            import shutil
            try:
                shutil.rmtree(parquet_path)
            except Exception:
                pass
        
        if DAFT_AVAILABLE and isinstance(df, daft.DataFrame):
            # Save as parquet for Daft
            # Convert to pandas first to avoid lazy evaluation issues
            # Daft's write_parquet can fail during optimization if it tries to read
            # non-existent files. Converting to pandas first avoids this.
            try:
                pd_df = df.to_pandas()
                
                # Save using pandas (more reliable for new files)
                pd_df.to_parquet(parquet_path, engine='pyarrow')
                self._usage_stats['parquet_writes'] += 1
                self._usage_stats['last_used'] = datetime.now().isoformat()
                
                # Also save as JSON for compatibility
                pd_df.to_json(json_path, orient='records', indent=2)
                self._usage_stats['json_writes'] += 1
            except Exception as e:
                # If pandas parquet fails, try JSON only
                print(f"Warning: Parquet write failed, using JSON only: {e}")
                try:
                    if 'pd_df' not in locals():
                        pd_df = df.to_pandas()
                    pd_df.to_json(json_path, orient='records', indent=2)
                    self._usage_stats['json_writes'] += 1
                    self._usage_stats['last_used'] = datetime.now().isoformat()
                except Exception as e2:
                    print(f"Error: Both parquet and JSON save failed: {e2}")
        else:
            # Pandas or fallback mode
            if isinstance(df, pd.DataFrame):
                df.to_json(json_path, orient='records', indent=2)
                self._usage_stats['json_writes'] += 1
                self._usage_stats['last_used'] = datetime.now().isoformat()
                try:
                    df.to_parquet(parquet_path)
                    self._usage_stats['parquet_writes'] += 1
                except Exception:
                    pass

    def log_quiz_attempt(self, entry: Dict):
        """Log a quiz attempt with structured storage.

        Expected fields:
        - user_id: str
        - question_id: str
        - user_answer: str (optional)
        - answer: str (optional)
        - correct: bool
        - hesitation_seconds: float
        - timestamp: float
        - difficulty_level: int
        """
        schema = {
            "user_id": str,
            "question_id": str,
            "user_answer": str,
            "answer": str,
            "correct": bool,
            "hesitation_seconds": float,
            "timestamp": float,
            "difficulty_level": int
        }

        # Ensure all fields have defaults
        complete_entry = {
            "user_id": entry.get("user_id", "unknown"),
            "question_id": entry.get("question_id", ""),
            "user_answer": entry.get("user_answer", entry.get("answer", "")),
            "answer": entry.get("answer", ""),
            "correct": entry.get("correct", False),
            "hesitation_seconds": float(entry.get("hesitation_seconds", 0)),
            "timestamp": float(entry.get("timestamp", datetime.now().timestamp())),
            "difficulty_level": int(entry.get("difficulty_level", 1))
        }

        # Load existing data
        if DAFT_AVAILABLE:
            try:
                df = self._load_or_create_df(self.quiz_attempts_path, self.quiz_attempts_json, schema)

                # Append new entry
                new_row = daft.from_pydict({k: [v] for k, v in complete_entry.items()})
                df = df.concat(new_row)

                self._save_df(df, self.quiz_attempts_path, self.quiz_attempts_json)
            except Exception as e:
                # If Daft fails, fallback to JSON
                print(f"Warning: Daft storage failed, using JSON fallback: {e}")
                data = self._load_json(self.quiz_attempts_json)
                data.append(complete_entry)
                self._save_json(self.quiz_attempts_json, data)
        else:
            # JSON fallback
            data = self._load_json(self.quiz_attempts_json)
            data.append(complete_entry)
            self._save_json(self.quiz_attempts_json, data)
        
        self._usage_stats['quiz_attempts_logged'] += 1

    def log_lesson_event(self, entry: Dict):
        """Log a lesson event with structured storage.

        Expected fields:
        - user_id: str
        - module: str
        - event: str (optional)
        - difficulty_level: int
        - learning_style: str (optional)
        - task_description: str (optional)
        - timestamp: float
        """
        schema = {
            "user_id": str,
            "module": str,
            "event": str,
            "difficulty_level": int,
            "learning_style": str,
            "task_description": str,
            "timestamp": float
        }

        complete_entry = {
            "user_id": entry.get("user_id", "unknown"),
            "module": entry.get("module", ""),
            "event": entry.get("event", "viewed"),
            "difficulty_level": int(entry.get("difficulty_level", 1)),
            "learning_style": entry.get("learning_style", "text"),
            "task_description": entry.get("task_description", ""),
            "timestamp": float(entry.get("timestamp", datetime.now().timestamp()))
        }

        if DAFT_AVAILABLE:
            try:
                df = self._load_or_create_df(self.lesson_log_path, self.lesson_log_json, schema)
                
                # If df is None, Daft failed, use JSON fallback
                if df is None:
                    raise ValueError("Daft DataFrame creation failed")
                
                new_row = daft.from_pydict({k: [v] for k, v in complete_entry.items()})
                df = df.concat(new_row)
                self._save_df(df, self.lesson_log_path, self.lesson_log_json)
            except Exception as e:
                # If Daft fails, fallback to JSON
                print(f"Warning: Daft storage failed, using JSON fallback: {e}")
                data = self._load_json(self.lesson_log_json)
                data.append(complete_entry)
                self._save_json(self.lesson_log_json, data)
        else:
            data = self._load_json(self.lesson_log_json)
            data.append(complete_entry)
            self._save_json(self.lesson_log_json, data)
        
        self._usage_stats['lesson_events_logged'] += 1
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for admin dashboard."""
        return self._usage_stats.copy()

    def update_user_progress(self, user_id: str, progress: Dict):
        """Update user progress with structured storage."""
        schema = {
            "user_id": str,
            "current_module": str,
            "difficulty_level": int,
            "completed_modules": str,  # JSON string
            "quiz_performance": str,   # JSON string
            "hesitation_history": str, # JSON string
            "preferred_learning_style": str,
            "created_at": str,
            "last_active": str
        }

        # Serialize complex fields
        complete_entry = {
            "user_id": user_id,
            "current_module": progress.get("current_module", "diagnostic"),
            "difficulty_level": int(progress.get("difficulty_level", 1)),
            "completed_modules": json.dumps(progress.get("completed_modules", [])),
            "quiz_performance": json.dumps(progress.get("quiz_performance", [])),
            "hesitation_history": json.dumps(progress.get("hesitation_history", [])),
            "preferred_learning_style": progress.get("preferred_learning_style") or "",
            "created_at": progress.get("created_at", datetime.now().isoformat()),
            "last_active": progress.get("last_active", datetime.now().isoformat())
        }

        if DAFT_AVAILABLE:
            df = self._load_or_create_df(self.user_progress_path, self.user_progress_json, schema)

            # Remove existing user entry
            try:
                df = df.where(df["user_id"] != user_id)
            except Exception:
                pass

            # Add updated entry
            new_row = daft.from_pydict({k: [v] for k, v in complete_entry.items()})
            df = df.concat(new_row)

            self._save_df(df, self.user_progress_path, self.user_progress_json)
        else:
            data = self._load_json(self.user_progress_json)
            data = [d for d in data if d.get("user_id") != user_id]

            # Convert serialized fields back to original format for JSON
            json_entry = {**progress, "user_id": user_id}
            data.append(json_entry)
            self._save_json(self.user_progress_json, data)

    def _load_json(self, path: Path) -> List[Dict]:
        """Load JSON file."""
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_json(self, path: Path, data: List[Dict]):
        """Save JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# Global storage instance
_storage = DaftStorage()

# Module-level functions for backward compatibility
def log_quiz_attempt(entry: Dict):
    """Log a quiz attempt."""
    _storage.log_quiz_attempt(entry)

def log_lesson_event(entry: Dict):
    """Log a lesson event."""
    _storage.log_lesson_event(entry)

def update_user_progress(user_id: str, progress: Dict):
    """Update user progress."""
    _storage.update_user_progress(user_id, progress)
