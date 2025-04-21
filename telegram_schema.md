# 📊 Telegram Database Schema

## 1. app_users
- id: UUID, PK
- email: TEXT, UNIQUE
- password_hash: TEXT
- session_file: TEXT (path to session)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

## 2. target_chats
- id: SERIAL, PK
- chat_id: BIGINT, UNIQUE
- title: TEXT
- username: TEXT
- access_hash: BIGINT
- type: TEXT (group, channel, supergroup)
- status: TEXT (new, collected, monitoring)
- added_by: UUID (FK to app_users)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

## 3. users
- id: BIGINT, PK
- access_hash: BIGINT
- username: TEXT
- first_name: TEXT
- last_name: TEXT
- phone: TEXT
- is_contact: BOOLEAN
- is_deleted: BOOLEAN
- is_bot: BOOLEAN
- is_verified: BOOLEAN
- is_restricted: BOOLEAN
- is_scam: BOOLEAN
- is_fake: BOOLEAN
- lang_code: TEXT
- status: TEXT
- last_seen_at: TIMESTAMP
- added_by_user: UUID
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

## 4. chat_participants
- id: SERIAL, PK
- chat_id: BIGINT (FK to target_chats)
- user_id: BIGINT (FK to users)
- participant_type: TEXT (admin, creator, member)
- inviter_user_id: BIGINT (nullable)
- joined_date: TIMESTAMP (nullable)
- added_at: TIMESTAMP

## 5. messages
- id: BIGINT, PK
- chat_id: BIGINT (FK to target_chats)
- user_id: BIGINT (FK to users)
- message_text: TEXT
- message_type: TEXT (text, media, etc.)
- media_path: TEXT (nullable)
- media_type: TEXT (nullable)
- reply_to_msg_id: BIGINT (nullable)
- forwarded_from_id: BIGINT (nullable)
- views: INTEGER (nullable)
- forwards: INTEGER (nullable)
- reactions: JSONB (nullable)
- date: TIMESTAMP

## 6. private_messages
- id: BIGINT, PK
- from_user_id: BIGINT
- to_user_id: BIGINT
- message_text: TEXT
- date: TIMESTAMP
- media_type: TEXT (nullable)
- media_path: TEXT (nullable)

## 7. user_contacts
- id: SERIAL, PK
- owner_user_id: UUID (FK to app_users)
- contact_user_id: BIGINT (nullable)
- phone: TEXT
- first_name: TEXT
- last_name: TEXT
- username: TEXT
- imported_at: TIMESTAMP

## 8. message_entities
- id: SERIAL, PK
- message_id: BIGINT (FK to messages)
- type: TEXT (url, mention, etc.)
- offset: INTEGER
- length: INTEGER
- value: TEXT

## 9. message_files
- id: SERIAL, PK
- message_id: BIGINT (FK to messages)
- file_type: TEXT (photo, video, document)
- file_path: TEXT
- file_size: INTEGER (nullable)
- mime_type: TEXT (nullable)