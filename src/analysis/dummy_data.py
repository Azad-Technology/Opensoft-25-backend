import random 
import math
import json
from datetime import datetime, timedelta
import os

behavior_patterns = {
    "Work_Overload_Stress": {
        "work_hours": (10, 12), "messages": (60, 90), "emails": (15, 30), "meetings": (4, 6), "trend": "decline",
        "leave_percentage": 0.12, "leave_probabilities": {"Sick Leave": 0.5, "Personal Leave": 0.3, "Vacation Leave": 0.1, "Unpaid Leave": 0.1}
    },
    "Lack_of_Engagement": {
        "work_hours": (4, 6), "messages": (5, 15), "emails": (1, 5), "meetings": (0, 2), "trend": "low",
        "leave_percentage": 0.06, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1}
    },
    "Feeling_Undervalued": {
        "work_hours": (5, 8), "messages": (20, 40), "emails": (4, 12), "meetings": (2, 4), "trend": "fluctuate",
        "leave_percentage": 0.09, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.5, "Vacation Leave": 0.1, "Unpaid Leave": 0.1}
    },
    "Career_Concerns": {
        "work_hours": (7, 9), "messages": (25, 50), "emails": (6, 15), "meetings": (3, 5), "trend": "erratic",
        "leave_percentage": 0.1, "leave_probabilities": {"Sick Leave": 0.4, "Personal Leave": 0.3, "Vacation Leave": 0.2, "Unpaid Leave": 0.1}
    },
    "Lack_of_Work_Life_Balance": {
        "work_hours": (10, 14), "messages": (30, 70), "emails": (8, 20), "meetings": (3, 5), "trend": "unstable",
        "leave_percentage": 0.13, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1}
    },
    "Recognition_Gap": {
        "work_hours": (7, 10), "messages": (40, 60), "emails": (8, 18), "meetings": (3, 4), "trend": "drop",
        "leave_percentage": 0.1, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1}
    },
    "Highly_Engaged_Employee": {
        "work_hours": (8, 10), "messages": (60, 100), "emails": (15, 30), "meetings": (5, 7), "trend": "stable",
        "leave_percentage": 0.04, "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.3, "Vacation Leave": 0.4, "Unpaid Leave": 0.1}
    },
    "High_Performance_Contributor": {
        "work_hours": (9, 11), "messages": (80, 120), "emails": (25, 45), "meetings": (6, 8), "trend": "stable",
        "leave_percentage": 0.05, "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.3, "Vacation Leave": 0.4, "Unpaid Leave": 0.1}
    },
    "Innovative_Problem_Solver": {
        "work_hours": (7, 9), "messages": (35, 65), "emails": (12, 25), "meetings": (3, 5), "trend": "stable",
        "leave_percentage": 0.06, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.3, "Vacation Leave": 0.3, "Unpaid Leave": 0.1}
    },
    "Strong_Team_Collaborator": {
        "work_hours": (7, 10), "messages": (50, 80), "emails": (15, 28), "meetings": (4, 6), "trend": "increase",
        "leave_percentage": 0.05, "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.3, "Vacation Leave": 0.3, "Unpaid Leave": 0.1}
    },
    "Job_Satisfaction_Champion": {
        "work_hours": (7, 9), "messages": (40, 70), "emails": (10, 20), "meetings": (2, 5), "trend": "consistent",
        "leave_percentage": 0.04, "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.4, "Vacation Leave": 0.3, "Unpaid Leave": 0.1}
    }
}

behavior_performance_mapping = {
    "Work_Overload_Stress": (2, 3),
    "Lack_of_Engagement": (1, 2),
    "Feeling_Undervalued": (2, 3),
    "Career_Concerns": (2, 3),
    "Workplace_Conflict": (1, 2),
    "Social_Isolation": (1, 2),
    "Lack_of_Work_Life_Balance": (2, 3),
    "Recognition_Gap": (2, 3),
    "Job_Satisfaction_Concerns": (2, 3),
    "Performance_Pressure": (3, 4),
    "Highly_Engaged_Employee": (4, 5),
    "High_Performance_Contributor": (4, 5),
    "Innovative_Problem_Solver": (4, 5),
    "Strong_Team_Collaborator": (4, 5),
    "Job_Satisfaction_Champion": (4, 5),
}

manager_feedback_mapping = {
    1: "Needs Improvement",
    2: "Meets Expectations",
    3: "Exceeds Expectations",
    4: "Exceeds Expectations",
    5: "Outstanding Performance"
}
def determine_promotion(performance_rating):
    return "TRUE" if performance_rating >= 4 else "FALSE"

def generate_employee_id():
    return "EMP" + str(random.randint(1000, 9999))

def generate_onboarding_data():
    entry = {
        'Joining_Date': datetime.now() - timedelta(days=random.randint(30, 1800)),
        "Onboarding_Feedback" : random.choice(["Poor", "Average", "Good", "Excellent"]),
        'Mentor_Assigned':bool(round(random.random())),
        'Initial_Training_Completed': bool(round(random.random())),
        }
    return entry

def distribute_behavior_days(total_days, behaviors):
    weights = [random.uniform(0.1, 0.5) for _ in range(len(behaviors) - 1)]
    weights.append(1 - sum(weights))
    return {behaviors[i]: int(total_days * weights[i]) for i in range(len(behaviors))}

def generate_activity_data(joining_date,behaviour_pattern):
    activity_data = []
    keys_list = list(behaviour_pattern.keys())
    for i in range(len(behaviour_pattern)):
        behavior = keys_list[i]
        behavior_info = behavior_patterns[behavior]
        days = behaviour_pattern[behavior]
        for day in range(days):
            date = joining_date + timedelta(days=day)
            work_hours = random.randint(behavior_info["work_hours"][0], behavior_info["work_hours"][1])
            messages = random.randint(behavior_info["messages"][0], behavior_info["messages"][1])
            emails = random.randint(behavior_info["emails"][0], behavior_info["emails"][1])
            meetings = random.randint(behavior_info["meetings"][0], behavior_info["meetings"][1])
            activity_data.append({
                "Date": date.strftime("%m/%d/%Y"),
                "Work_Hours": work_hours,
                "Messages": messages,
                "Emails": emails,
                "Meetings": meetings,
            })
    return activity_data

def generate_leave_data(employee_id, joining_date, behavior_distribution):
    leave_data = []
    for behavior, days in behavior_distribution.items():
        behavior_info = behavior_patterns[behavior]
        leave_days = int(days * behavior_info["leave_percentage"])
        for _ in range(leave_days):
            leave_type = random.choices(
                list(behavior_info["leave_probabilities"].keys()),
                list(behavior_info["leave_probabilities"].values())
            )[0]
            leave_start = joining_date + timedelta(days=random.randint(0, days - 1))
            leave_end = leave_start + timedelta(days=random.randint(1, 3))
            leave_data.append({
                "Leave_Type": leave_type,
                "Leave_Days": (leave_end - leave_start).days + 1,
                "Leave_Start_Date": leave_start.strftime("%m/%d/%Y"),
                "Leave_End_Date": leave_end.strftime("%m/%d/%Y"),
            })
    return leave_data

def generate_performance_data(employee_id, joining_date, behavior_distribution):
    total_days = (datetime.now() - joining_date).days
    
    review_period = "Annual 2023" if total_days >= 365 else "H2 2023" if total_days >= 180 else "H1 2023"
    
    dominant_behavior = max(behavior_distribution, key=behavior_distribution.get)
    performance_rating = random.randint(1, 4) if "Stress" in dominant_behavior else random.randint(3, 4)
    manager_feedback = "Needs Improvement" if performance_rating == 1 else "Meets Expectations" if performance_rating == 2 else "Exceeds Expectations"
    promotion_consideration = performance_rating >= 3
    
    return {
        "Review_Period": review_period,
        "Performance_Rating": performance_rating,
        "Manager_Feedback": manager_feedback,
        "Promotion_Consideration": promotion_consideration
    }

def generate_reward_data(employee_id, behavior_patterns, start_date, days):
    award_types = ["Innovation Award", "Leadership Excellence", "Best Team Player", "Star Performer"]
    rewards = []
    for day in range(days):
        date = start_date + timedelta(days=day)
        behavior = random.choice(list(behavior_patterns.keys()))
        performance_rating = random.randint(
            behavior_performance_mapping[behavior][0],
            behavior_performance_mapping[behavior][1]
        )
        if performance_rating >= 4:
            rewards.append({
                "Award_Type": random.choice(award_types),
                "Award_Date": date.strftime('%Y-%m-%d'),
                "Reward_Points": random.randint(50, 500)
            })
    return rewards

def calculate_vibe_scores(joining_date, behavior_distribution):
    total_days = (datetime.now() - joining_date).days
    vibe_scores = {}
    
    # Define score ranges for different behavior types
    behavior_scores = {
        "Work_Overload_Stress": (2, 3),
        "Lack_of_Engagement": (1, 2),
        "Feeling_Undervalued": (2, 3),
        "Career_Concerns": (2, 3),
        "Lack_of_Work_Life_Balance": (2, 3),
        "Recognition_Gap": (2, 3),
        "Highly_Engaged_Employee": (4, 5),
        "High_Performance_Contributor": (4, 5),
        "Innovative_Problem_Solver": (4, 5),
        "Strong_Team_Collaborator": (4, 5),
        "Job_Satisfaction_Champion": (4, 5),
    }
    
    current_date = joining_date
    for behavior, days in behavior_distribution.items():
        min_score, max_score = behavior_scores.get(behavior, (2, 3))
        for _ in range(days):
            vibe_score = round(random.uniform(min_score, max_score), 2)
            vibe_scores[current_date.strftime('%Y-%m-%d')] = vibe_score
            current_date += timedelta(days=1)
    
    return vibe_scores

def generate_dummy_data(num_entries=5, num_behaviors=3):
    dataset = []
    for _ in range(num_entries):
        behaviors=[]
        for _ in range(num_behaviors):
            behaviors.append(input("Enter behavior pattern: "))
        emp_id = generate_employee_id()
        onboarding_exp = generate_onboarding_data()
        behavior_distribution = distribute_behavior_days((datetime.now() - onboarding_exp["Joining_Date"]).days, behaviors)
        print(behavior_distribution)
        activity_data = generate_activity_data(onboarding_exp["Joining_Date"], behavior_distribution)
        leave_data = generate_leave_data(emp_id, onboarding_exp["Joining_Date"], behavior_distribution)
        performance_data = generate_performance_data(emp_id, onboarding_exp["Joining_Date"], behavior_distribution)
        rewards = generate_reward_data(emp_id, behavior_patterns, onboarding_exp["Joining_Date"], (datetime.now() - onboarding_exp["Joining_Date"]).days)
        vibe_scores = calculate_vibe_scores(onboarding_exp["Joining_Date"], behavior_distribution)
        dataset.append({
            "Employee_ID": emp_id,
            "Onboarding": onboarding_exp,
            "Activity": activity_data,
            "Leaves": leave_data,
            "Performance": performance_data,
            "Rewards": rewards,
            "Vibe_Scores": vibe_scores
        })
    return dataset

def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError("Type not serializable")

file_path = os.path.expanduser("~/Desktop/output.json")  # Saves to Desktop
with open(file_path, "w") as file:
    json.dump(generate_dummy_data(10, 3), file, indent=4, default=json_serial)

print(f"JSON file successfully created at {file_path}")

