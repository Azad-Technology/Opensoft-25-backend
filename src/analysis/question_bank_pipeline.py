from typing import List, Dict
import json
from utils.api_key_rotate import APIKeyManager
from src.analysis.data.question_bank import question_bank 
from utils.config import settings
from src.chatbot.system_prompts import QUESTION_BANK_TAGGING_PROMPT, RELATIONSHIP_SCORE_SYSTEM_PROMPT
from pathlib import Path
from langsmith.wrappers import wrap_openai
from openai import OpenAI


def get_model(google_api_manager):
    google_client = OpenAI(
        api_key=google_api_manager.use_and_get_key(),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    return wrap_openai(google_client)

def save_to_json(data: Dict, filename: str):
    """Save data to JSON file, appending if file exists"""
    file_path = Path(filename)
    
    try:
        # Read existing data if file exists
        if file_path.exists():
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        else:
            existing_data = []
            
        # Append new data
        existing_data.append(data)
        
        # Write back to file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
            
    except Exception as e:
        print(f"Error saving to JSON: {e}")

def tag_question(question, api_manager) -> Dict:
    try:
        # Initialize model client
        model_client = get_model(api_manager)
        response = model_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": QUESTION_BANK_TAGGING_PROMPT},
                {"role": "user", "content": f"Please analyze this question and provide relevant tags: {question}"}
            ],
            response_format={"type": "json_object"}
        )
        print(response.choices[0].message.content)
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error processing question: {e}")
        return None

def process_question_bank(question_bank: List[str], api_keys: List[str]):
    # Initialize API key manager
    api_manager = APIKeyManager(
        api_keys=api_keys,
        model_name="gemini-2.0-flash",
        rate_limit=14,
        cooldown_period=60
    )
    
    for idx, question in enumerate(question_bank, 1):
        try:
            # Get tags for the question
            result = tag_question(question, api_manager)
            
            if result:
                tagged_question = {
                    "id": idx,
                    "question": result["question"],
                    "tags": result["tags"]
                }
                
                # Save each question result individually
                save_to_json(tagged_question, "Opensoft-25-backend/src/analysis/data/tagged_questions.json")
                print(f"Processed and saved question {idx}")

            
        except Exception as e:
            print(f"Error processing question {idx}: {e}")
            continue
        
        
def load_tagged_questions(filename: str) -> List[Dict]:
    """Load tagged questions from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tagged questions: {e}")
        return []

def calculate_question_relationship(question1: str, question2: str, api_manager) -> float:
    """Calculate relationship score between two questions"""
    try:
        model_client = get_model(api_manager)
        response = model_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": RELATIONSHIP_SCORE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question 1: {question1}\nQuestion 2: {question2}"}
            ]
        )
        
        # Assuming the response is just a score between 0 and 1
        score = float(response.choices[0].message.content.strip())
        return score
    
    except Exception as e:
        print(f"Error calculating relationship: {e}")
        return 0.0

def process_question_relationships(api_keys: List[str]):
    # Load tagged questions
    tagged_questions = load_tagged_questions("src/analysis/data/tagged_questions.json")
    
    if not tagged_questions:
        print("No tagged questions found")
        return

    # Initialize API key manager
    api_manager = APIKeyManager(
        api_keys=api_keys,
        model_name="gemini-2.0-flash",
        rate_limit=14,
        cooldown_period=60
    )

    relationships = []
    
    # Compare each question with all other questions
    for i, reference_question in enumerate(tagged_questions):
        # Compare with all questions after the current one to avoid duplicates
        for other_question in tagged_questions[i + 1:]:
            try:
                # Skip if it's the same question
                if reference_question["id"] == other_question["id"]:
                    continue
                    
                score = calculate_question_relationship(
                    reference_question["question"],
                    other_question["question"],
                    api_manager
                )
                
                relationship = {
                    "from_id": reference_question["id"],
                    "to_id": other_question["id"],
                    "score": score
                }
                
                relationships.append(relationship)
                
                # Save each relationship individually
                save_to_json(relationship, "src/analysis/data/question_relationships.json")
                
                print(f"Processed relationship between questions {reference_question['id']} and {other_question['id']}")
                
            except Exception as e:
                print(f"Error processing relationship between questions {reference_question['id']} and {other_question['id']}: {e}")
                continue


if __name__ == "__main__":
    # Example usage:
    api_keys = [
        settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2, settings.GOOGLE_API_KEY3, settings.GOOGLE_API_KEY4, settings.GOOGLE_API_KEY5, settings.GOOGLE_API_KEY6, settings.GOOGLE_API_KEY7
    ]

    # process_question_bank(question_bank, api_keys)
    
    process_question_relationships(api_keys)