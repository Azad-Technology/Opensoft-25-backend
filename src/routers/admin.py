from datetime import UTC, datetime, timedelta
from collections import defaultdict
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from src.analysis.data_analyze_pipeline import analyzed_profile
from src.models.auth import OnboardingRequest
from utils.analysis import get_vibe, process_doc, serialize_datetime
from utils.app_logger import setup_logger
from utils.auth import get_current_user, get_password_hash
from utils.config import get_async_database
from fastapi.responses import JSONResponse
from datetime import datetime
from collections import defaultdict
import asyncio

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/admin.py")

@router.get("/")
async def get_root():
    return {"message": "Welcome to the Admin API"}

from datetime import datetime, timedelta
from typing import Dict, List

def get_last_7_days(today):
            return [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        
        # Helper function to safely get nested values
def get_nested(data, *keys, default=None):
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError):
            return default
    return data

@router.get("/overall_dashboard")
async def get_overall_dashboard(current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the dashboard"
            )
        
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        today_end = today_start + timedelta(days=1)
        seven_days_ago = today_start - timedelta(days=7)
     
        # Get all collections we need
        intent_data, vibemeter_data, users_data = await asyncio.gather(
            async_db["intent_data"].find({
                "updated_at": {
                    "$gte": today_start,
                    "$lt": today_end
                },
                "intent_data.chat_completed": True
            }).to_list(length=None),
            async_db["vibemeter"].find({
                "Response_Date": {
                    "$gte": seven_days_ago,
                    "$lte": today_end
                }
            }).to_list(length=None),
            async_db["users"].find({"role": "employee"}).to_list(length=None)
        )
        
        # 1. Calculate overall_risk_score (average risk_level of today's records)
        overall_risk_score = 0.0
        valid_intents = [
            intent for intent in intent_data 
            if get_nested(intent, "intent_data", "chat_completed") is True
        ]
        
        if valid_intents:
            total_risk = sum(
                get_nested(intent, "intent_data", "chat_analysis", "risk_assessment", "risk_level", default=0)
                for intent in valid_intents
            )
            overall_risk_score = round(total_risk / len(valid_intents), 2)
        
        # 2. Get critical cases (risk_level > 3)
        critical_intents = [
            intent for intent in intent_data 
            if get_nested(intent, "intent_data", "chat_analysis", "risk_assessment", "risk_level", default=0) > 3
        ]
        
        critical_cases = []
        for intent in critical_intents:
            # user = next((u for u in users_data if u.get("employee_id") == intent.get("employee_id")), None)
            user = await async_db["users"].find_one({"employee_id": intent.get("employee_id")})
            print('user: ', user)
            risk_level = get_nested(intent, "intent_data", "chat_analysis", "risk_assessment", "risk_level", default=0)
            
            critical_cases.append({
                "employee_id": intent.get("employee_id", "Unknown"),
                "name": user.get("name", "Unknown") if user else "Unknown",
                "email": user.get("email", "Unknown") if user else "Unknown",
                "risk_level": risk_level,
            })
        
        # 3. Get total employees
        total_employees = len(users_data)
        
        # 4. Get overall mood and mood distribution
        latest_vibes = {}
        for vibe in sorted(vibemeter_data, key=lambda x: (x.get("Employee_ID", ""), x.get("Response_Date", "")), reverse=True):
            if "Employee_ID" in vibe and vibe["Employee_ID"] not in latest_vibes:
                latest_vibes[vibe["Employee_ID"]] = vibe.get("Vibe_Score", 0)
        
        vibe_scores = list(latest_vibes.values())
        overall_mood = round(sum(vibe_scores) / len(vibe_scores), 2) if vibe_scores else 0.0
        
        mood_distribution = {
            "excited": sum(1 for v in vibe_scores if v == 5),
            "happy": sum(1 for v in vibe_scores if v == 4),
            "ok": sum(1 for v in vibe_scores if v == 3),
            "sad": sum(1 for v in vibe_scores if v == 2),
            "frustrated": sum(1 for v in vibe_scores if v == 1)
        }
        
        # 5. Weekly risk trend
        weekly_risk_trend: Dict[str, float] = {}
        for day in get_last_7_days(today):
            day_start = datetime.strptime(day, "%Y-%m-%d")
            day_end = day_start + timedelta(days=1)
            
            day_intents = await async_db["intent_data"].find({
                "updated_at": {
                    "$gte": day_start,
                    "$lt": day_end
                }

            }).to_list(length=None)
            
            valid_day_intents = [
                intent for intent in day_intents 
                if get_nested(intent, "intent_data", "chat_completed") is True
            ]
            
            if valid_day_intents:
                print('day intents:', day)
                day_risk = sum(
                    get_nested(intent, "intent_data", "chat_analysis", "risk_assessment", "risk_level", default=0)
                    for intent in valid_day_intents
                )
                weekly_risk_trend[day] = round(day_risk / len(valid_day_intents), 2)
            else:
                weekly_risk_trend[day] = 0.0
        
        return {
            "overall_risk_score": overall_risk_score,
            "critical_cases": critical_cases,
            "total_employees": total_employees,
            "overall_mood": overall_mood,
            "mood_distribution": mood_distribution,
            "weekly_risk_trend": weekly_risk_trend,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        return {
            "error": "Could not generate overall dashboard",
            "details": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@router.get("/employees/all")
async def get_all_employees(current_user: dict = Depends(get_current_user)):
    try:
        # Pipeline to get latest vibemeter for each employee
        vibe_pipeline = [
            {
                '$sort': {
                    'Employee_ID': 1,
                    'Response_Date': -1
                }
            },
            {
                '$group': {
                    '_id': '$Employee_ID',
                    'latest_vibe': {
                        '$first': {
                            'vibe_score': '$Vibe_Score',
                            'response_date': '$Response_Date'
                        }
                    }
                }
            }
        ]

        # Pipeline to get latest intent data for each employee
        intent_pipeline = [
            {
                '$match': {
                    'intent_data.chat_completed': True
                }
            },
            {
                '$sort': {
                    'employee_id': 1,
                    'updated_at': -1
                }
            },
            {
                '$group': {
                    '_id': '$employee_id',
                    'latest_intent': {
                        '$first': {
                            'risk_level': '$intent_data.chat_analysis.risk_assessment.risk_level',
                            'updated_at': '$updated_at'
                        }
                    }
                }
            }
        ]

        # Pipeline to get latest performance for each employee
        performance_pipeline = [
            {
                '$sort': {
                    'Employee_ID': 1,
                    'Review_Period': -1
                }
            },
            {
                '$group': {
                    '_id': '$Employee_ID',
                    'latest_performance': {
                        '$first': {
                            'rating': '$Performance_Rating',
                            'feedback': '$Manager_Feedback',
                            'review_period': '$Review_Period'
                        }
                    }
                }
            }
        ]

        # Get all data in parallel with optimized queries
        users_data, vibe_data, intent_data, performance_data = await asyncio.gather(
            async_db["users"].find().to_list(length=None),
            async_db["vibemeter"].aggregate(vibe_pipeline).to_list(length=None),
            async_db["intent_data"].aggregate(intent_pipeline).to_list(length=None),
            async_db["performance"].aggregate(performance_pipeline).to_list(length=None)
        )

        # Convert pipeline results to maps for easier access
        vibe_map = {doc['_id']: doc['latest_vibe'] for doc in vibe_data}
        intent_map = {doc['_id']: doc['latest_intent'] for doc in intent_data}
        performance_map = {doc['_id']: doc['latest_performance'] for doc in performance_data}

        # Process each user
        processed_users = []
        for user in users_data:
            try:
                employee_id = user.get("employee_id")
                vibe_info = vibe_map.get(employee_id, {})
                intent_info = intent_map.get(employee_id, {})
                performance_info = performance_map.get(employee_id, {})

                # Determine risk assessment
                vibe_score = vibe_info.get("vibe_score", 0)
                vibe_date = vibe_info.get("response_date")
                intent_date = intent_info.get("updated_at")
                intent_risk = intent_info.get("risk_level", 1)

                risk_level = intent_risk
                if vibe_score > 3 and vibe_date and intent_date:
                    if vibe_date > intent_date:
                        risk_level = 1

                processed_users.append({
                    "employee_id": employee_id,
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "role": user.get("role", "employee"),
                    "current_vibe": {
                        "score": vibe_score,
                        "last_check_in": vibe_date.isoformat() if vibe_date else None
                    },
                    "performance": {
                        "rating": performance_info.get("rating"),
                        "feedback": performance_info.get("feedback"),
                        "period": performance_info.get("review_period")
                    },
                    "risk_assessment": risk_level
                })
            except Exception as e:
                logger.error(f"Error processing user {user.get('employee_id')}: {str(e)}")
                continue

        # Sort by employee_id
        processed_users.sort(key=lambda x: x["employee_id"])

        return JSONResponse(content={
            "count": len(processed_users),
            "users": processed_users
        })

    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user list: {str(e)}"
        )

@router.post("/add_onboarding")
async def add_onboarding(
    request: OnboardingRequest,
    current_user: dict = Depends(get_current_user)):
    """
    Onboard a new employee (HR personnel only)
    """
    try:
        # Verify HR authorization
        if current_user["role"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to onboard employees"
            )

        # Check if employee_id already exists
        existing_employee = await async_db.users.find_one({"employee_id": request.employee_id})
        if existing_employee:
            raise HTTPException(
                status_code=400,
                detail="Employee ID already exists"
            )

        # Check if email already exists
        existing_email = await async_db.users.find_one({"email": request.email})
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Create user data
        user_data = {
            "role_type": request.role_type,
            "name": request.name,
            "role": request.role,
            "employee_id": request.employee_id,
            "email": request.email,
            "password": get_password_hash(request.password),
            "created_at": datetime.now(UTC),
            "created_by": current_user["employee_id"]
        }

        # Insert into database
        result = await async_db.users.insert_one(user_data)
        
        # Create onboarding record
        onboarding_data = {
            "name": request.name,
            "employee_id": request.employee_id,
            "onboarded_by": current_user["employee_id"],
            "initial_role": request.role,
            "member_type": request.role_type,
            "email": request.email,
        }

        return JSONResponse(content=onboarding_data)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in onboarding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during onboarding"
        )
    
@router.get("/get_all_tickets", summary="Get all tickets with pagination")
async def get_all_tickets(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, gt=0, description="Page number starting from 1"),
    page_size: int = Query(10, gt=0, le=100, description="Number of items per page (max 100)")
):
    try:
        if current_user.get("role") != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to access tickets"
            )

        skip = (page - 1) * page_size
        total_tickets = await async_db["tickets"].count_documents({})
        
        if total_tickets == 0:
            raise HTTPException(
                status_code=404,
                detail="No tickets found in the system"
            )
        
        total_pages = (total_tickets + page_size - 1) // page_size

        cursor = async_db["tickets"].find({}).skip(skip).limit(page_size)
        tickets = await cursor.to_list(length=page_size)

        for ticket in tickets:
            ticket.pop("_id")

        return {
            "data": tickets,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_tickets": total_tickets,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tickets: {str(e)}"
        )
    
@router.post("/set_ticket_status", summary="Set the status of a ticket")
async def set_ticket_status(ticket_id : str , status_update: bool,  current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to resolve or unresolve tickets"
            )

        ticket = await async_db["tickets"].find_one({"ticket_id": ticket_id})
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"No tickets found"
            )
        
        update_result = await async_db["tickets"].update_one(
            {"ticket_id": ticket_id},
            {
                "$set": {
                    "is_resolved": status_update,
                    "update_at" : datetime.now().timestamp()
                }
            }
        )
        return {
            "ticket_id" : ticket_id,
            "new_status" : status_update,
            "response": f"Ticket:{ticket_id} updated successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tickets: {str(e)}"
        )
    
@router.get("/start_analyzing_the_profile")
async def start_analyzing_the_profile(
    id: str
):
    try:
        if id != "IamAdmin":
            return {
                "message": "You are not authorized to analyze the profile"
            }
            
        result = await analyzed_profile()
        
        # Convert BulkWriteResult to dictionary
        result_dict = {
            "modified_count": result.modified_count,
            "upserted_count": result.upserted_count,
            "matched_count": result.matched_count
        }
    
        logger.info(f"Profile analysis completed. Results: {result_dict}")
        return {
            "message": "Profile analysis completed successfully",
            "result": result_dict
        }
    except Exception as e:
        logger.error(f"Error in analyzing the profile: {str(e)}")
        return {
            "message": "Error in analyzing the profile",
            "error": str(e)
        }