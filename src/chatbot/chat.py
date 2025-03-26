import json
import random
from utils.config import get_async_database
from src.chatbot.llm_models import get_model
from typing import Dict, List
from datetime import datetime, timezone
from utils.app_logger import setup_logger
from src.analysis.data_sample import create_employee_profile
from src.chatbot.system_prompts import (
    INTENT_ANALYSIS_SYSTEM_PROMPT,
    INTENT_EXTRACTION_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RESPONSE_ANALYSIS_SYSTEM_PROMPT,
    RESPONSE_ANALYSIS_PROMPT
)

logger = setup_logger("src/chatbot/chat.py")
async_db = get_async_database()
groq_model = get_model()
google_model = get_model(model_provider="GROQ")
Model = "llama-3.3-70b-versatile"
chat_model = google_model

async def get_chat_history(session_id: str) -> List:
    """
    Retrieve chat history from MongoDB for a specific session
    """
    try:
        if not session_id:
            logger.error("Session ID is required to retrieve chat history.")
            return []
        
        chat_history = await async_db.chat_history.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(length=None)
        
        if not chat_history or len(chat_history) == 0:
            return None
        
        for chat in chat_history:
            chat.pop("timestamp", None)  # Remove timestamp for cleaner output
            if chat["role"] == "assistant":
                chat["message"] = f'Question - {chat["message"]["question"]}, Intent - {chat["message"]["intent"]}' if chat["message"] else "No message"                
                
        # Append a user message at top
        chat_history.insert(0, {
            "role": "user",
            "message": "Hi"
        })
                
        return chat_history
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return []

async def save_to_chat_history(employee_id: str, session_id: str, role: str, message: str) -> bool:
    """
    Save a message to chat history in MongoDB
    """
    try:
        collection = async_db.chat_history
        await collection.insert_one({
            "session_id": session_id,
            "employee_id": employee_id,
            "role": role,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Error saving to chat history: {str(e)}")
        return False

async def save_intent_data(employee_id: str, session_id: str, intent_data: Dict) -> bool:
    """
    Save intent data to MongoDB
    """
    try:
        collection = async_db.intent_data
        await collection.update_one(
            {"session_id": session_id, "employee_id": employee_id},
            {"$set": {
                "intent_data": intent_data,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error saving intent data: {str(e)}")
        return False

async def get_intent_data(session_id: str) -> Dict:
    """
    Retrieve intent data from MongoDB
    """
    try:
        if not session_id:
            logger.error("Session ID is required to retrieve intent data.")
            return {}
        
        collection = async_db.intent_data
        # Modified query to only fetch intent_data
        intent_data = await collection.find_one(
            {"session_id": session_id},
            {"intent_data": 1, "_id": 0,}  # Only include intent_data, exclude _id
        )
        
        if not intent_data:
            logger.warning(f"No intent data found for session {session_id}")
            return {}
        
            
        return intent_data.get("intent_data", {})
        
    except Exception as e:
        logger.error(f"Error retrieving intent data: {str(e)}")
        return {}
    
async def save_conversation_status(session_id: str, status: str) -> bool:
    """
    Save conversation status to MongoDB
    """
    try:
        collection = async_db.conversation_status
        await collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error saving conversation status: {str(e)}")
        return False

async def get_conversation_status(session_id: str) -> str:
    """
    Retrieve conversation status from MongoDB
    """
    try:
        collection = async_db.conversation_status
        status_doc = await collection.find_one(
            {"session_id": session_id},
            {"_id": 0, "status": 1}
        )
        return status_doc.get("status", "new") if status_doc else "new"
    except Exception as e:
        logger.error(f"Error retrieving conversation status: {str(e)}")
        return "new"

async def extract_intent_from_employee(employee_profile):
    try:        
        response = chat_model.chat.completions.create(
            model=Model,
            messages=[
                {"role": "system", "content": INTENT_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": INTENT_EXTRACTION_PROMPT.format(profile=employee_profile)}
            ],
            temperature=0.7,
            response_format={ "type": "json_object" }  # Add this to ensure JSON response
        )
        raw_response = response.choices[0].message.content
        # Attempt to parse JSON
        intent_data = json.loads(raw_response)
        
        logger.info(f"Intent data extracted: {intent_data}")
        return intent_data

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in intent extraction: {str(e)} - Raw response: {raw_response}")
        return None
    except Exception as e:
        logger.error(f"Error in intent extraction: {str(e)}")
        return None

async def generate_next_question(
    intent_data: Dict,
    chat_history: List,
    required_info: List
) -> str:
    """
    Generate the next question based on context and missing information
    """
    try:
        # Start with system message
        messages = [{
            "role": "system",
            "content": QUESTION_GENERATION_SYSTEM_PROMPT
        }]
        
        # Add chat history
        for chat in chat_history:
            messages.append({
                "role": chat["role"],
                "content": chat["message"]
            })
            
        # Add current context and requirements
        messages.append({
            "role": "user",
            "content": QUESTION_GENERATION_PROMPT.format(
                context=json.dumps(intent_data, indent=2),
                required_info=json.dumps(required_info, indent=2),
                chat_history=json.dumps(chat_history, indent=2)
            )
        })
        
        response = chat_model.chat.completions.create(
            model=Model,
            messages=messages,
            temperature=0.65,
            response_format={ "type": "json_object" }  # Add this to ensure JSON response
        )
        
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.error(f"Error in question generation: {str(e)}")
        return None

async def analyze_response(
    response: str,
    intent_data: Dict,
    chat_history: List
) -> Dict:
    """
    Analyze employee response to determine if needed information was provided
    """
    try:
        # Start with system message
        messages = [{
            "role": "system",
            "content": RESPONSE_ANALYSIS_SYSTEM_PROMPT
        }]
        
        # Add chat history
        for chat in chat_history:
            messages.append({
                "role": chat["role"],
                "content": chat["message"]
            })
            
        # Add current response and context
        messages.append({
            "role": "user",
            "content": RESPONSE_ANALYSIS_PROMPT.format(
                response=response,
                intent_data=json.dumps(intent_data, indent=2)
            )
        })
        
        print(messages)

        response = chat_model.chat.completions.create(
            model=Model,
            messages=messages,
            temperature=0.65,
            response_format={ "type": "json_object" }  # Add this to ensure JSON response
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.error(f"Error in response analysis: {str(e)}")
        return None

# Update chat_complete function to pass chat_history
async def chat_complete(employee_id: str, session_id: str = None, message: str = None) -> Dict:
    """
    Main chat function handling the conversation flow
    """
    try:
        # Get chat history
        chat_history = await get_chat_history(session_id)
        print(f"Chat history for session {session_id}: {chat_history}")
        # If new conversation
        if not chat_history:
            employee_profile = await create_employee_profile(employee_id)
            intent_data = await extract_intent_from_employee(employee_profile)
            await save_intent_data(employee_id, session_id, intent_data)
            
            question = await generate_next_question(
                intent_data,
                [],  # Empty chat history for first question
                intent_data["required_information"]
            )
            
            await save_to_chat_history(employee_id, session_id, "assistant", question)
            return {"response": question, "conversation_status": "ongoing"}

        # Analyze employee response with chat history
        analysis = await analyze_response(
            await get_intent_data(session_id),
            chat_history
        )

        if len(chat_history) >= 10 or analysis["conversation_complete"]:
            await save_conversation_status(session_id, "complete")
            return {
                "response": "Thank you for sharing. I'll make sure to get this information to the right team.", 
                "conversation_status": "complete"
            }
            
        chat_history.append({
            "role": "user",
            "message": message
        })

        # Generate next question with updated chat history
        next_question = await generate_next_question(
            await get_intent_data(session_id),
            chat_history,
            analysis["missing_information"]
        )

        # Save to chat history
        await save_to_chat_history(employee_id, session_id, "user", message)
        await save_to_chat_history(employee_id, session_id, "assistant", next_question)

        return {"response": next_question, "conversation_status": "ongoing"}

    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        return {"error": "An error occurred during the conversation"}
    
    
if __name__ == "__main__":
    import asyncio
    # asyncio.run(get_chat_history("1742832471.228664"))
    # # Example usage
    session_id = "1742832471.228664"
    message = "I am feeling overwhelmed with my workload."
    employee_id = 'EMP0454'
    
    response = asyncio.run(chat_complete(employee_id, session_id, message))
    print(response)