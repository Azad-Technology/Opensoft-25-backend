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
    
def tag_questions_batch(questions: List[str], api_manager) -> List[Dict]:
    try:
        # Initialize model client
        model_client = get_model(api_manager)
        
        # Prepare the questions as a batch
        batch_content = "Please analyze these questions and provide relevant tags for each:\n"
        for i, q in enumerate(questions, 1):
            batch_content += f"Question {i}: {q}\n"
            
        response = model_client.chat.completions.create(
            model="gemini-2.5-pro-exp-03-25",
            messages=[
                {"role": "system", "content": QUESTION_BANK_TAGGING_PROMPT},
                {"role": "user", "content": batch_content}
            ],
            response_format={"type": "json_object"}
        )
        
        print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error processing question batch: {e}")
        return None

def process_question_bank(question_bank: List[str], api_keys: List[str], batch_size: int = 10):
    # Initialize API key manager
    api_manager = APIKeyManager(
        api_keys=api_keys,
        model_name="gemini-2.5-pro-exp-03-25",
        rate_limit=2,
        cooldown_period=60
    )
    
    # Process questions in batches
    for i in range(0, len(question_bank), batch_size):
        try:
            # Get the current batch of questions
            batch = question_bank[i:i + batch_size]
            
            # Get tags for the batch of questions
            result = tag_questions_batch(batch, api_manager)
            
            if result:
                # Process each tagged question in the batch
                for j, tagged_question in enumerate(result, 1):
                    question_data = {
                        "id": i + j,  # Calculate the overall question ID
                        "question": tagged_question["question"],
                        "tags": tagged_question["tags"]
                    }
                    
                    # Save each question result
                    save_to_json(question_data, "src/analysis/data/tagged_questions1.json")
                    
                print(f"Processed and saved batch of questions {i+1} to {i+len(batch)}")
            
        except Exception as e:
            print(f"Error processing batch starting at question {i+1}: {e}")
            continue
        
def load_tagged_questions(filename: str) -> List[Dict]:
    """Load tagged questions from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tagged questions: {e}")
        return []

def calculate_question_relationships_batch(question_a: str, other_questions: List[str], api_manager) -> List[Dict]:
    """Calculate relationship scores between one question and multiple other questions"""
    try:
        model_client = get_model(api_manager)
        
        # Format the other questions list
        formatted_other_questions = "\n".join([f"{i+1}. {q}" for i, q in enumerate(other_questions)])
        
        # Prepare the prompt
        user_prompt = f"""Using the relationship analysis logic and JSON output format defined in your system prompt, calculate the relationship score between the primary "Question A" and *each* of the questions provided in the "Other Questions List".

        **Question A:**
        "{question_a}"

        **Other Questions List:**
        {formatted_other_questions}

        Provide the results strictly as a JSON array of objects as specified in the system prompt."""
        
        response = model_client.chat.completions.create(
            model="gemini-2.5-pro-exp-03-25",
            messages=[
                {"role": "system", "content": RELATIONSHIP_SCORE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error calculating batch relationships: {e}")
        return None

def process_question_relationships(api_keys: List[str], batch_size: int = 50):
    # Load tagged questions
    tagged_questions = load_tagged_questions("src/analysis/data/tagged_questions1.json")
    
    if not tagged_questions:
        print("No tagged questions found")
        return

    # Initialize API key manager
    api_manager = APIKeyManager(
        api_keys=api_keys,
        model_name="gemini-2.5-pro-exp-03-25",
        rate_limit=2,
        cooldown_period=60,
        day_limit=40
    )

    # Process each question as the primary question
    for i, primary_question in enumerate(tagged_questions):
        
        
        # 4 is left 
        if (i>10 or i<=3):
            continue
        print(f"Processing relationships for question {i}")
        
        remaining_questions = tagged_questions[i + 1:]
        
        # Process remaining questions in batches
        for j in range(0, len(remaining_questions), batch_size):
            try:
                batch = remaining_questions[j:j + batch_size]
                batch_questions = [q["question"] for q in batch]
                
                # Get relationship scores for the batch
                results = calculate_question_relationships_batch(
                    primary_question["question"],
                    batch_questions,
                    api_manager
                )
                
                if results:
                    # Process and save each relationship
                    for k, result in enumerate(results):
                        relationship = {
                            "from_id": primary_question["id"],
                            "to_id": batch[k]["id"],
                            "score": result["relationship_score"]
                        }
                        
                        # Save each relationship individually
                        save_to_json(relationship, "src/analysis/data/question_relationships1.json")
                        
                    print(f"Processed relationships for question {primary_question['id']} with questions {batch[0]['id']} to {batch[-1]['id']}")
                
            except Exception as e:
                print(f"Error processing batch for question {primary_question['id']}: {e}")
                continue


if __name__ == "__main__":
    # Example usage:
    api_keys = [
        settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2, settings.GOOGLE_API_KEY3, settings.GOOGLE_API_KEY4, settings.GOOGLE_API_KEY5, settings.GOOGLE_API_KEY6, settings.GOOGLE_API_KEY7, settings.GOOGLE_API_KEY8, settings.GOOGLE_API_KEY9, settings.GOOGLE_API_KEY10, settings.GOOGLE_API_KEY11, settings.GOOGLE_API_KEY12, settings.GOOGLE_API_KEY13, settings.GOOGLE_API_KEY14
    ]

    # process_question_bank(question_bank, api_keys)
    
    process_question_relationships(api_keys)