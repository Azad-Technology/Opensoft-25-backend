from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel
from src.chatbot.chat_bot import (
    chat_complete,
    get_chat_history
)
from utils.auth import get_current_user
from utils.config import get_async_database
from utils.app_logger import setup_logger

router = APIRouter()
logger = setup_logger("src/routers/chat.py")
async_db = get_async_database()

class ChatMessage(BaseModel):
    message: str = None

class ChatSession(BaseModel):
    session_id: str
    start_time: datetime
    status: str
    last_message: Optional[str]

@router.post("/message")
async def start_chat(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user),
    session_id: str = None
):
    try:
        if session_id and not message.message:
            raise HTTPException(
                status_code=400,
                detail="Message is required for existing session"
            )
        
        if not session_id:
            # Generate a new session ID
            session_id = str(datetime.now().timestamp())
            message.message = None
        
        # Process the message
        response = await chat_complete(
            employee_id=current_user["employee_id"],
            session_id=session_id,
            message=message.message
        )

        return {
            "session_id": session_id,
            **response
        }

    except Exception as e:
        logger.error(f"Error in start_chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing chat message"
        )

@router.get("/history/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat history for a specific session
    """
    try:
        # Verify session belongs to user
        session = await async_db.chat_history.find_one({
            "session_id": session_id,
            "employee_id": current_user["employee_id"]
        })
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
            
        chat_history = await get_chat_history(session_id)

        return {
            "session_id": session_id,
            "history": chat_history
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving chat history"
        )

@router.get("/sessions")
async def list_chat_sessions(
    current_user: dict = Depends(get_current_user)
):
    """
    Get latest messages for each chat session of the user
    """
    try:
        # Get latest message for each session using MongoDB aggregation
        latest_messages = await async_db.chat_history.aggregate([
            {
                "$match": {
                    "employee_id": current_user["employee_id"]
                }
            },
            {
                "$sort": {"timestamp": -1}  # Sort by timestamp descending
            },
            {
                "$group": {
                    "_id": "$session_id",
                    "last_message": {"$first": "$message"},
                    "timestamp": {"$first": "$timestamp"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "session_id": "$_id",
                    "last_message": 1,
                    "timestamp": 1
                }
            }
        ]).to_list(length=None)

        return {"sessions": latest_messages}

    except Exception as e:
        logger.error(f"Error listing chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving chat sessions"
        )