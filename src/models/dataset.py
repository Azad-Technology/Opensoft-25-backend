from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime , date

class VibeData(BaseModel):
    response_date: datetime
    vibe_score: int
    emotion_zone: str

class RewardData(BaseModel):
    award_type: str
    award_date: datetime
    reward_points: int

class PerformanceData(BaseModel):
    review_period: str
    performance_rating: int
    manager_feedback: str
    promotion_consideration: bool

class OnboardingData(BaseModel):
    joining_date: datetime
    onboarding_feedback: str
    mentor_assigned: bool
    initial_training_completed: bool

class LeaveData(BaseModel):
    leave_type: str
    leave_days: int
    leave_start_date: datetime
    leave_end_date: datetime

class ActivityData(BaseModel):
    date: datetime
    teams_messages_sent: int
    emails_sent: int
    meetings_attended: int
    work_hours: Optional[float]

class ScheduleEntry(BaseModel):
    date: date
    title: str
    note: str

class TicketEntry(BaseModel):
    title: str
    description: str

class VibeSubmission(BaseModel):
    vibe_score: int = Field(..., gt=0, lt=6)

