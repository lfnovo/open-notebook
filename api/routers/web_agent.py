from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.web_agent_service import compile_study_guide, StudyGuideRequest, StudyGuideResponse
import traceback

router = APIRouter()

@router.post("/compile-guide", response_model=StudyGuideResponse, summary="Compile a web-enhanced study guide")
async def compile_guide_endpoint(request: StudyGuideRequest):
    try:
        response = await compile_study_guide(request)
        return response
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
