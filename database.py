import sqlite3
import os
import json
from datetime import datetime, timedelta

DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot_data.db")

class Database:
    """Database operations for the bot."""
    
    def __init__(self):
        self.init_db()
    
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_searches INTEGER DEFAULT 0,
                saved_words INTEGER DEFAULT 0,
                quiz_attempts INTEGER DEFAULT 0,
                quiz_correct INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0
            )
        ''')
        
        # Saved words table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                definition TEXT,
                part_of_speech TEXT,
                saved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, word)
            )
        ''')
        
        # Word searches log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name, last_name=None):
        """Add a new user or update existing user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def add_word_search(self, user_id, word):
        """Log a word search."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Increment search count
        cursor.execute('''
            UPDATE users 
            SET total_searches = total_searches + 1 
            WHERE user_id = ?
        ''', (user_id,))
        
        # Log the search
        cursor.execute('''
            INSERT INTO word_searches (user_id, word)
            VALUES (?, ?)
        ''', (user_id, word))
        
        conn.commit()
        conn.close()
    
    def save_word(self, user_id, word, definition, part_of_speech):
        """Save a word to user's vocabulary."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO saved_words (user_id, word, definition, part_of_speech)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word, definition, part_of_speech))
            
            if cursor.rowcount > 0:
                # Increment saved words count
                cursor.execute('''
                    UPDATE users 
                    SET saved_words = saved_words + 1,
                        points = points + 5
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
            else:
                return False
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_saved_words(self, user_id):
        """Get all saved words for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT word, definition, part_of_speech, saved_date
            FROM saved_words
            WHERE user_id = ?
            ORDER BY saved_date DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def get_saved_words_count(self, user_id):
        """Get count of saved words."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM saved_words
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] if result else 0
    
    def update_quiz_result(self, user_id, is_correct):
        """Update quiz statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET quiz_attempts = quiz_attempts + 1,
                quiz_correct = quiz_correct + ?,
                points = points + ?
            WHERE user_id = ?
        ''', (1 if is_correct else 0, 2 if is_correct else 0, user_id))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id):
        """Get user statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                total_searches,
                saved_words,
                quiz_attempts,
                quiz_correct,
                points,
                CASE 
                    WHEN quiz_attempts > 0 
                    THEN ROUND(100.0 * quiz_correct / quiz_attempts, 1)
                    ELSE 0
                END as success_rate
            FROM users
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None
