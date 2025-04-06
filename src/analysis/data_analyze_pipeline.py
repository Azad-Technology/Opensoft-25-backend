import re
from math import nan
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from pymongo import UpdateOne
import pytz
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from utils.app_logger import setup_logger
from utils.config import get_async_database

async_db = get_async_database()
logger = setup_logger("src/analysis/data_analyze_pipeline.py")


async def load_collection_to_dataframe(collection_name):
    collection = async_db[collection_name]
    cursor = collection.find({})
    df = pd.DataFrame(await cursor.to_list(length=None))

    if "_id" in df.columns:
        df = df.drop("_id", axis=1)

    return df


def calculate_decay_score(
    df,
    score_prefix,
    date_prefix,
    date_format,
    output_column,
    baseline,
    decay_rate=0.1,
    staleness_rate=0.05,
):
    result_df = df.copy()
    reference_date = datetime.now()
    score_prefix_escaped = re.escape(score_prefix)
    score_pattern = re.compile(f"{score_prefix_escaped}_(\d+)")
    score_date_pairs = []
    for col in df.columns:
        match = score_pattern.match(col)
        if match:
            num = match.group(1)
            date_col = f"{date_prefix}_{num}"
            if date_col in df.columns:
                score_date_pairs.append((col, date_col))

    def process_row(row):
        valid_pairs = []
        for score_col, date_col in score_date_pairs:
            if pd.notna(row[score_col]) and pd.notna(row[date_col]):
                try:
                    score = float(row[score_col])
                    date_str = str(row[date_col])
                    date = datetime.strptime(date_str, date_format)
                    valid_pairs.append((score, date))
                except (ValueError, TypeError) as e:
                    print(
                        f"Warning: Could not process {score_col}={row[score_col]} or {date_col}={row[date_col]} - {e}"
                    )
                    continue

        if not valid_pairs:
            return np.nan
        most_recent_date = max(pair[1] for pair in valid_pairs)
        if len(valid_pairs) == 1:
            score = valid_pairs[0][0]
            date = valid_pairs[0][1]
            time_diff_days = max(0, (reference_date - date).days)
            decay_factor = np.exp(-decay_rate * time_diff_days / 365)
            return score * decay_factor + baseline * (1 - decay_factor)

        internal_weights = []
        for score, date in valid_pairs:
            internal_time_diff = max(0, (most_recent_date - date).days)
            internal_weight = np.exp(-decay_rate * internal_time_diff / 365)
            internal_weights.append((score, internal_weight))
        internal_weighted_sum = sum(
            score * weight for score, weight in internal_weights
        )
        total_internal_weight = sum(weight for _, weight in internal_weights)
        internal_score = internal_weighted_sum / total_internal_weight
        staleness_days = max(0, (reference_date - most_recent_date).days)
        freshness_factor = np.exp(-staleness_rate * staleness_days / 365)
        final_score = internal_score * freshness_factor + baseline * (
            1 - freshness_factor
        )
        return final_score

    result_df[output_column] = result_df.apply(process_row, axis=1)
    return result_df


def activity_data(activity_df):
    activity_df["Date"] = pd.to_datetime(
        activity_df["Date"], format="%m/%d/%Y"
    ).dt.strftime("%Y-%m")
    monthly_activity = (
        activity_df.groupby(["Employee_ID", "Date"])
        .agg(
            {
                "Teams_Messages_Sent": "mean",
                "Emails_Sent": "mean",
                "Meetings_Attended": "mean",
                "Work_Hours": "mean",
            }
        )
        .round(2)
        .reset_index()
    )
    communication_features = ["Teams_Messages_Sent", "Emails_Sent", "Meetings_Attended"]
    weights = {
        "Teams_Messages_Sent_norm": 0.50,
        "Meetings_Attended_norm": 0.30,
        "Emails_Sent_norm": 0.20,
    }
    for feature in communication_features:
        feature_min = monthly_activity[feature].min()
        feature_max = monthly_activity[feature].max()
        monthly_activity[f"{feature}_norm"] = (
            monthly_activity[feature] - feature_min
        ) / (feature_max - feature_min + 1e-9)
    monthly_activity["Team_Interaction"] = (
        monthly_activity["Teams_Messages_Sent_norm"]
        * weights["Teams_Messages_Sent_norm"]
        + monthly_activity["Meetings_Attended_norm"] * weights["Meetings_Attended_norm"]
        + monthly_activity["Emails_Sent_norm"] * weights["Emails_Sent_norm"]
    )
    monthly_activity["Team_Interaction_Adj"] = monthly_activity["Team_Interaction"] * (
        monthly_activity["Work_Hours"] / 8
    )
    monthly_activity = monthly_activity.drop(
        columns=[f"{feat}_norm" for feat in communication_features]
        + ["Team_Interaction"]
    )

    def process_activity(df):
        df_sorted = df.sort_values(["Employee_ID", "Date"]).copy()
        df_sorted["seq"] = df_sorted.groupby("Employee_ID").cumcount() + 1
        max_seq = df_sorted["seq"].max()
        result_data = []
        for emp_id, group in df_sorted.groupby("Employee_ID"):
            row = {"Employee_ID": emp_id}
            for _, entry in group.iterrows():
                seq = entry["seq"]
                row[f"Activity_Date_{seq}"] = entry["Date"]
                row[f"Activity_Interaction_{seq}"] = entry["Team_Interaction_Adj"]

            result_data.append(row)
        result = pd.DataFrame(result_data)
        columns = ["Employee_ID"]
        for i in range(1, max_seq + 1):
            columns.extend([f"Activity_Date_{i}", f"Activity_Interaction_{i}"])
        return result.reindex(columns=columns, fill_value=None)

    unique_ids = set(monthly_activity["Employee_ID"].unique())
    initial_filter = pd.DataFrame({"Employee_ID": list(unique_ids)})
    activity_processed = process_activity(monthly_activity)
    activity = initial_filter.merge(activity_processed, on="Employee_ID", how="left")
    activity = calculate_decay_score(
        df=activity,
        score_prefix="Activity_Interaction",
        date_prefix="Activity_Date",
        date_format="%Y-%m",
        output_column="Activity_Interaction_Decay",
        baseline=0.65,
    )
    return activity


def leave_data(leave_df):
    leave = leave_df.rename(columns={"Leave_Start_Date": "Date"})
    leave["Date"] = pd.to_datetime(leave["Date"]).dt.strftime("%Y")
    leave.drop("Leave_End_Date", axis=1, inplace=True)
    aggregated = (
        leave.groupby(["Employee_ID", "Date"])
        .agg(
            Total_Leave_Days=("Leave_Days", "sum"),
        )
        .reset_index()
        .round(2)
    )
    median = aggregated["Total_Leave_Days"].median()

    def process_leave(df):
        sorted_df = df.sort_values("Date").reset_index(drop=True)
        grouped = sorted_df.groupby("Employee_ID")
        max_entries = sorted_df.groupby("Employee_ID").size().max()
        result = (
            grouped.apply(
                lambda x: pd.Series(
                    {
                        **{
                            f"Leave_Days_{i + 1}": x.iloc[i]["Total_Leave_Days"]
                            for i in range(len(x))
                        },
                        **{
                            f"Leave_Date_{i + 1}": x.iloc[i]["Date"]
                            for i in range(len(x))
                        },
                    }
                )
            )
            .unstack()
            .reset_index()
        )
        columns = ["Employee_ID"]
        for i in range(1, max_entries + 1):
            columns.extend([f"Leave_Date_{i}", f"Leave_Days_{i}"])
        return result.reindex(columns=columns, fill_value=None)

    unique_ids = set()
    unique_ids.update(aggregated["Employee_ID"].unique())
    initial_filter = pd.DataFrame({"Employee_ID": list(unique_ids)})
    leave_processed = process_leave(aggregated)
    leave = initial_filter.merge(leave_processed, on="Employee_ID", how="left")
    leave = calculate_decay_score(
        df=leave,
        score_prefix="Leave_Days",
        date_prefix="Leave_Date",
        date_format="%Y",
        output_column="Leave_Day_Decay",
        baseline=median,
    )
    return leave


def onboard_data(onboard_df):
    onboard_df.to_csv("1_onboard.csv", index=0)
    onboard = onboard_df.rename(columns={"Joining_Date": "Date"})
    onboard["Date"] = pd.to_datetime(onboard["Date"]).dt.strftime("%Y-%m-%d")
    onboard["company_efforts"] = (
        onboard["Mentor_Assigned"] & onboard["Initial_Training_Completed"]
    ).astype(int)

    feedback_mapping = {"Excellent": 1.0, "Good": 0.75, "Average": 0.5, "Poor": 0.25}
    onboard["employee_satisfaction"] = onboard["Onboarding_Feedback"].map(
        feedback_mapping
    )

    onboard["onboard_weighted_score"] = (onboard["company_efforts"] * 0.6) + (
        onboard["employee_satisfaction"] * 0.4
    )
    conditions = [
        (onboard["company_efforts"] == 1) & (onboard["employee_satisfaction"] >= 0.75),
        (onboard["company_efforts"] == 1) & (onboard["employee_satisfaction"] < 0.75),
        (onboard["company_efforts"] == 0) & (onboard["employee_satisfaction"] >= 0.75),
        (onboard["company_efforts"] == 0) & (onboard["employee_satisfaction"] < 0.75),
    ]
    categories = [1, 2, 3, 4]
    onboard["onboard_category"] = np.select(conditions, categories, default=0)

    def process_onboard(df):
        sorted_df = df.sort_values("Date").reset_index(drop=True)
        grouped = sorted_df.groupby("Employee_ID")
        max_entries = sorted_df.groupby("Employee_ID").size().max()
        if max_entries == 1:
            result = sorted_df[["Employee_ID", "onboard_category", "Date"]].copy()
            result.rename(
                columns={
                    "onboard_category": "Onboard_Category_1",
                    "Date": "Onboard_Date_1",
                },
                inplace=True,
            )
            return result
        else:
            result = (
                grouped.apply(
                    lambda x: pd.Series(
                        {
                            **{
                                f"Onboard_Category_{i + 1}": x.iloc[i][
                                    "onboard_category"
                                ]
                                for i in range(len(x))
                            },
                            **{
                                f"Onboard_Date_{i + 1}": x.iloc[i]["Date"]
                                for i in range(len(x))
                            },
                        }
                    )
                )
                .unstack()
                .reset_index()
            )
            columns = ["Employee_ID"]
            for i in range(1, max_entries + 1):
                columns.extend([f"Onboard_Date_{i}", f"Onboard_Category_{i}"])
            return result.reindex(columns=columns, fill_value=None)

    unique_ids = set()
    unique_ids.update(onboard["Employee_ID"].unique())
    initial_filter = pd.DataFrame({"Employee_ID": list(unique_ids)})
    onboard_processed = process_onboard(onboard)
    onboard = initial_filter.merge(onboard_processed, on="Employee_ID", how="left")
    onboard_cat_columns = [
        col for col in onboard.columns if col.startswith("Onboard_Category_")
    ]

    def get_last_cat_value(row):
        for col in reversed(onboard_cat_columns):
            if pd.notna(row[col]):
                return row[col]
        return np.nan

    onboard["Onboard_Last_Category"] = onboard.apply(get_last_cat_value, axis=1)
    return onboard


def performance_data(performance_df):
    weights = {
        "performance_rating": 0.60,
        "manager_feedback": 0.30,
        "promotion_consideration": 0.10,
    }
    feedback_map = {
        "Exceeds Expectations": 1.0,
        "Meets Expectations": 0.8,
        "Needs Improvement": 0.5,
    }

    def convert_performance_date(row, fiscal_year_end_month=12):
        year = row.split()[-1]
        if "H1" in row:
            month = str(fiscal_year_end_month // 2).zfill(2)
        elif "H2" in row or "Annual" in row:
            month = str(fiscal_year_end_month).zfill(2)
        else:
            return None
        return f"{year}-{month}"

    def calculate_master_score(row):
        perf_score = row["Performance_Rating"] / 4
        feedback_score = feedback_map[row["Manager_Feedback"]]
        promotion_score = 1 if row["Promotion_Consideration"] else 0
        return (
            (perf_score * weights["performance_rating"])
            + (feedback_score * weights["manager_feedback"])
            + (promotion_score * weights["promotion_consideration"])
        )

    performance_df["Per_Score"] = performance_df.apply(calculate_master_score, axis=1)
    performance_df["Per_Score"] = performance_df["Per_Score"].round(3)
    performance_df["Review_Period"] = performance_df["Review_Period"].apply(
        lambda x: convert_performance_date(x, fiscal_year_end_month=12)
    )
    performance = performance_df.rename(columns={"Review_Period": "Date"})
    median = performance["Per_Score"].median()

    def process_performance(df):
        sorted_df = df.sort_values("Date").reset_index(drop=True)
        grouped = sorted_df.groupby("Employee_ID")
        max_entries = sorted_df.groupby("Employee_ID").size().max()
        if max_entries == 1:
            result = sorted_df[["Employee_ID", "Per_Score", "Date"]].copy()
            result.rename(
                columns={"Per_Score": "Per_Score_1", "Date": "Per_Date_1"}, inplace=True
            )
            return result
        else:
            result = (
                grouped.apply(
                    lambda x: pd.Series(
                        {
                            **{
                                f"Per_Score_{i + 1}": x.iloc[i]["Per_Score"]
                                for i in range(len(x))
                            },
                            **{
                                f"Per_Date_{i + 1}": x.iloc[i]["Date"]
                                for i in range(len(x))
                            },
                        }
                    )
                )
                .unstack()
                .reset_index()
            )
            columns = ["Employee_ID"]
            for i in range(1, max_entries + 1):
                columns.extend([f"Per_Date_{i}", f"Per_Score_{i}"])
            return result.reindex(columns=columns, fill_value=None)

    unique_ids = set()
    unique_ids.update(performance["Employee_ID"].unique())
    initial_filter = pd.DataFrame({"Employee_ID": list(unique_ids)})
    performance_processed = process_performance(performance)
    performance = initial_filter.merge(
        performance_processed, on="Employee_ID", how="left"
    )
    performance = calculate_decay_score(
        df=performance,
        score_prefix="Per_Score",
        date_prefix="Per_Date",
        date_format="%Y-%m",
        output_column="Per_Score_Decay",
        baseline=median,
    )
    return performance


def rewards_data(rewards_df):
    rewards = rewards_df.copy()
    rewards["Award_Date"] = pd.to_datetime(
        rewards["Award_Date"], format="%Y-%m-%d"
    ).dt.strftime("%Y-%m-%d")
    rewards = rewards.rename(columns={"Award_Date": "Date"})
    rewards = rewards.drop("Reward_Points", axis=1)

    def process_rewards(df):
        sorted_df = df.sort_values("Date").reset_index(drop=True)
        grouped = sorted_df.groupby("Employee_ID")
        max_entries = sorted_df.groupby("Employee_ID").size().max()
        result = (
            grouped.apply(
                lambda x: pd.Series(
                    {
                        **{
                            f"Award_Type_{i + 1}": x.iloc[i]["Award_Type"]
                            for i in range(len(x))
                        },
                        **{
                            f"Award_Date_{i + 1}": x.iloc[i]["Date"]
                            for i in range(len(x))
                        },
                    }
                )
            )
            .unstack()
            .reset_index()
        )
        columns = ["Employee_ID"]
        for i in range(1, max_entries + 1):
            columns.extend([f"Award_Date_{i}", f"Award_Type_{i}"])
        return result.reindex(columns=columns, fill_value=None)

    unique_ids = set()
    unique_ids.update(rewards["Employee_ID"].unique())
    initial_filter = pd.DataFrame({"Employee_ID": list(unique_ids)})
    rewards_processed = process_rewards(rewards)
    rewards = initial_filter.merge(rewards_processed, on="Employee_ID", how="left")
    award_type_columns = [
        col for col in rewards.columns if col.startswith("Award_Type_")
    ]
    rewards["Award_Count"] = rewards[award_type_columns].notna().sum(axis=1)
    return rewards


def find_unique_ids(activity, leave, onboard, performance, rewards):
    unique_ids = set()
    for name in [
        activity,
        leave,
        onboard,
        performance,
        rewards,
    ]:
        unique_ids.update(name["Employee_ID"].unique())
    all_unique_ids = pd.DataFrame({"Employee_ID": list(unique_ids)})
    return all_unique_ids


def vibemeter_data(vibe_df, activity, leave, onboard, performance, rewards):
    def process_vibemeter(df):
        sorted_df = df.sort_values("Date").reset_index(drop=True)
        grouped = sorted_df.groupby("Employee_ID")
        max_entries = sorted_df.groupby("Employee_ID").size().max()
        result = (
            grouped.apply(
                lambda x: pd.Series(
                    {
                        **{
                            f"Vibe_Score_{i + 1}": x.iloc[i]["Vibe_Score"]
                            for i in range(len(x))
                        },
                        **{
                            f"Vibe_Date_{i + 1}": x.iloc[i]["Date"]
                            for i in range(len(x))
                        },
                    }
                )
            )
            .unstack()
            .reset_index()
        )
        columns = ["Employee_ID"]
        for i in range(1, max_entries + 1):
            columns.extend([f"Vibe_Score_{i}", f"Vibe_Date_{i}"])
        return result.reindex(columns=columns, fill_value=None)

    def categorize_emotion_zone(score):
        if 0 <= score < 1.5:
            return "Frustrated"
        elif 1.5 <= score < 2.5:
            return "Sad"
        elif 2.5 <= score < 3.5:
            return "Okay"
        elif 3.5 <= score < 4.5:
            return "Happy"
        elif 4.5 <= score < 5:
            return "Excited"

    vibe_df["Response_Date"] = pd.to_datetime(
        vibe_df["Response_Date"], format="%d-%m-%Y"
    ).dt.strftime("%Y-%m-%d")
    vibemeter = vibe_df.rename(columns={"Response_Date": "Date"})
    median = vibemeter["Vibe_Score"].median()
    vibemeter_processed = process_vibemeter(vibemeter)
    all_unique_ids = find_unique_ids(activity, leave, onboard, performance, rewards)
    vibemeter = all_unique_ids.merge(vibemeter_processed, on="Employee_ID", how="left")
    vibemeter = calculate_decay_score(
        df=vibemeter,
        score_prefix="Vibe_Score",
        date_prefix="Vibe_Date",
        date_format="%Y-%m-%d",
        output_column="Vibe_Score_Decay",
        baseline=median,
    )
    vibemeter["Vibe_Emotion_Trend"] = vibemeter["Vibe_Score_Decay"].apply(
        categorize_emotion_zone
    )
    return vibemeter


def divide_emotions(vibemeter, activity, leave, onboard, performance, rewards):
    df_negative = vibemeter[vibemeter["Vibe_Emotion_Trend"].isin(["Sad", "Frustrated"])]
    df_negative = df_negative[["Employee_ID", "Vibe_Emotion_Trend"]]
    df_positive = vibemeter[
        vibemeter["Vibe_Emotion_Trend"].isin(["Okay", "Happy", "Excited"])
    ]
    df_positive = df_positive[["Employee_ID", "Vibe_Emotion_Trend"]]
    df_empty = vibemeter[
        vibemeter["Vibe_Emotion_Trend"].isna() | (vibemeter["Vibe_Emotion_Trend"] == "")
    ]
    df_empty = df_empty[["Employee_ID"]]

    def process(df):
        df = pd.merge(
            df,
            activity[["Employee_ID", "Activity_Interaction_Decay"]],
            on="Employee_ID",
            how="left",
        )
        df = pd.merge(
            df,
            leave[["Employee_ID", "Leave_Day_Decay"]],
            on="Employee_ID",
            how="left",
        )
        df = pd.merge(
            df,
            onboard[["Employee_ID", "Onboard_Last_Category"]],
            on="Employee_ID",
            how="left",
        )
        df = pd.merge(
            df,
            performance[["Employee_ID", "Per_Score_Decay"]],
            on="Employee_ID",
            how="left",
        )
        df = pd.merge(
            df,
            rewards[["Employee_ID", "Award_Count"]],
            on="Employee_ID",
            how="left",
        )
        return df

    df_negative = process(df_negative)
    df_positive = process(df_positive)
    df_empty = process(df_empty)
    df_empty.insert(loc=1, column="Vibe_Emotion_Trend", value=np.nan)

    return df_negative, df_positive, df_empty


def impute_data(negative, positive, empty_emotions):
    merged_df = pd.concat([empty_emotions, negative, positive], ignore_index=True)
    merged_df = merged_df.sort_values(by=["Employee_ID"], ascending=True)

    target_columns = [
        "Activity_Interaction_Decay",
        "Leave_Day_Decay",
        "Onboard_Last_Category",
        "Per_Score_Decay",
        "Award_Count",
    ]

    data = merged_df[target_columns]
    model = BayesianRidge()
    imputer = IterativeImputer(
        estimator=model,
        max_iter=50,
        random_state=42,
        verbose=0,
        tol=0.01,
        imputation_order="roman",
    )

    if data.isna().any().any():
        imputed_data = imputer.fit_transform(data)
        imputed_df = pd.DataFrame(
            imputed_data, columns=target_columns, index=data.index
        )
        for column in target_columns:
            merged_df[column] = merged_df[column].fillna(imputed_df[column])

    return merged_df


def predict_emotions(imputed_dataset):
    emotion_map = {"Frustrated": 1, "Sad": 2, "Okay": 3, "Happy": 4, "Excited": 5}

    def convert_emotion(emotion):
        if pd.isna(emotion):
            return np.nan
        return emotion_map.get(emotion, np.nan)

    imputed_dataset["Vibe_Emotion_Trend"] = imputed_dataset["Vibe_Emotion_Trend"].apply(
        convert_emotion
    )

    imputed_clean = imputed_dataset.dropna(subset=["Vibe_Emotion_Trend"])
    imputed_null_emo = imputed_dataset[imputed_dataset["Vibe_Emotion_Trend"].isna()]
    sad_test = imputed_clean[imputed_clean["Vibe_Emotion_Trend"].isin([1.0, 2.0])]
    sad_train, _ = train_test_split(sad_test, test_size=0.1, random_state=42)
    train = pd.concat([sad_train])
    test = pd.concat([sad_test])
    x_train = train.drop(columns=["Employee_ID", "Vibe_Emotion_Trend"])
    y_train = train["Vibe_Emotion_Trend"]
    x_test = test.drop(columns=["Employee_ID", "Vibe_Emotion_Trend"])
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(x_train_scaled, y_train)
    y_train_pred = rf.predict(x_train_scaled)
    y_test_pred = rf.predict(x_test_scaled)
    train_results = train
    train_results["Predicted"] = y_train_pred
    test_results = test
    test_results["Predicted"] = y_test_pred
    df_y = test_results

    sad_df = imputed_clean[imputed_clean["Vibe_Emotion_Trend"].isin([1.0, 2.0])]
    happy_df = imputed_clean[~imputed_clean["Vibe_Emotion_Trend"].isin([1.0, 2.0])]
    sad_train, sad_test = train_test_split(sad_df, test_size=0.1, random_state=42)
    happy_train, happy_test = train_test_split(happy_df, test_size=0.3, random_state=42)
    happy_test = pd.concat([happy_df, imputed_null_emo])
    train = pd.concat([sad_train, happy_train])
    test = pd.concat([happy_test])
    x_train = train.drop(columns=["Employee_ID", "Vibe_Emotion_Trend"])
    y_train = train["Vibe_Emotion_Trend"]
    x_test = test.drop(columns=["Employee_ID", "Vibe_Emotion_Trend"])
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(x_train_scaled, y_train)
    y_train_pred = rf.predict(x_train_scaled)
    y_test_pred = rf.predict(x_test_scaled)
    train_results = train
    train_results["Predicted"] = y_train_pred
    test_results = test
    test_results["Predicted"] = y_test_pred
    df_x = test_results
    df_net = pd.concat([df_x, df_y])
    df = df_net
    emotion_bins = {
        "Frustrated": (0, 1.5),
        "Sad": (1.50001, 2.5),
        "Okay": (2.50001, 3.5),
        "Happy": (3.50001, 4.5),
        "Excited": (4.50001, 5.0),
    }
    train_results = df

    def categorize_vibe(score):
        if pd.isna(score):
            return np.nan
        for emotion, (low, high) in emotion_bins.items():
            if low <= score <= high:
                return emotion
        return nan

    train_results["Actual_Emotion"] = train_results["Vibe_Emotion_Trend"].apply(
        categorize_vibe
    )
    train_results["Predicted_Emotion"] = train_results["Predicted"].apply(
        categorize_vibe
    )

    return train_results


async def save_to_mongodb(final_dataset):
    try:
        # Get current time in UTC and convert to IST
        current_utc = datetime.now(timezone.utc)
        ist_tz = pytz.timezone("Asia/Kolkata")
        current_ist = current_utc.astimezone(ist_tz)
        current_ist_date = current_ist.date().isoformat()

        # Prepare bulk operations
        bulk_operations = []

        for _, row in final_dataset.iterrows():
            data = row.to_dict()
            data["timestamp"] = current_utc  # Store in UTC
            data["ist_date"] = current_ist_date  # Store IST date

            # Update operation for each employee - will update if exists, create if doesn't
            bulk_operations.append(
                UpdateOne(
                    {"Employee_ID": data["Employee_ID"], "ist_date": current_ist_date},
                    {"$set": data},
                    upsert=True,
                )
            )
        result = None
        if bulk_operations:
            result = await async_db.analyzed_profile.bulk_write(bulk_operations)
            print(
                f"Data saved to MongoDB at {current_ist.strftime('%Y-%m-%d %I:%M %p IST')}"
            )
            print(
                f"Modified: {result.modified_count}, Upserted: {result.upserted_count}"
            )

        return result
    except Exception as e:
        logger.error(f"Error saving to MongoDB: {str(e)}", exc_info=True)
        return None


async def get_employee_profile_json(employee_id: str) -> dict:
    """Create a JSON format profile for a single employee with limited recent data"""
    logger.info(f"Creating JSON profile for employee: {employee_id}")

    try:
        # Get all performance records and sort them manually
        all_performance = await async_db.performance.find(
            {"Employee_ID": employee_id}, {"_id": 0}
        ).to_list(length=None)

        # Custom sorting function for performance periods
        def sort_performance(record):
            period = record["Review_Period"]
            year = int(period.split()[-1])
            half = 1 if "H1" in period else 2
            return (year, half)

        # Sort and get last 3 entries
        sorted_performance = sorted(
            all_performance, key=sort_performance, reverse=True
        )[:3]

        collections_data = {
            "employee_id": employee_id,
            "onboarding": await async_db.onboarding.find_one(
                {"Employee_ID": employee_id}, {"_id": 0}
            ),
            "vibemeter": await async_db.vibemeter.find(
                {"Employee_ID": employee_id}, {"_id": 0}
            )
            .sort([("Response_Date", -1)])
            .limit(3)
            .to_list(length=None),
            "performance": sorted_performance,  # Use manually sorted performance data
            "rewards": await async_db.rewards.find(
                {"Employee_ID": employee_id}, {"_id": 0}
            )
            .sort([("Award_Date", -1)])
            .limit(3)
            .to_list(length=None),
            "leave": await async_db.leave.find({"Employee_ID": employee_id}, {"_id": 0})
            .sort([("Leave_Start_Date", -1)])
            .limit(3)
            .to_list(length=None),
            "activity": await async_db.activity.find(
                {"Employee_ID": employee_id}, {"_id": 0}
            )
            .sort([("Date", -1)])
            .limit(3)
            .to_list(length=None),
            "analyzed_profile": await async_db.analyzed_profile.find_one(
                {"Employee_ID": employee_id}, {"_id": 0}, sort=[("timestamp", -1)]
            ),
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
        logger.error(
            f"Error creating JSON profile for {employee_id}: {str(e)}", exc_info=True
        )
        return {}


async def analyzed_profile():
    try:
        activity_df = await load_collection_to_dataframe("activity")
        leave_df = await load_collection_to_dataframe("leave")
        onboard_df = await load_collection_to_dataframe("onboarding")
        performance_df = await load_collection_to_dataframe("performance")
        rewards_df = await load_collection_to_dataframe("rewards")
        vibemeter_df = await load_collection_to_dataframe("vibemeter")

        activity = activity_data(activity_df)
        leave = leave_data(leave_df)
        onboard = onboard_data(onboard_df)
        performance = performance_data(performance_df)
        rewards = rewards_data(rewards_df)
        vibemeter = vibemeter_data(
            vibemeter_df, activity, leave, onboard, performance, rewards
        )

        negative, positive, empty_emotions = divide_emotions(
            vibemeter, activity, leave, onboard, performance, rewards
        )
        imputed_dataset = impute_data(negative, positive, empty_emotions)
        final_dataset = predict_emotions(imputed_dataset)

        result = await save_to_mongodb(final_dataset)
        return result

    except Exception as e:
        logger.error(f"Error in analyzed_profile: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(analyzed_profile()))
