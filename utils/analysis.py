from datetime import datetime, timezone
import random

import pytz


def get_vibe(score):
    if not isinstance(score, (int, float)):
        return "unknown"
    if score>4.5 and score<=5:
        return "Excited"
    elif score>3.5 and score<=4.5:
        return "Happy"
    elif score>2.5 and score<=3.5:
        return "Okay"
    elif score>1.5 and score<=2.5:
        return "Sad"
    elif score>=0 and score<=1.5:
        return "Frustrated"
    else:
        return "unknown"
    
def serialize_datetime(obj):
    """Helper function to serialize datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj
    
def process_doc(doc):
            if not doc:
                return {}
            processed = {}
            for key, value in doc.items():
                if key == '_id':
                    processed[key] = str(value)
                elif isinstance(value, datetime):
                    processed[key] = value.isoformat()
                else:
                    processed[key] = value
            return processed
        
def convert_to_ist(utc_dt):
    """Helper function to convert UTC datetime to IST"""
    if not utc_dt:
        return None
    if not utc_dt.tzinfo:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    ist_tz = pytz.timezone('Asia/Kolkata')
    return utc_dt.astimezone(ist_tz)
    
def get_project_details():
    projects = [
        {
            'id': '1',
            'name': 'Website Redesign',
            'priority': 'high',
            'status': 'in-progress',
            'startDate': '2024-03-01',
            'endDate': '2024-04-15',
            'progress': '65',
            'assignees': ['Sarah J.', 'Michael C.'],
        },
        {
            'id': '2',
            'name': 'Mobile App Development',
            'priority': 'medium',
            'status': 'not-started',
            'startDate': '2024-04-01',
            'endDate': '2024-06-30',
            'progress': '0',
            'assignees': ['Emily D.', 'John S.'],
        },
        {
            'id': '3',
            'name': 'Data Migration',
            'priority': 'low',
            'status': 'completed',
            'startDate': '2024-02-15',
            'endDate': '2024-03-15',
            'progress': '100',
            'assignees': ['Robert K.', 'Lisa M.'],
        },
        {
            'id': '4',
            'name': 'AI Implementation',
            'priority': 'high',
            'status': 'in-progress',
            'startDate': '2024-03-15',
            'endDate': '2024-07-30',
            'progress': '25',
            'assignees': ['David W.', 'Anna P.'],
        },
        {
            'id': '5',
            'name': 'Security Audit',
            'priority': 'high',
            'status': 'not-started',
            'startDate': '2024-04-10',
            'endDate': '2024-05-10',
            'progress': '0',
            'assignees': ['Tom H.', 'Jessica R.'],
        },
        {
            'id': '6',
            'name': 'Cloud Migration',
            'priority': 'medium',
            'status': 'in-progress',
            'startDate': '2024-03-01',
            'endDate': '2024-06-01',
            'progress': '45',
            'assignees': ['Mark L.', 'Sophie B.'],
        },
        {
            'id': '7',
            'name': 'E-commerce Integration',
            'priority': 'high',
            'status': 'not-started',
            'startDate': '2024-05-01',
            'endDate': '2024-07-15',
            'progress': '0',
            'assignees': ['Chris M.', 'Rachel S.'],
        },
        {
            'id': '8',
            'name': 'CRM Implementation',
            'priority': 'medium',
            'status': 'completed',
            'startDate': '2024-01-15',
            'endDate': '2024-03-01',
            'progress': '100',
            'assignees': ['Peter K.', 'Emma T.'],
        },
        {
            'id': '9',
            'name': 'Database Optimization',
            'priority': 'low',
            'status': 'in-progress',
            'startDate': '2024-03-10',
            'endDate': '2024-04-10',
            'progress': '75',
            'assignees': ['James B.', 'Linda W.'],
        },
        {
            'id': '10',
            'name': 'API Development',
            'priority': 'high',
            'status': 'in-progress',
            'startDate': '2024-02-01',
            'endDate': '2024-05-01',
            'progress': '50',
            'assignees': ['Alex M.', 'Nina P.'],
        },
        {
            'id': '11',
            'name': 'User Training Program',
            'priority': 'low',
            'status': 'not-started',
            'startDate': '2024-06-01',
            'endDate': '2024-07-15',
            'progress': '0',
            'assignees': ['Oliver R.', 'Kate S.'],
        },
        {
            'id': '12',
            'name': 'Hardware Upgrade',
            'priority': 'medium',
            'status': 'completed',
            'startDate': '2024-02-01',
            'endDate': '2024-03-01',
            'progress': '100',
            'assignees': ['William T.', 'Helen M.'],
        },
        {
            'id': '13',
            'name': 'DevOps Implementation',
            'priority': 'high',
            'status': 'in-progress',
            'startDate': '2024-03-15',
            'endDate': '2024-06-15',
            'progress': '35',
            'assignees': ['George P.', 'Julia K.'],
        },
        {
            'id': '14',
            'name': 'Quality Assurance',
            'priority': 'medium',
            'status': 'not-started',
            'startDate': '2024-04-15',
            'endDate': '2024-05-15',
            'progress': '0',
            'assignees': ['Daniel F.', 'Mary B.'],
        },
        {
            'id': '15',
            'name': 'Network Infrastructure',
            'priority': 'high',
            'status': 'in-progress',
            'startDate': '2024-03-01',
            'endDate': '2024-08-01',
            'progress': '15',
            'assignees': ['Steve C.', 'Laura H.'],
        }
    ]
    
    # Randomly select 3 projects
    return random.sample(projects, 3)
    
    
MOCK_DATA = {
    "departments": ["Technology Consulting", "Strategy & Operations", "Risk Advisory", "Financial Advisory"],
    "locations": ["New York", "London", "Singapore", "Mumbai", "Sydney"],
    "managers": ["Jane Smith", "Michael Johnson", "Sarah Williams", "David Chen"],
    "skills": [
        "Cloud Architecture", "Digital Transformation", "Project Management", "Solution Design",
        "Data Analytics", "AI/ML", "Blockchain", "Cybersecurity"
    ],
    "certifications": [
        "AWS Certified Solutions Architect", "Certified Scrum Master", "ITIL Foundation", "PMP",
        "Google Cloud Professional", "Azure Solutions Architect", "CISSP", "Six Sigma Black Belt"
    ]
}