import pandas as pd

def create_employee_time_series():
    # Load all datasets
    vibemeter_df = pd.read_csv('src/analysis/data/vibemeter_dataset.csv')
    rewards_df = pd.read_csv('src/analysis/data/rewards_dataset.csv')
    performance_df = pd.read_csv('src/analysis/data/performance_dataset.csv')
    onboarding_df = pd.read_csv('src/analysis/data/onboarding_dataset.csv')
    leave_df = pd.read_csv('src/analysis/data/leave_dataset.csv')
    activity_df = pd.read_csv('src/analysis/data/activity_tracker_dataset.csv')

    # Convert date columns to datetime
    date_columns = {
        'vibemeter_df': 'Response_Date',
        'rewards_df': 'Award_Date',
        'onboarding_df': 'Joining_Date',
        'leave_df': ['Leave_Start_Date', 'Leave_End_Date'],
        'activity_df': 'Date'
    }

    for df_name, columns in date_columns.items():
        df = globals()[df_name]
        if isinstance(columns, list):
            for col in columns:
                df[col] = pd.to_datetime(df[col])
        else:
            df[columns] = pd.to_datetime(df[columns])
    
    # Create a list of all dataframes with their timestamp columns
    dfs = [
        (vibemeter_df, 'Response_Date'),
        (rewards_df, 'Award_Date'),
        (performance_df, None),  # Performance doesn't have a clear timestamp
        (onboarding_df, 'Joining_Date'),
        (leave_df, 'Leave_Start_Date'),
        (activity_df, 'Date')
    ]

    # Add a source identifier to each dataframe
    for i, (df, time_col) in enumerate(dfs):
        df_copy = df.copy()
        df_copy['Data_Source'] = f'Source_{i}'
        if time_col:
            df_copy['Timestamp'] = df_copy[time_col]
        else:
            df_copy['Timestamp'] = pd.NaT
        dfs[i] = df_copy

    # Concatenate all dataframes vertically
    all_data = pd.concat([df for df in dfs], ignore_index=True)

    # Sort by Employee_ID and Timestamp
    all_data = all_data.sort_values(['Employee_ID', 'Timestamp'])

    return all_data

async def get_employee_profile(employee_id):
    
    # Create time series data
    employee_time_series = create_employee_time_series()
    
    profile = employee_time_series[employee_time_series['Employee_ID'] == employee_id]
    if profile.empty:
        return f"No data found for Employee {employee_id}"

    summary = f"Time Series Profile for {employee_id}:\n"

    # Process each record chronologically
    for _, row in profile.iterrows():
        source = row['Data_Source']
        timestamp = row['Timestamp'] if pd.notna(row['Timestamp']) else 'No Date'
        summary += f"\n{timestamp} - "

        if source == 'Source_0':  # Vibemeter
            summary += f"Vibe Meter\n"
            summary += f"  Score: {row['Vibe_Score']}\n"
            summary += f"  Emotion Zone: {row['Emotion_Zone']}\n"

        elif source == 'Source_1':  # Rewards
            summary += f"Reward\n"
            summary += f"  Type: {row['Award_Type']}\n"
            summary += f"  Points: {row['Reward_Points']}\n"

        elif source == 'Source_2':  # Performance
            summary += f"Performance Review\n"
            summary += f"  Period: {row['Review_Period']}\n"
            summary += f"  Rating: {row['Performance_Rating']}\n"
            summary += f"  Feedback: {row['Manager_Feedback']}\n"
            summary += f"  Promotion: {row['Promotion_Consideration']}\n"

        elif source == 'Source_3':  # Onboarding
            summary += f"Onboarding\n"
            summary += f"  Feedback: {row['Onboarding_Feedback']}\n"
            summary += f"  Mentor: {row['Mentor_Assigned']}\n"
            summary += f"  Training: {row['Initial_Training_Completed']}\n"

        elif source == 'Source_4':  # Leave
            summary += f"Leave\n"
            summary += f"  Type: {row['Leave_Type']}\n"
            summary += f"  Days: {row['Leave_Days']}\n"
            summary += f"  End: {row['Leave_End_Date']}\n"

        elif source == 'Source_5':  # Activity
            summary += f"Activity\n"
            summary += f"  Teams Messages: {row['Teams_Messages_Sent']}\n"
            summary += f"  Emails: {row['Emails_Sent']}\n"
            summary += f"  Meetings: {row['Meetings_Attended']}\n"
            summary += f"  Hours: {row['Work_Hours'] if pd.notna(row['Work_Hours']) else 'N/A'}\n"

    return summary

if __name__ == "__main__":
    
    # Get profile for a specific employee
    sample_employee = 'EMP0454'
    print(get_employee_profile(sample_employee))
