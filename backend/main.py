from fastapi import FastAPI
from sqlalchemy import text

from database import engine, Base

from routes.users import router as user_router
from routes.friends import router as friend_router
from routes import messages
app = FastAPI()
from routes import websocket
from routes import online
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

# Create all database tables
Base.metadata.create_all(bind=engine)

app.include_router(user_router)
app.include_router(friend_router)
app.include_router(messages.router)
app.include_router(websocket.router)
app.include_router(online.router)

@app.get("/")
def home():
    return {"message": "Chat App Backend Running"}


@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "Database Connected Successfully"}
    except Exception as e:
        return {"error": str(e)}