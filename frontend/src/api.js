const API_URL = "http://127.0.0.1:8000";

export async function getUsers() {
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${API_URL}/users`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error("Failed to load users");
    }

    return await response.json();
}