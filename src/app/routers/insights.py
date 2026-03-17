from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.app.auth.security import require_api_key
from src.app.db.db import get_db
from src.app.models.schemas import AIInsightOut, PatientSummaryGenerateIn
from src.app.services.insights import get_or_generate_patient_summary

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/insights/patients/{patient_id}/summary", response_model=AIInsightOut)
def generate_patient_summary(
    patient_id: int,
    payload: PatientSummaryGenerateIn,
    db: Session = Depends(get_db),
):
    try:
        return get_or_generate_patient_summary(
            db,
            patient_id=patient_id,
            report_text=payload.report_text,
            report_data=payload.report_data,
            language=payload.language,
            force_regenerate=payload.force_regenerate,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"GenAI unavailable: {e}") from e
