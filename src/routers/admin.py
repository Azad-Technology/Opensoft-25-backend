from datetime import UTC, datetime
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

@router.get("/overall_dashboard")
async def get_overall_dashboard(current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the dashboard"
            )
    
    
        pass
    
    except Exception as e:
        return {
            "error": "Could not generate overall dashboard",
            "details": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@router.get("/{employee_id}/summary")
async def get_employee_summary(employee_id: str, current_user: dict = Depends(get_current_user)):
    try:
        
        if current_user["role_type"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the summary"
            )
        
        today = datetime.now()
        months_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        leave_per_month = defaultdict(lambda: {
            'sick': 0,
            'casual': 0,
            'annual': 0,
            'unpaid': 0,
            'other': 0
        })

        for i in range(12):
            month_num = (today.month - 1 - i) % 12 + 1
            year = today.year - (1 if (today.month - 1 - i) < 0 else 0)
            month_name = months_order[month_num - 1]
            key = f"{month_name} {year}"
            leave_per_month[key]  # This ensures all months are initialized

        # Base employee data
                # Get base employee data from both collections in parallel
        employee_data, user_data = await asyncio.gather(
            async_db["onboarding"].find_one({"Employee_ID": employee_id}),
            async_db["users"].find_one({"employee_id": employee_id})
        )

        if not employee_data and not user_data:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Determine employee name with fallback logic
        employee_name = user_data.get('name') if user_data else None
        employee_email = user_data.get('email') if user_data else None

        # Get all data in parallel
        leave_data, activity_data, vibe_data, rewards_data, performance_data = await asyncio.gather(
            async_db["leave"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["activity"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["vibemeter"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["rewards"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["performance"].find({"Employee_ID": employee_id}).to_list(length=None)
        )

        # Process leave data with detailed monthly breakdown
        for leave in leave_data:
            if 'Leave_Start_Date' in leave and isinstance(leave['Leave_Start_Date'], datetime):
                leave_date = leave['Leave_Start_Date']
                month_num = leave_date.month
                month_name = months_order[month_num - 1]
                year = leave_date.year
                month_key = f"{month_name} {year}"
                
                leave_type = leave.get('Leave_Type', '').lower()
                leave_days = leave.get('Leave_Days', 0)
                
                if 'sick' in leave_type:
                    leave_per_month[month_key]['sick'] += leave_days
                elif 'casual' in leave_type:
                    leave_per_month[month_key]['casual'] += leave_days
                elif 'annual' in leave_type:
                    leave_per_month[month_key]['annual'] += leave_days
                elif 'unpaid' in leave_type:
                    leave_per_month[month_key]['unpaid'] += leave_days
                else:
                    leave_per_month[month_key]['other'] += leave_days

        # Convert to ordered dictionary (most recent first)
        ordered_leave_per_month = {}
        for i in range(12):
            month_num = (today.month - 1 - i) % 12 + 1
            year = today.year - (1 if (today.month - 1 - i) < 0 else 0)
            month_name = months_order[month_num - 1]
            key = f"{month_name} {year}"
            ordered_leave_per_month[key] = leave_per_month[key]

        # Process mental states from vibe data
        mental_states = defaultdict(int)
        for vibe in vibe_data:
            state = get_vibe(vibe.get('Vibe_Score'))
            mental_states[state] += 1

        # Process weekly communication activity
        weekly_activity = defaultdict(lambda: defaultdict(int))
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Process activity data (last 10 years)
        recent_activity = [a for a in activity_data if 
                         (datetime.now() - a['Date']).days <= 3650] if activity_data else [] 

        activity_stats = {
            "teams_messages_sent": int(sum(a['Teams_Messages_Sent'] for a in recent_activity)),
            "emails_sent": int(sum(a['Emails_Sent'] for a in recent_activity)),
            "meetings_attended": sum(a['Meetings_Attended'] for a in recent_activity),
            "work_hours": sum(a['Work_Hours'] for a in recent_activity),
            "data_points": len(recent_activity)
        }

        # Process weekly communication activity
        weekly_activity = defaultdict(lambda: defaultdict(int))
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for activity in activity_data:
            if 'Date' in activity and isinstance(activity['Date'], datetime):
                day = weekdays[activity['Date'].weekday()]
                weekly_activity[day]["teams_messages_sent"] += activity.get('Teams_Messages_Sent', 0)
                weekly_activity[day]["emails_sent"] += activity.get('Emails_Sent', 0)
                weekly_activity[day]["meetings_attended"] += activity.get('Meetings_Attended', 0)
                weekly_activity[day]["work_hours"] += activity.get('Work_Hours', 0)

        leave_counts = defaultdict(int)
        for leave in leave_data:
            leave_counts[leave['Leave_Type']] += leave['Leave_Days']

        # Calculate communication averages
        avg_activity = {
            "teams_messages_sent": round(sum(a.get('Teams_Messages_Sent', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
            "emails_sent": round(sum(a.get('Emails_Sent', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
            "meetings_attended": round(sum(a.get('Meetings_Attended', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
            "work_hours": round(sum(a.get('Work_Hours', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0
        }

        # Process leave data per month
        leave_per_month = defaultdict(int)
        for leave in leave_data:
            if 'Leave_Start_Date' in leave and isinstance(leave['Leave_Start_Date'], datetime):
                month = leave['Leave_Start_Date'].strftime('%Y-%m')
                leave_per_month[month] += leave.get('Leave_Days', 0)

        # Process performance rating month-wise
        perf_per_month = defaultdict(list)
        for perf in performance_data:
            if 'Review_Period' in perf:
                # Assuming Review_Period is in format like "2023-01" or "Jan-2023"
                month = perf['Review_Period'][-7:]  # Get last 7 chars (for "Jan-2023" format)
                perf_per_month[month].append(perf.get('Performance_Rating', 0))
        
        # Convert to average performance per month
        avg_perf_per_month = {
            month: round(sum(ratings)/len(ratings), 2) 
            for month, ratings in perf_per_month.items()
        }

        # Process working hours month-wise
        work_hours_per_month = defaultdict(list)
        for activity in activity_data:
            if 'Date' in activity and isinstance(activity['Date'], datetime):
                month = activity['Date'].strftime('%Y-%m')
                work_hours_per_month[month].append(activity.get('Work_Hours', 0))
        
        avg_work_hours_per_month = {
            month: round(sum(hours)/len(hours), 2) 
            for month, hours in work_hours_per_month.items()
        }

        # Latest vibe data
        latest_vibe = None
        if vibe_data:
            latest_vibe_data = sorted(vibe_data, key=lambda x: x.get('Response_Date', datetime.min), reverse=True)[0]
            latest_vibe = {
                "vibe_score": latest_vibe_data.get('Vibe_Score'),
                "vibe": get_vibe(latest_vibe_data.get('Vibe_Score')),
                "response_date": latest_vibe_data.get('Response_Date').isoformat() 
                    if isinstance(latest_vibe_data.get('Response_Date'), datetime) 
                    else None
            }
            
        # Get the latest intent data
        latest_intent = await async_db["intent_data"].find_one(
            {
                "employee_id": employee_id,
                "intent_data.chat_completed": True  # Only get completed chats
            },
            sort=[("updated_at", -1)]  # Get the most recent one
        )

        # Process intent and chat analysis
        intent_analysis = {}
        chat_analysis = {}
        
        if latest_intent and "intent_data" in latest_intent:
            intent_data = latest_intent["intent_data"]
            
            # Process intent analysis
            intent_analysis = {
                "primary_issues": intent_data.get("primary_issues"),
                "tags": intent_data.get("tags", []),
                "updated_at": serialize_datetime(latest_intent.get("updated_at"))
            }
            
            # Process chat analysis if it exists
            if intent_data.get("chat_completed") and "chat_analysis" in intent_data:
                chat_data = intent_data["chat_analysis"]
                chat_analysis = {
                    "summary": chat_data.get("summary"),
                    "recommended_mentor": chat_data.get("recommended_mentor"),
                    "wellbeing_analysis": chat_data.get("wellbeing_analysis", {}),
                    "risk_assessment": chat_data.get("risk_assessment", {}),
                    "updated_at": serialize_datetime(chat_data.get("updated_at"))
                }
                
        
        # Build comprehensive response
        response = {
            "name": employee_name,
            "employee_id": employee_id,
            "email": employee_email,
            "joining_date": employee_data.get('Joining_Date', '').isoformat(),
            "leaves": {
                "sick": leave_counts.get('Sick Leave', 0),
                "casual": leave_counts.get('Casual Leave', 0),
                "annual": leave_counts.get('Annual Leave', 0),
                "unpaid": leave_counts.get('Unpaid Leave', 0),
                "other": sum(v for k,v in leave_counts.items() if k not in ['Sick Leave', 'Casual Leave', 'Annual Leave', "Unpaid Leave"]),
                "per_month": ordered_leave_per_month
            },
            "onboarding_data": {
                "feedback": employee_data.get('Onboarding_Feedback'),
                "mentor_assigned": employee_data.get('Mentor_Assigned', False),
                "training_completed": employee_data.get('Initial_Training_Completed', False)
            },
            "communication_activity": activity_stats,
            "communication_activity_weekly": {day: dict(data) for day, data in weekly_activity.items()},
            "communication_activity_average": avg_activity,
            "latest_vibe": latest_vibe,
            "mental_states": dict(mental_states),
            "rewards": {
                "total_points": sum(r.get('Reward_Points', 0) for r in rewards_data) if rewards_data else 0,
                "awards": [r.get('Award_Type') for r in rewards_data if r.get('Award_Type')]
            },
            "performance": process_doc(performance_data[0]) if performance_data else None,
            "performance_rating_month_wise": avg_perf_per_month,
            "working_hours_month_wise": avg_work_hours_per_month,
            "intent_analysis": intent_analysis,
            "post_chat_analysis": chat_analysis
        }
        return JSONResponse(content=response)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching employee dashboard: {str(e)}"
        )
    
@router.get("/employees/all")
async def get_all_employees(current_user: dict = Depends(get_current_user)):
    try:
        
        if current_user["role_type"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the summary"
            )
        
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
            async_db["users"].find({"role_type": "employee"}).to_list(length=None),
            async_db["vibemeter"].aggregate(vibe_pipeline).to_list(length=None),
            async_db["intent_data"].aggregate(intent_pipeline).to_list(length=None),
            async_db["performance"].aggregate(performance_pipeline).to_list(length=None)
        )
        
        print(len(users_data), len(vibe_data), len(intent_data), len(performance_data))

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