from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any, Optional

import pytz
from src.chatbot.chat_bot import is_chat_required
from src.models.dataset import ScheduleEntry, TicketEntry, VibeSubmission
from utils.analysis import get_project_details, get_vibe
from utils.app_logger import setup_logger
from utils.auth import get_current_user
from utils.config import get_async_database
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
import numpy as np
import asyncio
import uuid
from pydantic import BaseModel

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/employee.py")

@router.get("/dashboard")
async def get_employee_summary(current_user: dict = Depends(get_current_user)):
    try:
        employee_id = current_user["employee_id"]
        logger.info(f"Fetching dashboard data for employee ID: {employee_id}")
        # Get all data in parallel
        vibe_data, performance_data, activity_data, rewards_data, leave_data = await asyncio.gather(
            # Vibemeter - sort by Response_Date descending
            async_db["vibemeter"].find(
                {"Employee_ID": employee_id}
            ).sort("Response_Date", -1).to_list(length=None),
            
            # Performance - sort by Review_Period descending
            async_db["performance"].find(
                {"Employee_ID": employee_id}
            ).sort("Review_Period", -1).to_list(length=None),
            
            # Activity - sort by Date descending
            async_db["activity"].find(
                {"Employee_ID": employee_id}
            ).sort("Date", -1).to_list(length=None),
            
            # Rewards - sort by Award_Date descending
            async_db["rewards"].find(
                {"Employee_ID": employee_id}
            ).sort("Award_Date", -1).to_list(length=None),
            
            # Leave - sort by Leave_Start_Date descending
            async_db["leave"].find(
                {"Employee_ID": employee_id}
            ).sort("Leave_Start_Date", -1).to_list(length=None)
        )

        # Initialize with default values
        response = {
            "latest_vibe": {},
            "vibe_trend": [],
            "leave_balance": 20,  # Default leave balance
            "meetings_attended": 0,
            "performance_rating": [],
            "total_work_hours": 0,
            "average_work_hours": 0,
            "awards": [],
            "activity_level": [],
            "overall_activity_level": {
                "teams_messages_sent": 0,
                "emails_sent": 0,
                "meetings_attended": 0
            },
            "leaves": {},
            "all_leaves": [],
            "projects": get_project_details(),
            "is_chat_required": True
        }

        # Process Vibe Data if available
        if vibe_data and len(vibe_data) > 0:
            try:
                response["latest_vibe"] = {
                    "vibe_score": vibe_data[0].get("Vibe_Score", 0),
                    "date": vibe_data[0].get("Response_Date", datetime.now()).isoformat() 
                        if isinstance(vibe_data[0].get("Response_Date"), datetime) 
                        else datetime.now().isoformat()
                }

                response["vibe_trend"] = [
                    {
                        "date": vibe.get("Response_Date", datetime.now()).isoformat() 
                            if isinstance(vibe.get("Response_Date"), datetime) 
                            else datetime.now().isoformat(),
                        "vibe_score": vibe.get("Vibe_Score", 0),
                        "vibe": get_vibe(vibe.get("Vibe_Score", 0))
                    } for vibe in vibe_data
                ]
            except Exception as e:
                logger.error(f"Error processing vibe data: {str(e)}")

        # Process Performance Data if available
        if performance_data and len(performance_data) > 0:
            try:
                for performance in performance_data:
                    performance.pop("_id", None)
                response["performance_rating"] = performance_data
            except Exception as e:
                logger.error(f"Error processing performance data: {str(e)}")

        # Process Activity Data if available
        if activity_data and len(activity_data) > 0:
            try:
                recent_activity = [a for a in activity_data if 
                                isinstance(a.get('Date'), datetime) and
                                (datetime.now() - a.get('Date')).days <= 3650]
                
                response["activity_level"] = [
                    {
                        "date": activity.get("Date", datetime.now()).isoformat(),
                        "teamsMessages": activity.get("Teams_Messages_Sent", 0),
                        "emails": activity.get("Emails_Sent", 0),
                        "meetings": activity.get("Meetings_Attended", 0)
                    } for activity in activity_data
                ]

                if recent_activity:
                    total_work_hours = sum(a.get('Work_Hours', 0) for a in recent_activity)
                    response["total_work_hours"] = round(total_work_hours, 2)
                    response["average_work_hours"] = round(total_work_hours / len(recent_activity), 2)
                    
                    response["overall_activity_level"] = {
                        "teams_messages_sent": int(sum(a.get('Teams_Messages_Sent', 0) for a in recent_activity)),
                        "emails_sent": int(sum(a.get('Emails_Sent', 0) for a in recent_activity)),
                        "meetings_attended": int(sum(a.get('Meetings_Attended', 0) for a in recent_activity))
                    }
                    
                    response["meetings_attended"] = response["overall_activity_level"]["meetings_attended"]
            except Exception as e:
                logger.error(f"Error processing activity data: {str(e)}")

        # Process Rewards Data if available
        if rewards_data and len(rewards_data) > 0:
            try:
                response["awards"] = [
                    {
                        "type": reward.get('Award_Type', 'Unknown'),
                        "date": reward.get('Award_Date', datetime.now()).isoformat() 
                            if isinstance(reward.get('Award_Date'), datetime) 
                            else datetime.now().isoformat(),
                        "reward_points": reward.get('Reward_Points', 0)
                    } for reward in rewards_data
                ]
            except Exception as e:
                logger.error(f"Error processing rewards data: {str(e)}")
                
        # Get current time in UTC and IST
        current_utc = datetime.now(timezone.utc)
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = current_utc.astimezone(ist_tz)

        # Get latest vibe submission for this employee
        latest_vibe = await async_db.vibemeter.find_one(
            {"Employee_ID": current_user["employee_id"]},
            sort=[("Response_Date", -1)]
        )

        response["is_vibe_feedback_required"] = True
        # Check if already submitted today
        if latest_vibe and "Response_Date" in latest_vibe:
            latest_vibe_utc = latest_vibe["Response_Date"].replace(tzinfo=timezone.utc)
            latest_vibe_ist = latest_vibe_utc.astimezone(ist_tz)

            # Check if latest submission was on the same day (IST)
            if latest_vibe_ist.date() == current_ist.date():
                response["is_vibe_feedback_required"] = False

        # Process Leave Data if available
        if leave_data and len(leave_data) > 0:
            try:
                leave_counts = defaultdict(int)
                leave_info = []
                
                for leave in leave_data:
                    leave_type = leave.get('Leave_Type', 'other').lower().replace(' ', '_')
                    leave_counts[leave_type] += leave.get('Leave_Days', 0)
                    
                    leave_info.append({
                        'leave_start_date': leave.get('Leave_Start_Date', datetime.now()).isoformat() 
                            if isinstance(leave.get('Leave_Start_Date'), datetime) 
                            else datetime.now().isoformat(),
                        'leave_end_date': leave.get('Leave_End_Date', datetime.now()).isoformat() 
                            if isinstance(leave.get('Leave_End_Date'), datetime) 
                            else datetime.now().isoformat(),
                        'leave_days': leave.get('Leave_Days', 0),
                        'leave_type': leave.get('Leave_Type', 'other')
                    })

                response["leaves"] = dict(leave_counts)
                response["all_leaves"] = leave_info
                response["leave_balance"] = 20 - sum(leave_counts.values())  # Assuming 20 is total leave balance
                response["projects"] = get_project_details()
                response["is_chat_required"] = await is_chat_required(employee_id)
            except Exception as e:
                logger.error(f"Error processing leave data: {str(e)}")

        return JSONResponse(content=response)
    
    except Exception as e:
        logger.error(f"Error in get_employee_summary: {str(e)}")
        # Return default response structure even on error
        return JSONResponse(content={
            "latest_vibe": {},
            "vibe_trend": [],
            "leave_balance": 20,
            "meetings_attended": 0,
            "performance_rating": None,
            "total_work_hours": 0,
            "average_work_hours": 0,
            "awards": [],
            "activity_level": [],
            "overall_activity_level": {
                "teams_messages_sent": 0,
                "emails_sent": 0,
                "meetings_attended": 0
            },
            "leaves": {},
            "all_leaves": [],
            "projects": get_project_details(),
            "is_chat_required": True
        })
    
# Help & Support APIs
@router.get("/get_employee_tickets", summary="Get tickets created by an employee")
async def get_employee_tickets(current_user: dict = Depends(get_current_user)):
    try:
        employee_id = current_user["employee_id"]

        cursor = async_db["tickets"].find({
            "employee_id": employee_id,
        })

        tickets = await cursor.to_list(length=None)

        if not tickets:
            raise HTTPException(
                status_code=404,
                detail=f"No tickets found for employee {employee_id}"
            )
        
        for ticket in tickets:
            ticket.pop("_id")

        return {
            "employee_id": employee_id,
            "tickets": tickets
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tickets: {str(e)}"
        )


@router.post("/add_ticket", summary="Add a new ticket")
async def add_ticket(entry: TicketEntry, current_user: dict = Depends(get_current_user)):
    try:
        entry_dict = entry.model_dump()
        entry_dict['date'] = datetime.now().timestamp()
        entry_dict['employee_id'] = current_user["employee_id"]
        entry_dict['employee_name'] = current_user["name"]
        entry_dict['is_resolved'] = False
        entry_dict['ticket_id'] = str(uuid.uuid4())[:8]

        result = await async_db["tickets"].insert_one(entry_dict)
        return {"message": "Ticket entry added successfully", "id": str(result.inserted_id)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while adding the ticket: {str(e)}"
        )
        
@router.post("/submit_vibe")
async def submit_vibe(
    submission: VibeSubmission,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit vibe score for the day. Only one submission allowed per day (IST).
    """
    try:
        # Get current time in UTC and IST
        current_utc = datetime.now(timezone.utc)
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_ist = current_utc.astimezone(ist_tz)

        # Get latest vibe submission for this employee
        latest_vibe = await async_db.vibemeter.find_one(
            {"Employee_ID": current_user["employee_id"]},
            sort=[("Response_Date", -1)]
        )

        # Check if already submitted today
        if latest_vibe and "Response_Date" in latest_vibe:
            latest_vibe_utc = latest_vibe["Response_Date"].replace(tzinfo=timezone.utc)
            latest_vibe_ist = latest_vibe_utc.astimezone(ist_tz)

            # Check if latest submission was on the same day (IST)
            if latest_vibe_ist.date() == current_ist.date():
                raise HTTPException(
                    status_code=400,
                    detail="Vibe score already submitted today"

                )

        # Create new submission
        vibe_data = {
            "Employee_ID": current_user["employee_id"],
            "Employee_Name": current_user["name"],
            "Vibe_Score": submission.vibe_score,
            "Message": submission.message,
            "Response_Date": current_utc
        }

        # Insert into database
        result = await async_db.vibemeter.insert_one(vibe_data)

        if not result.inserted_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to save vibe submission"
            )

        return {
            "status": "success",
            "message": "Vibe score submitted successfully",
            "submission_time": current_ist.strftime('%I:%M %p IST'),
            "data": {
                "vibe_score": submission.vibe_score,
                "message": submission.message,
                "date": current_ist.strftime('%Y-%m-%d'),
                "time": current_ist.strftime('%I:%M %p IST')
            }
        }

    except Exception as e:
        logger.error(f"Error in vibe submission: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting vibe: {str(e)}"
        )

if __name__ == "__main__":
    pass

