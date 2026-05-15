"""
Data validation API routes

GENE-QC 지표설계 명세서 v2.0 기준 — Completeness · Plausibility · Conformance
28개 지표 전체를 `validation_service.run_validation()` 으로 위임 실행합니다.
검증 결과는 ValidationJob 테이블에 영속 저장됩니다.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import UPLOADS_DIR
from app.db.session import SessionLocal, get_db
from app.models.base import DataFile as DataFileModel
from app.models.base import Project as ProjectModel
from app.models.base import ValidationJob
from app.services.validation_service import (
    METRIC_METADATA,
    _infer_data_type,
    run_validation,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# 데이터 타입별 결측률 임계값 (옛 ValidationRule 호환용)
LEGACY_THRESHOLD_KEYS = {
    "genomics": "dna_threshold",
    "transcriptomics": "rna_threshold",
    "proteomics": "protein_threshold",
    "metabolomics": "methyl_threshold",
}


class LegacyValidationRule(BaseModel):
    """프론트엔드 하위 호환을 위한 단순 임계값 규칙 스키마"""
    dna_threshold: float = 1.0
    rna_threshold: float = 20.0
    protein_threshold: float = 25.0
    methyl_threshold: float = 25.0
    batch_effect_threshold: float = 5.0
    sample_matching_enabled: bool = True
    range_validation_enabled: bool = True


class ValidationExecuteRequest(BaseModel):
    """명세서 §5 기준 검증 실행 요청 스키마"""
    enabled_metrics: Optional[List[str]] = Field(None, alias="enabledMetrics")
    params_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(None, alias="paramsOverrides")

    class Config:
        populate_by_name = True


# ───────────────────────── 헬퍼 ─────────────────────────


def _legacy_params_overrides(rules: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    옛 임계값 7필드(dna/rna/protein/methyl_threshold 등) → 28개 지표용 params_overrides 변환
    """
    overrides: Dict[str, Dict[str, Any]] = {}

    # 결측률 임계값 — comp_C002 / comp_F003 (글로벌 평균)
    thresholds = [
        rules.get("dna_threshold"),
        rules.get("rna_threshold"),
        rules.get("protein_threshold"),
        rules.get("methyl_threshold"),
    ]
    valid_thresholds = [t for t in thresholds if isinstance(t, (int, float))]
    if valid_thresholds:
        avg = sum(valid_thresholds) / len(valid_thresholds)
        overrides["comp_C002"] = {"threshold": avg}
        overrides["comp_F003"] = {"threshold": avg}

    return overrides


def _file_data_types_for_project(db: Session, project_id: int) -> Dict[str, str]:
    """프로젝트에 등록된 파일들의 dataType 매핑 — DB → 파일명 추론 순"""
    file_map: Dict[str, str] = {}
    files = db.query(DataFileModel).filter(DataFileModel.project_id == project_id).all()
    for f in files:
        if f.data_type:
            file_map[f.name] = f.data_type
        else:
            file_map[f.name] = _infer_data_type(f.name)
    return file_map


# ───────────────────────── 백그라운드 실행 ─────────────────────────


def _run_validation_task(
    job_id: str,
    project_id: int,
    enabled_metrics: Optional[List[str]],
    params_overrides: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    """validation_service.run_validation 실행 + ValidationJob 영속화"""
    db = SessionLocal()
    try:
        job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
        if not job:
            logger.error(f"[Job {job_id}] ValidationJob row not found")
            return

        project_dir = UPLOADS_DIR / f"project_{project_id}" / "raw"
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")

        # 파일별 dataType 매핑
        file_data_types = _file_data_types_for_project(db, project_id)

        # paramsOverrides 가 비어있고 프로젝트에 옛 임계값이 저장되어 있으면 자동 적용
        effective_overrides: Dict[str, Dict[str, Any]] = dict(params_overrides or {})
        if not effective_overrides:
            project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
            if project and project.legacy_validation_thresholds:
                effective_overrides = _legacy_params_overrides(
                    project.legacy_validation_thresholds
                )
                logger.info(
                    f"[Job {job_id}] Applied legacy thresholds → params_overrides: {effective_overrides}"
                )

        logger.info(f"[Job {job_id}] Starting validation for project {project_id}")
        results = run_validation(
            project_dir=project_dir,
            file_data_types=file_data_types,
            enabled_metrics=enabled_metrics,
            params_overrides=effective_overrides,
        )

        # 프로젝트의 dataType별 품질점수 업데이트 (5종 일관)
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if project:
            scores = results.get("completeness_scores", {}) or {}

            def _set_score(attr: str, key: str) -> None:
                if scores.get(key) is not None:
                    setattr(project, attr, scores[key])

            _set_score("genomics_quality_score", "genomics")
            _set_score("transcriptomics_quality_score", "transcriptomics")
            _set_score("proteomics_quality_score", "proteomics")
            _set_score("metabolomics_quality_score", "metabolomics")
            _set_score("metadata_quality_score", "metadata")

            # 옛 컬럼도 동기화 (프론트 하위 호환)
            project.genomics_quality_score = project.genomics_quality_score or scores.get("genomics")
            project.dna_quality_score = project.genomics_quality_score
            project.rna_quality_score = project.transcriptomics_quality_score
            project.protein_quality_score = project.proteomics_quality_score
            project.methyl_quality_score = project.metabolomics_quality_score

            available = [v for v in scores.values() if isinstance(v, (int, float))]
            if available:
                project.quality_score = sum(available) / len(available)

            project.validation_status = "검증완료" if results.get("all_passed") else "처리중"

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.results = results
        db.commit()
        logger.info(f"[Job {job_id}] Validation completed")

    except Exception as exc:
        logger.exception(f"[Job {job_id}] Validation failed")
        try:
            job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.failed_at = datetime.utcnow()
                job.error_message = str(exc)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


# ───────────────────────── 엔드포인트 ─────────────────────────


@router.post("/execute")
async def execute_validation(
    project_id: int,
    background_tasks: BackgroundTasks,
    payload: Optional[ValidationExecuteRequest] = Body(None),
    db: Session = Depends(get_db),
):
    """
    프로젝트 데이터에 대한 GENE-QC 28개 지표 검증 실행

    Body (선택):
    {
      "enabledMetrics": ["comp_F001", "comp_C002", ...],
      "paramsOverrides": { "comp_C002": {"threshold": 20.0} }
    }
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    enabled_metrics: Optional[List[str]] = None
    params_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    if payload:
        enabled_metrics = payload.enabled_metrics
        params_overrides = payload.params_overrides

    job_id = str(uuid.uuid4())
    job = ValidationJob(
        job_id=job_id,
        project_id=project_id,
        status="processing",
        enabled_metrics=enabled_metrics,
        params_overrides=params_overrides,
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(
        _run_validation_task,
        job_id=job_id,
        project_id=project_id,
        enabled_metrics=enabled_metrics,
        params_overrides=params_overrides,
    )

    return {
        "jobId": job_id,
        "status": "processing",
        "message": "GENE-QC validation job started",
        "estimatedTime": 30,
        "enabledMetricsCount": len(enabled_metrics) if enabled_metrics else len(METRIC_METADATA),
    }


@router.get("/status/{job_id}")
async def get_validation_status(job_id: str, db: Session = Depends(get_db)):
    """검증 작업 상태 조회 (DB 영속화 기반)"""
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload: Dict[str, Any] = {
        "jobId": job.job_id,
        "projectId": job.project_id,
        "status": job.status,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        "failedAt": job.failed_at.isoformat() if job.failed_at else None,
        "enabledMetrics": job.enabled_metrics,
        "paramsOverrides": job.params_overrides,
    }
    if job.status == "completed":
        payload["results"] = job.results
    if job.status == "failed":
        payload["error"] = job.error_message
    return payload


@router.post("/rules/{project_id}")
async def save_validation_rules(
    project_id: int,
    rules: LegacyValidationRule,
    db: Session = Depends(get_db),
):
    """
    [하위 호환] 프로젝트의 결측률 임계값 7필드 저장.
    `Project.legacy_validation_thresholds` JSON 컬럼에 영속 저장합니다.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    payload = rules.model_dump()
    project.legacy_validation_thresholds = payload
    db.commit()

    return {
        "message": "Validation thresholds saved",
        "project_id": project_id,
        "rules": payload,
        "paramsOverrides": _legacy_params_overrides(payload),
    }


@router.get("/rules/{project_id}")
async def get_validation_rules(project_id: int, db: Session = Depends(get_db)):
    """[하위 호환] 프로젝트의 결측률 임계값 7필드 조회 (없으면 기본값)"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if project.legacy_validation_thresholds:
        return project.legacy_validation_thresholds
    return LegacyValidationRule().model_dump()


@router.get("/download-report/{project_id}")
async def download_validation_report(project_id: int, db: Session = Depends(get_db)):
    """
    검증 결과 보고서 PDF 다운로드 (reportlab 기반, 크로스 플랫폼)
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"reportlab not installed: {e}. Run 'pip install reportlab'.",
        )

    # 가장 최근 완료된 검증 작업 조회
    job = (
        db.query(ValidationJob)
        .filter(
            ValidationJob.project_id == project_id,
            ValidationJob.status == "completed",
        )
        .order_by(ValidationJob.completed_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"No completed validation results found for project {project_id}",
        )

    results = job.results or {}

    # 한글 폰트 등록 (Mac/Linux 공용 후보)
    font_name = "Helvetica"
    for font_path in [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont("KoreanFont", font_path))
                font_name = "KoreanFont"
                break
            except Exception:
                continue

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Title"], fontName=font_name, fontSize=18, leading=22
    )
    body_style = ParagraphStyle(
        "body", parent=styles["BodyText"], fontName=font_name, fontSize=10, leading=14
    )
    h2_style = ParagraphStyle(
        "h2", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=16
    )

    story = []
    story.append(Paragraph("GENE-QC 데이터 품질 검증 결과 보고서", title_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            f"프로젝트 ID: {project_id} &nbsp;&nbsp;&nbsp; 작업 ID: {job.job_id}",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f"검증 완료: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else 'N/A'}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # 요약
    summary_rows = [
        ["전체 파일", str(results.get("total_files", 0))],
        ["통과 파일", str(results.get("passed_files", 0))],
        ["통과 지표 (pass)", str(results.get("pass_count", 0))],
        ["경고 지표 (warning)", str(results.get("warning_count", 0))],
        ["실패 지표 (fail)", str(results.get("fail_count", 0))],
        ["전체 결과", "통과" if results.get("all_passed") else "실패"],
    ]
    summary_table = Table(summary_rows, colWidths=[6 * cm, 10 * cm])
    summary_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.6 * cm))

    # 지표별 결과
    story.append(Paragraph("지표별 상세 결과", h2_style))
    story.append(Spacer(1, 0.2 * cm))

    metrics = results.get("metrics", []) or []
    metric_rows = [["metricId", "dimension", "severity", "file", "passed", "value", "details"]]
    for m in metrics[:200]:  # 너무 길어지지 않게 200개로 컷
        passed = m.get("passed")
        passed_str = "—" if passed is None else ("PASS" if passed else "FAIL")
        details = str(m.get("details", ""))
        if len(details) > 60:
            details = details[:57] + "..."
        metric_rows.append([
            str(m.get("metricId", "")),
            str(m.get("dimension", "")),
            str(m.get("severity", "")),
            str(m.get("filename", ""))[:18],
            passed_str,
            str(m.get("value", "")),
            details,
        ])
    metric_table = Table(metric_rows, repeatRows=1)
    metric_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(metric_table)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=validation_report_project_{project_id}.pdf"
            )
        },
    )
