from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any, Optional
from utils.analysis import get_vibe
from utils.app_logger import setup_logger
from utils.auth import get_current_user
from utils.config import get_async_database
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import asyncio

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/employee.py")

@router.get("/vibescore-trend", summary="Get vibe score trends over time")
async def get_vibescore_trend(time_period: str = "monthly", limit: int = 12):
    """
    Get average vibe score trends over time.
    
    Parameters:
    - time_period: "daily", "weekly", or "monthly" aggregation
    - limit: number of periods to return
    """
    try:
        cursor = async_db["vibemeter"].find({})
        documents = await cursor.to_list(length=None)
        
        if not documents:
            return {"message": "No vibe score data available"}
        
        df = pd.DataFrame(documents)
        df['Response_Date'] = pd.to_datetime(df['Response_Date'])
        
        # Group by time period
        if time_period == "daily":
            df['period'] = df['Response_Date'].dt.date
            group_col = 'period'
        elif time_period == "weekly":
            df['period'] = df['Response_Date'].dt.strftime('%Y-%U')
            group_col = 'period'
        else:  # monthly
            df['period'] = df['Response_Date'].dt.strftime('%Y-%m')
            group_col = 'period'
        
        result = df.groupby(group_col)['Vibe_Score'].agg(['mean', 'count']).reset_index()
        result = result.sort_values(group_col).tail(limit)
        
        return JSONResponse(content=result.to_dict(orient='records'))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee-performance", summary="Get employee performance analytics")
async def get_employee_performance(employee_id: Optional[str] = None):
    """
    Get performance analytics for all employees or a specific employee.
    
    Parameters:
    - employee_id: Optional employee ID to filter for a specific employee
    """
    try:
        match_filter = {"Employee_ID": employee_id} if employee_id else {}

        # Process performance data
        perf_cursor = async_db["performance"].find(match_filter)
        perf_data = await perf_cursor.to_list(length=None)
        
        if not perf_data:
            return {"message": "No performance data available"}

        # Convert ObjectId and datetime fields for performance data
        processed_perf = []
        for doc in perf_data:
            doc['_id'] = str(doc['_id'])
            # Add datetime conversion if you have datetime fields in performance
            processed_perf.append(doc)

        # Process rewards data
        rewards_cursor = async_db["rewards"].find(match_filter)
        rewards_data = await rewards_cursor.to_list(length=None)
        
        # Convert ObjectId and datetime fields for rewards data
        processed_rewards = []
        for doc in rewards_data:
            doc['_id'] = str(doc['_id'])
            if 'Award_Date' in doc:
                doc['Award_Date'] = doc['Award_Date'].isoformat()
            processed_rewards.append(doc)

        # Convert to DataFrames
        perf_df = pd.DataFrame(processed_perf)
        rewards_df = pd.DataFrame(processed_rewards) if processed_rewards else pd.DataFrame()

        # Basic performance stats
        if employee_id:
            result = {
                "employee_id": employee_id,
                "performance_rating_avg": perf_df['Performance_Rating'].mean(),
                "promotion_consideration_rate": perf_df['Promotion_Consideration'].mean(),
                "total_rewards_points": rewards_df['Reward_Points'].sum() if not rewards_df.empty else 0,
                "award_count": len(rewards_df) if not rewards_df.empty else 0,
                "performance_reviews": perf_df.replace({np.nan: None}).to_dict(orient='records')
            }
        else:
            # Aggregate for all employees
            result = {
                "avg_performance_rating": perf_df['Performance_Rating'].mean(),
                "promotion_consideration_rate": perf_df['Promotion_Consideration'].mean(),
                "performance_rating_distribution": perf_df['Performance_Rating'].value_counts().astype(int).to_dict(),
                "top_performers": perf_df.nlargest(5, 'Performance_Rating').replace({np.nan: None}).to_dict(orient='records')
            }

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leave-analysis", summary="Get leave pattern analytics")
async def get_leave_analysis(leave_type: Optional[str] = None):
    """
    Analyze leave patterns across the organization.
    
    Parameters:
    - leave_type: Optional filter for specific leave type
    """
    try:
        match_filter = {"Leave_Type": leave_type} if leave_type else {}
        
        cursor = async_db["leave"].find(match_filter)
        documents = await cursor.to_list(length=None)
        
        if not documents:
            return {"message": "No leave data available"}
        
        df = pd.DataFrame(documents)
        
        # Convert dates
        df['Leave_Start_Date'] = pd.to_datetime(df['Leave_Start_Date'])
        df['Leave_End_Date'] = pd.to_datetime(df['Leave_End_Date'])
        
        # Calculate leave duration
        df['duration'] = (df['Leave_End_Date'] - df['Leave_Start_Date']).dt.days + 1
        
        result = {
            "total_leave_days": df['Leave_Days'].sum(),
            "avg_leave_duration": df['duration'].mean(),
            "leave_type_distribution": df['Leave_Type'].value_counts().to_dict(),
            "monthly_leave_trend": df.groupby(df['Leave_Start_Date'].dt.strftime('%Y-%m'))['Leave_Days'].sum().to_dict(),
            "employees_with_most_leave": df.groupby('Employee_ID')['Leave_Days'].sum().nlargest(5).to_dict()
        }
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/onboarding-success", summary="Get onboarding success metrics")
async def get_onboarding_success():
    """
    Analyze onboarding success rates and patterns.
    """
    try:
        cursor = async_db["onboarding"].find({})
        documents = await cursor.to_list(length=None)
        
        if not documents:
            return {"message": "No onboarding data available"}
        
        df = pd.DataFrame(documents)
        
        result = {
            "mentor_assignment_rate": df['Mentor_Assigned'].mean(),
            "training_completion_rate": df['Initial_Training_Completed'].mean(),
            "feedback_distribution": df['Onboarding_Feedback'].value_counts().to_dict(),
            "feedback_vs_training": pd.crosstab(df['Onboarding_Feedback'], df['Initial_Training_Completed']).to_dict(),
            "feedback_vs_mentor": pd.crosstab(df['Onboarding_Feedback'], df['Mentor_Assigned']).to_dict()
        }
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee-activity", summary="Get employee activity patterns")
async def get_employee_activity(time_period: str = "daily", employee_id: Optional[str] = None):
    """
    Analyze employee activity patterns.
    
    Parameters:
    - time_period: "daily", "weekly", or "monthly" aggregation
    - employee_id: Optional filter for specific employee
    """
    try:
        match_filter = {"Employee_ID": employee_id} if employee_id else {}
        
        cursor = async_db["activity"].find(match_filter)
        documents = await cursor.to_list(length=None)
        
        if not documents:
            return {"message": "No activity data available"}

        # Convert MongoDB documents to serializable format
        processed_docs = []
        for doc in documents:
            new_doc = {}
            for key, value in doc.items():
                if key == '_id':
                    new_doc[key] = str(value)
                elif isinstance(value, datetime):
                    new_doc[key] = value.isoformat()
                else:
                    new_doc[key] = value
            processed_docs.append(new_doc)
        
        df = pd.DataFrame(processed_docs)
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Group by time period
        if time_period == "daily":
            df['period'] = df['Date'].dt.date
            group_col = 'period'
        elif time_period == "weekly":
            df['period'] = df['Date'].dt.strftime('%Y-%U')
            group_col = 'period'
        else:  # monthly
            df['period'] = df['Date'].dt.strftime('%Y-%m')
            group_col = 'period'
        
        # Aggregate metrics
        agg_df = df.groupby(group_col).agg({
            'Teams_Messages_Sent': 'mean',
            'Emails_Sent': 'mean',
            'Meetings_Attended': 'mean',
            'Work_Hours': 'mean'
        }).reset_index()
        
        # Calculate productivity score (example metric)
        agg_df['productivity_score'] = (
            agg_df['Teams_Messages_Sent'] * 0.2 +
            agg_df['Emails_Sent'] * 0.2 +
            agg_df['Meetings_Attended'] * 0.3 +
            agg_df['Work_Hours'] * 0.3
        )
        
        # Convert date objects to strings in the final result
        result = agg_df.sort_values(group_col)
        
        # Handle different period types
        if time_period == "daily":
            result['period'] = result['period'].astype(str)
        elif time_period == "weekly":
            result['period'] = result['period'].astype(str)
        else:  # monthly
            result['period'] = result['period'].astype(str)
        
        # Replace NaN values with None for JSON serialization
        result = result.replace({np.nan: None}).to_dict(orient='records')
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee-correlation", summary="Find correlations between different metrics")
async def get_employee_correlation():
    """
    Find correlations between different employee metrics across collections.
    """
    try:
        # Get data from all relevant collections
        vibes = await async_db["vibemeter"].find({}).to_list(length=None)
        performance = await async_db["performance"].find({}).to_list(length=None)
        activity = await async_db["activity"].find({}).to_list(length=None)
        rewards = await async_db["rewards"].find({}).to_list(length=None)
        
        if not vibes or not performance or not activity:
            return {"message": "Insufficient data for correlation analysis"}

        # Convert MongoDB documents to serializable format
        def process_documents(docs):
            processed = []
            for doc in docs:
                new_doc = {}
                for key, value in doc.items():
                    if key == '_id':
                        new_doc[key] = str(value)
                    elif isinstance(value, datetime):
                        new_doc[key] = value.isoformat()
                    else:
                        new_doc[key] = value
                processed.append(new_doc)
            return processed

        vibes_processed = process_documents(vibes)
        perf_processed = process_documents(performance)
        activity_processed = process_documents(activity)
        rewards_processed = process_documents(rewards) if rewards else []
        
        # Create DataFrames
        vibes_df = pd.DataFrame(vibes_processed)
        perf_df = pd.DataFrame(perf_processed)
        activity_df = pd.DataFrame(activity_processed)
        rewards_df = pd.DataFrame(rewards_processed) if rewards_processed else pd.DataFrame()
        
        # Aggregate data by employee
        employee_vibes = vibes_df.groupby('Employee_ID')['Vibe_Score'].mean().reset_index()
        employee_perf = perf_df.groupby('Employee_ID')['Performance_Rating'].mean().reset_index()
        
        employee_activity = activity_df.groupby('Employee_ID').agg({
            'Teams_Messages_Sent': 'mean',
            'Emails_Sent': 'mean',
            'Meetings_Attended': 'mean',
            'Work_Hours': 'mean'
        }).reset_index()
        
        if not rewards_df.empty:
            employee_rewards = rewards_df.groupby('Employee_ID')['Reward_Points'].sum().reset_index()
        else:
            employee_rewards = pd.DataFrame(columns=['Employee_ID', 'Reward_Points'])
        
        # Merge all data
        merged = employee_vibes.merge(employee_perf, on='Employee_ID', how='left')
        merged = merged.merge(employee_activity, on='Employee_ID', how='left')
        
        if not employee_rewards.empty:
            merged = merged.merge(employee_rewards, on='Employee_ID', how='left')
        
        # Calculate correlations and handle NaN values
        numeric_cols = merged.select_dtypes(include=[np.number]).columns
        corr_matrix = merged[numeric_cols].corr()
        
        # Replace NaN with None for JSON serialization
        corr_matrix = corr_matrix.where(pd.notnull(corr_matrix), None)
        
        # Get top correlations
        corr_pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                col1 = numeric_cols[i]
                col2 = numeric_cols[j]
                corr_value = corr_matrix.loc[col1, col2]
                if corr_value is not None:
                    corr_pairs.append({
                        "metric1": col1,
                        "metric2": col2,
                        "correlation": float(corr_value)  # Ensure native float type
                    })
        
        # Sort by absolute correlation value
        corr_pairs = sorted(corr_pairs, key=lambda x: abs(x['correlation']), reverse=True)
        
        return JSONResponse(content={
            "correlation_matrix": corr_matrix.to_dict(),
            "top_correlations": corr_pairs[:10],
            "merged_metrics_sample": merged.head(5).replace({np.nan: None}).to_dict(orient='records')
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/total-employees", summary="Get total number of unique employees")
async def get_total_employees():
    """
    Returns the count of unique employees across all collections.
    """
    try:
        # Collections that contain employee data
        collections = ["vibemeter", "rewards", "performance", "onboarding", "leave", "activity"]
        employee_ids = set()

        for collection in collections:
            # Get distinct employee IDs from each collection
            ids = await async_db[collection].distinct("Employee_ID")
            employee_ids.update(ids)

        total_employees = len(employee_ids)

        return {
            "total_employees": total_employees,
            "collections_analyzed": collections,
            "note": "Count represents unique Employee_IDs across all specified collections"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating total employees: {str(e)}"
        )
    
@router.get("/employee-mood", summary="Get overall employee mood analysis")
async def get_employee_mood(time_period: str = "monthly", last_n: int = 3):
    """
    Analyze and return overall employee mood based on vibe scores.
    
    Parameters:
    - time_period: "daily", "weekly", or "monthly" aggregation
    - last_n: Number of recent periods to analyze (default: 3 months/weeks/days)
    """
    try:
        # Get vibe data
        cursor = async_db["vibemeter"].find({})
        documents = await cursor.to_list(length=None)
        
        if not documents:
            return {"message": "No vibe data available"}
        
        # Process data
        df = pd.DataFrame(documents)
        df['Response_Date'] = pd.to_datetime(df['Response_Date'])
        
        # Group by time period
        if time_period == "daily":
            df['period'] = df['Response_Date'].dt.date
        elif time_period == "weekly":
            df['period'] = df['Response_Date'].dt.strftime('%Y-%U')
        else:  # monthly
            df['period'] = df['Response_Date'].dt.strftime('%Y-%m')
        
        # Get most recent periods
        unique_periods = sorted(df['period'].unique(), reverse=True)[:last_n]
        df = df[df['period'].isin(unique_periods)]
        
        # Calculate mood metrics
        mood_analysis = {
            "average_score": round(df['Vibe_Score'].mean(), 2),
            "score_distribution": df['Vibe_Score'].value_counts().to_dict(),
            "trend": "improving" if df.groupby('period')['Vibe_Score'].mean().is_monotonic_increasing else "declining",
            "mood_classification": classify_mood(df['Vibe_Score'].mean()),
            "periods_analyzed": unique_periods,
            "time_period": time_period,
            "total_responses": len(df)
        }
        
        # Add period-wise breakdown
        period_stats = df.groupby('period').agg({
            'Vibe_Score': ['mean', 'count']
        }).reset_index()
        period_stats.columns = ['period', 'average_score', 'response_count']
        mood_analysis['period_details'] = period_stats.to_dict(orient='records')
        
        return JSONResponse(content=mood_analysis)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing employee mood: {str(e)}"
        )

def classify_mood(average_score: float) -> str:
    """Classify overall mood based on average vibe score"""
    if average_score >= 4.5:
        return "Excellent"
    elif average_score >= 3.5:
        return "Good"
    elif average_score >= 2.5:
        return "Neutral"
    elif average_score >= 1.5:
        return "Poor"
    else:
        return "Concerning"

@router.get("/dashboard")
async def get_employee_summary(current_user: dict = Depends(get_current_user)):
    try:
        employee_id = current_user["employee_id"]
        # Get all data in parallel
        vibe_data, performance_data, activity_data, rewards_data, leave_data = await asyncio.gather(
            async_db["vibemeter"].find({"Employee_ID": employee_id}).sort("Response_Date", -1).to_list(length=None),
            async_db["performance"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["activity"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["rewards"].find({"Employee_ID": employee_id}).to_list(length=None),
            async_db["leave"].find({"Employee_ID": employee_id}).to_list(length=None)
        )

        latest_vibe = None
        if vibe_data:
            latest_vibe = {
                    "vibe_score": vibe_data[0].get("Vibe_Score"),
                    "date": vibe_data[0].get("Response_Date").isoformat() 
                        if isinstance(vibe_data[0].get("Response_Date"), datetime) 
                        else None
                }

            vibe_trend = []
            for vibe in vibe_data:
                try:
                    response_date = vibe.get("Response_Date")
                    if isinstance(response_date, datetime):
                        response_date = response_date.isoformat()
                    
                    curr_vibe = {
                        "date": response_date,
                        "vibe_score": vibe.get("Vibe_Score"),
                        "vibe": get_vibe(vibe.get("Vibe_Score"))
                    }
                        
                    vibe_trend.append(curr_vibe)
                except Exception as e:
                    print(f"Skipping malformed vibe record: {e}")

        # Process performance data
        performance_rating = None
        if performance_data:
            performance_rating = performance_data[0].get('Performance_Rating')

        # Process activity data (last 10 years)
        recent_activity = None
        activities = []
        if activity_data:
            recent_activity = [a for a in activity_data if 
                            (datetime.now() - a.get('Date', datetime.now())).days <= 3650]
            
            for activity in activity_data:
                curr_activity = {
                    "date": activity.get("Date").isoformat(),
                    "teamsMessages": activity.get("Teams_Messages_Sent"),
                    "emails": activity.get("Emails_Sent"),
                    "meetings": activity.get("Meetings_Attended")
                }
                activities.append(curr_activity)
            total_work_hours = sum(a.get('Work_Hours', 0) for a in recent_activity)
            average_work_hours = total_work_hours / len(recent_activity)
        
        # Process rewards data
        awards = []
        if rewards_data:
            for reward in rewards_data:
                award_info = {
                    "type": reward.get('Award_Type'),
                    "date": reward.get('Award_Date').isoformat() 
                        if isinstance(reward.get('Award_Date'), datetime) 
                        else None,
                    "reward_points": reward.get('Reward_Points'),
                }
                # if award_info['award_type']:  # Only include if award_type exists
                awards.append(award_info)

        # Process leave data
        leave_counts = defaultdict(int)
        leave_info = []
        if leave_data:
            for leave in leave_data:
                leave_type = leave.get('Leave_Type', 'other').lower().replace(' ', '_')
                leave_counts[leave_type] += leave.get('Leave_Days', 0)
                info = {
                    'leave_start_date' : leave.get('Leave_Start_Date').isoformat(),
                    'leave_end_date' : leave.get('Leave_End_Date').isoformat(),
                    'leave_days' : leave.get('Leave_Days'),
                    'leave_type' : leave.get('Leave_Type'),
                }
                leave_info.append(info)

        # Build response
        response = {
            "latest_vibe": latest_vibe,
            "vibe_trend": vibe_trend,
            "leave_balance": 20 - len(leave_data),
            "meetings_attended": int(sum(a.get('Meetings_Attended', 0) for a in recent_activity)),
            "performance_rating": performance_rating,
            "total_work_hours": round(total_work_hours, 2),
            "average_work_hours": round(average_work_hours, 2),
            "awards": awards,
            # "activity_level": activities,
            "overall_activity_level": {
                "teams_messages_sent": int(sum(a.get('Teams_Messages_Sent', 0) for a in recent_activity)),
                "emails_sent": int(sum(a.get('Emails_Sent', 0) for a in recent_activity)),
                "meetings_attended": int(sum(a.get('Meetings_Attended', 0) for a in recent_activity))
            },
            "leaves": dict(leave_counts),
            "all_leaves": leave_info,
        }

        return JSONResponse(content=response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching employee summary: {str(e)}"
        )
        
        
if __name__ == "__main__":
    pass