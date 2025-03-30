from fastapi import APIRouter, Depends, HTTPException
from utils.analysis import get_vibe
from utils.app_logger import setup_logger
from utils.auth import get_current_user
from utils.config import get_async_database
from fastapi.responses import JSONResponse
from datetime import datetime
from collections import defaultdict
import numpy as np
import asyncio

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/admin_analysis.py")

@router.get("/{employee_id}/summary")
async def get_employee_dashboard(employee_id: str, current_user: dict = Depends(get_current_user)):
    try:
        # Base employee data (from onboarding collection)
        employee_data = await async_db["onboarding"].find_one({"Employee_ID": employee_id})
        if not employee_data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Convert MongoDB document to serializable format
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
        
        # Get all data in parallel
        leave_data, activity_data, vibe_data, rewards_data, performance_data = await asyncio.gather(
            async_db["leave"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["activity"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["vibemeter"].find({"Employee_ID": employee_id})
                         .sort("Response_Date", -1)  
                         .limit(1)  
                         .to_list(length=None),
            async_db["rewards"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["performance"].find({"Employee_ID": employee_id}).to_list(length=None)
        )
        
        # Process leave data
        leave_counts = defaultdict(int)
        for leave in leave_data:
            leave_counts[leave['Leave_Type']] += leave['Leave_Days']
        
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
        
        # Determining latest vibe
        
        latest_vibe = None
        if vibe_data and len(vibe_data) > 0:
            latest_vibe = {
                "vibe_score": vibe_data[0].get('Vibe_Score'),
                "emotion_zone": vibe_data[0].get('Emotion_Zone'),
                "response_date": vibe_data[0].get('Response_Date').isoformat() 
                    if isinstance(vibe_data[0].get('Response_Date'), datetime) 
                    else None
            }
        
        # Build response
        response = {
            "joining_date": employee_data.get('Joining_Date', '').isoformat(),
            "leaves": {
                "sick": leave_counts.get('Sick Leave', 0),
                "casual": leave_counts.get('Casual Leave', 0),
                "annual": leave_counts.get('Annual Leave', 0),
                "unpaid": leave_counts.get('Unpaid Leave', 0),
                "other": sum(v for k,v in leave_counts.items() if k not in ['Sick Leave', 'Casual Leave', 'Annual Leave', "Unpaid Leave"])
            },
            "onboarding_data": {
                "feedback": employee_data.get('Onboarding_Feedback'),
                "mentor_assigned": employee_data.get('Mentor_Assigned', False),
                "training_completed": employee_data.get('Initial_Training_Completed', False)
            },
            "communication_activity": activity_stats,
            "vibemeter": latest_vibe,
            "rewards": {
                "total_points": sum(r['Reward_Points'] for r in rewards_data) if rewards_data else 0,
                "awards": [r['Award_Type'] for r in rewards_data] if rewards_data else []
            },
            "performance": process_doc(performance_data[0]) if performance_data else None
        }
        
        return JSONResponse(content=response)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching employee dashboard: {str(e)}"
        )