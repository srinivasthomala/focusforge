from pydantic import BaseModel
from typing import List, Literal


# Default blocklist for users who haven't customized theirs (mirrors the
# extension's built-in default so both agree before the first sync).
DEFAULT_BLOCKLIST = ["youtube.com", "twitter.com", "reddit.com"]

BlockingMode = Literal["focus-only", "always"]


class LogEntry(BaseModel):
    userId: str = ""  # server-assigned from the caller's credential; ignored if sent
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
    refresh: bool = False


class SummaryResponse(BaseModel):
    summary: str
    model: str
    cached: bool
    generatedAt: str


class ApiKeyCreateRequest(BaseModel):
    label: str = ""


class ApiKeyInfo(BaseModel):
    id: int
    prefix: str
    label: str
    createdAt: str
    lastUsedAt: str | None = None


class ApiKeyCreateResponse(ApiKeyInfo):
    key: str  # plaintext, returned exactly once at creation


class SettingsData(BaseModel):
    blocklist: List[str]
    blockingMode: BlockingMode


