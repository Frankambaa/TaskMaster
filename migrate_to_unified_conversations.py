#!/usr/bin/env python3
"""
Migration script to merge UserConversation and LiveChatSession tables into unified_conversations
and LiveChatMessage into unified_messages.
"""

import os
import sys
import json
from datetime import datetime
from uuid import uuid4

# Add the current directory to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import UnifiedConversation, UnifiedMessage

def migrate_user_conversations():
    """Migrate data from user_conversations table to unified_conversations"""
    print("🔄 Migrating UserConversation data to UnifiedConversation...")
    
    try:
        # Check if the old table exists
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user_conversations';
            """))
            if not result.fetchone():
                print("✅ user_conversations table not found, skipping migration")
                return
        
        # Fetch old conversation data
        with db.engine.connect() as conn:
            old_conversations = conn.execute(db.text("""
                SELECT * FROM user_conversations
            """)).fetchall()
        
        migrated_count = 0
        for row in old_conversations:
            # Check if already migrated
            existing = UnifiedConversation.query.filter_by(
                user_identifier=row.user_identifier,
                conversation_type='chatbot'
            ).first()
            
            if existing:
                continue
            
            # Create new unified conversation
            session_id = f"chatbot_{uuid4().hex[:12]}"
            conversation = UnifiedConversation(
                session_id=session_id,
                user_identifier=row.user_identifier,
                username=row.username,
                email=row.email,
                device_id=row.device_id,
                conversation_type='chatbot',
                status='active',
                created_at=row.created_at,
                updated_at=row.last_activity,
                last_activity=row.last_activity
            )
            
            db.session.add(conversation)
            db.session.flush()  # Get the ID
            
            # Migrate conversation history to individual messages
            try:
                conversation_data = json.loads(row.conversation_data) if row.conversation_data else []
                
                for i, msg_data in enumerate(conversation_data):
                    msg_type = msg_data.get('type', 'user')
                    sender_type = 'user' if msg_type == 'human' else 'assistant'
                    
                    message = UnifiedMessage(
                        session_id=session_id,
                        message_id=f"migrated_{uuid4().hex[:12]}",
                        sender_type=sender_type,
                        sender_name='User' if sender_type == 'user' else 'Assistant',
                        message_content=msg_data.get('content', ''),
                        message_type='text',
                        created_at=datetime.fromisoformat(msg_data.get('timestamp', row.created_at.isoformat()).replace('Z', '+00:00')) if 'timestamp' in msg_data else row.created_at
                    )
                    db.session.add(message)
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Error parsing conversation data for {row.user_identifier}: {e}")
            
            migrated_count += 1
        
        db.session.commit()
        print(f"✅ Migrated {migrated_count} user conversations to unified model")
        
    except Exception as e:
        print(f"❌ Error migrating user conversations: {e}")
        db.session.rollback()

def migrate_live_chat_sessions():
    """Migrate data from live_chat_sessions and live_chat_messages to unified tables"""
    print("🔄 Migrating LiveChatSession data to UnifiedConversation...")
    
    try:
        # Check if the old tables exist
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='live_chat_sessions';
            """))
            if not result.fetchone():
                print("✅ live_chat_sessions table not found, skipping migration")
                return
        
        # Fetch old session data
        with db.engine.connect() as conn:
            old_sessions = conn.execute(db.text("""
                SELECT * FROM live_chat_sessions
            """)).fetchall()
        
        migrated_sessions = 0
        migrated_messages = 0
        
        for row in old_sessions:
            # Check if already migrated
            existing = UnifiedConversation.query.filter_by(
                session_id=row.session_id
            ).first()
            
            if existing:
                continue
            
            # Create new unified conversation
            conversation = UnifiedConversation(
                session_id=row.session_id,
                user_identifier=row.user_identifier,
                username=row.username,
                email=row.email,
                agent_id=row.agent_id,
                agent_name=row.agent_name,
                conversation_type='live_chat',
                status=row.status,
                priority=row.priority,
                department=row.department,
                initial_message=row.initial_message,
                tags=row.tags,
                created_at=row.created_at,
                updated_at=row.updated_at,
                last_activity=row.updated_at,
                completed_at=row.completed_at
            )
            
            db.session.add(conversation)
            db.session.flush()
            
            # Migrate associated messages
            with db.engine.connect() as conn:
                old_messages = conn.execute(db.text("""
                    SELECT * FROM live_chat_messages WHERE session_id = :session_id
                """), {"session_id": row.session_id}).fetchall()
            
            for msg_row in old_messages:
                # Check if message already migrated
                existing_msg = UnifiedMessage.query.filter_by(
                    message_id=msg_row.message_id
                ).first()
                
                if existing_msg:
                    continue
                
                message = UnifiedMessage(
                    session_id=msg_row.session_id,
                    message_id=msg_row.message_id,
                    sender_type=msg_row.sender_type,
                    sender_id=msg_row.sender_id,
                    sender_name=msg_row.sender_name,
                    message_content=msg_row.message_content,
                    message_type=msg_row.message_type,
                    message_metadata=msg_row.message_metadata,
                    is_read=msg_row.is_read,
                    created_at=msg_row.created_at
                )
                db.session.add(message)
                migrated_messages += 1
            
            migrated_sessions += 1
        
        db.session.commit()
        print(f"✅ Migrated {migrated_sessions} live chat sessions and {migrated_messages} messages to unified model")
        
    except Exception as e:
        print(f"❌ Error migrating live chat sessions: {e}")
        db.session.rollback()

def create_unified_tables():
    """Create the new unified tables"""
    print("🔄 Creating unified conversation tables...")
    
    try:
        with app.app_context():
            db.create_all()
        print("✅ Unified tables created successfully")
        
    except Exception as e:
        print(f"❌ Error creating unified tables: {e}")

def verify_migration():
    """Verify the migration was successful"""
    print("\n📊 Migration verification:")
    
    try:
        chatbot_conversations = UnifiedConversation.query.filter_by(conversation_type='chatbot').count()
        live_chat_conversations = UnifiedConversation.query.filter_by(conversation_type='live_chat').count()
        total_messages = UnifiedMessage.query.count()
        
        print(f"✅ Chatbot conversations: {chatbot_conversations}")
        print(f"✅ Live chat conversations: {live_chat_conversations}")
        print(f"✅ Total messages: {total_messages}")
        print(f"✅ Total unified conversations: {chatbot_conversations + live_chat_conversations}")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")

def main():
    """Main migration function"""
    print("🚀 Starting migration to unified conversation model...\n")
    
    with app.app_context():
        # Create new tables
        create_unified_tables()
        
        # Migrate data
        migrate_user_conversations()
        migrate_live_chat_sessions()
        
        # Verify migration
        verify_migration()
    
    print("\n✅ Migration completed successfully!")
    print("\n📝 Next steps:")
    print("1. Update your application to use UnifiedConversation instead of UserConversation and LiveChatSession")
    print("2. Test the application thoroughly")
    print("3. Once verified, you can drop the old tables: user_conversations, live_chat_sessions, live_chat_messages")

if __name__ == "__main__":
    main()