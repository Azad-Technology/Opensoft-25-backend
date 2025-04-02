import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from utils.app_logger import setup_logger
from utils.auth import get_current_user
from utils.config import get_async_database

router = APIRouter()
async_db = get_async_database()
logger = setup_logger("src/routers/common.py")

MOCK_DATA = {
    "departments": [
        "Technology Consulting",
        "Strategy & Operations",
        "Risk Advisory",
        "Financial Advisory",
    ],
    "locations": ["New York", "London", "Singapore", "Mumbai", "Sydney"],
    "managers": ["Jane Smith", "Michael Johnson", "Sarah Williams", "David Chen"],
    "skills": [
        "Cloud Architecture",
        "Digital Transformation",
        "Project Management",
        "Solution Design",
        "Data Analytics",
        "AI/ML",
        "Blockchain",
        "Cybersecurity",
    ],
    "certifications": [
        "AWS Certified Solutions Architect",
        "Certified Scrum Master",
        "ITIL Foundation",
        "PMP",
        "Google Cloud Professional",
        "Azure Solutions Architect",
        "CISSP",
        "Six Sigma Black Belt",
    ],
}


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Get employee profile information
    """
    try:
        employee_id = current_user.get("employee_id")
        # Get user data from database
        user = await async_db.users.find_one({"employee_id": employee_id})
        if not user:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Random selection for mock data
        random.seed(employee_id)  # Use employee_id as seed for consistent random data

        profile_data = {
            "name": user.get("name"),
            "profilePic": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
            "employeeId": user.get("employee_id"),
            "jobTitle": user.get("role", "Consultant"),
            "department": random.choice(MOCK_DATA["departments"]),
            "doj": user.get("created_at", datetime.now()).strftime("%Y-%m-%d"),
            "location": random.choice(MOCK_DATA["locations"]),
            "manager": random.choice(MOCK_DATA["managers"]),
            "email": user.get("email"),
            "phone": f"+1 (555) {random.randint(100,999)}-{random.randint(1000,9999)}",
            "extension": str(random.randint(1000, 9999)),
            "backgroundDetails": {
                "employmentType": "Full-time",
                "skills": random.sample(MOCK_DATA["skills"], 4),
                "certifications": random.sample(MOCK_DATA["certifications"], 3),
                "experience": [
                    {
                        "company": "Previous Tech Corp",
                        "role": "Technology Consultant",
                        "duration": "2019-2022",
                    },
                    {
                        "company": "Start-up Solutions",
                        "role": "Senior Developer",
                        "duration": "2017-2019",
                    },
                ],
                "education": [
                    {
                        "degree": "Master of Science in Computer Science",
                        "institution": "Stanford University",
                        "year": "2017",
                    },
                    {
                        "degree": "Bachelor of Engineering",
                        "institution": "MIT",
                        "year": "2015",
                    },
                ],
            },
            "documents": {
                "compliance": [
                    {
                        "name": "Code of Conduct",
                        "status": "Completed",
                        "date": (datetime.now()).strftime("%Y-%m-%d"),
                    },
                    {
                        "name": "Data Privacy Training",
                        "status": "Due",
                        "date": (datetime.now()).strftime("%Y-%m-%d"),
                    },
                ],
                "hrDocs": [
                    {
                        "name": "Offer Letter",
                        "type": "PDF",
                        "uploadDate": user.get("created_at", datetime.now()).strftime(
                            "%Y-%m-%d"
                        ),
                        "url": "https://example.com/docs/offer_letter.pdf",
                    },
                    {
                        "name": "Latest Payslip",
                        "type": "PDF",
                        "uploadDate": datetime.now().strftime("%Y-%m-%d"),
                        "url": "https://example.com/docs/payslip.pdf",
                    },
                ],
            },
        }

        return profile_data

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving profile: {e!s}")
        raise HTTPException(
            status_code=500, detail="Error retrieving profile information"
        )
