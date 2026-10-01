from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import EmailStr


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    venue: str
    capacity: int
    organizer: str
    status: str = "Open"


class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int
    student_name: str
    roll_number: str
    email: EmailStr


class EventCreate(SQLModel):
    title: str
    venue: str
    capacity: int
    organizer: str
    status: str = "Open"


class EventUpdate(SQLModel):
    title: Optional[str] = None
    venue: Optional[str] = None
    capacity: Optional[int] = None
    organizer: Optional[str] = None
    status: Optional[str] = None


class ReservationCreate(SQLModel):
    student_name: str
    roll_number: str
    email: EmailStr