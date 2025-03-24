from passlib.context import CryptContext
from datetime import UTC, datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from utils.config import get_async_database
from utils.app_logger import setup_logger
from utils.config import settings

logger = setup_logger("src/auth/utils.py")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.ENC_SECRET_KEY
ALGORITHM = "HS256"

security = HTTPBearer()
async_db = get_async_database()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """
    Create a new access token
    """
    try:
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(UTC)  # issued at
        })
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error creating access token"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify token and return current user
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication credentials"
            )
        
        # Get user from database
        user = await async_db.users.find_one({"email": email})
        if user is None:
            raise HTTPException(
                status_code=401, 
                detail="User not found"
            )
            
        # Convert ObjectId to string for JSON serialization
        user["_id"] = str(user["_id"])
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while authenticating"
        )