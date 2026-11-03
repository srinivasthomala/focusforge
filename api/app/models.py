import math

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

# Ingest bounds. Long URLs (big query strings) are normal, so they are trimmed
# rather than rejected: the extension retries a failed batch, and one long URL
# must not poison the whole queue.
MAX_LOGS_PER_BATCH = 1000
MAX_URL_LENGTH = 2048
MAX_DOMAIN_LENGTH = 253
MAX_MINUTES_PER_ENTRY = 24 * 60


# Default blocklist for users who haven't customized theirs (mirrors the
# extension's built-in default so both agree before the first sync).
# Empty on purpose: nothing is blocked until the user chooses what to block.
DEFAULT_BLOCKLIST: list[str] = []

BlockingMode = Literal["focus-only", "always"]


class LogEntry(BaseModel):
    userId: str = Field("", max_length=255)  # server-assigned; ignored if sent
    timestamp: str = Field(max_length=64)
    url: str
    domain: str
    minutesActive: float
    isFocusSession: bool
    isDistractionAttempt: bool

    @field_validator("url")
    @classmethod
    def _trim_url(cls, v: str) -> str:
        return v[:MAX_URL_LENGTH]

    @field_validator("domain")
    @classmethod
    def _trim_domain(cls, v: str) -> str:
        return v[:MAX_DOMAIN_LENGTH]

    @field_validator("minutesActive")
    @classmethod
    def _clamp_minutes(cls, v: float) -> float:
        # A laptop asleep mid-session can report days; NaN/inf can't be stored.
        if not math.isfinite(v):
            raise ValueError("minutesActive must be a finite number")
        return min(max(v, 0.0), MAX_MINUTES_PER_ENTRY)


class LogBatch(BaseModel):
    logs: List[LogEntry] = Field(max_length=MAX_LOGS_PER_BATCH)


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
    # The day the metrics reflect (ISO date) and whether that's the actual today.
    # When a user has no activity today, the dashboard centers on their most
    # recent active day instead of going blank.
    asOf: str = ""
    isToday: bool = True


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


