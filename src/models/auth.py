# src/auth/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: EmailStr
    name: str
    role: str
    employee_id: str
    created_at: datetime
    
class OnboardingRequest(BaseModel):
    role_type: str = "employee"
    name: str
    role: str
    employee_id: str
    email: EmailStr
    password: str