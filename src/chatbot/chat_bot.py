import json

import pytz
from src.analysis.data_analyze_pipeline import get_employee_profile_json
from src.chatbot.mentors import mentor_chat_completion
from src.runner import graph_db
from utils.config import get_async_database
from src.chatbot.llm_models import get_model
from typing import Dict, List
from datetime import datetime, timezone
from utils.app_logger import setup_logger
from src.chatbot.system_prompts import (
    FINAL_CHAT_ANALYSIS_PROMPT,
    FINAL_CHAT_ANALYSIS_SYSTEM_PROMPT,
    INTENT_ANALYSIS_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RESPONSE_ANALYSIS_SYSTEM_PROMPT,
    RESPONSE_ANALYSIS_PROMPT
)

logger = setup_logger("src/chatbot/chat_bot.py")
async_db = get_async_database()
MODEL_PROVIDER = "GEMINI"
MODEL_NAME = "gemini-2.0-flash"

async def extract_questions(tag: str):
    try:
        questions = graph_db.get_questions_by_tag(tag)
        logger.info(f"Extracted {len(questions)} questions for tag: {tag}")
        extracted_questions = []
        for question in questions:
            extracted_questions.append(question.get("q.question"))
        
        return extracted_questions
    except Exception as e:
        logger.error(f"Error extracting questions for tag {tag}: {str(e)}")
        return []

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
        document = {
            "session_id": session_id,
            "employee_id": employee_id,
            "role": role,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        }
        await async_db.chat_history.insert_one(document)
        logger.info(f"[Session: {session_id}] Successfully saved message to chat history")
        return True
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error saving to chat history: {str(e)}")
        return False

async def save_intent_data(employee_id: str, session_id: str, intent_data: Dict) -> bool:
    logger.info(f"[Session: {session_id}] Saving intent data for employee: {employee_id}")
    try:
        current_utc = datetime.now(timezone.utc)
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = current_utc.astimezone(ist_tz)
        current_ist_date = current_ist.date().isoformat()
        
        await async_db.intent_data.update_one(
            {"session_id": session_id, "employee_id": employee_id},
            {"$set": {
                "intent_data": intent_data,
                "updated_at": datetime.now(timezone.utc),
                "ist_date": current_ist_date,
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
        
        intent_data = await async_db.intent_data.find_one(
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

async def analyze_response(intent_data: Dict, chat_history: List, current_tag: str, total_question: int, session_id: str) -> Dict:
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
                current_tag=current_tag,
                total_question_number=total_question
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
    
async def final_chat_analysis(session_id: str, chat_history, intent_data) -> Dict:
    """
    Analyze the complete chat history and provide final analysis with mentor recommendation
    """
    logger.info(f"[Session: {session_id}] Starting final chat analysis")
    try:
        
        if not chat_history or not intent_data:
            logger.error(f"[Session: {session_id}] Missing chat history or intent data for final analysis")
            return None
            
        # Format conversation for analysis
        formatted_conversation = {
            "conversation_flow": [
                {
                    "role": chat["role"],
                    "message": chat["message"]
                } for chat in chat_history
            ]
        }
        
        # Prepare messages for LLM
        messages = [
            {
                "role": "system",
                "content": FINAL_CHAT_ANALYSIS_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": FINAL_CHAT_ANALYSIS_PROMPT.format(intent_data=json.dumps(intent_data, indent=2), conversation_history=json.dumps(formatted_conversation, indent=2))
            }
        ]
        
        logger.info(f"[Session: {session_id}] Calling LLM for final analysis")
        chat_model = get_model(model_provider=MODEL_PROVIDER)
        response = chat_model.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            response_format={ "type": "json_object" }
        )
        
        try:
            analysis_result = json.loads(response.choices[0].message.content)
                
            # Validate mentor name
            valid_mentors = [
                "productivity_and_balance_coach",
                "career_navigator",
                "collaboration_and_conflict_guide",
                "performance_and_skills_enhancer",
                "communication_catalyst",
                "resilience_and_well_being_advocate",
                "innovation_and_solutions_spark",
                "workplace_engagement_ally",
                "change_adaptation_advisor",
                "leadership_foundations_guide",
                "ForwardingRequestToHR"
            ]
            
            if analysis_result.get("recommended_mentor") not in valid_mentors:
                raise ValueError(f"Invalid mentor name: {analysis_result['recommended_mentor']}")
            
            logger.info(f"[Session: {session_id}] Final analysis completed successfully")
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"[Session: {session_id}] JSON parsing error in final analysis: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in final analysis: {str(e)}", exc_info=True)
        return None

async def chat_complete(employee_id: str, session_id: str = None, message: str = None) -> Dict:
    logger.info(f"[Session: {session_id}] Starting chat completion for employee: {employee_id}")
    try:
        chat_history = await get_chat_history(session_id)
        
        # New conversation
        if not chat_history or len(chat_history) == 0:
            logger.info(f"[Session: {session_id}] Starting new conversation")
            employee_profile = await get_employee_profile_json(employee_id)
            
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
        
        if intent_data.get("chat_completed", False):
            logger.info(f"[Session: {session_id}] Mentor already assigned for this conversation")
            return {
                "response": await mentor_chat_completion(employee_id, intent_data, chat_history, session_id, message),
                "intent_data": intent_data
            }
        
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
            final_analysis = await final_chat_analysis(session_id, chat_history, intent_data)
            intent_data["chat_completed"] = True
            intent_data["chat_analysis"] = final_analysis
            intent_data["chat_analysis"]["updated_at"] = datetime.now(timezone.utc)
            
            await save_intent_data(employee_id, session_id, intent_data)
            if final_analysis['recommended_mentor'] == 'ForwardingRequestToHR':
                response = "Your issue has been forwarded to HR Management. Please wait for their response."
            else:
                response = f"Thank you for sharing your concerns. Based on our conversation, I recommend you speak with {final_analysis['recommended_mentor']}. You can continue the conversation with them directly in this chat."
            return {
                "response": response,
                "intent_data": intent_data
            }
        
        # Save user message if conversation is ongoing
        if message is not None:
            await save_to_chat_history(employee_id, session_id, "user", message)
            # Update chat_history after saving new message
            chat_history = await get_chat_history(session_id)
        
        # Analyze response
        analysis = await analyze_response(intent_data, chat_history, current_tag, total_questions, session_id)
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
        if number >= len(intent_data["tags"]) or analysis["force_conversation_end"]:
            logger.info(f"[Session: {session_id}] Conversation complete - Analysis based")
            final_analysis = await final_chat_analysis(session_id, chat_history, intent_data)
            intent_data["chat_completed"] = True
            intent_data["chat_analysis"] = final_analysis
            
            await save_intent_data(employee_id, session_id, intent_data)
            if final_analysis['recommended_mentor'] == 'ForwardingRequestToHR':
                response = "Your issue has been forwarded to HR Management. Please wait for their response."
            else:
                response = f"Thank you for sharing your concerns. Based on our conversation, I recommend you speak with {final_analysis['recommended_mentor']}. You can continue the conversation with them directly in this chat."
            return {
                "response": response,
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
            "intent_data": intent_data
        }

    except Exception as e:
        logger.error(f"[Session: {session_id}] Error in chat completion: {str(e)}", exc_info=True)
        return {"error": "An error occurred during the conversation", "conversation_status": "error"}
    
async def is_chat_required(employee_id: str) -> bool:
    """
    Determine if chat is required based on analyzed profile and intent data
    Returns True if:
    1. Predicted score is <= 2.5
    2. Actual emotion is "Sad" or "Frustrated"
    3. No intent data exists for today
    """
    try:
        # Get current IST date
        current_utc = datetime.now(timezone.utc)
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = current_utc.astimezone(ist_tz)
        current_ist_date = current_ist.date().isoformat()

        # Get latest analyzed profile
        latest_analysis = await async_db["analyzed_profile"].find_one(
            {"Employee_ID": employee_id},
            sort=[("timestamp", -1)]
        )

        if not latest_analysis:
            logger.info(f"No analyzed profile found for {employee_id}. Chat required.")
            return True

        # Check if we have intent data for today
        today_intent = await async_db["intent_data"].find_one(
            {
                "employee_id": employee_id,
                "intent_data.chat_completed": True,
                "ist_date": current_ist_date
            }
        )

        if today_intent:
            logger.info(f"Chat already completed today for {employee_id}. Chat not required.")
            return False

        # Check predicted score and emotions
        predicted_score = latest_analysis.get("Predicted", 0)
        actual_emotion = latest_analysis.get("Actual_Emotion", "unknown")

        # If predicted score is low or emotions indicate distress
        if predicted_score <= 2.5:
            logger.info(f"Low predicted score ({predicted_score}) for {employee_id}. Chat required.")
            return True

        if actual_emotion in ["Sad", "Frustrated"]:
            logger.info(f"Concerning emotion state ({actual_emotion}) for {employee_id}. Chat required.")
            return True

        logger.info(f"No chat required for {employee_id}")
        return False

    except Exception as e:
        logger.error(f"Error checking chat requirement for {employee_id}: {str(e)}")
        return True  # Default to requiring chat if there's an error
    
if __name__ == "__main__":
    import asyncio

    async def main():
        
        await extract_questions("Lack_of_Engagement")
        # try:
        #     session_id = "98162e50-00d8-4a51-bb7c-ae29a3776142"
            
        #     # Get chat history and intent data
        #     chat_history = await get_chat_history(session_id)
        #     if not chat_history:
        #         print("No chat history found")
        #         return
                
        #     intent_data = await get_intent_data(session_id)
        #     if not intent_data:
        #         print("No intent data found")
        #         return
            
        #     # Perform final analysis
        #     result = await final_chat_analysis(
        #         session_id=session_id,
        #         chat_history=chat_history,
        #         intent_data=intent_data
        #     )
            
        #     print("\nFinal Analysis:", result)
            
        # except Exception as e:
        #     print(f"An error occurred: {str(e)}")

    # Run all async operations in a single event loop
    asyncio.run(main())