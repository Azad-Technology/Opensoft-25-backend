from datetime import UTC, datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
import pytz
from src.analysis.data_analyze_pipeline import analyzed_profile
from src.models.auth import OnboardingRequest
from utils.analysis import convert_to_ist, get_vibe, process_doc, serialize_datetime
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

@router.get("/overall_dashboard")
async def get_overall_dashboard(current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role_type"] != "hr":
            raise HTTPException(status_code=403, detail="Unauthorized to see the dashboard")

        # Fetch the latest dashboard metrics
        dashboard_metrics = await async_db["admin_dashboard"].find_one({"_id": "current"})
        
        if not dashboard_metrics:
            return {
                "overall_risk_score": 0,
                "critical_cases": [],
                "total_employees": 0,
                "overall_mood": 0,
                "mood_distribution": {
                    "excited": 0,
                    "happy": 0,
                    "ok": 0,
                    "sad": 0,
                    "frustrated": 0
                },
                "weekly_mood_trend": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Remove MongoDB _id
        dashboard_metrics.pop("_id", None)
        
        # Ensure timestamp is in ISO format
        dashboard_metrics["timestamp"] = dashboard_metrics["timestamp"].isoformat()

        return JSONResponse(content=dashboard_metrics)

    except Exception as e:
        logger.error(f"Error fetching dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching dashboard metrics")
        
def process_activity_data(activity_data):
    """Process and analyze communication activity data"""
    
    if not activity_data:
        return {}

    # Group data by weeks (using 7-day periods)
    weeks_data = defaultdict(lambda: {
        "teams_messages": 0,
        "emails": 0,
        "meetings": 0,
        "work_hours": 0
    })
    
    activity_level = []
    
    # Process data week by week
    for activity in activity_data:
        if "Date" in activity:
            activity_level.append({
                    "date": convert_to_ist(activity.get("Date")).isoformat(),
                    "teamsMessages": activity.get("Teams_Messages_Sent", 0),
                    "emails": activity.get("Emails_Sent", 0),
                    "meetings": activity.get("Meetings_Attended", 0),
                    "work_hours": activity.get("Work_Hours", 0)
                })
            
            # Get week number from the date
            week_number = activity["Date"].isocalendar()[1]
            
            weeks_data[week_number].update({
                "teams_messages": weeks_data[week_number]["teams_messages"] + activity.get("Teams_Messages_Sent", 0),
                "emails": weeks_data[week_number]["emails"] + activity.get("Emails_Sent", 0),
                "meetings": weeks_data[week_number]["meetings"] + activity.get("Meetings_Attended", 0),
                "work_hours": weeks_data[week_number]["work_hours"] + activity.get("Work_Hours", 0)
            })

    # Calculate averages per week
    num_weeks = len(weeks_data)
    if num_weeks == 0:
        return {
            "weekly_averages": {
                "teams_messages": 0,
                "emails": 0,
                "meetings": 0,
                "work_hours": 0
            },
            "communication_scores": {
                "messages_score": 0,
                "emails_score": 0,
                "meetings_score": 0
            }
        }

    weekly_averages = {
        "teams_messages": round(sum(week["teams_messages"] for week in weeks_data.values()) / num_weeks, 2),
        "emails": round(sum(week["emails"] for week in weeks_data.values()) / num_weeks, 2),
        "meetings": round(sum(week["meetings"] for week in weeks_data.values()) / num_weeks, 2),
        "work_hours": round(sum(week["work_hours"] for week in weeks_data.values()) / num_weeks, 2)
    }

    # Calculate communication scores
    total_communications = weekly_averages["teams_messages"] + weekly_averages["emails"] + weekly_averages["meetings"]
    
    communication_scores = {
        "messages_score": round((weekly_averages["teams_messages"] / total_communications * 100), 2) if total_communications > 0 else 0,
        "emails_score": round((weekly_averages["emails"] / total_communications * 100), 2) if total_communications > 0 else 0,
        "meetings_score": round((weekly_averages["meetings"] / total_communications * 100), 2) if total_communications > 0 else 0
    }

    return {
        "weekly_averages": weekly_averages,
        "communication_scores": communication_scores,
        "activity_level": activity_level
    }

def process_leave_data(leave_data, current_ist):
    """Process leave data for last 12 months"""
    months_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    # Initialize monthly leave structure with defaultdict
    leave_per_month = defaultdict(
        lambda: {
            "sick": 0,
            "casual": 0,
            "annual": 0,
            "unpaid": 0,
            "other": 0
        }
    )

    # Pre-initialize last 12 months to ensure order
    ordered_months = []
    for i in range(12):
        month_num = (current_ist.month - 1 - i) % 12 + 1
        year = current_ist.year - (1 if (current_ist.month - 1 - i) < 0 else 0)
        month_name = f"{months_order[month_num - 1]} {year}"
        ordered_months.append(month_name)
        leave_per_month[month_name]  # Initialize the month

    # Process leave data
    total_leaves = defaultdict(int)
    for leave in leave_data:
        try:
            if "Leave_Start_Date" in leave:
                leave_date = convert_to_ist(leave["Leave_Start_Date"])
                month_name = f"{months_order[leave_date.month - 1]} {leave_date.year}"
                
                leave_type = leave.get("Leave_Type", "").lower()
                leave_days = leave.get("Leave_Days", 0)
                
                if "sick" in leave_type:
                    leave_per_month[month_name]["sick"] += leave_days
                    total_leaves["sick"] += leave_days
                elif "casual" in leave_type:
                    leave_per_month[month_name]["casual"] += leave_days
                    total_leaves["casual"] += leave_days
                elif "annual" in leave_type:
                    leave_per_month[month_name]["annual"] += leave_days
                    total_leaves["annual"] += leave_days
                elif "unpaid" in leave_type:
                    leave_per_month[month_name]["unpaid"] += leave_days
                    total_leaves["unpaid"] += leave_days
                else:
                    leave_per_month[month_name]["other"] += leave_days
                    total_leaves["other"] += leave_days
        except Exception as e:
            logger.error(f"Error processing leave: {str(e)}")
            continue

    # Create ordered dictionary with only last 12 months
    ordered_leave_data = {
        month: leave_per_month[month]
        for month in ordered_months
    }

    return {
        "monthly_breakdown": ordered_leave_data,
        "total_leaves": dict(total_leaves)
    }


@router.get("/{employee_id}/summary")
async def get_employee_summary(employee_id: str, current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role_type"] != "hr":
            raise HTTPException(status_code=403, detail="Unauthorized to see the summary")

        # Get current time in IST
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = datetime.now(ist_tz)
        
        # Calculate date ranges
        vibe_start_date = current_ist - timedelta(days=14)  # Last 14 days for vibe trend
        activity_start_date = current_ist - timedelta(days=30)  # Last 30 days for activity
        one_year_ago = current_ist - timedelta(days=365)  # Last year for leaves and awards

        # Convert to UTC for database queries
        vibe_start_date_utc = vibe_start_date.astimezone(timezone.utc)
        activity_start_date_utc = activity_start_date.astimezone(timezone.utc)
        one_year_ago_utc = one_year_ago.astimezone(timezone.utc)
        
        performance_pipeline = [
            {
                '$match': {
                    'Employee_ID': employee_id
                }
            },
            {
                '$sort': {
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
                    },
                    'all_performances': {
                        '$push': {
                            'rating': '$Performance_Rating',
                            'feedback': '$Manager_Feedback',
                            'review_period': '$Review_Period'
                        }
                    }
                }
            }
        ]

        # Get all required data in parallel
        employee_data, user_data, vibe_data, latest_intent, activity_data, leave_data, rewards_data, latest_vibe, performance_data = await asyncio.gather(
            async_db["onboarding"].find_one({"Employee_ID": employee_id}),
            async_db["users"].find_one({"employee_id": employee_id}),
            async_db["vibemeter"].find({
                "Employee_ID": employee_id,
                "Response_Date": {"$gte": vibe_start_date_utc}
            }).sort("Response_Date", -1).to_list(length=None),
            async_db["intent_data"].find_one(
                {"employee_id": employee_id, "intent_data.chat_completed": True},
                sort=[("updated_at", -1)]
            ),
            async_db["activity"].find({
                "Employee_ID": employee_id,
                "Date": {"$gte": activity_start_date_utc}
            }).sort("Date", -1).to_list(length=None),
            async_db["leave"].find({
                "Employee_ID": employee_id,
                "Leave_Start_Date": {"$gte": one_year_ago_utc}
            }).sort("Leave_Start_Date", -1).to_list(length=None),
            async_db["rewards"].find({
                "Employee_ID": employee_id,
                "Award_Date": {"$gte": one_year_ago_utc}
            }).sort("Award_Date", -1).to_list(length=None),
            async_db["vibemeter"].find_one(
                {"Employee_ID": employee_id},
                sort=[("Response_Date", -1)]
            ),
            async_db["performance"].aggregate(performance_pipeline).to_list(length=None)
        )

        # Process performance data
        performance_info = {}
        if performance_data and len(performance_data) > 0:
            perf_doc = performance_data[0]
            latest_perf = perf_doc.get('latest_performance', {})
            all_perfs = perf_doc.get('all_performances', [])
            
            performance_info = {
                "current": {
                    "rating": latest_perf.get('rating'),
                    "feedback": latest_perf.get('feedback'),
                    "period": latest_perf.get('review_period')
                },
                "history": [
                    {
                        "rating": perf.get('rating'),
                        "feedback": perf.get('feedback'),
                        "period": perf.get('review_period')
                    } for perf in all_perfs
                ],
                "trend": {
                    "ratings": [perf.get('rating', 0) for perf in all_perfs],
                    "periods": [perf.get('review_period') for perf in all_perfs]
                }
            }

        # Process Current State
        current_state = {
            "vibe_score": latest_vibe.get("Vibe_Score", 0) if latest_vibe else 0,
            "last_check_in": convert_to_ist(latest_vibe.get("Response_Date")).isoformat() if latest_vibe else None,
            "risk_assessment": latest_intent.get("intent_data", {}).get("chat_analysis", {}).get("risk_assessment", {}).get("risk_level", 1) if latest_intent else 1
        }

        # Process Vibe Trend
        vibe_trend = [
            {
                "date": convert_to_ist(vibe.get("Response_Date")).isoformat(),
                "vibe_score": vibe.get("Vibe_Score", 0),
                "vibe": get_vibe(vibe.get("Vibe_Score", 0))
            } for vibe in vibe_data
        ] if vibe_data else []

        # Process Intent and Chat Analysis
        intent_analysis = {}
        chat_analysis = {}
        if latest_intent and "intent_data" in latest_intent:
            intent_data = latest_intent["intent_data"]
            intent_analysis = {
                "primary_issues": intent_data.get("primary_issues", {}),
                "tags": intent_data.get("tags", []),
                "updated_at": convert_to_ist(latest_intent.get("updated_at")).isoformat()
            }
            
            if "chat_analysis" in intent_data:
                chat_analysis = intent_data["chat_analysis"]

        # Process Communication Activity
        activity_analysis = process_activity_data(activity_data)

        # Process Leave Data (Last 12 months)
        leave_analysis = process_leave_data(leave_data, current_ist)

        # Process Awards (unique types)
        awards_data = {
            "total_points": sum(r.get("Reward_Points", 0) for r in rewards_data),
            "award_types": list(set(r.get("Award_Type") for r in rewards_data if r.get("Award_Type"))),
            "recent_awards": [
                {
                    "type": r.get("Award_Type"),
                    "date": convert_to_ist(r.get("Award_Date")).isoformat(),
                    "points": r.get("Reward_Points", 0)
                } for r in rewards_data[:5]  # Last 5 awards
            ]
        }

        # Compile final response
        response = {
            "employee_info": {
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "employee_id": employee_id,
                "joining_date": convert_to_ist(employee_data.get("Joining_Date")).isoformat() if employee_data and employee_data.get("Joining_Date") else None
            },
            "current_state": current_state,
            "vibe_trend": vibe_trend,
            "intent_analysis": intent_analysis,
            "chat_analysis": chat_analysis,
            "performance": performance_info,  # Added performance data
            "onboarding_experience": {
                "feedback": employee_data.get("Onboarding_Feedback") if employee_data else None,
                "mentor_assigned": employee_data.get("Mentor_Assigned", False) if employee_data else None,
                "training_completed": employee_data.get("Initial_Training_Completed", False) if employee_data else None,
            },
            "communication_activity": activity_analysis,
            "leave_analysis": leave_analysis,
            "awards_and_recognition": awards_data
        }

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_employee_summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching employee summary: {str(e)}")
    
@router.get("/employees/all")
async def get_all_employees(current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role_type"] != "hr":
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to see the summary"
            )
        
        # Modified vibe pipeline to ensure datetime handling
        vibe_pipeline = [
            {
                '$match': {
                    'Response_Date': {'$exists': True, '$ne': None}  # Ensure date exists
                }
            },
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
        
        # Get current time and calculate date ranges
        current_time = datetime.now(timezone.utc)
        seven_days_ago = current_time - timedelta(days=7)

        # Add pipeline for last 7 days vibe data
        seven_day_vibe_pipeline = [
            {
                '$match': {
                    'Response_Date': {
                        '$gte': seven_days_ago,
                        '$lte': current_time
                    }
                }
            },
            {
                '$sort': {
                    'Employee_ID': 1,
                    'Response_Date': -1
                }
            },
            {
                '$group': {
                    '_id': {
                        'employee_id': '$Employee_ID',
                        'date': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$Response_Date'
                            }
                        }
                    },
                    'vibe_score': { '$first': '$Vibe_Score' }
                }
            }
        ]
        
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

        # Modified intent pipeline
        intent_pipeline = [
            {
                '$match': {
                    'intent_data.chat_completed': True,
                    'updated_at': {'$exists': True, '$ne': None}  # Ensure date exists
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

        # Get all data in parallel
        users_data, vibe_data, seven_day_vibe_data, intent_data, performance_data = await asyncio.gather(
            async_db["users"].find({"role_type": "employee"}).to_list(length=None),
            async_db["vibemeter"].aggregate(vibe_pipeline).to_list(length=None),
            async_db["vibemeter"].aggregate(seven_day_vibe_pipeline).to_list(length=None),
            async_db["intent_data"].aggregate(intent_pipeline).to_list(length=None),
            async_db["performance"].aggregate(performance_pipeline).to_list(length=None)
        )

        # Create maps with safe defaults
        # Process maps as before...
        vibe_map = {doc['_id']: doc['latest_vibe'] for doc in vibe_data if doc.get('_id') and doc.get('latest_vibe')}
        intent_map = {doc['_id']: doc['latest_intent'] for doc in intent_data if doc.get('_id') and doc.get('latest_intent')}
        performance_map = {doc['_id']: doc['latest_performance'] for doc in performance_data if doc.get('_id')}

        # Initialize dashboard metrics
        total_risk_score = 0
        critical_cases = []
        total_employees = len(users_data)
        current_mood_scores = []
        mood_distribution = {
            "excited": 0,
            "happy": 0,
            "ok": 0,
            "sad": 0,
            "frustrated": 0
        }

        # Process daily mood trends
        daily_mood_trends = defaultdict(list)
        for vibe in seven_day_vibe_data:
            date = vibe['_id']['date']
            daily_mood_trends[date].append(vibe['vibe_score'])

        # Calculate weekly mood trend
        weekly_mood_trend = {
            date: round(sum(scores) / len(scores), 2)
            for date, scores in daily_mood_trends.items()
        }

        # Process each user
        processed_users = []
        for user in users_data:
            try:
                employee_id = user.get("employee_id")
                if not employee_id:
                    continue

                # Get info with safe defaults
                vibe_info = vibe_map.get(employee_id, {})
                intent_info = intent_map.get(employee_id, {})
                performance_info = performance_map.get(employee_id, {})

                # Safe datetime conversions
                vibe_date_utc = vibe_info.get("response_date")
                intent_date_utc = intent_info.get("updated_at")

                vibe_date_ist = convert_to_ist(vibe_date_utc)
                intent_date_ist = convert_to_ist(intent_date_utc)

                # Safe value extractions
                vibe_score = vibe_info.get("vibe_score", 0)
                intent_risk = intent_info.get("risk_level", 1)

                # Determine risk assessment with null safety
                risk_level = intent_risk
                if (vibe_score > 3 and 
                    vibe_date_ist is not None and 
                    intent_date_ist is not None and 
                    vibe_date_ist.date() > intent_date_ist.date()):
                    risk_level = 1
                    
                total_risk_score += risk_level
                if risk_level > 3:
                    critical_cases.append({
                        "employee_id": employee_id,
                        "email": user.get("email", ""),
                        "name": user.get("name", ""),
                        "role": user.get("role", "employee"),
                        "current_vibe": {
                            "score": vibe_score,
                            "last_check_in": vibe_date_ist.isoformat() if vibe_date_ist else None
                        },
                        "performance": {
                            "rating": performance_info.get("rating"),
                            "feedback": performance_info.get("feedback"),
                            "period": performance_info.get("review_period")
                        },
                        "risk_assessment": risk_level
                    })

                if vibe_score > 0:
                    current_mood_scores.append(vibe_score)
                    mood_distribution[get_vibe(vibe_score).lower()] += 1

                processed_users.append({
                    "employee_id": employee_id,
                    "email": user.get("email", ""),
                    "name": user.get("name", ""),
                    "role": user.get("role", "employee"),
                    "current_vibe": {
                        "score": vibe_score,
                        "last_check_in": vibe_date_ist.isoformat() if vibe_date_ist else None
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
            
        dashboard_metrics = {
            "timestamp": current_time,
            "overall_risk_score": round(total_risk_score / total_employees, 2) if total_employees > 0 else 0,
            "critical_cases_count": len(critical_cases),
            "critical_cases": critical_cases,
            "total_employees": total_employees,
            "overall_mood": round(sum(current_mood_scores) / len(current_mood_scores), 2) if current_mood_scores else 0,
            "mood_distribution": mood_distribution,
            "weekly_mood_trend": weekly_mood_trend
        }

        # Store dashboard metrics
        await async_db["admin_dashboard"].update_one(
            {"_id": "current"},
            {"$set": dashboard_metrics},
            upsert=True
        )

        return JSONResponse(content={
            "count": len(processed_users),
            "users": processed_users
        })

    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching user list"
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
        
        total_pages = (total_tickets + page_size - 1) // page_size

        cursor = async_db["tickets"].find({}).skip(skip).limit(page_size)
        tickets = await cursor.to_list(length=page_size)

        for ticket in tickets:
            ticket.pop("_id")
            ticket["date"] = convert_to_ist(ticket["date"]).date()

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