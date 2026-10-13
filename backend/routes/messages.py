import os
import shutil
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db
from models import User, Message, FriendRequest
from schemas import MessageCreate, MessageEdit, MessageResponse
from security import get_current_user
from connection_manager import manager


router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)


# =====================================
# Send Message
# =====================================
@router.post("/send", response_model=MessageResponse)
def send_message(
    request: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receiver = db.query(User).filter(User.email == request.receiver_email).first()

    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    if receiver.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot message yourself")

    friendship = db.query(FriendRequest).filter(
        (
            (FriendRequest.sender_id == current_user.id) &
            (FriendRequest.receiver_id == receiver.id)
        ) |
        (
            (FriendRequest.sender_id == receiver.id) &
            (FriendRequest.receiver_id == current_user.id)
        ),
        FriendRequest.status == "accepted"
    ).first()

    if not friendship:
        raise HTTPException(status_code=403, detail="You can only message your friends")

    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        message=request.message
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


# =====================================
# Chat History
# =====================================
@router.get("/chat/{friend_id}")
def get_chat_history(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    friendship = db.query(FriendRequest).filter(
        (
            (FriendRequest.sender_id == current_user.id) &
            (FriendRequest.receiver_id == friend_id)
        ) |
        (
            (FriendRequest.sender_id == friend_id) &
            (FriendRequest.receiver_id == current_user.id)
        ),
        FriendRequest.status == "accepted"
    ).first()

    if not friendship:
        raise HTTPException(status_code=403, detail="You are not friends with this user")

    messages = db.query(Message).filter(
        or_(
            and_(
                Message.sender_id == current_user.id,
                Message.receiver_id == friend_id
            ),
            and_(
                Message.sender_id == friend_id,
                Message.receiver_id == current_user.id
            )
        )
    ).order_by(Message.created_at.asc()).all()

    return messages


# =====================================
# Upload File (Fixed for FormData)
# =====================================
@router.post("/upload")
async def upload_file(
    receiver_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    if receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot send a file to yourself")

    friendship = db.query(FriendRequest).filter(
        (
            (FriendRequest.sender_id == current_user.id) &
            (FriendRequest.receiver_id == receiver_id)
        ) |
        (
            (FriendRequest.sender_id == receiver_id) &
            (FriendRequest.receiver_id == current_user.id)
        ),
        FriendRequest.status == "accepted"
    ).first()

    if not friendship:
        raise HTTPException(status_code=403, detail="You can only send files to your friends")

    original_filename = file.filename or "uploaded_file"
    content_type = file.content_type or ""
    BASE_DIR = Path(__file__).resolve().parent.parent

    if content_type.startswith("image"):
        folder = BASE_DIR / "uploads" / "images"
        message_type = "image"
    elif content_type.startswith("video"):
        folder = BASE_DIR / "uploads" / "videos"
        message_type = "video"
    else:
        folder = BASE_DIR / "uploads" / "documents"
        message_type = "document"

    folder.mkdir(parents=True, exist_ok=True)
    extension = os.path.splitext(original_filename)[1]
    unique_name = f"{uuid4()}{extension}"
    
    absolute_path = folder / unique_name
    relative_path = Path("uploads") / folder.name / unique_name

    try:
        with open(absolute_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not save uploaded file")

    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message=None,
        file_name=original_filename,
        file_path=relative_path.as_posix(),
        message_type=message_type,
        status="sent"
    )

    try:
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
    except Exception as e:
        db.rollback()
        if absolute_path.exists():
            absolute_path.unlink()
        raise HTTPException(status_code=500, detail="Could not save file message to database")

    return {
        "message": "File uploaded successfully",
        "file_name": original_filename,
        "file_path": relative_path.as_posix(),
        "message_type": message_type,
        "message_id": new_message.id,
        "status": new_message.status
    }


# =====================================
# Edit Message
# =====================================
@router.put("/edit/{message_id}")
async def edit_message(
    message_id: int,
    data: MessageEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")

    if message.message_type != "text":
        raise HTTPException(status_code=400, detail="Only text messages can be edited")

    new_message = data.message.strip()
    if not new_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    message.message = new_message
    db.commit()
    db.refresh(message)

    edit_response = {
        "type": "edit",
        "message_id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "message": message.message,
        "message_type": message.message_type
    }

    await manager.send_personal_message(edit_response, message.receiver_id)
    await manager.send_personal_message(edit_response, message.sender_id)

    return {
        "message": "Message edited successfully",
        "message_id": message.id,
        "new_message": message.message
    }


# =====================================
# Delete Message
# =====================================
@router.delete("/delete/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can delete only your own messages")

    if message.file_path and os.path.exists(message.file_path):
        os.remove(message.file_path)

    receiver_id = message.receiver_id
    sender_id = message.sender_id
    message_id_to_delete = message.id

    db.delete(message)
    db.commit()
    
    await manager.send_delete_message(message_id_to_delete, sender_id)
    await manager.send_delete_message(message_id_to_delete, receiver_id)
    
    return {"message": "Message deleted successfully"}


# =====================================
# Mark Messages Read (Bulk)
# =====================================
@router.put("/read/friend/{friend_id}")
async def mark_messages_read(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        Message.sender_id == friend_id,
        Message.receiver_id == current_user.id,
        Message.status != "read"
    ).all()

    for msg in messages:
        msg.status = "read"

    db.commit()

    if manager.is_online(friend_id):
        for msg in messages:
            await manager.send_personal_message(
                {"type": "status", "message_id": msg.id, "status": "read"},
                friend_id
            )

    return {"message": "Messages marked as read"}


# =====================================
# Mark Single Message Read
# =====================================
@router.put("/read/message/{message_id}")
def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot mark this message as read")

    if message.status == "read":
        return {"message": "Message already read", "message_id": message.id}

    message.status = "read"
    db.commit()

    return {"message": "Message marked as read", "message_id": message.id}