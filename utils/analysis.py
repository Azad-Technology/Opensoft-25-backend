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
    
def get_project_details():
    return [
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
        }
    ]
    
    
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