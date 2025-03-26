import json
import random
from src.database.graph_db import extract_questions
from utils.config import get_async_database
from src.chatbot.llm_models import get_model
from typing import Dict, List
from datetime import datetime, timezone
from utils.app_logger import setup_logger
from src.analysis.data_sample import create_employee_profile
from src.chatbot.system_prompts import (
    INTENT_ANALYSIS_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RESPONSE_ANALYSIS_SYSTEM_PROMPT,
    RESPONSE_ANALYSIS_PROMPT
)

logger = setup_logger("src/chatbot/chat.py")
async_db = get_async_database()
MODEL_PROVIDER = "GEMINI"
MODEL_NAME = "gemini-2.0-flash"

async def get_chat_history(session_id: str) -> List:
    logger.info(f"[Session: {session_id}] Fetching chat history")
    try:
        if not session_id:
            logger.error("[Session: None] Session ID is required to retrieve chat history")
            return []
        
        chat_history = await async_db.chat_history.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(length=None)
        
        logger.info(f"[Session: {session_id}] Found {len(chat_history) if chat_history else 0} messages in chat history")
        if not chat_history or len(chat_history) == 0:
            return []
              
        return chat_history
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error retrieving chat history: {str(e)}")
        return []

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

async def save_intent_data(employee_id: str, session_id: str, intent_data: Dict) -> bool:
    logger.info(f"[Session: {session_id}] Saving intent data for employee: {employee_id}")
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
        logger.info(f"[Session: {session_id}] Successfully saved intent data")
        return True
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error saving intent data: {str(e)}")
        return False

async def get_intent_data(session_id: str) -> Dict:
    logger.info(f"[Session: {session_id}] Retrieving intent data")
    try:
        if not session_id:
            logger.error("[Session: None] Session ID is required to retrieve intent data")
            return {}
        
        collection = async_db.intent_data
        intent_data = await collection.find_one(
            {"session_id": session_id},
            {"intent_data": 1, "_id": 0}
        )
        
        if not intent_data:
            logger.warning(f"[Session: {session_id}] No intent data found")
            return {}
        
        logger.info(f"[Session: {session_id}] Successfully retrieved intent data")
        return intent_data.get("intent_data", {})
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error retrieving intent data: {str(e)}")
        return {}
    
async def save_conversation_status(session_id: str, status: str) -> bool:
    logger.info(f"[Session: {session_id}] Saving conversation status: {status}")
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
        logger.info(f"[Session: {session_id}] Successfully saved conversation status")
        return True
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error saving conversation status: {str(e)}")
        return False

async def get_conversation_status(session_id: str) -> str:
    logger.info(f"[Session: {session_id}] Retrieving conversation status")
    try:
        collection = async_db.conversation_status
        status_doc = await collection.find_one(
            {"session_id": session_id},
            {"_id": 0, "status": 1}
        )
        status = status_doc.get("status", "new") if status_doc else "new"
        logger.info(f"[Session: {session_id}] Current conversation status: {status}")
        return status
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error retrieving conversation status: {str(e)}")
        return "new"

async def extract_intent_from_employee(employee_profile, session_id: str):
    logger.info(f"[Session: {session_id}] Starting intent extraction from employee profile")
    try:        
        chat_model = get_model(model_provider=MODEL_PROVIDER)
        response = chat_model.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": INTENT_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze the following employee profile comprehensively and provide the output in the JSON format specified above: Employee Profile: {employee_profile}"}
            ],
            temperature=0.7,
            response_format={ "type": "json_object" }
        )
        intent_data = json.loads(response.choices[0].message.content)
        logger.info(f"[Session: {session_id}] Successfully extracted intent data: {json.dumps(intent_data, indent=2)}")
        return intent_data
    
    except json.JSONDecodeError as e:
        logger.error(f"[Session: {session_id}] JSON parsing error in intent extraction: {str(e)} - Raw response: {response.choices[0].message.content}")
        return None
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in intent extraction: {str(e)}")
        return None
    
async def get_questions_from_tags(tags, tag_number=0, max_questions=10, session_id: str = None):
    logger.info(f"[Session: {session_id}] Getting questions for tag number {tag_number}")
    try:
        if not tags or tag_number < 0 or tag_number >= len(tags):
            logger.warning(f"[Session: {session_id}] Invalid tags or tag_number")
            return []
        
        selected_tag = tags[tag_number]["tag"]
        logger.info(f"[Session: {session_id}] Selected tag: {selected_tag}")
        
        questions = await extract_questions(selected_tag)
        logger.info(f"[Session: {session_id}] Retrieved {len(questions) if questions else 0} questions for tag")
        
        if not questions:
            logger.warning(f"[Session: {session_id}] No questions found for tag")
            return []
        
        return questions[:max_questions]
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in question extraction: {str(e)}")
        return []

async def generate_next_question(intent_data: Dict, chat_history: List, move_to_next_tag: int = 0, session_id: str = None) -> str:
    logger.info(f"[Session: {session_id}] Generating next question for tag index: {move_to_next_tag}")
    try:
        reference_question = await get_questions_from_tags(
            intent_data["tags"], 
            move_to_next_tag,
            session_id=session_id
        )
    
        messages = [{
            "role": "system",
            "content": QUESTION_GENERATION_SYSTEM_PROMPT
        }]
        
        question_number = 1
        
        if chat_history and len(chat_history) > 0:
            logger.info(f"[Session: {session_id}] Processing chat history with {len(chat_history)} messages")
            chat_history.insert(0, {"role": "user", "message": "Hii"})
            for chat in chat_history:
                messages.append({
                    "role": chat["role"],
                    "content": chat["message"]
                })
                
                if chat["role"] == "assistant":
                    question_number += 1

        prompt = QUESTION_GENERATION_PROMPT.format(
            intent_data=json.dumps(intent_data, indent=2),
            question_number=question_number,
            reference_question=reference_question,
            tag_name=intent_data["tags"][move_to_next_tag]["tag"]
        )
                
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        logger.info(f"[Session: {session_id}] Calling LLM for question generation")
        chat_model = get_model(model_provider=MODEL_PROVIDER)
        response = chat_model.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.65,
            response_format={ "type": "text" }
        )
        
        generated_question = response.choices[0].message.content
        logger.info(f"[Session: {session_id}] Generated question: {generated_question}")
        return generated_question

    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in question generation: {str(e)}")
        return None

async def analyze_response(intent_data: Dict, chat_history: List, current_tag: str, session_id: str) -> Dict:
    logger.info(f"[Session: {session_id}] Starting response analysis for tag: {current_tag}")
    try:
        messages = [{
            "role": "system",
            "content": RESPONSE_ANALYSIS_SYSTEM_PROMPT
        }]
        
        if chat_history and len(chat_history) > 0:
            logger.info(f"[Session: {session_id}] Processing chat history for analysis")
            chat_history.insert(0, {"role": "user", "message": "Hii"})
            for chat in chat_history:
                messages.append({
                    "role": chat["role"],
                    "content": chat["message"]
                })
            
        messages.append({
            "role": "user",
            "content": RESPONSE_ANALYSIS_PROMPT.format(
                intent_data=json.dumps(intent_data, indent=2),
                current_tag=current_tag
            )
        })

        logger.info(f"[Session: {session_id}] Calling LLM for response analysis")
        chat_model = get_model(model_provider=MODEL_PROVIDER)
        response = chat_model.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.65,
            response_format={ "type": "json_object" }
        )

        analysis_result = json.loads(response.choices[0].message.content)
        logger.info(f"[Session: {session_id}] Analysis result: {json.dumps(analysis_result, indent=2)}")
        return analysis_result

    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in response analysis: {str(e)}")
        return None

async def chat_complete(employee_id: str, session_id: str = None, message: str = None) -> Dict:
    logger.info(f"[Session: {session_id}] Starting chat completion for employee: {employee_id}")
    try:
        chat_history = await get_chat_history(session_id)
        
        # New conversation
        if not chat_history or len(chat_history) == 0:
            logger.info(f"[Session: {session_id}] Starting new conversation")
            employee_profile = await create_employee_profile(employee_id)
            
            intent_data = await extract_intent_from_employee(employee_profile, session_id)
            if not intent_data:
                logger.error(f"[Session: {session_id}] Failed to extract intent data")
                return {"error": "Failed to analyze employee profile", "conversation_status": "error"}
            
            await save_intent_data(employee_id, session_id, intent_data)
            
            question = await generate_next_question(
                intent_data,
                chat_history, 
                move_to_next_tag=0,
                session_id=session_id
            )
            
            if not question:
                logger.error(f"[Session: {session_id}] Failed to generate initial question")
                return {"error": "Failed to generate question", "conversation_status": "error"}
            
            await save_to_chat_history(employee_id, session_id, "assistant", question)
            return {"response": question, "conversation_status": "ongoing", "intent_data": intent_data}
        
        # Existing conversation
        intent_data = await get_intent_data(session_id)
        if not intent_data:
            logger.error(f"[Session: {session_id}] Failed to retrieve intent data")
            return {"error": "Failed to retrieve conversation context", "conversation_status": "error"}
        
        # Check conversation limits before processing message
        total_questions = sum(1 for chat in chat_history if chat["role"] == "assistant")
        
        # Find current tag
        current_tag = None
        number = 0
        for index, tag in enumerate(intent_data["tags"]):
            if not tag.get("completed", False):
                current_tag = tag["tag"]
                number = index
                break
        
        # Check if conversation should end
        if (total_questions >= 10 or 
            not current_tag or 
            number >= len(intent_data["tags"])):
            logger.info(f"[Session: {session_id}] Conversation complete - Limits reached")
            await save_conversation_status(session_id, "complete")
            return {
                "response": "Thank you for sharing. I'll make sure to get this information to the right team.",
                "conversation_status": "complete",
                "intent_data": intent_data
            }
        
        # Save user message if conversation is continuing
        if message is not None:
            await save_to_chat_history(employee_id, session_id, "user", message)
            # Update chat_history after saving new message
            chat_history = await get_chat_history(session_id)

        # Analyze response
        analysis = await analyze_response(intent_data, chat_history, current_tag, session_id)
        if not analysis:
            logger.error(f"[Session: {session_id}] Failed to analyze response")
            return {"error": "Failed to analyze response", "conversation_status": "error"}
        
        logger.info(f"[Session: {session_id}] Updating tag summary for {current_tag} and number {number}")
        intent_data["tags"][number]["summary"] = analysis["tag_summary"]
        
        # Update tag status
        if analysis["tag_covered"]:
            logger.info(f"[Session: {session_id}] Tag {current_tag} covered completely")
            intent_data["tags"][number]["completed"] = True
            number += 1
        
        # Check if conversation should end after analysis
        if (analysis["conversation_complete"] or 
            number >= len(intent_data["tags"])):
            logger.info(f"[Session: {session_id}] Conversation complete - Analysis based")
            await save_conversation_status(session_id, "complete")
            await save_intent_data(employee_id, session_id, intent_data)
            return {
                "response": "Thank you for sharing. I'll make sure to get this information to the right team.",
                "conversation_status": "complete",
                "intent_data": intent_data
            }

        # Generate next question
        next_question = await generate_next_question(
            intent_data,
            chat_history,
            move_to_next_tag=number,
            session_id=session_id
        )

        if not next_question:
            logger.error(f"[Session: {session_id}] Failed to generate next question")
            return {"error": "Failed to generate question", "conversation_status": "error"}

        # Save question and updated intent data
        await save_to_chat_history(employee_id, session_id, "assistant", next_question)
        await save_intent_data(employee_id, session_id, intent_data)

        logger.info(f"[Session: {session_id}] Successfully completed chat iteration")
        return {
            "response": next_question, 
            "conversation_status": "ongoing", 
            "intent_data": intent_data
        }

    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in chat completion: {str(e)}", exc_info=True)
        return {"error": "An error occurred during the conversation", "conversation_status": "error"}
    
    
if __name__ == "__main__":
    import asyncio
    # asyncio.run(get_chat_history("1742832471.228664"))
    # # Example usage
    session_id = "1742832471.228665"
    # That definitely sounds like a lot to handle, and it's understandable that you're feeling overwhelmed when you have to cover for absent team members on top of your own tasks. To get a better understanding, how often does this situation of your team being absent occur?\n
    message = "recently, it occuring too much "
    employee_id = 'EMP0454'
    
    response = asyncio.run(chat_complete(employee_id, session_id, message))
    print(response)