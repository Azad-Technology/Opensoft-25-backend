from typing import List, Dict
import json
from utils.api_key_rotate import APIKeyManager
from src.chatbot.llm_models import get_model
from src.analysis.data.question_bank import question_bank 
from utils.config import settings
from src.chatbot.system_prompts import QUESTION_BANK_TAGGING_PROMPT
from pathlib import Path

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

def tag_question(question: str, model_client) -> Dict:
    try:
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
        rate_limit=10,
        cooldown_period=60
    )
    
    # Initialize model client
    model_client = get_model(model_provider="GEMINI")
    
    for idx, question in enumerate(question_bank, 1):
        try:
            # Get tags for the question
            result = tag_question(question, model_client)
            
            if result:
                tagged_question = {
                    "id": idx,
                    "question": result["question"],
                    "tags": result["tags"]
                }
                
                # Save each question result individually
                save_to_json(tagged_question, "Opensoft-25-backend/src/analysis/data/tagged_questions.json")
                print(f"Processed and saved question {idx}")
                
            break  # Remove this if you want to process all questions
            
        except Exception as e:
            print(f"Error processing question {idx}: {e}")
            continue

if __name__ == "__main__":
    # Example usage:
    api_keys = [
        settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2
    ]

    process_question_bank(question_bank, api_keys)