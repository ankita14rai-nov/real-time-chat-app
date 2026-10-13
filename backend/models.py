from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False)

    email = Column(String(100), unique=True, nullable=False)

    password = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)



class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id = Column(Integer, primary_key=True, index=True)

    sender_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    status = Column(
        String,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    sender = relationship(
        "User",
        foreign_keys=[sender_id]
    )

    receiver = relationship(
        "User",
        foreign_keys=[receiver_id]
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    sender_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    # Text Message
    message = Column(
        String(255),
        nullable=True
    )

    # Uploaded File Name
    file_name = Column(
        String(255),
        nullable=True
    )

    # Stored File Path
    file_path = Column(
        String(255),
        nullable=True
    )

    # text / image / video / document
    message_type = Column(
        String(20),
        default="text"
    )

    # sent / delivered / read
    status = Column(
        String(20),
        default="sent"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )