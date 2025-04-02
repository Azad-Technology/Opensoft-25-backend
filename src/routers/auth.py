from fastapi import APIRouter, HTTPException, Depends
from src.models.auth import UserLogin
from utils.auth import (
    verify_password, 
    create_access_token, 
    get_current_user
)
from utils.config import get_async_database
from utils.app_logger import setup_logger
from utils.config import settings

router = APIRouter()
logger = setup_logger("src/routers/auth.py")
async_db = get_async_database()

@router.post("/login")
async def login(user: UserLogin):
    try:
        # Find user
        db_user = await async_db.users.find_one({"email": user.email})
        if not db_user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email"
            )

        # Verify password
        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect password"
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user.email}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": db_user["email"],
                "name": db_user["name"],
                "role": db_user["role"],
                "role_type": db_user["role_type"],
                "employee_id": db_user.get("employee_id", None)
            }
        }

    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in login: {str(e)}"
        )

@router.get("/token")
async def get_access_token(current_user: dict = Depends(get_current_user)):
    """
    Generate new access token for authenticated user
    """
    try:
        # Ensure we have the email
        if not current_user.get("email"):
            raise HTTPException(
                status_code=400,
                detail="User email not found"
            )

        # Create new access token
        access_token = create_access_token(
            data={
                "sub": current_user["email"],
                "role": current_user.get("role", "employee"),
                "name": current_user.get("name", "")
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error in get_access_token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in get_access_token: {str(e)}"
        )