"""
Data validation API routes

GENE-QC 지표설계 명세서 v2.0 기준 — Completeness · Plausibility · Conformance
28개 지표 전체를 `validation_service.run_validation()` 으로 위임 실행합니다.
검증 결과는 ValidationJob 테이블에 영속 저장됩니다.
"""

from __future__ import annotations

import io
import logging
import math
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import UPLOADS_DIR
from app.db.session import SessionLocal, get_db
from app.models.base import DataFile as DataFileModel
from app.models.base import Project as ProjectModel
from app.models.base import ValidationJob
from app.services.project_storage import (
    ProjectDataNotFoundError,
    ensure_project_raw_dir,
    validate_ai_validation_prerequisites,
)
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


def _to_json_safe(value: Any) -> Any:
    """
    검증 결과를 MySQL JSON 컬럼에 안전하게 저장할 수 있도록 변환합니다.

    validation_service 내부에서는 pandas/numpy 연산 결과(`numpy.bool_`,
    `numpy.int64`, `numpy.float64`, `numpy.ndarray`, `pd.Timestamp` 등)가
    그대로 dict에 들어가는 경우가 많은데, Python 내장 `json` 모듈은 이런
    타입을 직렬화하지 못해 `TypeError: Object of type bool is not JSON
    serializable` 오류가 발생합니다.

    추가로 numpy NaN/Infinity는 JSON 표준에 없으므로 `None`으로 치환합니다.
    """
    if value is None:
        return None
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        f = float(value)
        return None if not math.isfinite(f) else f
    if isinstance(value, np.ndarray):
        return [_to_json_safe(v) for v in value.tolist()]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]
    return value


def _status_from_metric(passed: Optional[bool], severity: str) -> Optional[str]:
    """
    validation_service 의 (passed, severity) → 프론트엔드 RuleResult.status 변환.
    `passed is None`(건너뜀)은 None을 돌려주어 호출부에서 제외할 수 있게 한다.
    """
    if passed is None:
        return None
    if passed:
        return "pass"
    if severity in ("fatal", "error"):
        return "fail"
    if severity == "convention":
        return "convention"
    # warning, characterization 등은 모두 경고로 묶는다
    return "warning"


def _build_rule_results(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    validation_service.run_validation()의 `metrics` 리스트를
    프론트엔드 ValidationResults 컴포넌트가 기대하는 RuleResult 형태로 변환한다.
    건너뛴(skipped) 지표는 제외한다.
    """
    rule_results: List[Dict[str, Any]] = []
    for m in metrics:
        severity = m.get("severity") or "warning"
        status = _status_from_metric(m.get("passed"), severity)
        if status is None:
            continue

        rule_results.append({
            "ruleId": m.get("metricId", ""),
            "ruleName": m.get("metricName", ""),
            "dimension": m.get("dimension", ""),
            "level": m.get("qualityLevel") or "basic",
            "severity": severity,
            "fileName": m.get("filename") or "(전체)",
            "status": status,
            "message": m.get("details", ""),
            "metricValue": m.get("value"),
            # 임계값은 지표마다 위치가 달라 일괄 추출이 어렵지만,
            # `message` 안에 "(임계값: ...)" 형태로 이미 포함되어 있다.
            "threshold": None,
        })
    return rule_results


def _build_dimension_summary(rule_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """차원별 pass / warning / fail / convention 카운트 집계"""
    dims = ("Completeness", "Plausibility", "Conformance")
    summary: Dict[str, Dict[str, int]] = {
        dim: {"pass": 0, "warning": 0, "fail": 0, "convention": 0, "total": 0}
        for dim in dims
    }
    for r in rule_results:
        dim = r.get("dimension")
        if dim not in summary:
            continue
        status = r.get("status")
        if status in summary[dim]:
            summary[dim][status] += 1
        summary[dim]["total"] += 1
    return summary


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

        project_dir = ensure_project_raw_dir(project_id, db)

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
        raw_results = run_validation(
            project_dir=project_dir,
            file_data_types=file_data_types,
            enabled_metrics=enabled_metrics,
            params_overrides=effective_overrides,
        )

        # validation_service 결과에는 numpy.bool_/float64 등이 섞여 있어
        # MySQL JSON 컬럼에 그대로 넣으면 직렬화 오류가 난다. 한 곳에서 정화한다.
        results = _to_json_safe(raw_results)

        # 프론트엔드(ValidationResults / DimensionSummary)가 기대하는 형태로
        # `metrics` 를 차원별 규칙 리스트와 요약으로 변환해서 추가한다.
        metrics_list = results.get("metrics") or []
        rule_results = _build_rule_results(metrics_list)
        results["rule_results"] = rule_results
        results["dimension_summary"] = _build_dimension_summary(rule_results)

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
        # 직전 commit이 실패해 세션이 오염된 상태일 수 있으므로 먼저 rollback
        try:
            db.rollback()
        except Exception:
            pass
        try:
            job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.failed_at = datetime.utcnow()
                job.error_message = str(exc)
                db.commit()
        except Exception:
            logger.exception(f"[Job {job_id}] Failed to persist failure state")
            db.rollback()
    finally:
        db.close()


# ───────────────────────── AI 일관성 검증 백그라운드 태스크 ─────────────────────────


def _ai_consistency_to_rule_results(payload: Dict[str, Any], min_corr: float) -> List[Dict[str, Any]]:
    """
    원격 MOCHI 일관성 검증 JSON 을 프론트엔드 RuleResult 형태로 변환.
    overall + 모달리티별 4건을 모두 추가해 한 화면에서 차원/정도를 한눈에 보게 한다.
    """
    rule_results: List[Dict[str, Any]] = []
    overall = payload.get("overall_pearson")
    overall_status = "pass" if (isinstance(overall, (int, float)) and overall >= min_corr) else "warning"
    rule_results.append({
        "ruleId": "plau_X002_ai",
        "ruleName": "MOCHI 교차 예측 일관성 (overall)",
        "dimension": "Plausibility",
        "level": "advanced",
        "severity": "warning",
        "fileName": "RNA ↔ Protein ↔ Methyl",
        "status": overall_status,
        "message": (
            f"세 모달리티 평균 Pearson={overall:.3f} (임계값: {min_corr})"
            if isinstance(overall, (int, float))
            else "전체 Pearson 계산 불가 (관측 데이터 부족)"
        ),
        "metricValue": round(overall, 4) if isinstance(overall, (int, float)) else None,
        "threshold": min_corr,
    })

    per = payload.get("per_modality") or {}
    file_map = payload.get("files") or {}
    for modality in ("rna", "protein", "methyl"):
        m = per.get(modality) or {}
        pearson = m.get("pearson")
        status = "pass" if (isinstance(pearson, (int, float)) and pearson >= min_corr) else "warning"
        rule_results.append({
            "ruleId": f"plau_X002_ai__{modality}",
            "ruleName": f"MOCHI 일관성 — {modality.upper()}",
            "dimension": "Plausibility",
            "level": "advanced",
            "severity": "warning",
            "fileName": file_map.get(modality, modality),
            "status": status,
            "message": (
                f"Pearson={pearson:.3f}, RMSE={m.get('rmse'):.3f}, MAE={m.get('mae'):.3f}, n={m.get('n')}"
                if isinstance(pearson, (int, float)) else "관측 데이터 부족으로 측정 불가"
            ),
            "metricValue": round(pearson, 4) if isinstance(pearson, (int, float)) else None,
            "threshold": min_corr,
        })

    return rule_results


def _run_ai_validation_task(job_id: str, project_id: int, min_correlation: float) -> None:
    """원격 MOCHI 일관성 검증 실행 + ValidationJob 영속화

    AI(Plausibility) 교차 예측 결과와 로컬 표준 검증(Completeness + Conformance)을
    함께 실행해 세 차원이 모두 결과로 표시되도록 합니다.
    """
    from app.services.remote_ai_validation_service import RemoteAICrossValidationService

    db = SessionLocal()
    try:
        job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
        if not job:
            logger.error(f"[Job {job_id}] ValidationJob row not found (AI)")
            return

        project_dir = validate_ai_validation_prerequisites(project_id, db)

        # ── 1. 원격 AI 일관성 검증 (Plausibility) ──────────────────────────
        local_data_dir = UPLOADS_DIR
        logger.info(f"[Job {job_id}] Starting AI cross-prediction validation for project {project_id}")
        svc = RemoteAICrossValidationService()
        payload = svc.execute(project_id=project_id, job_id=job_id, local_data_dir=local_data_dir)

        ai_rule_results = _ai_consistency_to_rule_results(payload, min_corr=min_correlation)

        # ── 2. 로컬 표준 검증 (Completeness + Conformance) ──────────────────
        # Plausibility는 AI 결과로 대체하므로 나머지 두 차원만 실행한다.
        std_rule_results: List[Dict[str, Any]] = []
        if project_dir.exists():
            comp_conf_metrics = [
                mid for mid, meta in METRIC_METADATA.items()
                if meta["dimension"] in ("Completeness", "Conformance")
            ]
            file_data_types = _file_data_types_for_project(db, project_id)
            try:
                std_raw = run_validation(
                    project_dir=project_dir,
                    file_data_types=file_data_types,
                    enabled_metrics=comp_conf_metrics,
                )
                std_results = _to_json_safe(std_raw)
                std_rule_results = _build_rule_results(std_results.get("metrics") or [])
                logger.info(
                    f"[Job {job_id}] Local Completeness/Conformance validation done"
                    f" ({len(std_rule_results)} rules)"
                )
            except Exception as std_exc:
                logger.warning(
                    f"[Job {job_id}] Local standard validation failed (non-fatal): {std_exc}"
                )

        # ── 3. 결과 합산 ─────────────────────────────────────────────────────
        all_rule_results = std_rule_results + ai_rule_results
        dimension_summary = _build_dimension_summary(all_rule_results)

        results = {
            "mode": "ai_consistency",
            "ai_payload": _to_json_safe(payload),
            "rule_results": all_rule_results,
            "dimension_summary": dimension_summary,
            "all_passed": all(r["status"] in ("pass", "convention") for r in all_rule_results),
            "pass_count": sum(1 for r in all_rule_results if r["status"] == "pass"),
            "warning_count": sum(1 for r in all_rule_results if r["status"] == "warning"),
            "fail_count": sum(1 for r in all_rule_results if r["status"] == "fail"),
            "files": [],
            "total_files": 0,
            "passed_files": 0,
        }

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.results = results
        db.commit()
        logger.info(f"[Job {job_id}] AI validation completed")

    except Exception as exc:
        logger.exception(f"[Job {job_id}] AI validation failed")
        try:
            db.rollback()
        except Exception:
            pass
        try:
            job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.failed_at = datetime.utcnow()
                job.error_message = str(exc)
                db.commit()
        except Exception:
            logger.exception(f"[Job {job_id}] Failed to persist AI failure state")
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

    try:
        ensure_project_raw_dir(project_id, db)
    except ProjectDataNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


class AIValidationExecuteRequest(BaseModel):
    """AI 일관성 검증 옵션"""
    min_correlation: float = Field(0.3, alias="minCorrelation", ge=-1.0, le=1.0)

    class Config:
        populate_by_name = True


@router.post("/execute-ai")
async def execute_ai_validation(
    project_id: int,
    background_tasks: BackgroundTasks,
    payload: Optional[AIValidationExecuteRequest] = Body(None),
    db: Session = Depends(get_db),
):
    """
    원격 MOCHI tri-joint 모델을 사용한 AI 일관성 검증 실행

    RNA + Protein + Methyl 세 오믹스 파일이 모두 등록된 프로젝트에서만 의미가 있으며,
    체크포인트 학습 차원과 입력 차원이 다르면 명확한 오류로 실패합니다.

    상태 조회는 일반 검증과 동일하게 `GET /api/validation/status/{job_id}` 를 사용합니다.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    try:
        validate_ai_validation_prerequisites(project_id, db)
    except ProjectDataNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    min_corr = payload.min_correlation if payload else 0.3

    job_id = str(uuid.uuid4())
    job = ValidationJob(
        job_id=job_id,
        project_id=project_id,
        status="processing",
        enabled_metrics=["plau_X002_ai"],
        # mode 표식을 params_overrides 에 보관해 상태 조회 시 일반 검증과 구분 가능
        params_overrides={"_ai_mode": True, "minCorrelation": min_corr},
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(
        _run_ai_validation_task,
        job_id=job_id,
        project_id=project_id,
        min_correlation=min_corr,
    )

    return {
        "jobId": job_id,
        "status": "processing",
        "mode": "ai_consistency",
        "message": "Remote MOCHI cross-prediction validation job started",
        "estimatedTime": 600,
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
    예시 보고서 구조: Executive Summary → Data Overview → Quality by Dimension
                    → Detailed Results → File-Level Summary → Recommendations
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            HRFlowable,
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
    font_name_bold = "Helvetica-Bold"
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
                font_name_bold = "KoreanFont"
                break
            except Exception:
                continue

    # ── 색상 팔레트 ────────────────────────────────────────────────────────
    C_DARK    = colors.HexColor("#2C3E50")
    C_BLUE    = colors.HexColor("#2980B9")
    C_PASS    = colors.HexColor("#27AE60")
    C_WARN    = colors.HexColor("#E67E22")
    C_FAIL    = colors.HexColor("#E74C3C")
    C_HEADER  = colors.HexColor("#1A252F")
    C_ALT     = colors.HexColor("#F2F3F4")
    C_SECTION = colors.HexColor("#D6EAF8")

    # ── 데이터 분석 ────────────────────────────────────────────────────────
    metrics_raw = results.get("metrics", []) or []
    files       = results.get("files", []) or []
    executed    = [m for m in metrics_raw if m.get("passed") is not None]

    def get_status(m: dict) -> str:
        if m.get("passed") is None:
            return "SKIP"
        if m.get("passed"):
            return "PASS"
        sev = m.get("severity", "")
        return "FAIL" if sev in ("fatal", "error") else "WARNING"

    total_checks  = len(executed)
    passed_count  = sum(1 for m in executed if m.get("passed"))
    warning_count = sum(1 for m in executed if get_status(m) == "WARNING")
    fail_count    = sum(1 for m in executed if get_status(m) == "FAIL")
    pass_rate     = (passed_count / total_checks * 100) if total_checks > 0 else 0.0
    rules_applied = len({m.get("metricId") for m in executed if m.get("metricId")})
    total_files   = results.get("total_files", len(files))

    generated_at = (
        job.completed_at.strftime("%Y-%m-%d %H:%M:%S")
        if job.completed_at
        else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    report_id = (
        f"RPT-{job.completed_at.strftime('%Y%m%d%H%M%S')}"
        if job.completed_at
        else "RPT-UNKNOWN"
    )

    def quality_grade(rate: float) -> str:
        if rate >= 95: return "A (Excellent)"
        if rate >= 80: return "B (Good)"
        if rate >= 60: return "C (Fair)"
        return "D (Poor)"

    def assess(rate: float) -> str:
        if rate >= 90: return "Excellent"
        if rate >= 80: return "Good"
        if rate >= 60: return "Fair"
        if rate >= 40: return "Poor"
        return "Critical"

    grade = quality_grade(pass_rate)

    # 지표 영문 이름 매핑
    METRIC_EN: dict[str, str] = {
        "comp_F001": "File Header Existence",
        "comp_F003": "Overall Data Missing Rate",
        "comp_C001": "Required Sample ID Column",
        "comp_C002": "Column-level Missing Rate",
        "comp_C003": "Row (Sample) Completeness",
        "comp_C004": "Conditional Required Column",
        "comp_X001": "Cross-Dataset Sample Matching Rate",
        "comp_X002": "Common Sample Count",
        "comp_X003": "Metadata-Omics Sample Linkage",
        "plau_C001": "Expression Value Lower Bound",
        "plau_C002": "Expression Value Upper Bound",
        "plau_C003": "IQR-Based Outlier Detection",
        "plau_C004": "Zero-Variance Column Detection",
        "plau_V001": "Sex/Gender Value Set Check",
        "plau_V002": "Age Value Range Check",
        "plau_V003": "Negative Value Check (Raw Count)",
        "plau_T001": "Survival Time Plausibility",
        "plau_T002": "Temporal Plausibility Check",
        "plau_X001": "Omics Subtype Consistency",
        "plau_X002": "Exploratory Batch Separation (PC1/PC2)",
        "conf_F001": "File Format Consistency",
        "conf_C001": "Primary Key Uniqueness",
        "conf_C002": "Expression Data Type Check",
        "conf_C003": "Batch Label Availability",
        "conf_C004": "Sample ID Format Pattern",
        "conf_V001": "Allowed Value Set Check",
        "conf_V002": "Date Format Standard Check",
        "conf_X001": "Cross-Dataset ID Format Consistency",
    }

    def metric_name(m: dict) -> str:
        return METRIC_EN.get(m.get("metricId", ""), m.get("metricName", m.get("metricId", "")))

    DATA_TYPE_DISPLAY: dict[str, str] = {
        "genomics":       "Genomics",
        "transcriptomics":"RNA",
        "proteomics":     "Protein",
        "metabolomics":   "Methylation",
        "metadata":       "Metadata",
        "survival":       "Survival",
        "unknown":        "Unknown",
    }

    # ── 스타일 정의 ───────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def _ps(name: str, parent: str = "BodyText", **kw) -> ParagraphStyle:
        defaults = {"fontName": font_name, "fontSize": 9, "leading": 13}
        defaults.update(kw)
        return ParagraphStyle(name, parent=styles[parent], **defaults)

    title_style  = _ps("rpt_title",    "Title",    fontSize=20, leading=24, textColor=C_DARK)
    sub_style    = _ps("rpt_sub",                  fontSize=11, leading=14, textColor=C_BLUE)
    meta_style   = _ps("rpt_meta",                 fontSize=8,  leading=11, textColor=colors.HexColor("#5D6D7E"))
    h2_style     = _ps("rpt_h2",       "Heading2", fontSize=12, leading=16, textColor=C_DARK,  spaceBefore=8)
    h3_style     = _ps("rpt_h3",       "Heading3", fontSize=10, leading=13, textColor=C_BLUE,  spaceBefore=5)
    body_style   = _ps("rpt_body",                 fontSize=9,  leading=13)
    cell_style   = _ps("rpt_cell",                 fontSize=8,  leading=11)
    small_style  = _ps("rpt_small",                fontSize=7,  leading=10)
    footer_style = _ps("rpt_footer",               fontSize=7.5,leading=10, textColor=colors.HexColor("#7F8C8D"))
    note_style   = _ps("rpt_note",                 fontSize=7.5,leading=11, textColor=colors.HexColor("#5D6D7E"))

    PAGE_W = A4[0] - 4 * cm  # 좌우 2cm 여백 제외 가용 너비

    def base_tbl_style(extra: list | None = None) -> TableStyle:
        cmds = [
            ("FONTNAME",      (0, 0), (-1, -1), font_name),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#BDC3C7")),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ]
        if extra:
            cmds.extend(extra)
        return TableStyle(cmds)

    def status_para(status: str) -> Paragraph:
        color_hex = {
            "PASS": "#27AE60", "WARNING": "#E67E22",
            "FAIL": "#E74C3C", "SKIP":    "#95A5A6",
        }.get(status, "#7F8C8D")
        return Paragraph(f'<font color="{color_hex}"><b>{status}</b></font>', cell_style)

    def p(text: str, style: ParagraphStyle = None) -> Paragraph:
        return Paragraph(str(text), style or cell_style)

    # ══════════════════════════════════════════════════════════════
    # Story 구성
    # ══════════════════════════════════════════════════════════════
    story: list = []

    # ── Header ────────────────────────────────────────────────────
    story.append(p("GENE-QC", title_style))
    story.append(Spacer(1, 0.1 * cm))
    story.append(p("Genomic Data Quality Validation Report", sub_style))
    story.append(Spacer(1, 0.1 * cm))
    story.append(p(
        f"Generated: {generated_at} &nbsp;|&nbsp; "
        "Framework: Clinical Data Life Cycle DQM (An et al., JMIR 2025)",
        meta_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_DARK, spaceAfter=6))

    # ── 1. Executive Summary ──────────────────────────────────────
    story.append(p("1. Executive Summary", h2_style))
    story.append(Spacer(1, 0.2 * cm))

    w4 = PAGE_W / 4
    exec_rows = [
        [p("<b>Total Checks</b>"),  p(f"<b>{total_checks}</b>"),
         p("<b>Quality Grade</b>"), p(f"<b>{grade}</b>")],
        [p("<b>Passed</b>"),        p(str(passed_count)),
         p("<b>Pass Rate</b>"),     p(f"{pass_rate:.1f}%")],
        [p("<b>Warnings</b>"),      p(str(warning_count)),
         p("<b>Files Validated</b>"),p(str(total_files))],
        [p("<b>Failed</b>"),        p(str(fail_count)),
         p("<b>Rules Applied</b>"), p(str(rules_applied))],
    ]
    exec_tbl = Table(exec_rows, colWidths=[w4 * 1.5, w4 * 0.5, w4 * 1.5, w4 * 0.5])
    exec_tbl.setStyle(base_tbl_style([
        ("BACKGROUND", (0, 0), (0, -1), C_ALT),
        ("BACKGROUND", (2, 0), (2, -1), C_ALT),
        ("FONTNAME",   (0, 0), (-1, -1), font_name_bold),
    ]))
    story.append(exec_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── 2. Data Overview ──────────────────────────────────────────
    story.append(p("2. Data Overview", h2_style))
    story.append(Spacer(1, 0.2 * cm))

    ow = [140, 72, 52, 58, 68, PAGE_W - 140 - 72 - 52 - 58 - 68]
    ov_hdr = [
        p("<b>File</b>"),        p("<b>Data Type</b>"),
        p("<b>Samples</b>"),     p("<b>Features</b>"),
        p("<b>Total Cells</b>"), p("<b>Missing Rate</b>"),
    ]
    ov_rows = [ov_hdr]
    tot_samples = 0
    tot_features = 0
    tot_cells = 0
    tot_nan = 0

    for f in files:
        shape    = f.get("shape", [0, 0])
        samples  = shape[0] if len(shape) > 0 else 0
        features = max(0, (shape[1] if len(shape) > 1 else 0) - 1)
        tcells   = samples * features
        nan_pct  = f.get("nan_percentage", 0.0) or 0.0
        dt_label = DATA_TYPE_DISPLAY.get(f.get("data_type", "unknown"), f.get("data_type", "Unknown"))

        tot_samples  = max(tot_samples, samples)
        tot_features += features
        tot_cells    += tcells
        tot_nan      += int(tcells * nan_pct / 100)

        ov_rows.append([
            p(f.get("filename", ""), small_style),
            p(dt_label),
            p(f"{samples:,}"),
            p(f"{features:,}"),
            p(f"{tcells:,}"),
            p(f"{nan_pct:.1f}%"),
        ])

    overall_miss = (tot_nan / tot_cells * 100) if tot_cells > 0 else 0.0
    ov_rows.append([
        p(f"<b>TOTAL</b> {len(files)} files"),
        p(""), p(f"<b>{tot_samples:,}</b>"),
        p(f"<b>{tot_features:,}</b>"),
        p(f"<b>{tot_cells:,}</b>"),
        p(f"<b>{overall_miss:.1f}%</b>"),
    ])

    nrow_ov = len(ov_rows)
    ov_tbl = Table(ov_rows, colWidths=ow, repeatRows=1)
    ov_tbl.setStyle(base_tbl_style([
        ("BACKGROUND", (0, 0),            (-1, 0),            C_HEADER),
        ("TEXTCOLOR",  (0, 0),            (-1, 0),            colors.white),
        ("BACKGROUND", (0, nrow_ov - 1),  (-1, nrow_ov - 1),  C_SECTION),
        *[("BACKGROUND", (0, i), (-1, i), C_ALT) for i in range(2, nrow_ov - 1, 2)],
    ]))
    story.append(ov_tbl)
    story.append(Spacer(1, 0.15 * cm))
    story.append(p(
        f"Dataset Scale: {len(files)} file(s), up to {tot_samples:,} samples, "
        f"{tot_features:,} total features, {tot_cells:,} total data cells. | "
        f"Overall Missing: {tot_nan:,} cells ({overall_miss:.1f}%).",
        note_style,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 3. Quality by Dimension ───────────────────────────────────
    story.append(p("3. Quality by Dimension", h2_style))
    story.append(Spacer(1, 0.2 * cm))

    DIMENSIONS = ["Completeness", "Plausibility", "Conformance"]
    dw = [110, 58, 52, 52, 52, 68, PAGE_W - 110 - 58 - 52 - 52 - 52 - 68]
    dim_hdr = [
        p("<b>Dimension</b>"),  p("<b>Checks</b>"),
        p("<b>Pass</b>"),       p("<b>Warn</b>"),
        p("<b>Fail</b>"),       p("<b>Pass Rate</b>"),
        p("<b>Assessment</b>"),
    ]
    dim_rows = [dim_hdr]
    for dim in DIMENSIONS:
        dm   = [m for m in executed if m.get("dimension", "") == dim]
        dc   = len(dm)
        dp   = sum(1 for m in dm if m.get("passed"))
        dw_  = sum(1 for m in dm if get_status(m) == "WARNING")
        df_  = sum(1 for m in dm if get_status(m) == "FAIL")
        dr   = (dp / dc * 100) if dc > 0 else 0.0
        dim_rows.append([
            p(dim), p(str(dc)), p(str(dp)), p(str(dw_)), p(str(df_)),
            p(f"{dr:.1f}%"), p(assess(dr)),
        ])

    dim_tbl = Table(dim_rows, colWidths=dw, repeatRows=1)
    dim_tbl.setStyle(base_tbl_style([
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        *[("BACKGROUND", (0, i), (-1, i), C_ALT) for i in range(2, len(dim_rows), 2)],
    ]))
    story.append(dim_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── 4. Detailed Validation Results ───────────────────────────
    story.append(p("4. Detailed Validation Results", h2_style))

    det_w = [130, 100, 50, 68, PAGE_W - 130 - 100 - 50 - 68]
    det_hdr = [
        p("<b>Rule</b>"),     p("<b>File</b>"),
        p("<b>Status</b>"),   p("<b>Severity</b>"),
        p("<b>Details</b>"),
    ]

    for idx, dim in enumerate(DIMENSIONS, 1):
        story.append(Spacer(1, 0.25 * cm))
        story.append(p(f"4.{idx} {dim}", h3_style))
        story.append(Spacer(1, 0.1 * cm))

        dm = [m for m in executed if m.get("dimension", "") == dim]
        det_rows = [det_hdr[:]]
        for m in dm:
            status  = get_status(m)
            details = str(m.get("details", ""))
            if len(details) > 85:
                details = details[:82] + "..."
            fname = str(m.get("filename", "")) or "Multi-dataset"
            det_rows.append([
                p(metric_name(m)),
                p(fname, small_style),
                status_para(status),
                p(str(m.get("severity", "")), small_style),
                p(details, small_style),
            ])

        if len(det_rows) == 1:
            det_rows.append([p("No checks executed")] + [p("")] * 4)

        extra_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ]
        for ri in range(1, len(det_rows)):
            if ri - 1 < len(dm):
                st = get_status(dm[ri - 1])
                if st == "WARNING":
                    extra_cmds.append(("BACKGROUND", (2, ri), (2, ri), colors.HexColor("#FEF9E7")))
                elif st == "FAIL":
                    extra_cmds.append(("BACKGROUND", (2, ri), (2, ri), colors.HexColor("#FDEDEC")))
            if ri % 2 == 0:
                extra_cmds.extend([
                    ("BACKGROUND", (0, ri), (1, ri), C_ALT),
                    ("BACKGROUND", (3, ri), (-1, ri), C_ALT),
                ])

        det_tbl = Table(det_rows, colWidths=det_w, repeatRows=1)
        det_tbl.setStyle(base_tbl_style(extra_cmds))
        story.append(det_tbl)

    story.append(Spacer(1, 0.4 * cm))

    # ── 5. File-Level Summary ─────────────────────────────────────
    story.append(p("5. File-Level Summary", h2_style))
    story.append(Spacer(1, 0.2 * cm))

    file_metrics: dict[str, list] = {}
    for m in executed:
        fname = m.get("filename", "") or "Multi-dataset"
        file_metrics.setdefault(fname, []).append(m)

    fs_w = [160, 60, PAGE_W - 160 - 60]
    fs_hdr = [p("<b>Rule</b>"), p("<b>Status</b>"), p("<b>Message</b>")]

    for fname, fm in sorted(file_metrics.items()):
        fc   = len(fm)
        fp   = sum(1 for m in fm if m.get("passed"))
        fw   = sum(1 for m in fm if get_status(m) == "WARNING")
        ff   = sum(1 for m in fm if get_status(m) == "FAIL")
        frt  = (fp / fc * 100) if fc > 0 else 0.0
        story.append(p(
            f"<b>{fname}</b> — {fc} checks | "
            f"{fp} pass, {fw} warn, {ff} fail | Pass rate: {frt:.0f}%",
            body_style,
        ))
        non_pass = [m for m in fm if get_status(m) != "PASS"]
        if non_pass:
            fs_rows = [fs_hdr[:]]
            for m in non_pass:
                det = str(m.get("details", ""))
                if len(det) > 95:
                    det = det[:92] + "..."
                fs_rows.append([p(metric_name(m)), status_para(get_status(m)), p(det, small_style)])
            fs_tbl = Table(fs_rows, colWidths=fs_w, repeatRows=1)
            fs_tbl.setStyle(base_tbl_style([("BACKGROUND", (0, 0), (-1, 0), C_SECTION)]))
            story.append(fs_tbl)
        story.append(Spacer(1, 0.25 * cm))

    story.append(Spacer(1, 0.25 * cm))

    # ── 6. Recommendations ───────────────────────────────────────
    story.append(p("6. Recommendations", h2_style))
    story.append(Spacer(1, 0.15 * cm))

    recommendations: list[str] = []
    if fail_count > 0:
        recommendations.append(
            f"[CRITICAL] {fail_count} critical failure(s) detected. "
            "Resolve before any downstream analysis."
        )
    if warning_count > 0:
        recommendations.append(
            f"[MEDIUM] {warning_count} warning(s) detected. "
            "Consider reviewing outlier patterns and missing data distributions."
        )
    if any(f.get("nan_percentage", 0) > 0 for f in files):
        recommendations.append(
            "[ACTION] Missing data detected. Consider running imputation "
            "(MOCHI tri-joint for multi-omics, or KNN/mean for single datasets)."
        )
    if pass_rate >= 80:
        recommendations.append(
            "[INFO] Data quality is acceptable with minor issues. "
            "Address warnings before publication-level analysis."
        )
    elif pass_rate >= 60:
        recommendations.append(
            "[INFO] Data quality needs improvement. "
            "Review dimension-specific issues above."
        )
    else:
        recommendations.append(
            "[INFO] Data quality is below acceptable levels. "
            "Comprehensive data review required."
        )
    if not recommendations:
        recommendations.append("[INFO] All checks passed. Data quality is excellent.")

    rec_style = _ps("rpt_rec", fontSize=8.5, leading=12)
    for i, rec in enumerate(recommendations, 1):
        story.append(p(f"{i}. {rec}", rec_style))
        story.append(Spacer(1, 0.08 * cm))

    # ── Footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7"), spaceBefore=4))
    story.append(p("GENE-QC Platform v1.0 | Clinical Data Life Cycle DQM (An et al., JMIR 2025)", footer_style))
    story.append(p(f"Report ID: {report_id} | Validation Date: {generated_at[:10]}", footer_style))

    # ── 문서 빌드 ─────────────────────────────────────────────────
    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 7.5)
        canvas.drawCentredString(A4[0] / 2, 1.0 * cm, f"-- {doc.page} --")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=1.8 * cm,
    )
    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
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
