from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.models import AIInsight, Patient
from src.app.services.genai_client import GenAIError, generate_patient_summary

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


PROMPT_VERSION = "v1"
KIND_PATIENT_SUMMARY = "patient_summary"


def build_patient_summary_prompt(
    *,
    patient_external_id: str,
    report_text: str | None,
    report_data: dict | None,
    language: str,
) -> str:
    # Keep PHI out: only include external_id (which should be a ticket ID) + test values.
    # If external_id can be PHI, replace it with a facility-generated token.
    return (
        f"Language: {language}.\n"
        f"Patient ticket: {patient_external_id}.\n\n"
        "Task: Summarize the preventive health checkup results for the patient.\n"
        "Requirements:\n"
        "- Use short sections with headings: Overview, Highlights, Concerns, Suggested Follow-ups, Lifestyle Notes.\n"
        "- Be factual. If a reference range isn't provided, don't invent it.\n"
        "- Do NOT give a diagnosis. Use phrasing like 'may indicate' and 'consult a physician'.\n"
        "- Keep it within 200-350 words.\n\n"
        f"Report text (may be empty):\n{report_text or ''}\n\n"
        f"Structured data (JSON, may be empty):\n{json.dumps(report_data or {}, ensure_ascii=False)}\n"
    )


def get_or_generate_patient_summary(
    db: Session,
    *,
    patient_id: int,
    report_text: str | None,
    report_data: dict | None,
    language: str,
    force_regenerate: bool,
) -> AIInsight:
    try:
        patient = db.get(Patient, patient_id)
        if patient is None:
            logger.info("insights.summary patient_not_found patient_id=%s", patient_id)
            raise ValueError("patient not found")

        cached = None
        if not force_regenerate:
            cached = (
                db.execute(
                    select(AIInsight)
                    .where(
                        AIInsight.patient_id == patient_id,
                        AIInsight.kind == KIND_PATIENT_SUMMARY,
                        AIInsight.prompt_version == PROMPT_VERSION,
                    )
                    .order_by(AIInsight.created_at.desc())
                )
                .scalars()
                .first()
            )
        if cached is not None:
            logger.info("insights.summary cache_hit patient_id=%s", patient_id)
            return cached

        prompt = build_patient_summary_prompt(
            patient_external_id=str(getattr(patient, "external_id")),
            report_text=report_text,
            report_data=report_data,
            language=language,
        )

        result = generate_patient_summary(prompt)

        insight = AIInsight(
            patient_id=patient_id,
            kind=KIND_PATIENT_SUMMARY,
            prompt_version=PROMPT_VERSION,
            model=getattr(result, "model", ""),
            input_json=json.dumps(
                {
                    "report_text": report_text,
                    "report_data": report_data,
                    "language": language,
                },
                ensure_ascii=False,
            ),
            output_text=getattr(result, "text", ""),
            created_at=_utcnow(),
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        logger.info(
            "insights.summary generated patient_id=%s insight_id=%s",
            patient_id,
            getattr(insight, "id", None),
        )
        return insight
    except GenAIError as e:
        logger.error("insights.summary genai_error patient_id=%s err=%s", patient_id, e)
        raise RuntimeError(str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.error("insights.summary error patient_id=%s err=%s", patient_id, e)
        raise
