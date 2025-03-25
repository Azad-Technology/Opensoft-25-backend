from datetime import datetime
import pandas as pd
from utils.config import get_async_database
import asyncio

async def get_all_employees():
    """Get a list of all unique employee IDs across all collections"""
    async_db = get_async_database()
    
    all_employees = set()
    
    # Aggregate employee IDs from all collections
    try:
        vibemeter_employees = await async_db.vibemeter.distinct("Employee_ID")
        rewards_employees = await async_db.rewards.distinct("Employee_ID")
        performance_employees = await async_db.performance.distinct("Employee_ID")
        onboarding_employees = await async_db.onboarding.distinct("Employee_ID")
        leave_employees = await async_db.leave.distinct("Employee_ID")
        activity_employees = await async_db.activity.distinct("Employee_ID")
        
        all_employees.update(vibemeter_employees)
        all_employees.update(rewards_employees)
        all_employees.update(performance_employees)
        all_employees.update(onboarding_employees)
        all_employees.update(leave_employees)
        all_employees.update(activity_employees)
        
        return sorted(list(all_employees))
    except Exception as e:
        print(f"Error getting employee IDs: {e}")
        return []

async def create_employee_profile(employee_id):
    """Create a comprehensive profile for a single employee"""
    async_db = get_async_database()
    
    profile = f"Employee Profile for {employee_id}\n"
    profile += "=" * 50 + "\n\n"

    try:
        # Onboarding Information
        onboarding_data = await async_db.onboarding.find_one({"Employee_ID": employee_id})
        if onboarding_data:
            profile += "Onboarding Information:\n"
            profile += f"Joining Date: {onboarding_data['Joining_Date']}\n"
            profile += f"Onboarding Feedback: {onboarding_data['Onboarding_Feedback']}\n"
            profile += f"Mentor Assigned: {onboarding_data['Mentor_Assigned']}\n"
            profile += f"Initial Training Completed: {onboarding_data['Initial_Training_Completed']}\n\n"

        # Performance Information
        performance_cursor = async_db.performance.find({"Employee_ID": employee_id})
        performance_data = await performance_cursor.to_list(length=None)
        if performance_data:
            profile += "Performance Information:\n"
            for record in performance_data:
                profile += f"Review Period: {record['Review_Period']}\n"
                profile += f"Performance Rating: {record['Performance_Rating']}\n"
                profile += f"Manager Feedback: {record['Manager_Feedback']}\n"
                profile += f"Promotion Consideration: {record['Promotion_Consideration']}\n\n"

        # Rewards Information
        rewards_cursor = async_db.rewards.find({"Employee_ID": employee_id})
        rewards_data = await rewards_cursor.to_list(length=None)
        if rewards_data:
            profile += "Rewards Information:\n"
            for record in rewards_data:
                profile += f"Date: {record['Award_Date']}\n"
                profile += f"Award Type: {record['Award_Type']}\n"
                profile += f"Reward Points: {record['Reward_Points']}\n\n"

        # Vibe Meter Information
        vibe_cursor = async_db.vibemeter.find({"Employee_ID": employee_id})
        vibe_data = await vibe_cursor.to_list(length=None)
        if vibe_data:
            profile += "Vibe Meter Information:\n"
            for record in vibe_data:
                profile += f"Date: {record['Response_Date']}\n"
                profile += f"Vibe Score: {record['Vibe_Score']}\n\n"

        # Leave Information
        leave_cursor = async_db.leave.find({"Employee_ID": employee_id})
        leave_data = await leave_cursor.to_list(length=None)
        if leave_data:
            profile += "Leave Information:\n"
            for record in leave_data:
                profile += f"Leave Type: {record['Leave_Type']}\n"
                profile += f"Duration: {record['Leave_Days']} days\n"
                profile += f"Period: {record['Leave_Start_Date']} to {record['Leave_End_Date']}\n\n"

        # Activity Information
        activity_cursor = async_db.activity.find({"Employee_ID": employee_id})
        activity_data = await activity_cursor.to_list(length=None)
        if activity_data:
            profile += "Activity Information:\n"
            for record in activity_data:
                profile += f"Date: {record['Date']}\n"
                profile += f"Teams Messages Sent: {record['Teams_Messages_Sent']}\n"
                profile += f"Emails Sent: {record['Emails_Sent']}\n"
                profile += f"Meetings Attended: {record['Meetings_Attended']}\n"
                profile += f"Work Hours: {record.get('Work_Hours', 'N/A')}\n\n"

        return profile

    except Exception as e:
        print(f"Error creating profile for {employee_id}: {e}")
        return f"Error creating profile for {employee_id}"

async def get_employee_profile_json(employee_id):
    """Create a JSON format profile for a single employee"""
    async_db = get_async_database()
    
    try:
        profile = {
            "employee_id": employee_id,
            "onboarding": await async_db.onboarding.find_one(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ),
            "performance": await async_db.performance.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).to_list(length=None),
            "rewards": await async_db.rewards.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).to_list(length=None),
            "vibemeter": await async_db.vibemeter.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).to_list(length=None),
            "leave": await async_db.leave.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).to_list(length=None),
            "activity": await async_db.activity.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).to_list(length=None)
        }
        
        # Calculate some summary metrics
        profile["summary"] = {
            "average_vibe_score": sum(v["Vibe_Score"] for v in profile["vibemeter"]) / len(profile["vibemeter"]) if profile["vibemeter"] else None,
            "total_rewards": sum(r["Reward_Points"] for r in profile["rewards"]) if profile["rewards"] else 0,
            "latest_performance": profile["performance"][-1] if profile["performance"] else None,
            "total_leave_days": sum(l["Leave_Days"] for l in profile["leave"]) if profile["leave"] else 0,
            "average_work_hours": sum(a.get("Work_Hours", 0) for a in profile["activity"]) / len(profile["activity"]) if profile["activity"] else None
        }
        
        return profile

    except Exception as e:
        print(f"Error creating JSON profile for {employee_id}: {e}")
        return None

if __name__ == "__main__":
    async def main():
        # Get all employee IDs
        # all_employees = await get_all_employees()
        # print(f"Total number of unique employees: {len(all_employees)}\n")

        # Create and print profile for a sample employee
        sample_employee = 'EMP0454'
        
        # Text format
        print("Text Format Profile:")
        profile_text = await create_employee_profile(sample_employee)
        print(profile_text)
        
        # JSON format
        print("\nJSON Format Profile:")
        profile_json = await get_employee_profile_json(sample_employee)
        print(profile_json)

    asyncio.run(main())