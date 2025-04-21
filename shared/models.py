# telegram-intel/shared/models.py

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from sqlalchemy import (
    create_engine, MetaData, Table, Column, ForeignKey, CheckConstraint, UniqueConstraint, Index, ForeignKeyConstraint,
    Integer, String, BigInteger, Text, DateTime, Boolean, LargeBinary, JSON, Float, Enum as PgEnum
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func, and_ # Добавляем 'and_' для primaryjoin

# Используем TYPE_CHECKING для строковых type hints, чтобы избежать циклических импортов
if TYPE_CHECKING:
    from .models import ( # Предполагаем, что все модели в этом файле
        AppUser, TargetChat, User, ChatParticipant, Message,
        PrivateMessage, UserContact, MessageEntity, MessageFile
    )

# Определяем базовый класс для декларативных моделей
class Base(DeclarativeBase):
    pass

# 1. app_users - Пользователи нашего приложения
class AppUser(Base):
    __tablename__ = 'app_users'

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    session_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи (Relationships)
    added_target_chats: Mapped[List["TargetChat"]] = relationship(back_populates="added_by_user_rel")
    owned_contacts: Mapped[List["UserContact"]] = relationship(back_populates="owner_user")
    # added_telegram_users: Mapped[List["User"]] = relationship(back_populates="added_by_app_user_rel")

    def __repr__(self) -> str:
        return f"<AppUser(id={self.id}, email='{self.email}')>"

# 3. users - Пользователи Telegram
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    access_hash: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    is_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_scam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fake: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lang_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    added_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PgUUID(as_uuid=True), ForeignKey('app_users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Связи ---
    added_by_app_user_rel: Mapped[Optional["AppUser"]] = relationship(foreign_keys=[added_by_user_id])

    # Связь User -> Message (где User - отправитель)
    messages: Mapped[List["Message"]] = relationship(
        back_populates="user",
        foreign_keys="Message.user_id"
    )

    participations: Mapped[List["ChatParticipant"]] = relationship(
        back_populates="user",
        foreign_keys="ChatParticipant.user_id"
    )


    sent_private_messages: Mapped[List["PrivateMessage"]] = relationship(foreign_keys="PrivateMessage.from_user_id", back_populates="sender")
    received_private_messages: Mapped[List["PrivateMessage"]] = relationship(foreign_keys="PrivateMessage.to_user_id", back_populates="receiver")
    contacts: Mapped[List["UserContact"]] = relationship(back_populates="telegram_user")

    invited_participants: Mapped[List["ChatParticipant"]] = relationship(
        foreign_keys="ChatParticipant.inviter_user_id",
        back_populates="inviter"
    )


    forwarded_messages: Mapped[List["Message"]] = relationship(
        foreign_keys="Message.forwarded_from_id",
        back_populates="forwarded_from_user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

# 2. target_chats - Целевые чаты для сбора данных
class TargetChat(Base):
    __tablename__ = 'target_chats'

    internal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    access_hash: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default='new', nullable=False, index=True)
    added_by: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey('app_users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи
    added_by_user_rel: Mapped["AppUser"] = relationship(back_populates="added_target_chats")
    participants: Mapped[List["ChatParticipant"]] = relationship(
        back_populates="chat",
        primaryjoin="TargetChat.chat_id == ChatParticipant.chat_id",
        foreign_keys="ChatParticipant.chat_id"
    )
    messages: Mapped[List["Message"]] = relationship(
        back_populates="chat",
        primaryjoin="TargetChat.chat_id == Message.chat_id",
        foreign_keys="Message.chat_id"
    )

    __table_args__ = (
        UniqueConstraint('chat_id', name='uq_target_chats_chat_id'),
    )

    def __repr__(self) -> str:
        return f"<TargetChat(internal_id={self.internal_id}, chat_id={self.chat_id}, title='{self.title}')>"

# 4. chat_participants - Участники целевых чатов
class ChatParticipant(Base):
    __tablename__ = 'chat_participants'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('target_chats.chat_id'), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False) # Сам участник
    participant_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inviter_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True) # Пригласивший
    joined_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    chat: Mapped["TargetChat"] = relationship(back_populates="participants", foreign_keys=[chat_id])

    # Связь ChatParticipant -> User (участник)
    user: Mapped["User"] = relationship(back_populates="participations", foreign_keys=[user_id])

    # Связь ChatParticipant -> User (пригласивший)
    inviter: Mapped[Optional["User"]] = relationship(
        foreign_keys=[inviter_user_id],
        back_populates="invited_participants")

    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id', name='uq_chat_participant'),
        Index('ix_chat_participants_chat_id', 'chat_id'),
        Index('ix_chat_participants_user_id', 'user_id'),
    )

    def __repr__(self) -> str:
        return f"<ChatParticipant(chat_id={self.chat_id}, user_id={self.user_id}, type='{self.participant_type}')>"

# 5. messages - Сообщения из целевых чатов
class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('target_chats.chat_id'), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)
    message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message_type: Mapped[str] = mapped_column(Text, nullable=False, default='text', index=True)
    media_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reply_to_msg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    forwarded_from_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    forwards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reactions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Связи
    chat: Mapped["TargetChat"] = relationship(back_populates="messages", foreign_keys=[chat_id])
    user: Mapped[Optional["User"]] = relationship(back_populates="messages", foreign_keys=[user_id])
    forwarded_from_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[forwarded_from_id],
        back_populates="forwarded_messages"
    )
    entities: Mapped[List["MessageEntity"]] = relationship(back_populates="message")
    files: Mapped[List["MessageFile"]] = relationship(back_populates="message")

    __table_args__ = (
        UniqueConstraint('id', 'chat_id', name='uq_message_id_chat_id'),
        Index('ix_messages_chat_id_date', 'chat_id', 'date'),
        Index('ix_messages_user_id', 'user_id'),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, chat_id={self.chat_id}, user_id={self.user_id}, date='{self.date}')>"

# 6. private_messages - Сообщения из личных переписок
class PrivateMessage(Base):
    __tablename__ = 'private_messages'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    from_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    to_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    media_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи
    sender: Mapped["User"] = relationship(foreign_keys=[from_user_id], back_populates="sent_private_messages")
    receiver: Mapped["User"] = relationship(foreign_keys=[to_user_id], back_populates="received_private_messages")

    __table_args__ = (
        Index('ix_private_messages_dialog_date', 'from_user_id', 'to_user_id', 'date'),
    )

    def __repr__(self) -> str:
        return f"<PrivateMessage(id={self.id}, from={self.from_user_id}, to={self.to_user_id}, date='{self.date}')>"

# 7. user_contacts - Контакты, импортированные пользователями приложения
class UserContact(Base):
    __tablename__ = 'user_contacts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey('app_users.id'), nullable=False, index=True)
    contact_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    owner_user: Mapped["AppUser"] = relationship(back_populates="owned_contacts")
    telegram_user: Mapped[Optional["User"]] = relationship(back_populates="contacts")

    __table_args__ = (
        UniqueConstraint('owner_user_id', 'contact_user_id', name='uq_user_contact_link'),
        UniqueConstraint('owner_user_id', 'phone', name='uq_user_contact_phone'),
    )

    def __repr__(self) -> str:
        return f"<UserContact(id={self.id}, owner='{self.owner_user_id}', tg_user={self.contact_user_id}, phone='{self.phone}')>"

# 8. message_entities - Сущности в тексте сообщения
class MessageEntity(Base):
    __tablename__ = 'message_entities'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    offset: Mapped[int] = mapped_column(Integer, nullable=False)
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи
    message: Mapped["Message"] = relationship(
        back_populates="entities",
        primaryjoin="and_(MessageEntity.message_id == Message.id, MessageEntity.chat_id == Message.chat_id)",
        foreign_keys=[message_id, chat_id]
    )

    __table_args__ = (
        ForeignKeyConstraint(['message_id', 'chat_id'], ['messages.id', 'messages.chat_id'], name='fk_message_entity_message', ondelete='CASCADE'),
        Index('ix_message_entities_message_id_chat_id', 'message_id', 'chat_id'),
    )

    def __repr__(self) -> str:
        return f"<MessageEntity(id={self.id}, msg_id={self.message_id}, chat_id={self.chat_id}, type='{self.type}')>"

# 9. message_files - Файлы, прикрепленные к сообщениям
class MessageFile(Base):
    __tablename__ = 'message_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи
    message: Mapped["Message"] = relationship(
        back_populates="files",
        primaryjoin="and_(MessageFile.message_id == Message.id, MessageFile.chat_id == Message.chat_id)",
        foreign_keys=[message_id, chat_id]
    )

    __table_args__ = (
        ForeignKeyConstraint(['message_id', 'chat_id'], ['messages.id', 'messages.chat_id'], name='fk_message_file_message', ondelete='CASCADE'),
        Index('ix_message_files_message_id_chat_id', 'message_id', 'chat_id'),
    )

    def __repr__(self) -> str:
        return f"<MessageFile(id={self.id}, msg_id={self.message_id}, chat_id={self.chat_id}, type='{self.file_type}', path='{self.file_path}')>"


# Пример использования (для иллюстрации)
if __name__ == '__main__':
    print("SQLAlchemy модели определены в shared/models.py.")