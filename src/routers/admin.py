from datetime import UTC, datetime, timedelta  # Add timedelta to imports
from collections import defaultdict
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from src.models.auth import OnboardingRequest
from utils.analysis import get_vibe
from utils.app_logger import setup_logger
from utils.auth import get_current_user, get_password_hash
from utils.config import get_async_database
from fastapi.responses import JSONResponse
from datetime import datetime
from collections import defaultdict
import numpy as np
import asyncio

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/admin.py")

@router.get("/")
async def get_root():
    return {"message": "Welcome to the Admin API"}

@router.get("/{employee_id}/summary")
async def get_employee_summary(employee_id: str, current_user: dict = Depends(get_current_user)):
    try:
        
        if current_user["role_type"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the summary"
            )
        
        def process_doc(doc):
            if not doc:
                return {}
            processed = {}
            for key, value in doc.items():
                if key == '_id':
                    processed[key] = str(value)
                elif isinstance(value, datetime):
                    processed[key] = value.isoformat()
                else:
                    processed[key] = value
            return processed
        # Helper function to classify vibes
        def get_vibe(score):
            if not isinstance(score, (int, float)):
                return "unknown"
            if score > 4.5 and score <= 5:
                return "Excited"
            elif score > 3.5 and score <= 4.5:
                return "Happy"
            elif score > 2.5 and score <= 3.5:
                return "Okay"
            elif score > 1.5 and score <= 2.5:
                return "Sad"
            elif score >= 0 and score <= 1.5:
                return "Frustrated"
            return "unknown"
        
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
            "intent_analysis": {},
            "post_chat_analysis": {}
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
        # Get all data in parallel
        users_data, vibe_data, leave_data = await asyncio.gather(
            async_db["users"].find().to_list(length=None),
            async_db["vibemeter"].find().sort("Response_Date", -1).to_list(length=None),
            async_db["leave"].find().to_list(length=None)
        )
        
        # Create vibe mapping (get latest vibe for each employee)
        vibe_map = {}
        for vibe in vibe_data:
            emp_id = vibe.get("Employee_ID")
            if emp_id and emp_id not in vibe_map:
                vibe_map[emp_id] = {
                    "vibe_score": vibe.get("Vibe_Score"),
                    "response_date": vibe.get("Response_Date").isoformat() 
                        if isinstance(vibe.get("Response_Date"), datetime) 
                        else None
                }

        # Create leave mapping (total leaves for each employee)
        leave_map = {}
        current_year = datetime.now().year
        for leave in leave_data:
            emp_id = leave.get("Employee_ID")
            leave_date = leave.get("Leave_Start_Date")
            
            # Only count leaves for current year
            if emp_id and isinstance(leave_date, datetime) and leave_date.year == current_year:
                if emp_id not in leave_map:
                    leave_map[emp_id] = {
                        "total_leaves": 0,
                        "leave_types": defaultdict(int)
                    }
                leave_days = leave.get("Leave_Days", 0)
                leave_map[emp_id]["total_leaves"] += leave_days
                leave_map[emp_id]["leave_types"][leave.get("Leave_Type", "Other")] += leave_days

        # Process each user
        processed_users = []
        for user in users_data:
            try:
                employee_id = user.get("employee_id")
                vibe_info = vibe_map.get(employee_id, {})
                leave_info = leave_map.get(employee_id, {"total_leaves": 0, "leave_types": {}})
                
                processed_users.append({
                    "employee_id": employee_id,
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "role": user.get("role", "employee"),
                    "current_vibe": {
                        "score": vibe_info.get("vibe_score"),
                        "last_response": vibe_info.get("response_date")
                    },
                    "leaves":leave_info["total_leaves"],
                    "risk_assessment": "High" 
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
    
async def get_aggregated_wellness_data() -> Dict[str, Dict[str, any]]:
    """Get aggregated wellness data (mock implementation - replace with actual DB aggregation)"""
    # In production, this would use MongoDB aggregation pipeline
    # Example pipeline would group and calculate metrics directly in database
    
    # Mock data structure - replace with actual aggregation query
    return {
        "composite_scores": {
            "average": 62.3,
            "distribution": {
                "0-30": 5,   # Severe
                "31-50": 12,  # At-risk
                "51-70": 28,  # Moderate
                "71-100": 15  # Healthy
            }
        },
        "mood_analysis": {
            "happy": 32,
            "neutral": 45,
            "sad": 23
        },
        "risk_analysis": {
            "critical_cases": 8,
            "severe_cases": 3,
            "common_risk_factors": [
                {"factor": "overwhelmed", "count": 27},
                {"factor": "fatigue", "count": 19},
                {"factor": "disengagement", "count": 12}
            ]
        },
        "trends": {
            "weekly_avg_scores": {
                "Week 12": 58.2,
                "Week 13": 61.7,
                "Week 14": 63.1
            },
            "monthly_mood_changes": {
                "happy": +5,  # Percentage point change
                "neutral": -2,
                "sad": -3
            }
        },
        "correlations": {
            "performance_sentiment": 0.42,
            "hours_wellness": -0.31
        }
    }

@router.get("/analytics/hr-wellness-dashboard")
async def get_hr_wellness_dashboard():
    """Endpoint for HR dashboard with aggregated, non-PII wellness metrics"""
    try:
        # Get pre-aggregated data (implement proper DB aggregation in production)
        wellness_data = await get_aggregated_wellness_data()
        
        # Current date for reporting
        report_date = datetime.utcnow()
        
        # Structure the dashboard response
        return {
            "timestamp": report_date.isoformat() + "Z",
            "summary_metrics": {
                "average_wellness_score": wellness_data["composite_scores"]["average"],
                "employee_distribution": wellness_data["composite_scores"]["distribution"],
                "mood_distribution": {
                    "happy_percentage": wellness_data["mood_analysis"]["happy"],
                    "neutral_percentage": wellness_data["mood_analysis"]["neutral"],
                    "sad_percentage": wellness_data["mood_analysis"]["sad"]
                },
                "risk_metrics": {
                    "employees_at_risk": wellness_data["risk_analysis"]["critical_cases"],
                    "employees_in_crisis": wellness_data["risk_analysis"]["severe_cases"],
                    "top_risk_factors": wellness_data["risk_analysis"]["common_risk_factors"][:3]  # Top 3
                }
            },
            "trend_analysis": {
                "weekly_wellness_trend": wellness_data["trends"]["weekly_avg_scores"],
                "monthly_mood_changes": wellness_data["trends"]["monthly_mood_changes"]
            },
            "insights": {
                "performance_wellness_correlation": round(wellness_data["correlations"]["performance_sentiment"], 2),
                "workload_impact": round(wellness_data["correlations"]["hours_wellness"], 2),
                "alert_levels": {
                    "red_alert": wellness_data["risk_analysis"]["severe_cases"],
                    "yellow_alert": wellness_data["risk_analysis"]["critical_cases"] - wellness_data["risk_analysis"]["severe_cases"]
                }
            }
        }
    
    except Exception as e:
        return {
            "error": "Could not generate wellness dashboard",
            "details": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }