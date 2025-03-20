from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_users():
    return [{"username": "Rick"}, {"username": "Morty"}]

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"username": f"User {user_id}"}

@router.post("/")
async def create_user(user: dict):
    return {"message": "User created successfully", "user": user}
