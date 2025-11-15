from fastapi import APIRouter
from app.services.test_service import match_guru

router = APIRouter()

@router.post("/")
def post_test_result(payload: dict):
    answers = payload.get("answers", [])
    matched = match_guru(answers)
    return {"matched_guru": matched}
