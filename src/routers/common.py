import random
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Dict, List, Any, Optional
from src.models.dataset import ScheduleEntry
from utils.analysis import MOCK_DATA, convert_to_ist, get_vibe
from utils.app_logger import setup_logger
from utils.auth import get_current_user, get_password_hash, verify_password
from utils.config import get_async_database
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
import numpy as np
import asyncio

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/common.py")

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Get employee profile information
    """
    try:
    
        employee_id = current_user.get("employee_id")
        # Get user data from database
        user = await async_db.users.find_one({"employee_id": employee_id})
        if not user:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Random selection for mock data
        random.seed(employee_id)  # Use employee_id as seed for consistent random data
        
        profile_data = {
            "name": user.get("name"),
            "profilePic": f"https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
            "employeeId": user.get("employee_id"),
            "jobTitle": user.get("role", "Consultant"),
            "department": random.choice(MOCK_DATA["departments"]),
            "doj": user.get("created_at", datetime.now()).strftime("%Y-%m-%d"),
            "location": random.choice(MOCK_DATA["locations"]),
            "manager": random.choice(MOCK_DATA["managers"]),
            "email": user.get("email"),
            "phone": f"+1 (555) {random.randint(100,999)}-{random.randint(1000,9999)}",
            "extension": str(random.randint(1000,9999)),
            
            "backgroundDetails": {
                "employmentType": "Full-time",
                "skills": random.sample(MOCK_DATA["skills"], 4),
                "certifications": random.sample(MOCK_DATA["certifications"], 3),
                "experience": [
                    {
                        "company": "Previous Tech Corp",
                        "role": "Technology Consultant",
                        "duration": "2019-2022"
                    },
                    {
                        "company": "Start-up Solutions",
                        "role": "Senior Developer",
                        "duration": "2017-2019"
                    }
                ],
                "education": [
                    {
                        "degree": "Master of Science in Computer Science",
                        "institution": "Stanford University",
                        "year": "2017"
                    },
                    {
                        "degree": "Bachelor of Engineering",
                        "institution": "MIT",
                        "year": "2015"
                    }
                ]
            },
            
            "documents": {
                "compliance": [
                    {
                        "name": "Code of Conduct",
                        "status": "Completed",
                        "date": (datetime.now()).strftime("%Y-%m-%d")
                    },
                    {
                        "name": "Data Privacy Training",
                        "status": "Due",
                        "date": (datetime.now()).strftime("%Y-%m-%d")
                    }
                ],
                "hrDocs": [
                    {
                        "name": "Offer Letter",
                        "type": "PDF",
                        "uploadDate": user.get("created_at", datetime.now()).strftime("%Y-%m-%d"),
                        "url": "https://example.com/docs/offer_letter.pdf"
                    },
                    {
                        "name": "Latest Payslip",
                        "type": "PDF",
                        "uploadDate": datetime.now().strftime("%Y-%m-%d"),
                        "url": "https://example.com/docs/payslip.pdf"
                    }
                ]
            }
        }

        return profile_data

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving profile information"
        )
        
        
@router.get("/get_schedules", summary="Get schedules for an employee by month/year")
async def get_schedules(date: date, current_user: dict = Depends(get_current_user)):
    try:
        employee_id = current_user["employee_id"]
        target_month = date.month
        target_year = date.year
        start_date = date.replace(day=1)
        if target_month == 12:
            end_date = date.replace(year=target_year + 1, month=1, day=1)
        else:
            end_date = date.replace(month=target_month + 1, day=1)

        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        query = {
            "employee_id": employee_id,
            "date": {"$gte": start_date_str, "$lt": end_date_str}
        }

        cursor = async_db["schedules"].find(query)
        schedules = await cursor.to_list(length=None)
        
        if not schedules:
            schedules = []
            
        for schedule in schedules:
            schedule.pop("_id")
            schedule["date"] = convert_to_ist(schedule["date"])
            
        return {
            "employee_id": employee_id,
            "month": target_month,
            "year": target_year,
            "schedules": schedules
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving schedules: {str(e)}"
        )

@router.post("/add_schedule", summary="Add a new schedule entry")
async def add_schedule_entry(entry: ScheduleEntry, current_user: dict = Depends(get_current_user)):
    try:
        entry_dict = entry.model_dump()
        entry_dict['date'] = entry.date.isoformat()
        entry_dict['employee_id'] = current_user["employee_id"]
        entry_dict["schedule_id"] = str(uuid.uuid4())[:8]

        result = await async_db["schedules"].insert_one(entry_dict)
        return {"message": "Schedule entry added successfully", "id": str(result.inserted_id)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while adding the schedule entry: {str(e)}"
        )
        
@router.delete("/delete_schedule/{schedule_id}", summary="Delete a schedule entry")
async def delete_schedule(current_user: dict = Depends(get_current_user), schedule_id: str = None):
    try:
        if not schedule_id:
            raise HTTPException(
                status_code=400,
                detail="Schedule ID is required for deletion"
            )

        query = {
            "schedule_id": schedule_id,
            "employee_id": current_user["employee_id"]
        }

        result = await async_db["schedules"].delete_one(query)

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule entry with ID {schedule_id} not found"
            )

        return {"message": f"Schedule entry {schedule_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the schedule entry: {str(e)}"
        )
        
@router.post("/reset_password")
async def reset_password(
    current_user: dict = Depends(get_current_user),
    old_password: str = Body(...),
    new_password: str = Body(...),
    confirm_password: str = Body(...)
):
    """
    Reset user password after verifying old password
    """
    try:
        # Verify new password matches confirmation
        if new_password != confirm_password:
            raise HTTPException(
                status_code=400,
                detail="New password and confirmation do not match"
            )

        # Verify old password is correct
        user = await async_db.users.find_one({"employee_id": current_user["employee_id"]})
        if not user or not verify_password(old_password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect old password"
            )

        # Verify new password is different from old password
        if verify_password(new_password, user["password"]):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from old password"
            )

        # Update password in database
        hashed_password = get_password_hash(new_password)
        await async_db.users.update_one(
            {"employee_id": current_user["employee_id"]},
            {"$set": {
                "password": hashed_password,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        return JSONResponse(content={
            "status": "success",
            "message": "Password updated successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Password reset error for {current_user['employee_id']}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while resetting password"
        )