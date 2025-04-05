import random 
import math
import json
from datetime import datetime, timedelta
import os

behavior_patterns = {
    "Work_Overload_Stress": {
        "work_hours": (10, 12),
        "messages": (60, 90),
        "emails": (15, 30),
        "meetings": (4, 6),
        "trend": "decline",
        "leave_percentage": 0.12,
        "leave_probabilities": {"Sick Leave": 0.5, "Personal Leave": 0.3, "Vacation Leave": 0.1, "Unpaid Leave": 0.1},
        "award_percentage": 0.01
    },
    "Lack_of_Engagement": {
        "work_hours": (4, 6),
        "messages": (5, 15),
        "emails": (1, 5),
        "meetings": (0, 2),
        "trend": "low",
        "leave_percentage": 0.06,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1},
        "award_percentage": 0.01
    },
    "Feeling_Undervalued": {
        "work_hours": (5, 8),
        "messages": (20, 40),
        "emails": (4, 12),
        "meetings": (2, 4),
        "trend": "fluctuate",
        "leave_percentage": 0.09,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.5, "Vacation Leave": 0.1, "Unpaid Leave": 0.1},
        "award_percentage": 0.02
    },
    "Career_Concerns": {
        "work_hours": (7, 9),
        "messages": (25, 50),
        "emails": (6, 15),
        "meetings": (3, 5),
        "trend": "erratic",
        "leave_percentage": 0.1,
        "leave_probabilities": {"Sick Leave": 0.4, "Personal Leave": 0.3, "Vacation Leave": 0.2, "Unpaid Leave": 0.1},
        "award_percentage": 0.02
    },
    "Lack_of_Work_Life_Balance": {
        "work_hours": (10, 14),
        "messages": (30, 70),
        "emails": (8, 20),
        "meetings": (3, 5),
        "trend": "unstable",
        "leave_percentage": 0.13,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1},
        "award_percentage": 0.02
    },
    "Recognition_Gap": {
        "work_hours": (7, 10),
        "messages": (40, 60),
        "emails": (8, 18),
        "meetings": (3, 4),
        "trend": "drop",
        "leave_percentage": 0.1,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.4, "Vacation Leave": 0.2, "Unpaid Leave": 0.1},
        "award_percentage": 0.01
    },
    "Highly_Engaged_Employee": {
        "work_hours": (8, 10),
        "messages": (60, 100),
        "emails": (15, 30),
        "meetings": (5, 7),
        "trend": "stable",
        "leave_percentage": 0.04,
        "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.3, "Vacation Leave": 0.4, "Unpaid Leave": 0.1},
        "award_percentage": 0.05
    },
    "High_Performance_Contributor": {
        "work_hours": (9, 11),
        "messages": (80, 120),
        "emails": (25, 45),
        "meetings": (6, 8),
        "trend": "stable",
        "leave_percentage": 0.05,
        "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.3, "Vacation Leave": 0.4, "Unpaid Leave": 0.1},
        "award_percentage": 0.05
    },
    "Innovative_Problem_Solver": {
        "work_hours": (7, 9),
        "messages": (35, 65),
        "emails": (12, 25),
        "meetings": (3, 5),
        "trend": "stable",
        "leave_percentage": 0.06,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.3, "Vacation Leave": 0.3, "Unpaid Leave": 0.1},
        "award_percentage": 0.04
    },
    "Strong_Team_Collaborator": {
        "work_hours": (7, 10),
        "messages": (50, 80),
        "emails": (15, 28),
        "meetings": (4, 6),
        "trend": "increase",
        "leave_percentage": 0.05,
        "leave_probabilities": {"Sick Leave": 0.3, "Personal Leave": 0.3, "Vacation Leave": 0.3, "Unpaid Leave": 0.1},
        "award_percentage": 0.04
    },
    "Job_Satisfaction_Champion": {
        "work_hours": (7, 9),
        "messages": (40, 70),
        "emails": (10, 20),
        "meetings": (2, 5),
        "trend": "consistent",
        "leave_percentage": 0.04,
        "leave_probabilities": {"Sick Leave": 0.2, "Personal Leave": 0.4, "Vacation Leave": 0.3, "Unpaid Leave": 0.1},
        "award_percentage": 0.04
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

def generate_sequential_emp_id(index):
    """Generate sequential employee IDs"""
    return f"EMP{str(index+1).zfill(4)}"

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

def generate_reward_data(employee_id, behavior_distribution, start_date, days):
    award_types = ["Innovation Award", "Leadership Excellence", "Best Team Player", "Star Performer"]
    rewards = []
    
    # Calculate total number of award days based on behavior distribution
    award_days = 0
    for behavior, behavior_days in behavior_distribution.items():
        behavior_info = behavior_patterns[behavior]
        award_days += int(behavior_days * behavior_info["award_percentage"])
    
    # Generate random dates for awards
    all_possible_dates = [start_date + timedelta(days=x) for x in range(days)]
    award_dates = random.sample(all_possible_dates, min(award_days, len(all_possible_dates)))
    
    # Generate awards for selected dates
    for date in award_dates:
        rewards.append({
            "Award_Type": random.choice(award_types),
            "Award_Date": date.strftime('%Y-%m-%d'),
            "Reward_Points": random.randint(50, 500)
        })
    
    return rewards

def calculate_vibe_scores(joining_date, behavior_distribution):
    total_days = (datetime.now() - joining_date).days
    vibe_scores = {}
    
    # Define score ranges for different behavior types (using integers)
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
            # Using randint instead of uniform for integer values
            vibe_score = random.randint(min_score, max_score)
            vibe_scores[current_date.strftime('%Y-%m-%d')] = vibe_score
            current_date += timedelta(days=1)
    
    return vibe_scores

def generate_dummy_data(num_entries=20):
    dataset = []
    
    # Define different behavior combinations for different employee types
    employee_types = [
        # High performers
        ["Highly_Engaged_Employee", "High_Performance_Contributor", "Strong_Team_Collaborator"],
        ["High_Performance_Contributor", "Innovative_Problem_Solver", "Job_Satisfaction_Champion"],
        ["Innovative_Problem_Solver", "Strong_Team_Collaborator", "Highly_Engaged_Employee"],
        
        # Mixed performance
        ["Highly_Engaged_Employee", "Career_Concerns", "Strong_Team_Collaborator"],
        ["High_Performance_Contributor", "Work_Overload_Stress", "Strong_Team_Collaborator"],
        ["Innovative_Problem_Solver", "Lack_of_Work_Life_Balance", "Job_Satisfaction_Champion"],
        
        # Struggling employees
        ["Work_Overload_Stress", "Lack_of_Work_Life_Balance", "Career_Concerns"],
        ["Lack_of_Engagement", "Feeling_Undervalued", "Recognition_Gap"],
        ["Career_Concerns", "Recognition_Gap", "Feeling_Undervalued"],
        
        # Growth potential
        ["Career_Concerns", "Strong_Team_Collaborator", "Innovative_Problem_Solver"],
        ["Feeling_Undervalued", "High_Performance_Contributor", "Recognition_Gap"],
        ["Work_Overload_Stress", "Highly_Engaged_Employee", "Lack_of_Work_Life_Balance"],
        
        # New joiners
        ["Highly_Engaged_Employee", "Job_Satisfaction_Champion", "Career_Concerns"],
        ["Strong_Team_Collaborator", "Innovative_Problem_Solver", "Work_Overload_Stress"],
        
        # Senior employees
        ["High_Performance_Contributor", "Work_Overload_Stress", "Job_Satisfaction_Champion"],
        ["Highly_Engaged_Employee", "Strong_Team_Collaborator", "Lack_of_Work_Life_Balance"],
        
        # Mixed scenarios
        ["Recognition_Gap", "Innovative_Problem_Solver", "Strong_Team_Collaborator"],
        ["Lack_of_Work_Life_Balance", "High_Performance_Contributor", "Career_Concerns"],
        ["Feeling_Undervalued", "Highly_Engaged_Employee", "Work_Overload_Stress"],
        ["Career_Concerns", "Job_Satisfaction_Champion", "Recognition_Gap"]
    ]

    # Shuffle the employee types list
    random.shuffle(employee_types)

    for i in range(num_entries):
        behaviors = employee_types[i % len(employee_types)]  # Cycle through the shuffled behavior combinations
        # Shuffle the behaviors for this specific employee
        random.shuffle(behaviors)
        
        emp_id = generate_sequential_emp_id(i)
        onboarding_exp = generate_onboarding_data()
        behavior_distribution = distribute_behavior_days(
            (datetime.now() - onboarding_exp["Joining_Date"]).days, 
            behaviors
        )
        
        activity_data = generate_activity_data(onboarding_exp["Joining_Date"], behavior_distribution)
        leave_data = generate_leave_data(emp_id, onboarding_exp["Joining_Date"], behavior_distribution)
        performance_data = generate_performance_data(emp_id, onboarding_exp["Joining_Date"], behavior_distribution)
        rewards = generate_reward_data(
            emp_id, 
            behavior_distribution,
            onboarding_exp["Joining_Date"], 
            (datetime.now() - onboarding_exp["Joining_Date"]).days
        )
        vibe_scores = calculate_vibe_scores(onboarding_exp["Joining_Date"], behavior_distribution)
        
        dataset.append({
            "Employee_ID": emp_id,
            "Employee_Type": f"Type_{i+1}",
            "Behavior_Tags": behaviors,
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

if __name__ == "__main__":
    file_path = os.path.expanduser("output.json")  # Saves to Desktop
    with open(file_path, "w") as file:
        json.dump(generate_dummy_data(20), file, indent=4, default=json_serial)

    print(f"JSON file successfully created at {file_path}")