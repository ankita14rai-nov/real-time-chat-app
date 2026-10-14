import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css'; // We will add styling next

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');

        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        try {
            const response = await fetch("https://chat-app-backend-axgl.onrender.com/login", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData
            });

            if (!response.ok) throw new Error("Login failed");

            const data = await response.json();
            localStorage.setItem("chat_token", data.access_token);
            navigate('/chat'); // Redirect to chat page

        } catch (err) {
            setError("Login failed. Check your email and password.");
        }
    };

    return (
        <div className="login-wrapper">
            <div className="login-container">
                <h2>Welcome to Chat</h2>
                <form onSubmit={handleLogin}>
                    <div className="input-group">
                        <label>Email</label>
                        <input 
                            type="email" 
                            required 
                            value={email} 
                            onChange={(e) => setEmail(e.target.value)} 
                            placeholder="Enter your email" 
                        />
                    </div>
                    <div className="input-group">
                        <label>Password</label>
                        <input 
                            type="password" 
                            required 
                            value={password} 
                            onChange={(e) => setPassword(e.target.value)} 
                            placeholder="Enter your password" 
                        />
                    </div>
                    <button type="submit">Login</button>
                    {error && <div className="error-msg">{error}</div>}
                </form>
            </div>
        </div>
    );
}