from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import json

from database import SessionLocal
from models import Message, User, FriendRequest
from connection_manager import manager
from online_manager import online_manager
from security import SECRET_KEY, ALGORITHM


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    JWT-secured WebSocket endpoint.

    The authenticated user's ID is obtained
    from the JWT token, not from the URL.
    """

    # =====================================================
    # 1. VERIFY JWT TOKEN
    # =====================================================

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        subject = payload.get("sub")

        if subject is None:
            print("❌ JWT subject is missing")
            await websocket.close(code=1008)
            return

        # JWT may contain either:
        # sub = "1"
        # OR
        # sub = "rahul@gmail.com"

        if str(subject).isdigit():

            user_id = int(subject)

        else:

            db_auth: Session = SessionLocal()

            try:

                user = db_auth.query(User).filter(
                    User.email == subject
                ).first()

                if not user:
                    print(
                        f"❌ User not found for subject: {subject}"
                    )

                    await websocket.close(code=1008)
                    return

                user_id = user.id

            finally:

                db_auth.close()

    except (JWTError, ValueError, TypeError) as e:

        print(
            f"❌ Invalid WebSocket token: {e}"
        )

        await websocket.close(code=1008)
        return

    # =====================================================
    # 2. CONNECT USER
    # =====================================================

    await manager.connect(
        user_id,
        websocket
    )

    online_manager.connect(user_id)

    print(
        f"\n🟢 User {user_id} connected"
    )

    print(
        f"Online Users: "
        f"{online_manager.get_online_users()}"
    )

    db: Session = SessionLocal()

    try:

        # =================================================
        # 3. MAIN WEBSOCKET LOOP
        # =================================================

        while True:

            data = await websocket.receive_text()

            # -------------------------------------------------
            # Parse JSON
            # -------------------------------------------------

            try:

                message = json.loads(data)

            except json.JSONDecodeError:

                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

                continue

            message_type = message.get("type")

            # =================================================
            # 4. TYPING INDICATOR
            # =================================================

            if message_type == "typing":

                receiver_id = message.get("receiver_id")

                if receiver_id is None:
                    continue

                # Check receiver exists
                receiver = db.query(User).filter(
                    User.id == receiver_id
                ).first()

                if not receiver:
                    continue

                # Check friendship
                friendship = db.query(
                    FriendRequest
                ).filter(
                    (
                        (
                            FriendRequest.sender_id == user_id
                        )
                        &
                        (
                            FriendRequest.receiver_id
                            == receiver_id
                        )
                    )
                    |
                    (
                        (
                            FriendRequest.sender_id
                            == receiver_id
                        )
                        &
                        (
                            FriendRequest.receiver_id
                            == user_id
                        )
                    ),
                    FriendRequest.status == "accepted"
                ).first()

                if not friendship:
                    continue

                print(
                    f"✍️ User {user_id} "
                    f"is typing to User {receiver_id}"
                )

                await manager.send_personal_message(
                    {
                        "type": "typing",
                        "sender_id": user_id
                    },
                    receiver_id
                )

            # =================================================
            # 5. MARK MESSAGE AS READ
            # =================================================

            elif message_type == "read":

                message_id = message.get("message_id")

                if message_id is None:
                    continue

                print(
                    f"👀 User {user_id} "
                    f"is reading Message {message_id}"
                )

                db_message = db.query(Message).filter(
                    Message.id == message_id
                ).first()

                if not db_message:

                    print(
                        f"❌ Message {message_id} "
                        f"not found"
                    )

                    continue

                # Only receiver can mark it as read
                if db_message.receiver_id != user_id:

                    print(
                        f"❌ User {user_id} "
                        f"cannot mark Message "
                        f"{message_id} as read"
                    )

                    continue

                # Check current status
                if db_message.status == "read":

                    print(
                        f"ℹ️ Message {message_id} "
                        f"is already read"
                    )

                    continue

                db_message.status = "read"

                db.commit()

                print(
                    f"✅ Message {message_id} "
                    f"changed to READ"
                )

                # Notify sender
                await manager.send_personal_message(
                    {
                        "type": "status",
                        "message_id": db_message.id,
                        "sender_id": db_message.sender_id,
                        "status": "read"
                    },
                    db_message.sender_id
                )

                # Notify receiver
                await manager.send_personal_message(
                    {
                        "type": "status",
                        "message_id": db_message.id,
                        "sender_id": db_message.sender_id,
                        "status": "read"
                    },
                    user_id
                )

            # =================================================
            # 6. NORMAL TEXT MESSAGE
            # =================================================

            elif message_type == "message":

                receiver_id = message.get("receiver_id")
                message_text = message.get("message")

                # ---------------------------------------------
                # Validate receiver_id
                # ---------------------------------------------

                if receiver_id is None:

                    await websocket.send_json({
                        "type": "error",
                        "message": "receiver_id is required"
                    })

                    continue

                # ---------------------------------------------
                # Validate message
                # ---------------------------------------------

                if not isinstance(message_text, str):

                    await websocket.send_json({
                        "type": "error",
                        "message": "Message must be text"
                    })

                    continue

                message_text = message_text.strip()

                if not message_text:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Message cannot be empty"
                    })

                    continue

                # ---------------------------------------------
                # Check receiver exists
                # ---------------------------------------------

                receiver = db.query(User).filter(
                    User.id == receiver_id
                ).first()

                if not receiver:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Receiver not found"
                    })

                    continue

                # ---------------------------------------------
                # Prevent self messaging
                # ---------------------------------------------

                if receiver_id == user_id:

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "You cannot message yourself"
                        )
                    })

                    continue

                # ---------------------------------------------
                # Check friendship
                # ---------------------------------------------

                friendship = db.query(
                    FriendRequest
                ).filter(
                    (
                        (
                            FriendRequest.sender_id
                            == user_id
                        )
                        &
                        (
                            FriendRequest.receiver_id
                            == receiver_id
                        )
                    )
                    |
                    (
                        (
                            FriendRequest.sender_id
                            == receiver_id
                        )
                        &
                        (
                            FriendRequest.receiver_id
                            == user_id
                        )
                    ),
                    FriendRequest.status == "accepted"
                ).first()

                if not friendship:

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "You can only message "
                            "your friends"
                        )
                    })

                    continue

                print(
                    f"\n📨 Message received "
                    f"from User {user_id}"
                )

                # ---------------------------------------------
                # Save message
                # ---------------------------------------------

                new_message = Message(
                    sender_id=user_id,
                    receiver_id=receiver_id,
                    message=message_text,
                    message_type="text",
                    status="sent"
                )

                db.add(new_message)

                try:

                    db.commit()
                    db.refresh(new_message)

                except Exception as e:

                    db.rollback()

                    print(
                        f"❌ Database error: {e}"
                    )

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "Could not save message"
                        )
                    })

                    continue

                print(
                    f"💾 Saved Message ID: "
                    f"{new_message.id}"
                )

                # ---------------------------------------------
                # Message payload
                # ---------------------------------------------

                response = {
                    "type": "message",
                    "message_id": new_message.id,
                    "sender_id": user_id,
                    "receiver_id": receiver_id,
                    "message": new_message.message,
                    "message_type": "text",
                    "status": "sent",
                    "time": str(
                        new_message.created_at
                    )
                }

                # ---------------------------------------------
                # Send to receiver
                # ---------------------------------------------

                print(
                    f"➡️ Sending message "
                    f"to User {receiver_id}"
                )

                await manager.send_personal_message(
                    response,
                    receiver_id
                )

                print(
                    "✅ Receiver received message"
                )

                # ---------------------------------------------
                # Send copy to sender
                # ---------------------------------------------

                print(
                    f"➡️ Sending copy "
                    f"to User {user_id}"
                )

                await manager.send_personal_message(
                    response,
                    user_id
                )

                print(
                    "✅ Sender received copy"
                )

                # ---------------------------------------------
                # Delivered status
                # ---------------------------------------------

                print(
                    "Connected Users:",
                    list(
                        manager.active_connections.keys()
                    )
                )

                if manager.is_online(receiver_id):

                    print(
                        f"🟢 User {receiver_id} "
                        f"is online"
                    )

                    new_message.status = "delivered"

                    db.commit()

                    print(
                        "📦 Status changed "
                        "to DELIVERED"
                    )

                    await manager.send_personal_message(
                        {
                            "type": "status",
                            "message_id": new_message.id,
                            "sender_id": new_message.sender_id,
                            "status": "delivered"
                        },
                        user_id
                    )

                    print(
                        "✅ Delivered notification sent"
                    )

                else:

                    print(
                        f"🔴 User {receiver_id} "
                        f"is offline"
                    )

            # =================================================
            # 7. UNKNOWN EVENT
            # =================================================

            else:

                print(
                    f"❌ Unknown message type: "
                    f"{message_type}"
                )

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        f"Unknown message type: "
                        f"{message_type}"
                    )
                })

    # =====================================================
    # 8. DISCONNECT
    # =====================================================

    except WebSocketDisconnect:

        manager.disconnect(user_id)
        online_manager.disconnect(user_id)

        print(
            f"\n🔴 User {user_id} disconnected"
        )

        print(
            f"Online Users: "
            f"{online_manager.get_online_users()}"
        )

    except Exception as e:

        print(
            f"\n❌ WebSocket error "
            f"for User {user_id}: {e}"
        )

        manager.disconnect(user_id)
        online_manager.disconnect(user_id)

    finally:
        db.close()
