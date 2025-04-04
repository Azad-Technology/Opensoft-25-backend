from datetime import datetime
import pandas as pd
from utils.config import get_async_database
import asyncio
from utils.app_logger import setup_logger

async_db = get_async_database()
logger = setup_logger("src/analysis/data_sample.py")

async def get_all_employees():
    """Get a list of all unique employee IDs across all collections"""
    logger.info("Fetching all unique employee IDs")
    
    all_employees = set()
    
    try:
        # Aggregate employee IDs from all collections
        collections = {
            'vibemeter': await async_db.vibemeter.distinct("Employee_ID"),
            'rewards': await async_db.rewards.distinct("Employee_ID"),
            'performance': await async_db.performance.distinct("Employee_ID"),
            'onboarding': await async_db.onboarding.distinct("Employee_ID"),
            'leave': await async_db.leave.distinct("Employee_ID"),
            'activity': await async_db.activity.distinct("Employee_ID")
        }
        
        for collection_name, employees in collections.items():
            logger.debug(f"Found {len(employees)} employees in {collection_name}")
            all_employees.update(employees)
        
        logger.info(f"Total unique employees found: {len(all_employees)}")
        return sorted(list(all_employees))
    except Exception as e:
        logger.error(f"Error getting employee IDs: {str(e)}")
        return []

async def create_employee_profile(employee_id: str) -> str:
    """Create a comprehensive profile for a single employee"""
    logger.info(f"Creating text profile for employee: {employee_id}")
    
    profile = f"Employee Profile for {employee_id}\n"
    try:
        # Basic Information
        employee_data = await async_db.users.find_one({"employee_id": employee_id})
        if employee_data:
            logger.debug(f"Found basic information for employee: {employee_id}")
            profile += f"Name: {employee_data['name']}\n\n"
        
        # Collect data from each collection
        collections_data = {
            'onboarding': await async_db.onboarding.find_one({"Employee_ID": employee_id}),
            'performance': await async_db.performance.find({"Employee_ID": employee_id}).to_list(length=None),
            'rewards': await async_db.rewards.find({"Employee_ID": employee_id}).to_list(length=None),
            'vibemeter': await async_db.vibemeter.find({"Employee_ID": employee_id}).to_list(length=None),
            'leave': await async_db.leave.find({"Employee_ID": employee_id}).to_list(length=None),
            'activity': await async_db.activity.find({"Employee_ID": employee_id}).to_list(length=None)
        }

        # Onboarding Information
        if collections_data['onboarding']:
            logger.debug(f"Adding onboarding information for: {employee_id}")
            profile += "Onboarding Information:\n"
            profile += f"Joining Date: {collections_data['onboarding']['Joining_Date']}\n"
            profile += f"Onboarding Feedback: {collections_data['onboarding']['Onboarding_Feedback']}\n"
            profile += f"Mentor Assigned: {collections_data['onboarding']['Mentor_Assigned']}\n"
            profile += f"Initial Training Completed: {collections_data['onboarding']['Initial_Training_Completed']}\n\n"
            
        # Vibe Meter Information
        vibe_cursor = async_db.vibemeter.find({"Employee_ID": employee_id})
        vibe_data = await vibe_cursor.to_list(length=None)
        if vibe_data:
            profile += "Vibe Meter Information:\n"
            for record in vibe_data:
                profile += f"Date: {record['Response_Date']}\n"
                profile += f"Vibe Score: {record['Vibe_Score']}\n\n"

        # Performance Information
        if collections_data['performance']:
            logger.debug(f"Adding performance information for: {employee_id}")
            profile += "Performance Information:\n"
            for record in collections_data['performance']:
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

        logger.info(f"Successfully created profile for employee: {employee_id} - {profile}")
        return profile

    except Exception as e:
        logger.error(f"Error creating profile for {employee_id}: {str(e)}", exc_info=True)
        raise e

async def get_employee_profile_json(employee_id: str) -> dict:
    """Create a JSON format profile for a single employee with limited recent data"""
    logger.info(f"Creating JSON profile for employee: {employee_id}")
    
    try:
        
        # Get all performance records and sort them manually
        all_performance = await async_db.performance.find(
            {"Employee_ID": employee_id},
            {"_id": 0}
        ).to_list(length=None)
        
        # Custom sorting function for performance periods
        def sort_performance(record):
            period = record["Review_Period"]
            year = int(period.split()[-1])
            half = 1 if "H1" in period else 2
            return (year, half)
        
        # Sort and get last 3 entries
        sorted_performance = sorted(
            all_performance,
            key=sort_performance,
            reverse=True
        )[:3]
        
        collections_data = {
            "employee_id": employee_id,
            "onboarding": await async_db.onboarding.find_one(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ),
            "vibemeter": await async_db.vibemeter.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).sort([("Response_Date", -1)]).limit(3).to_list(length=None),
            
            "performance": sorted_performance,  # Use manually sorted performance data
            
            "rewards": await async_db.rewards.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).sort([("Award_Date", -1)]).limit(3).to_list(length=None),
            
            "leave": await async_db.leave.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).sort([("Leave_Start_Date", -1)]).limit(3).to_list(length=None),
            
            "activity": await async_db.activity.find(
                {"Employee_ID": employee_id},
                {"_id": 0}
            ).sort([("Date", -1)]).limit(3).to_list(length=None),
            
            "analyzed_profile": await async_db.analyzed_profile.find_one(
                {"Employee_ID": employee_id},
                {"_id": 0},
                sort=[("timestamp", -1)]
            )
        }
        
        logger.debug(f"Calculating summary metrics for: {employee_id}")
        
        # Calculate summary metrics
        # summary = {}
        
        # if collections_data["vibemeter"]:
        #     summary["average_vibe_score"] = sum(v["Vibe_Score"] for v in collections_data["vibemeter"]) / len(collections_data["vibemeter"])
        #     summary["latest_vibe_score"] = collections_data["vibemeter"][0]["Vibe_Score"]
        #     summary["latest_vibe_date"] = collections_data["vibemeter"][0]["Response_Date"]
        
        # if collections_data["rewards"]:
        #     summary["recent_rewards"] = sum(r["Reward_Points"] for r in collections_data["rewards"])
        #     summary["latest_reward"] = {
        #         "type": collections_data["rewards"][0]["Award_Type"],
        #         "date": collections_data["rewards"][0]["Award_Date"]
        #     }
        
        # if collections_data["performance"]:
        #     summary["latest_performance"] = {
        #         "rating": collections_data["performance"][0]["Performance_Rating"],
        #         "feedback": collections_data["performance"][0]["Manager_Feedback"],
        #         "period": collections_data["performance"][0]["Review_Period"]
        #     }
        
        # if collections_data["leave"]:
        #     summary["recent_leave_days"] = sum(l["Leave_Days"] for l in collections_data["leave"])
        #     summary["latest_leave"] = {
        #         "days": collections_data["leave"][0]["Leave_Days"],
        #         "start_date": collections_data["leave"][0]["Leave_Start_Date"]
        #     }
        
        # if collections_data["activity"]:
        #     summary["recent_avg_work_hours"] = sum(a.get("Work_Hours", 0) for a in collections_data["activity"]) / len(collections_data["activity"])
        #     summary["latest_activity"] = {
        #         "work_hours": collections_data["activity"][0]["Work_Hours"],
        #         "date": collections_data["activity"][0]["Date"]
        #     }
        
        # if collections_data["onboarding"]:
        #     summary["onboarding_status"] = {
        #         "mentor_assigned": collections_data["onboarding"]["Mentor_Assigned"],
        #         "training_completed": collections_data["onboarding"]["Initial_Training_Completed"],
        #         "feedback": collections_data["onboarding"]["Onboarding_Feedback"]
        #     }
        
        # collections_data["summary"] = summary
        
        logger.info(f"Successfully created JSON profile for: {employee_id}")
        return collections_data

    except Exception as e:
        logger.error(f"Error creating JSON profile for {employee_id}: {str(e)}", exc_info=True)
        return {}

if __name__ == "__main__":
    async def main():
        logger.info("Starting profile generation test")
        
        sample_employee = 'EMP0454'
        
        try:
            # Text format
            logger.info("Generating text format profile")
            profile_text = await create_employee_profile(sample_employee)
            print("Text Format Profile:")
            print(profile_text)
            
            # JSON format
            logger.info("Generating JSON format profile")
            profile_json = await get_employee_profile_json(sample_employee)
            print("\nJSON Format Profile:")
            print(profile_json)
            
            logger.info("Profile generation test completed successfully")
            
        except Exception as e:
            logger.error(f"Error in profile generation test: {str(e)}", exc_info=True)

    asyncio.run(main())