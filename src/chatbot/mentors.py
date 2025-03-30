from utils.config import get_async_database
from src.chatbot.mentors_system_prompt import productivity_and_balance_coach, career_navigator, collaboration_and_conflict_guide, performance_and_skills_enhancer, communication_catalyst, resilience_and_well_being_advocate, innovation_and_solutions_spark, workplace_engagement_ally, change_adaptation_advisor, leadership_foundations_guide
from src.chatbot.llm_models import get_model
from datetime import datetime, timezone
from utils.app_logger import setup_logger
from typing import Dict, List

logger = setup_logger("src/chatbot/mentors.py")
async_db = get_async_database()
MODEL_PROVIDER = "GROQ"
MODEL_NAME = "llama-3.3-70b-versatile"

async def save_to_chat_history(employee_id: str, session_id: str, role: str, message: str) -> bool:
    logger.info(f"[Session: {session_id}] Saving message to chat history - Role: {role}")
    try:
        collection = async_db.chat_history
        document = {
            "session_id": session_id,
            "employee_id": employee_id,
            "role": role,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        }
        await collection.insert_one(document)
        logger.info(f"[Session: {session_id}] Successfully saved message to chat history")
        return True
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error saving to chat history: {str(e)}")
        return False

async def mentor_chat_completion(employee_id: str, intent_data: Dict, chat_history: List, session_id: str, message: str = None) -> str:
    """
    Handle chat completion for mentor conversations
    """
    logger.info(f"[Session: {session_id}] Starting mentor chat completion")
    try:
        mentor_name = intent_data.get("chat_analysis", {}).get("recommended_mentor")
        if not mentor_name:
            logger.error(f"[Session: {session_id}] No mentor assigned")
            return "I apologize, but I don't see a mentor assigned to this conversation. Please start a new conversation."

        # Get appropriate system prompt based on mentor name
        system_prompts = {
            "productivity_and_balance_coach": productivity_and_balance_coach,
            "career_navigator": career_navigator,
            "collaboration_and_conflict_guide": collaboration_and_conflict_guide,
            "performance_and_skills_enhancer": performance_and_skills_enhancer,
            "communication_catalyst": communication_catalyst,
            "resilience_and_well_being_advocate": resilience_and_well_being_advocate,
            "innovation_and_solutions_spark": innovation_and_solutions_spark,
            "workplace_engagement_ally": workplace_engagement_ally,
            "change_adaptation_advisor": change_adaptation_advisor,
            "leadership_foundations_guide": leadership_foundations_guide
        }
        
        system_prompt = system_prompts.get(mentor_name)
        if not system_prompt:
            logger.error(f"[Session: {session_id}] Invalid mentor name: {mentor_name}")
            return "I apologize, but there seems to be an error with the mentor assignment. Please start a new conversation."

        # Prepare conversation context
        messages = [{
            "role": "system",
            "content": system_prompt
        }]
        
        for chat in chat_history:
            messages.append({
                "role": chat["role"],
                "content": chat["message"]
            })

        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })

        # Get response from LLM
        chat_model = get_model(model_provider=MODEL_PROVIDER)
        response = chat_model.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            response_format={ "type": "text" }
        )

        mentor_response = response.choices[0].message.content

        # Save interaction to chat history
        await save_to_chat_history(employee_id, session_id, "user", message)
        await save_to_chat_history(employee_id, session_id, "assistant", mentor_response)

        logger.info(f"[Session: {session_id}] Successfully completed mentor chat iteration")
        return mentor_response

    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in mentor chat completion: {str(e)}", exc_info=True)
        return "I apologize, but I encountered an error. Please try again or start a new conversation."