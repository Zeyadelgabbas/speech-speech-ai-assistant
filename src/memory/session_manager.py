import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime 
from ..utils import get_logger , config

logger = get_logger(__name__)


class SessionManager:
    """
    Manages persistent storage of conversation sessions in SQLite.
    
    This handles the "save session", "load session", "list sessions" functionality.
    
    Database schema:
    - sessions table: stores session metadata and messages
    - Each session has: id, name, created_at, last_updated, messages (JSON)
    
    Why SQLite?
    - Lightweight (single file, no server needed)
    - Fast queries (indexed by name, date)
    - Structured data (better than JSON files)
    - ACID transactions (data integrity)
    - Built into Python (no extra dependencies)
    
    Alternative approaches we rejected:
    - JSON files per session: Hard to query, no indexing
    - In-memory only: Lost on restart
    - PostgreSQL/MySQL: Overkill for local assistant
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize session manager and create database if needed.
        
        Args:
            db_path: Path to SQLite database file
                If None, uses config.DATA_DIR / "sessions.db"
        
        Why store in config.DATA_DIR?
        - Keeps all user data in one place
        - Easy to backup (copy data/ folder)
        - Automatically gitignored
        """
        self.db_path = db_path or (config.DATA_DIR / "sessions.db")
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"SessionManager initialized: {self.db_path}")
    
    def _init_database(self):
        """
        Create database schema if it doesn't exist.
        
        Schema:
        - sessions table:
          - id: INTEGER PRIMARY KEY (auto-increment)
          - name: TEXT (session name, e.g., "project planning")
          - created_at: TEXT (ISO format timestamp)
          - last_updated: TEXT (ISO format timestamp)
          - messages: TEXT (JSON-encoded message list)
          - message_count: INTEGER (cached count for quick queries)
        
        Why this schema?
        - id: Unique identifier (standard practice)
        - name: User-friendly identifier ("meeting notes" vs ID 42)
        - created_at/last_updated: Track session timeline
        - messages: Full conversation stored as JSON (flexible structure)
        - message_count: Cached for "list sessions" queries (avoid parsing JSON)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    message_count INTEGER NOT NULL
                )
            """)
            
            # Create index on name for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_name 
                ON sessions(name)
            """)
            
            # Create index on created_at for chronological queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_created 
                ON sessions(created_at DESC)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("Database schema initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_session(self, name: str, session_data: Dict) -> int:
        """
        Save a session to the database.
        
        Args:
            name: Session name (e.g., "project planning")
                Must be unique (will update if exists)
            session_data: Session data dictionary from SessionMemory.to_dict()
                Format: {
                    "messages": [...],
                    "session_start": "...",
                    "message_count": N,
                    "duration": "..."
                }
        
        Returns:
            Session ID (integer)
        
        Behavior:
        - If session with same name exists: UPDATE (overwrite)
        - If new name: INSERT (create new)
        
        Why allow overwriting?
        - User can "auto-save" to same name during long conversation
        - Natural behavior: "save session as notes" updates existing "notes"
        
        Usage:
            session_data = session_memory.to_dict()
            session_id = session_manager.save_session("meeting notes", session_data)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare data
            now = datetime.now().isoformat()
            messages_json = json.dumps(session_data["messages"])
            message_count = session_data["message_count"]
            
            # Check if session with this name exists
            cursor.execute("SELECT id FROM sessions WHERE name = ?", (name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing session
                session_id = existing[0]
                cursor.execute("""
                    UPDATE sessions 
                    SET last_updated = ?, messages = ?, message_count = ?
                    WHERE id = ?
                """, (now, messages_json, message_count, session_id))
                
                logger.info(f"Updated session '{name}' (ID: {session_id})")
            
            else:
                # Insert new session
                cursor.execute("""
                    INSERT INTO sessions (name, created_at, last_updated, messages, message_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, now, now, messages_json, message_count))
                
                session_id = cursor.lastrowid
                logger.info(f"Created new session '{name}' (ID: {session_id})")
            
            conn.commit()
            conn.close()
            
            return session_id
        
        except sqlite3.IntegrityError as e:
            logger.error(f"Database integrity error: {e}")
            raise ValueError(f"Session name '{name}' may contain invalid characters")
        
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise
    
    def load_session(self, name: str) -> Optional[Dict]:
        """
        Load a session from the database by name.
        
        Args:
            name: Session name
        
        Returns:
            Session data dictionary or None if not found
            Format: {
                "session_id": int,
                "name": str,
                "created_at": str,
                "last_updated": str,
                "messages": [...],
                "message_count": int
            }
        
        Usage:
            session_data = session_manager.load_session("meeting notes")
            if session_data:
                session_memory.from_dict(session_data)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, created_at, last_updated, messages, message_count
                FROM sessions
                WHERE name = ?
            """, (name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning(f"Session '{name}' not found")
                return None
            
            # Parse result
            session_data = {
                "session_id": row[0],
                "name": row[1],
                "created_at": row[2],
                "last_updated": row[3],
                "messages": json.loads(row[4]),
                "message_count": row[5]
            }
            
            logger.info(f"Loaded session '{name}' ({session_data['message_count']} messages)")
            return session_data
        
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            raise
    
    def load_session_by_id(self, session_id: int) -> Optional[Dict]:
        """
        Load a session from the database by ID.
        
        Args:
            session_id: Session ID
        
        Returns:
            Session data dictionary or None if not found
        
        Why load by ID?
        - When listing sessions, we show IDs
        - User can say "load session 3" instead of remembering name
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, created_at, last_updated, messages, message_count
                FROM sessions
                WHERE id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning(f"Session ID {session_id} not found")
                return None
            
            # Parse result
            session_data = {
                "session_id": row[0],
                "name": row[1],
                "created_at": row[2],
                "last_updated": row[3],
                "messages": json.loads(row[4]),
                "message_count": row[5]
            }
            
            logger.info(f"Loaded session ID {session_id} ('{session_data['name']}')")
            return session_data
        
        except Exception as e:
            logger.error(f"Failed to load session by ID: {e}")
            raise
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Dict]:
        """
        List all saved sessions (metadata only, not full messages).
        
        Args:
            limit: Maximum number of sessions to return (None = all)
        
        Returns:
            List of session summaries:
            [
                {
                    "session_id": 1,
                    "name": "project planning",
                    "created_at": "2025-11-05T10:30:00",
                    "last_updated": "2025-11-05T11:45:00",
                    "message_count": 24
                },
                ...
            ]
        
        Ordered by: most recent first (last_updated DESC)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query sessions (most recent first)
            query = """
                SELECT id, name, created_at, last_updated, message_count
                FROM sessions
                ORDER BY last_updated DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            # Format results
            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "last_updated": row[3],
                    "message_count": row[4]
                })
            
            logger.info(f"Listed {len(sessions)} sessions")
            return sessions
        
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise
    
    def delete_session(self, name: str) -> bool:
        """
        Delete a session by name.
        
        Args:
            name: Session name
        
        Returns:
            True if deleted, False if not found
        
        Usage:
            if session_manager.delete_session("old notes"):
                print("Session deleted")
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sessions WHERE name = ?", (name,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Deleted session '{name}'")
                return True
            else:
                logger.warning(f"Session '{name}' not found (nothing deleted)")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            raise
    
    def delete_session_by_id(self, session_id: int) -> bool:
        """
        Delete a session by ID.
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted, False if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Deleted session ID {session_id}")
                return True
            else:
                logger.warning(f"Session ID {session_id} not found (nothing deleted)")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete session by ID: {e}")
            raise
    
    def session_exists(self, name: str) -> bool:
        """
        Check if a session with given name exists.
        
        Args:
            name: Session name
        
        Returns:
            True if exists, False otherwise
        
        Why this method?
        - Before saving, check if we're overwriting
        - Show warning to user: "Session 'notes' already exists. Overwrite?"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE name = ?", (name,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
        
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False
    
    def get_session_count(self) -> int:
        """
        Get total number of saved sessions.
        
        Returns:
            Number of sessions
        
        Why this method?
        - Show stats to user: "You have 15 saved sessions"
        - Warn if too many: "You have 100+ sessions, consider cleaning up"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sessions")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        
        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0
    
    def search_sessions(self, query: str) -> List[Dict]:
        """
        Search sessions by name (case-insensitive partial match).
        
        Args:
            query: Search query (e.g., "meeting")
        
        Returns:
            List of matching sessions (same format as list_sessions)
        
        Why this method?
        - User can search: "find my project sessions"
        - Fuzzy matching: "meet" matches "meeting notes", "team meeting"
        
        Usage:
            results = session_manager.search_sessions("project")
            # Returns sessions with "project" in name
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use LIKE for partial matching, % wildcards
            cursor.execute("""
                SELECT id, name, created_at, last_updated, message_count
                FROM sessions
                WHERE name LIKE ?
                ORDER BY last_updated DESC
            """, (f"%{query}%",))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Format results
            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "last_updated": row[3],
                    "message_count": row[4]
                })
            
            logger.info(f"Search '{query}': found {len(sessions)} sessions")
            return sessions
        
        except Exception as e:
            logger.error(f"Failed to search sessions: {e}")
            raise
    
    def rename_session(self, old_name: str, new_name: str) -> bool:
        """
        Rename a session.
        
        Args:
            old_name: Current session name
            new_name: New session name
        
        Returns:
            True if renamed, False if not found
        
        Why this method?
        - User can fix typos: "meetng notes" → "meeting notes"
        - Better organization: "session1" → "project planning"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if new name already exists
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE name = ?", (new_name,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                raise ValueError(f"Session '{new_name}' already exists")
            
            # Rename
            cursor.execute("""
                UPDATE sessions 
                SET name = ?, last_updated = ?
                WHERE name = ?
            """, (new_name, datetime.now().isoformat(), old_name))
            
            updated_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                logger.info(f"Renamed session '{old_name}' → '{new_name}'")
                return True
            else:
                logger.warning(f"Session '{old_name}' not found (nothing renamed)")
                return False
        
        except Exception as e:
            logger.error(f"Failed to rename session: {e}")
            raise


# ============================================================================
# MODULE TEST
# ============================================================================
if __name__ == "__main__":
    import tempfile
    import shutil
    from pathlib import Path
    
    print("=" * 70)
    print("SESSION MANAGER TEST")
    print("=" * 70)
    
    # Create temporary database for testing
    temp_dir = Path(tempfile.mkdtemp())
    test_db = temp_dir / "test_sessions.db"
    
    try:
        # Test 1: Initialize manager
        print("\n📝 Test 1: Initialize session manager")
        print("-" * 70)
        
        manager = SessionManager(db_path=test_db)
        print(f"✅ Manager initialized: {test_db}")
        print(f"   Database exists: {test_db.exists()}")
        
        # Test 2: Save a session
        print("\n📝 Test 2: Save session")
        print("-" * 70)
        
        session_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"},
                {"role": "assistant", "content": "I'm doing well!"}
            ],
            "session_start": datetime.now().isoformat(),
            "message_count": 4,
            "duration": "2 minutes"
        }
        
        session_id = manager.save_session("test session", session_data)
        print(f"✅ Saved session: ID={session_id}")
        
        # Test 3: Load session
        print("\n📝 Test 3: Load session")
        print("-" * 70)
        
        loaded = manager.load_session("test session")
        print(f"✅ Loaded session: {loaded['name']}")
        print(f"   Messages: {loaded['message_count']}")
        print(f"   Created: {loaded['created_at']}")
        
        # Test 4: List sessions
        print("\n📝 Test 4: List sessions")
        print("-" * 70)
        
        # Save more sessions
        for i in range(3):
            data = session_data.copy()
            data["message_count"] = 5 + i
            manager.save_session(f"session {i+1}", data)
        
        sessions = manager.list_sessions()
        print(f"✅ Listed {len(sessions)} sessions:")
        for s in sessions:
            print(f"   [{s['session_id']}] {s['name']} - {s['message_count']} messages")
        
        # Test 5: Session exists check
        print("\n📝 Test 5: Check session existence")
        print("-" * 70)
        
        exists = manager.session_exists("test session")
        not_exists = manager.session_exists("nonexistent")
        
        print(f"✅ 'test session' exists: {exists}")
        print(f"   'nonexistent' exists: {not_exists}")
        
        # Test 6: Get session count
        print("\n📝 Test 6: Get session count")
        print("-" * 70)
        
        count = manager.get_session_count()
        print(f"✅ Total sessions: {count}")
        
        # Test 7: Search sessions
        print("\n📝 Test 7: Search sessions")
        print("-" * 70)
        
        results = manager.search_sessions("session")
        print(f"✅ Search 'session': found {len(results)} results")
        for r in results:
            print(f"   - {r['name']}")
        
        # Test 8: Rename session
        print("\n📝 Test 8: Rename session")
        print("-" * 70)
        
        renamed = manager.rename_session("test session", "renamed session")
        print(f"✅ Renamed: {renamed}")
        
        # Verify
        exists_old = manager.session_exists("test session")
        exists_new = manager.session_exists("renamed session")
        print(f"   Old name exists: {exists_old}")
        print(f"   New name exists: {exists_new}")
        
        # Test 9: Load by ID
        print("\n📝 Test 9: Load session by ID")
        print("-" * 70)
        
        loaded_by_id = manager.load_session_by_id(session_id)
        print(f"✅ Loaded by ID {session_id}: {loaded_by_id['name']}")
        
        # Test 10: Delete session
        print("\n📝 Test 10: Delete session")
        print("-" * 70)
        
        deleted = manager.delete_session("renamed session")
        print(f"✅ Deleted: {deleted}")
        
        # Verify
        count_after = manager.get_session_count()
        print(f"   Sessions remaining: {count_after}")
        
        # Test 11: Update existing session
        print("\n📝 Test 11: Update existing session")
        print("-" * 70)
        
        updated_data = session_data.copy()
        updated_data["message_count"] = 10
        
        manager.save_session("session 1", updated_data)  # Same name = update
        updated = manager.load_session("session 1")
        
        print(f"✅ Updated 'session 1'")
        print(f"   New message count: {updated['message_count']}")
        
        print("\n" + "=" * 70)
        print("✅ All session manager tests passed!")
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up test directory: {temp_dir}")