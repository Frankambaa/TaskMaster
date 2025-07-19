#!/usr/bin/env python3
"""
Migration script to add response analysis fields to existing RAG feedback records
and create the new response_templates table.

Run this script after updating the models to migrate existing data.
"""

import os
import sqlite3
from datetime import datetime

def migrate_database():
    """Migrate the database schema to add new response analysis features"""
    
    # Connect to the SQLite database
    db_path = 'instance/chatbot.db'  # Adjust path as needed
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Creating new database...")
        # The new tables will be created automatically when the app runs
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # Check if new columns already exist
        cursor.execute("PRAGMA table_info(rag_feedback)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            'response_category',
            'improvement_suggestions', 
            'admin_notes',
            'training_priority'
        ]
        
        # Add missing columns to rag_feedback table
        for column in new_columns:
            if column not in columns:
                if column == 'training_priority':
                    cursor.execute(f"ALTER TABLE rag_feedback ADD COLUMN {column} VARCHAR(20) DEFAULT 'normal'")
                else:
                    cursor.execute(f"ALTER TABLE rag_feedback ADD COLUMN {column} TEXT")
                print(f"Added column: {column}")
        
        # Check if response_templates table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='response_templates'")
        if not cursor.fetchone():
            print("Creating response_templates table...")
            cursor.execute("""
                CREATE TABLE response_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT,
                    trigger_keywords JSON,
                    question_patterns JSON,
                    categories JSON,
                    template_text TEXT NOT NULL,
                    fallback_response TEXT,
                    priority INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    requires_context BOOLEAN DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    success_rate FLOAT DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(255)
                )
            """)
            
            # Insert a sample template for API clarification
            cursor.execute("""
                INSERT INTO response_templates 
                (name, description, trigger_keywords, categories, template_text, priority, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'API Clarification',
                'Better response for vague API-related questions',
                '["api", "make api call", "call api", "use api"]',
                '["api_clarification", "vague"]',
                """I can help you with API-related tasks! Here are the specific things I can do:

🔍 **Check Your Account Information:**
- View your current token/credit balance
- Check your job posting status
- See how many job posts you have

💡 **Get Instructions:**
- Learn how to post jobs step-by-step  
- Understand platform features and limits
- Get best practices and tips

To use API tools, please be specific about what data you want to see (like "show me my credit balance" or "what's my job status").

For instructions on how to do something, I can guide you through the process using our knowledge base.

What specific information or help do you need?""",
                100,  # High priority
                'migration_script',
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            print("Created response_templates table with sample data")
        
        conn.commit()
        print("Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✅ Migration completed! You can now restart the application.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")