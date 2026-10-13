from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, FriendRequest
from schemas import (
    FriendRequestCreate,
    FriendResponse,
    FriendInfo
)
from security import get_current_user

router = APIRouter(
    prefix="/friends",
    tags=["Friends"]
)


# Send Friend Request
# ===========================
@router.post("/request", response_model=FriendResponse)
def send_friend_request(
    request: FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Find receiver
    receiver = db.query(User).filter(
        User.email == request.receiver_email
    ).first()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent sending request to yourself
    if receiver.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send a request to yourself"
        )

    # Check only pending request
    existing = db.query(FriendRequest).filter(
        FriendRequest.sender_id == current_user.id,
        FriendRequest.receiver_id == receiver.id,
        FriendRequest.status == "pending"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Friend request already sent"
        )

    # Create friend request
    friend_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        status="pending"
    )

    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)

    return friend_request


# ===========================
# Get Pending Requests
# ===========================
@router.get("/requests")
def get_friend_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    requests = db.query(FriendRequest).filter(
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()

    result = []

    for request in requests:

        sender = db.query(User).filter(
            User.id == request.sender_id
        ).first()

        result.append({
            "request_id": request.id,
            "sender_id": sender.id,
            "sender_username": sender.username,
            "sender_email": sender.email,
            "status": request.status
        })

    return result


# ===========================
# Accept Friend Request
# ===========================
@router.put("/accept/{request_id}")
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()

    if not friend_request:
        raise HTTPException(
            status_code=404,
            detail="Friend request not found"
        )

    friend_request.status = "accepted"

    db.commit()

    return {
        "message": "Friend request accepted successfully"
    }


# ===========================
# Reject Friend Request
# ===========================
@router.delete("/reject/{request_id}")
def reject_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()

    if not friend_request:
        raise HTTPException(
            status_code=404,
            detail="Friend request not found"
        )

    db.delete(friend_request)
    db.commit()

    return {
        "message": "Friend request rejected"
    }

@router.get("/list", response_model=list[FriendInfo])
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    accepted_requests = db.query(FriendRequest).filter(
        (
            (FriendRequest.sender_id == current_user.id) |
            (FriendRequest.receiver_id == current_user.id)
        ),
        FriendRequest.status == "accepted"
    ).all()

    friends = []

    for request in accepted_requests:

        if request.sender_id == current_user.id:
            friend = db.query(User).filter(
                User.id == request.receiver_id
            ).first()
        else:
            friend = db.query(User).filter(
                User.id == request.sender_id
            ).first()

        friends.append(friend)

    return friends