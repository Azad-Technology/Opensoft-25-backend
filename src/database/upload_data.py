import pandas as pd
from datetime import datetime
from utils.config import get_async_database
import asyncio
from faker import Faker

# Assuming these are your imports
from src.models.auth import UserCreate
from src.routers.auth import signup

async def preprocess_and_upload_data():
    # Initialize database connection
    async_db = get_async_database()
    
    # Helper function to convert date strings to datetime
    def convert_date(date_str):
        try:
            if isinstance(date_str, str):
                # Add more date formats, putting the expected format first
                formats = ['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            elif isinstance(date_str, datetime):
                return date_str
        except Exception as e:
            print(f"Error converting date: {date_str}, Error: {e}")
        return None

    # Load and preprocess vibemeter data
    vibemeter_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/vibemeter_dataset.csv')
    vibemeter_df['Response_Date'] = vibemeter_df['Response_Date'].apply(convert_date)
    vibemeter_data = vibemeter_df.to_dict('records')

    # Load and preprocess rewards data
    rewards_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/rewards_dataset.csv')
    rewards_df['Award_Date'] = rewards_df['Award_Date'].apply(convert_date)
    rewards_df['Reward_Points'] = rewards_df['Reward_Points'].astype(float)
    rewards_data = rewards_df.to_dict('records')

    # Load and preprocess performance data
    performance_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/performance_dataset.csv')
    performance_df['Performance_Rating'] = performance_df['Performance_Rating'].astype(float)
    performance_df['Promotion_Consideration'] = performance_df['Promotion_Consideration'].astype(bool)
    performance_data = performance_df.to_dict('records')

    # Load and preprocess onboarding data
    onboarding_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/onboarding_dataset.csv')
    onboarding_df['Joining_Date'] = onboarding_df['Joining_Date'].apply(convert_date)
    onboarding_df['Mentor_Assigned'] = onboarding_df['Mentor_Assigned'].astype(bool)
    onboarding_df['Initial_Training_Completed'] = onboarding_df['Initial_Training_Completed'].astype(bool)
    onboarding_data = onboarding_df.to_dict('records')

    # Load and preprocess leave data
    leave_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/leave_dataset.csv')
    leave_df['Leave_Start_Date'] = leave_df['Leave_Start_Date'].apply(convert_date)
    leave_df['Leave_End_Date'] = leave_df['Leave_End_Date'].apply(convert_date)
    leave_df['Leave_Days'] = leave_df['Leave_Days'].astype(float)
    leave_data = leave_df.to_dict('records')

    # Load and preprocess activity data
    activity_df = pd.read_csv('Opensoft-25-backend/src/analysis/data/activity_tracker_dataset.csv')
    activity_df['Date'] = activity_df['Date'].apply(convert_date)
    activity_df['Teams_Messages_Sent'] = activity_df['Teams_Messages_Sent'].astype(float)
    activity_df['Emails_Sent'] = activity_df['Emails_Sent'].astype(float)
    activity_df['Meetings_Attended'] = activity_df['Meetings_Attended'].astype(float)
    activity_df['Work_Hours'] = activity_df['Work_Hours'].fillna(0).astype(float)
    activity_data = activity_df.to_dict('records')

    # Upload to MongoDB
    try:
        # Clear existing collections
        await async_db.vibemeter.delete_many({})
        await async_db.rewards.delete_many({})
        await async_db.performance.delete_many({})
        await async_db.onboarding.delete_many({})
        await async_db.leave.delete_many({})
        await async_db.activity.delete_many({})

        # Insert new data
        if vibemeter_data:
            await async_db.vibemeter.insert_many(vibemeter_data)
        if rewards_data:
            await async_db.rewards.insert_many(rewards_data)
        if performance_data:
            await async_db.performance.insert_many(performance_data)
        if onboarding_data:
            await async_db.onboarding.insert_many(onboarding_data)
        if leave_data:
            await async_db.leave.insert_many(leave_data)
        if activity_data:
            await async_db.activity.insert_many(activity_data)

        print("Data upload completed successfully!")

    except Exception as e:
        print(f"Error uploading data: {e}")

fake = Faker()

async def create_bulk_employees():
    successful_creates = []
    failed_creates = []
    
    for i in range(1, 501):
        emp_id = f"EMP{str(i).zfill(4)}"
        
        # Create user data
        user_data = UserCreate(
            email=f"{emp_id}@deloitte.com",
            password="root",
            name=fake.name(),
            role="employee",
            employee_id=emp_id
        )
        
        try:
            # Call signup function directly
            await signup(user_data)
            successful_creates.append(emp_id)
            print(f"Successfully created employee: {emp_id}")
            
        except Exception as e:
            failed_creates.append(emp_id)
            print(f"Failed to create employee {emp_id}: {str(e)}")
            
    # Print summary
    print("\nCreation Summary:")
    print(f"Successfully created: {len(successful_creates)} employees")
    print(f"Failed to create: {len(failed_creates)} employees")
    
    if failed_creates:
        print("\nFailed Employee IDs:")
        print(failed_creates)
        
        
if __name__ == "__main__":
    
    asyncio.run(create_bulk_employees())
    
    # Upload data
    # asyncio.run(preprocess_and_upload_data())deloitte.com