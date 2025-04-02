from datetime import UTC, datetime, timedelta  # Add timedelta to imports
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
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

# @router.get("/{employee_id}/summary")
# async def get_employee_dashboard(employee_id: str, current_user: dict = Depends(get_current_user)):
#     try:
#         def process_doc(doc):
#             if not doc:
#                 return {}
#             processed = {}
#             for key, value in doc.items():
#                 if key == '_id':
#                     processed[key] = str(value)
#                 elif isinstance(value, datetime):
#                     processed[key] = value.isoformat()
#                 else:
#                     processed[key] = value
#             return processed

#         # Helper function to classify vibes
#         def get_vibe(score):
#             if not isinstance(score, (int, float)):
#                 return "unknown"
#             if score > 4.5 and score <= 5:
#                 return "Excited"
#             elif score > 3.5 and score <= 4.5:
#                 return "Happy"
#             elif score > 2.5 and score <= 3.5:
#                 return "Okay"
#             elif score > 1.5 and score <= 2.5:
#                 return "Sad"
#             elif score >= 0 and score <= 1.5:
#                 return "Frustrated"
#             return "unknown"
        
#          # Process leave data per month for last 12 months
#         leave_per_month = defaultdict(lambda: defaultdict(int))
#         months = [
#             "January", "February", "March", "April", "May", "June",
#             "July", "August", "September", "October", "November", "December"
#         ]
        
#         # Get current date and calculate date 12 months ago
#         today = datetime.now()
#         twelve_months_ago = today - timedelta(days=365)

#         # Base employee data
#         employee_data = await async_db["onboarding"].find_one({"Employee_ID": employee_id})
#         if not employee_data:
#             raise HTTPException(status_code=404, detail="Employee not found")
        
#         # Get employee email (assuming it's stored in onboarding or users collection)
#         employee_email = employee_data.get('Email')  # Check onboarding first
#         if not employee_email:
#             user_data = await async_db["users"].find_one({"employee_id": employee_id})
#             employee_email = user_data.get('email') if user_data else None

#         # Get all data in parallel
#         leave_data, activity_data, vibe_data, rewards_data, performance_data = await asyncio.gather(
#             async_db["leave"].find({"Employee_ID": employee_id}).to_list(length=None),
#             async_db["activity"].find({"Employee_ID": employee_id}).to_list(length=None),
#             async_db["vibemeter"].find({"Employee_ID": employee_id}).to_list(length=None),
#             async_db["rewards"].find({"Employee_ID": employee_id}).to_list(length=None),
#             async_db["performance"].find({"Employee_ID": employee_id}).to_list(length=None)
#         )

#         #Process leave counts
        # leave_counts = defaultdict(int)
        # for leave in leave_data:
        #     leave_counts[leave['Leave_Type']] += leave['Leave_Days']

#         # Process mental states from vibe data
#         mental_states = defaultdict(int)
#         for vibe in vibe_data:
#             state = get_vibe(vibe.get('Vibe_Score'))
#             mental_states[state] += 1

        # # Process weekly communication activity
        # weekly_activity = defaultdict(lambda: defaultdict(int))
        # weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # # Process activity data (last 10 years)
        # recent_activity = [a for a in activity_data if 
        #                  (datetime.now() - a['Date']).days <= 3650] if activity_data else [] 

        # activity_stats = {
        #     "teams_messages_sent": int(sum(a['Teams_Messages_Sent'] for a in recent_activity)),
        #     "emails_sent": int(sum(a['Emails_Sent'] for a in recent_activity)),
        #     "meetings_attended": sum(a['Meetings_Attended'] for a in recent_activity),
        #     "work_hours": sum(a['Work_Hours'] for a in recent_activity),
        #     "data_points": len(recent_activity)
        # }
        
#         for activity in activity_data:
#             if 'Date' in activity and isinstance(activity['Date'], datetime):
#                 day = weekdays[activity['Date'].weekday()]
#                 weekly_activity[day]["teams_messages_sent"] += activity.get('Teams_Messages_Sent', 0)
#                 weekly_activity[day]["emails_sent"] += activity.get('Emails_Sent', 0)
#                 weekly_activity[day]["meetings_attended"] += activity.get('Meetings_Attended', 0)
#                 weekly_activity[day]["work_hours"] += activity.get('Work_Hours', 0)

#         # Calculate communication averages
#         avg_activity = {
#             "teams_messages_sent": round(sum(a.get('Teams_Messages_Sent', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
#             "emails_sent": round(sum(a.get('Emails_Sent', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
#             "meetings_attended": round(sum(a.get('Meetings_Attended', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0,
#             "work_hours": round(sum(a.get('Work_Hours', 0) for a in activity_data) / len(activity_data), 2) if activity_data else 0
#         }

#         # Process leave data per month
#         leave_per_month = defaultdict(int)
#         for leave in leave_data:
#             if 'Leave_Start_Date' in leave and isinstance(leave['Leave_Start_Date'], datetime):
#                 month = leave['Leave_Start_Date'].strftime('%Y-%m')
#                 leave_per_month[month] += leave.get('Leave_Days', 0)

#         for leave in leave_data:
#             if 'Leave_Start_Date' in leave and isinstance(leave['Leave_Start_Date'], datetime):
#                 leave_date = leave['Leave_Start_Date']
#                 if leave_date >= twelve_months_ago:
#                     month_num = leave_date.month
#                     month_name = months[month_num - 1]  # Convert to month name
#                     year = leave_date.year
#                     key = f"{month_name} {year}"
                    
#                     leave_type = leave.get('Leave_Type', 'other')
#                     if leave_type == 'Sick Leave':
#                         leave_per_month[key]['sick'] += leave.get('Leave_Days', 0)
#                     elif leave_type == 'Casual Leave':
#                         leave_per_month[key]['casual'] += leave.get('Leave_Days', 0)
#                     elif leave_type == 'Annual Leave':
#                         leave_per_month[key]['annual'] += leave.get('Leave_Days', 0)
#                     elif leave_type == 'Unpaid Leave':
#                         leave_per_month[key]['unpaid'] += leave.get('Leave_Days', 0)
#                     else:
#                         leave_per_month[key]['other'] += leave.get('Leave_Days', 0)

#         # Convert to regular dict and ensure all months have all categories
#         formatted_leave_per_month = {}
#         current_month = today.month
#         current_year = today.year
        
#         # Generate last 12 months in reverse chronological order
#         for i in range(12):
#             month_num = (current_month - 1 - i) % 12 + 1
#             year = current_year - (1 if (current_month - 1 - i) < 0 else 0)
#             month_name = months[month_num - 1]
#             key = f"{month_name} {year}"
            
#             formatted_leave_per_month[key] = {
#                 'sick': leave_per_month[key].get('sick', 0),
#                 'casual': leave_per_month[key].get('casual', 0),
#                 'annual': leave_per_month[key].get('annual', 0),
#                 'unpaid': leave_per_month[key].get('unpaid', 0),
#                 'other': leave_per_month[key].get('other', 0)
#             }

#         # Process performance rating month-wise
#         perf_per_month = defaultdict(list)
#         for perf in performance_data:
#             if 'Review_Period' in perf:
#                 # Assuming Review_Period is in format like "2023-01" or "Jan-2023"
#                 month = perf['Review_Period'][-7:]  # Get last 7 chars (for "Jan-2023" format)
#                 perf_per_month[month].append(perf.get('Performance_Rating', 0))
        
#         # Convert to average performance per month
#         avg_perf_per_month = {
#             month: round(sum(ratings)/len(ratings), 2) 
#             for month, ratings in perf_per_month.items()
#         }

#         # Process working hours month-wise
#         work_hours_per_month = defaultdict(list)
#         for activity in activity_data:
#             if 'Date' in activity and isinstance(activity['Date'], datetime):
#                 month = activity['Date'].strftime('%Y-%m')
#                 work_hours_per_month[month].append(activity.get('Work_Hours', 0))
        
#         avg_work_hours_per_month = {
#             month: round(sum(hours)/len(hours), 2) 
#             for month, hours in work_hours_per_month.items()
#         }

#         # Latest vibe data
#         latest_vibe = None
#         if vibe_data:
#             latest_vibe_data = sorted(vibe_data, key=lambda x: x.get('Response_Date', datetime.min), reverse=True)[0]
#             latest_vibe = {
#                 "vibe_score": latest_vibe_data.get('Vibe_Score'),
#                 "vibe": get_vibe(latest_vibe_data.get('Vibe_Score')),
#                 "response_date": latest_vibe_data.get('Response_Date').isoformat() 
#                     if isinstance(latest_vibe_data.get('Response_Date'), datetime) 
#                     else None
#             }

#         # Build comprehensive response
#         response = {
#             "employee_id": employee_id,
#             "email": employee_email,
#             "joining_date": employee_data.get('Joining_Date', '').isoformat(),
#             "leaves": {
#                 "sick": leave_counts.get('Sick Leave', 0),
#                 "casual": leave_counts.get('Casual Leave', 0),
#                 "annual": leave_counts.get('Annual Leave', 0),
#                 "unpaid": leave_counts.get('Unpaid Leave', 0),
#                 "other": sum(v for k,v in leave_counts.items() if k not in ['Sick Leave', 'Casual Leave', 'Annual Leave', "Unpaid Leave"]),
#                 "per_month": formatted_leave_per_month
#             },
#             "onboarding_data": {
#                 "feedback": employee_data.get('Onboarding_Feedback'),
#                 "mentor_assigned": employee_data.get('Mentor_Assigned', False),
#                 "training_completed": employee_data.get('Initial_Training_Completed', False)
#             },
#             "communication_activity": activity_stats,
#             "communication_activity_weekly": {day: dict(data) for day, data in weekly_activity.items()},
#             "communication_activity_average": avg_activity,
#             "vibemeter": latest_vibe,
#             "mental_states": dict(mental_states),
#             "rewards": {
#                 "total_points": sum(r.get('Reward_Points', 0) for r in rewards_data) if rewards_data else 0,
#                 "awards": [r.get('Award_Type') for r in rewards_data if r.get('Award_Type')]
#             },
#             "performance": process_doc(performance_data[0]) if performance_data else None,
#             "performance_rating_month_wise": avg_perf_per_month,
#             "working_hours_month_wise": avg_work_hours_per_month
#         }
        
#         return JSONResponse(content=response)
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching employee dashboard: {str(e)}"
#         )

@router.get("/{employee_id}/summary")
async def get_employee_dashboard(employee_id: str, current_user: dict = Depends(get_current_user)):
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
            "vibemeter": latest_vibe,
            "mental_states": dict(mental_states),
            "rewards": {
                "total_points": sum(r.get('Reward_Points', 0) for r in rewards_data) if rewards_data else 0,
                "awards": [r.get('Award_Type') for r in rewards_data if r.get('Award_Type')]
            },
            "performance": process_doc(performance_data[0]) if performance_data else None,
            "performance_rating_month_wise": avg_perf_per_month,
            "working_hours_month_wise": avg_work_hours_per_month
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
async def get_all_users(current_user: dict = Depends(get_current_user)):
    """
    Fetch details of all users in the system.
    Returns:
        - Basic user information
        - Onboarding status
        - Activity summary
    """
    try:
        # Get all users in parallel
        users_data, onboarding_data = await asyncio.gather(
            async_db["users"].find().to_list(length=None),
            async_db["onboarding"].find().to_list(length=None)
        )

        # Create mapping of employee_id to onboarding data
        onboarding_map = {o["Employee_ID"]: o for o in onboarding_data if "Employee_ID" in o}

        # Process each user
        processed_users = []
        for user in users_data:
            employee_id = user.get("employee_id")
            onboarding = onboarding_map.get(employee_id, {})
            
            processed_users.append({
                "employee_id": employee_id,
                "email": user.get("email"),
                "name": user.get("name", onboarding.get("Employee_Name")),
                "role": user.get("role", onboarding.get("Designation")),
                "department": onboarding.get("Department"),
                "joining_date": onboarding.get("Joining_Date", "").isoformat() 
                    if isinstance(onboarding.get("Joining_Date"), datetime) 
                    else None,
                "onboarding_completed": onboarding.get("Onboarding_Completed", False),
                "account_active": user.get("is_active", True)
            })

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
    
@router.get("/employees/all-detailed")
async def get_all_users_detailed(current_user: dict = Depends(get_current_user)):

    try:
        # Get all data in parallel
        users_data, onboarding_data, activity_data, vibe_data, performance_data = await asyncio.gather(
            async_db["users"].find().to_list(length=None),
            async_db["onboarding"].find().to_list(length=None),
            async_db["activity"].find().to_list(length=None),
            async_db["vibemeter"].find().to_list(length=None),
            async_db["performance"].find().to_list(length=None)
        )

        # Create mappings for faster lookup
        onboarding_map = {o["Employee_ID"]: o for o in onboarding_data if "Employee_ID" in o}
        activity_map = defaultdict(list)
        for a in activity_data:
            if "Employee_ID" in a:
                activity_map[a["Employee_ID"]].append(a)
        
        vibe_map = {}
        for v in vibe_data:
            if "Employee_ID" in v:
                # Keep only the latest vibe per employee
                if v["Employee_ID"] not in vibe_map or (
                    "Response_Date" in v and 
                    (v["Employee_ID"] not in vibe_map or 
                     v["Response_Date"] > vibe_map[v["Employee_ID"]].get("Response_Date", datetime.min))
                ):
                    vibe_map[v["Employee_ID"]] = v
        
        performance_map = {}
        for p in performance_data:
            if "Employee_ID" in p:
                # Keep only the latest performance review
                if p["Employee_ID"] not in performance_map or (
                    "Review_Date" in p and 
                    (p["Employee_ID"] not in performance_map or 
                     p["Review_Date"] > performance_map[p["Employee_ID"]].get("Review_Date", datetime.min))
                ):
                    performance_map[p["Employee_ID"]] = p

        # Process each user
        processed_users = []
        for user in users_data:
            employee_id = user.get("employee_id")
            onboarding = onboarding_map.get(employee_id, {})
            activities = activity_map.get(employee_id, [])
            latest_vibe = vibe_map.get(employee_id)
            latest_perf = performance_map.get(employee_id)
            
            # Calculate activity summaries
            recent_activities = [a for a in activities 
                               if "Date" in a and 
                               (datetime.now() - a["Date"]).days <= 30]  # Last 30 days
            
            activity_summary = {
                "teams_messages": sum(a.get("Teams_Messages_Sent", 0) for a in recent_activities),
                "emails_sent": sum(a.get("Emails_Sent", 0) for a in recent_activities),
                "meetings_attended": sum(a.get("Meetings_Attended", 0) for a in recent_activities),
                "avg_work_hours": round(sum(a.get("Work_Hours", 0) for a in recent_activities) / len(recent_activities), 2) 
                    if recent_activities else 0
            }
            
            processed_users.append({
                "employee_id": employee_id,
                "email": user.get("email"),
                "name": user.get("name", onboarding.get("Employee_Name")),
                "role": user.get("role", onboarding.get("Designation")),
                "department": onboarding.get("Department"),
                "status": "Active" if user.get("is_active", True) else "Inactive",
                "onboarding_status": "Completed" if onboarding.get("Onboarding_Completed") else "Pending",
                "last_activity": max(a["Date"] for a in activities).isoformat() 
                    if activities else None,
                "current_vibe": get_vibe(latest_vibe.get("Vibe_Score")) if latest_vibe else None,
                "performance_rating": latest_perf.get("Performance_Rating") if latest_perf else None,
                # "recent_activity": activity_summary
            })

        return JSONResponse(content={
            "count": len(processed_users),
            "users": sorted(processed_users, key=lambda x: x["name"] if x["name"] else "")
        })

    except Exception as e:
        logger.error(f"Error fetching detailed user list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user details: {str(e)}"
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