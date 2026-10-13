from fastapi import APIRouter

from online_manager import online_manager

router = APIRouter(
    prefix="/online",
    tags=["Online Status"]
)


@router.get("/users")
def get_online_users():

    return {
        "online_users": online_manager.get_online_users()
    }