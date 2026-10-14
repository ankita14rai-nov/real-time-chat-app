import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './Chat.css';

export default function Chat() {
    const navigate = useNavigate();
    const [currentUser, setCurrentUser] = useState(null);
    const [friends, setFriends] = useState([]);
    const [activeFriend, setActiveFriend] = useState(null);
    const [messages, setMessages] = useState([]);
    const [messageInput, setMessageInput] = useState("");
    const [typingText, setTypingText] = useState("");
    
    // Modal State
    const [showModal, setShowModal] = useState(false);
    const [friendEmail, setFriendEmail] = useState("");
    const [pendingRequests, setPendingRequests] = useState([]);

    const socketRef = useRef(null);
    const messagesEndRef = useRef(null);
    const activeFriendRef = useRef(null); // NEW: Track active friend for WebSocket
    const jwtToken = localStorage.getItem("chat_token");

    // NEW: Keep ref updated so WebSocket always knows who we are chatting with
    useEffect(() => {
        activeFriendRef.current = activeFriend;
    }, [activeFriend]);

    const formatTime = (dateString) => {
        if (!dateString) return "";
        const safeDate = dateString.endsWith('Z') ? dateString : dateString + 'Z';
        const date = new Date(safeDate);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const fetchFriends = async () => {
        try {
            const res = await fetch("https://chat-app-backend-axgl.onrender.com/friends/list", {
                headers: { "Authorization": `Bearer ${jwtToken}` }
            });
            const data = await res.json();
            setFriends(data);
        } catch (err) {
            console.error("Failed to load friends", err);
        }
    };

    useEffect(() => {
        if (!jwtToken) {
            navigate('/login');
            return;
        }

        const initializeData = async () => {
            try {
                const profileRes = await fetch("https://chat-app-backend-axgl.onrender.com/profile", {
                    headers: { "Authorization": `Bearer ${jwtToken}` }
                });
                if (!profileRes.ok) throw new Error("Session expired");
                const profile = await profileRes.json();
                setCurrentUser(profile);

                fetchFriends();
                connectWebSocket(profile.id);
            } catch (err) {
                console.error(err);
                handleLogout();
            }
        };

        initializeData();

        // NEW: Silently refresh friends list every 5 seconds to catch accepted friend requests instantly
        const friendInterval = setInterval(() => {
            fetchFriends();
        }, 5000);

        return () => {
            clearInterval(friendInterval);
            if (socketRef.current) socketRef.current.close();
        };
    }, []);

    const connectWebSocket = (userId) => {
        const ws = new WebSocket(`wss://chat-app-backend-axgl.onrender.com/ws?token=${encodeURIComponent(jwtToken)}`);
        socketRef.current = ws;

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "delete") {
                setMessages(prev => prev.filter(msg => (msg.message_id || msg.id) !== data.message_id));
                return;
            }

            if (data.type === "edit") {
                setMessages(prev => prev.map(msg => 
                    (msg.message_id || msg.id) === data.message_id ? { ...msg, message: data.message } : msg
                ));
                return;
            }

            if (data.type === "typing") {
                setTypingText("User is typing...");
                setTimeout(() => setTypingText(""), 1500);
                return;
            }

            if (data.type === "message" || data.type === "file") {
                const currentActive = activeFriendRef.current;
                
                // NEW: Only show the message if it belongs to the currently open chat
                if (currentActive && (data.sender_id === currentActive.id || data.receiver_id === currentActive.id)) {
                    const newMsg = { ...data, created_at: data.created_at || new Date().toISOString() };
                    
                    setMessages(prev => {
                        // Prevent duplicates if server echoes our own message back
                        if (prev.some(m => (m.message_id || m.id) === (newMsg.message_id || newMsg.id))) return prev;
                        return [...prev, newMsg];
                    });
                    
                    if (data.sender_id !== userId) {
                        ws.send(JSON.stringify({ type: "read", message_id: data.message_id || data.id }));
                    }
                }
                
                // Fetch friends to update sidebar (like moving the person to top or showing unread badge)
                fetchFriends();
                return;
            }

            if (data.type === "status") {
                setMessages(prev => prev.map(msg => 
                    (msg.message_id || msg.id) == data.message_id ? { ...msg, status: data.status } : msg
                ));
            }
        };
    };

    const handleLogout = () => {
        localStorage.removeItem("chat_token");
        if (socketRef.current) socketRef.current.close();
        navigate('/login');
    };

    const selectFriend = async (friend) => {
        setActiveFriend(friend);
        try {
            const res = await fetch(`https://chat-app-backend-axgl.onrender.com/messages/chat/${friend.id}`, {
                headers: { "Authorization": `Bearer ${jwtToken}` }
            });
            const data = await res.json();
            setMessages(data);
            scrollToBottom();

            data.forEach(msg => {
                if (msg.sender_id === friend.id && msg.status !== 'read' && socketRef.current) {
                    socketRef.current.send(JSON.stringify({ 
                        type: "read", 
                        message_id: msg.id || msg.message_id 
                    }));
                }
            });
        } catch (err) {
            console.error("Failed to load history", err);
        }
    };

    const sendMessage = (e) => {
        e?.preventDefault();
        if (!messageInput.trim() || !activeFriend || !socketRef.current) return;

        // NEW: Instantly draw the message on my own screen (Optimistic UI)
        const tempMessage = {
            message_id: Date.now(), // Temporary ID until page refreshes next time
            sender_id: currentUser.id,
            receiver_id: activeFriend.id,
            message: messageInput,
            message_type: "text",
            created_at: new Date().toISOString(),
            status: "sent"
        };
        setMessages(prev => [...prev, tempMessage]);

        socketRef.current.send(JSON.stringify({ 
            type: "message", 
            receiver_id: activeFriend.id, 
            message: messageInput 
        }));
        setMessageInput("");
        scrollToBottom();
    };

    const handleTyping = (e) => {
        setMessageInput(e.target.value);
        if (socketRef.current && activeFriend) {
            socketRef.current.send(JSON.stringify({ type: "typing", receiver_id: activeFriend.id }));
        }
    };

    const uploadFile = async (e) => {
        const file = e.target.files[0];
        if (!file || !activeFriend) return;
        
        const formData = new FormData();
        formData.append("receiver_id", activeFriend.id);
        formData.append("file", file);
        
        try {
            await fetch("https://chat-app-backend-axgl.onrender.com/messages/upload", {
                method: "POST",
                headers: { "Authorization": `Bearer ${jwtToken}` },
                body: formData
            });
            e.target.value = ""; 
            selectFriend(activeFriend);
        } catch (err) {
            alert("Upload failed.");
        }
    };

    const deleteMessage = async (id) => {
        if (!window.confirm("Delete message?")) return;
        await fetch(`https://chat-app-backend-axgl.onrender.com/messages/delete/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${jwtToken}` }
        });
    };

    const editMessage = async (id) => {
        const newText = window.prompt("Edit message:");
        if (!newText) return;
        await fetch(`https://chat-app-backend-axgl.onrender.com/messages/edit/${id}`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${jwtToken}`, "Content-Type": "application/json" },
            body: JSON.stringify({ message: newText })
        });
    };

    const scrollToBottom = () => {
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const openModal = async () => {
        setShowModal(true);
        try {
            const res = await fetch("https://chat-app-backend-axgl.onrender.com/friends/requests", {
                headers: { "Authorization": `Bearer ${jwtToken}` }
            });
            const data = await res.json();
            setPendingRequests(data);
        } catch (err) { console.error(err); }
    };

    const sendFriendRequest = async () => {
        if (!friendEmail.trim()) return;
        try {
            const res = await fetch("https://chat-app-backend-axgl.onrender.com/friends/request", {
                method: "POST",
                headers: { "Authorization": `Bearer ${jwtToken}`, "Content-Type": "application/json" },
                body: JSON.stringify({ receiver_email: friendEmail })
            });
            if (res.ok) {
                alert("Request sent!");
                setFriendEmail("");
            } else {
                const err = await res.json();
                alert(err.detail);
            }
        } catch (err) { console.error(err); }
    };

    const respondToRequest = async (id, action) => {
        try {
            await fetch(`https://chat-app-backend-axgl.onrender.com/friends/${action}/${id}`, {
                method: action === 'accept' ? 'PUT' : 'DELETE',
                headers: { "Authorization": `Bearer ${jwtToken}` }
            });
            openModal();
            fetchFriends();
        } catch (err) { console.error(err); }
    };

    if (!currentUser) return <div className="loading">Loading...</div>;

    return (
        <div className="chat-layout">
            <div className="sidebar">
                <div className="sidebar-header">
                    <span>{currentUser.username}</span>
                    <div className="header-actions">
                        <button className="icon-btn" onClick={openModal}>➕ Add Friend</button>
                        <button className="logout-btn" onClick={handleLogout}>Logout</button>
                    </div>
                </div>
                <div className="friends-list">
                    {friends.length === 0 ? (
                        <div className="empty-state">No friends yet.</div>
                    ) : (
                        friends.map(friend => (
                            <div 
                                key={friend.id} 
                                className={`friend-item ${activeFriend?.id === friend.id ? 'active' : ''}`}
                                onClick={() => selectFriend(friend)}
                            >
                                <div className="avatar">{friend.username.charAt(0).toUpperCase()}</div>
                                <div className="friend-info">
                                    <span className="friend-name">{friend.username}</span>
                                    <span className="friend-email">{friend.email}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <div className="chat-area">
                <div className="chat-header">
                    <h3>{activeFriend ? `Chatting with ${activeFriend.username}` : "Select a friend to start chatting"}</h3>
                    <div className="typing-indicator">{activeFriend && typingText}</div>
                </div>
                
                <div className="chat-messages">
                    {messages.map((msg, index) => {
                        const isSender = String(msg.sender_id) === String(currentUser.id);
                        const msgId = msg.message_id || msg.id;
                        
                        return (
                            <div key={index} className={`message ${isSender ? 'sent' : 'received'}`}>
                                <span className="sender-name">{isSender ? 'Me' : activeFriend?.username}</span>
                                
                                {msg.message_type === "text" && <span className="text-content">{msg.message}</span>}
                                {msg.message_type === "image" && <img src={`https://chat-app-backend-axgl.onrender.com/${msg.file_path}`} alt="upload" className="msg-image" />}
                                {msg.message_type === "file" && <a href={`https://chat-app-backend-axgl.onrender.com/${msg.file_path}`} target="_blank" rel="noreferrer" className="msg-file">📄 {msg.file_name}</a>}
                                
                                <div className="message-meta" style={{ display: 'flex', alignItems: 'center', gap: '5px', justifyContent: 'flex-end', marginTop: '5px' }}>
                                    <span style={{ fontSize: '10px', color: '#999' }}>
                                        {formatTime(msg.created_at || msg.timestamp)}
                                    </span>
                                    
                                    {isSender && (
                                        <span style={{
                                            color: msg.status === 'read' ? '#34B7F1' : '#999', 
                                            fontSize: '12px', 
                                            fontWeight: 'bold',
                                            letterSpacing: msg.status === 'delivered' || msg.status === 'read' ? '-2px' : '0'
                                        }}>
                                            {msg.status === "read" ? "✓✓" : (msg.status === "delivered" ? "✓✓" : "✓")}
                                        </span>
                                    )}
                                </div>

                                {isSender && (
                                    <div className="message-actions">
                                        {msg.message_type === "text" && <button className="action-btn" onClick={() => editMessage(msgId)}>Edit</button>}
                                        <button className="action-btn delete" onClick={() => deleteMessage(msgId)}>Delete</button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>
                
                <div className="input-area">
                    <div className="file-upload-wrapper">
                        <button className="file-upload-btn" disabled={!activeFriend}>📎 Attach</button>
                        <input type="file" onChange={uploadFile} disabled={!activeFriend} />
                    </div>
                    <form onSubmit={sendMessage} style={{flex: 1, display: 'flex', gap: '10px'}}>
                        <input 
                            type="text" 
                            value={messageInput}
                            onChange={handleTyping}
                            placeholder="Type a message..." 
                            disabled={!activeFriend}
                            className="text-input"
                        />
                        <button type="submit" disabled={!activeFriend} className="send-btn">Send</button>
                    </form>
                </div>
            </div>

            {showModal && (
                <div className="modal">
                    <div className="modal-content">
                        <span className="close" onClick={() => setShowModal(false)}>&times;</span>
                        <h3>Add a New Friend</h3>
                        <div className="add-friend-form">
                            <input 
                                type="email" 
                                value={friendEmail}
                                onChange={(e) => setFriendEmail(e.target.value)}
                                placeholder="Enter friend's email" 
                            />
                            <button onClick={sendFriendRequest}>Send Request</button>
                        </div>
                        <h3>Pending Friend Requests</h3>
                        <div className="request-list">
                            {pendingRequests.length === 0 ? (
                                <div className="empty-state">No pending requests.</div>
                            ) : (
                                pendingRequests.map(req => (
                                    <div key={req.request_id} className="request-item">
                                        <div className="request-info">
                                            <strong>{req.sender_username}</strong>
                                            <span>{req.sender_email}</span>
                                        </div>
                                        <div className="request-actions">
                                            <button className="btn-accept" onClick={() => respondToRequest(req.request_id, 'accept')}>Accept</button>
                                            <button className="btn-reject" onClick={() => respondToRequest(req.request_id, 'reject')}>Reject</button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}