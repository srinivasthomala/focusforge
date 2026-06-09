from fastapi import APIRouter
from app.models import SummaryRequest, SummaryResponse

router = APIRouter()


def generate_fake_summary(logs) -> str:
    """
    Generate a fake AI summary based on log counts.
    
    In production, this would call Claude or OpenAI with the actual logs.
    """
    if not logs:
        return "No activity data available yet. Start a focus session to track your progress!"
    
    total_minutes = sum(log.minutesActive for log in logs)
    focus_sessions = sum(1 for log in logs if log.isFocusSession)
    distraction_attempts = sum(1 for log in logs if log.isDistractionAttempt)
    
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    
    summary = f"Based on {len(logs)} activity entries: "
    
    if hours > 0:
        summary += f"You spent {hours}h {minutes}m "
    else:
        summary += f"You spent {minutes}m "
    
    summary += f"across {focus_sessions} focus session(s). "
    
    if distraction_attempts > 0:
        summary += f"You resisted {distraction_attempts} distraction(s). "
    
    if focus_sessions > 2:
        summary += "Great consistency today!"
    elif focus_sessions > 0:
        summary += "Keep building that focus habit!"
    else:
        summary += "Try starting a focus session to boost productivity."
    
    return summary


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(request: SummaryRequest):
    """
    Generate an AI summary from activity logs.
    
    Currently returns a fake summary. Will integrate with Claude/OpenAI later.
    """
    summary_text = generate_fake_summary(request.logs)
    return SummaryResponse(summary=summary_text)


