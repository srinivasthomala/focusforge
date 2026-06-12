from pydantic import BaseModel
from typing import List


class LogEntry(BaseModel):
    userId: str
    timestamp: str
    url: str
    domain: str
    minutesActive: float
    isFocusSession: bool
    isDistractionAttempt: bool


class LogBatch(BaseModel):
    logs: List[LogEntry]


class WeekData(BaseModel):
    date: str
    minutes: int


class DashboardResponse(BaseModel):
    todayFocusMinutes: int
    todaySessions: int
    distractionAttempts: int
    topDistractions: List[str]
    aiSummary: str
    week: List[WeekData]


class SummaryRequest(BaseModel):
    userId: str = "default-user"
    refresh: bool = False


class SummaryResponse(BaseModel):
    summary: str
    model: str
    cached: bool
    generatedAt: str


