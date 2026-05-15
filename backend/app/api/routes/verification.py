"""
Verification API routes
GENE-QC 지표설계 명세서 v2.0 §5 기준 검증 규칙 CRUD
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.base import (
    Project,
    VerificationRule as VerificationRuleModel,
    VerificationStatus as VerificationStatusModel,
)
from app.models.schemas import (
    VerificationDashboardSample,
    VerificationRule as VerificationRuleSchema,
    VerificationStatus as VerificationStatusSchema,
)
from app.services.validation_service import METRIC_METADATA

router = APIRouter()


# 차원 ↔ 한글 카테고리 매핑 (옛 프론트엔드 표시 호환)
_DIMENSION_TO_LEGACY_CATEGORY = {
    "Completeness": "완전성",
    "Plausibility": "타당성",
    "Conformance": "적합성",
}
_LEGACY_CATEGORY_TO_DIMENSION = {v: k for k, v in _DIMENSION_TO_LEGACY_CATEGORY.items()}


def _rule_to_response(rule: VerificationRuleModel) -> Dict[str, Any]:
    """DB 모델 → 신규+옛 필드 모두 포함된 응답"""
    params = rule.parameters or {}

    # 옛 condition/threshold 추정
    legacy_condition = params.get("operator")
    legacy_threshold = params.get("threshold")
    if legacy_threshold is None:
        # range / column_range / value_set 등은 단순 threshold 가 없음
        legacy_threshold = params.get("max") or params.get("min") or 0

    return {
        "id": rule.id,
        # 명세서 §5
        "metricId": rule.metric_id,
        "name": rule.name,
        "dimension": rule.dimension,
        "qualityLevel": rule.quality_level,
        "severity": rule.severity,
        "description": rule.description,
        "dataTypes": rule.data_types or [],
        "validationType": rule.validation_type,
        "parameters": params,
        "metricLevel": rule.metric_level,
        "context": rule.context,
        "isCustom": rule.is_custom,
        "enabled": rule.enabled,
        # 옛 필드 (프론트엔드 하위 호환)
        "label": rule.name,
        "status": "active" if rule.enabled else "inactive",
        "category": _DIMENSION_TO_LEGACY_CATEGORY.get(rule.dimension, rule.dimension),
        "metric": rule.validation_type,
        "condition": legacy_condition or ">=",
        "threshold": legacy_threshold or 0,
    }


def _payload_to_rule_fields(payload: VerificationRuleSchema) -> Dict[str, Any]:
    """
    신규 + 옛 스키마 모두 입력으로 받아 DB 필드값 dict 로 변환

    옛 스키마(label, category, metric, condition, threshold) 만 들어와도
    합리적인 GENE-QC metricId 로 변환합니다.
    """
    data = payload.model_dump(exclude_none=True)

    metric_id = data.get("metric_id") or data.get("metricId")
    name = data.get("name") or data.get("label") or "사용자 정의 규칙"
    dimension = data.get("dimension")

    # 옛 category 한글 → dimension 변환
    if not dimension and data.get("category"):
        dimension = _LEGACY_CATEGORY_TO_DIMENSION.get(data["category"], "Completeness")

    severity = data.get("severity") or "warning"
    quality_level = data.get("quality_level") or "basic"
    validation_type = data.get("validation_type") or data.get("metric") or "threshold"
    parameters = data.get("parameters") or {}

    # 옛 condition/threshold → parameters 로 흡수
    if data.get("threshold") is not None and "threshold" not in parameters:
        parameters["threshold"] = data["threshold"]
    if data.get("condition") and "operator" not in parameters:
        parameters["operator"] = data["condition"]

    # metric_id 가 없으면 custom_ 으로 자동 부여
    if not metric_id:
        metric_id = f"custom_{abs(hash(name)) % 100000:05d}"

    # metric_id 가 명세서에 있으면 메타데이터 보정
    meta = METRIC_METADATA.get(metric_id)
    metric_level = data.get("metric_level") or (meta or {}).get("level")
    context = data.get("context") or (meta or {}).get("context")
    if meta and not dimension:
        dimension = meta["dimension"]
    if meta and severity == "warning":
        severity = meta["severity"]

    return {
        "metric_id": metric_id,
        "name": name,
        "dimension": dimension or "Completeness",
        "quality_level": quality_level,
        "severity": severity,
        "description": data.get("description"),
        "data_types": data.get("data_types") or data.get("dataTypes") or [],
        "validation_type": validation_type,
        "parameters": parameters,
        "metric_level": metric_level,
        "context": context,
        "is_custom": data.get("is_custom", True) if not meta else False,
        "enabled": data.get("enabled", True) if "status" not in data else (data["status"] == "active"),
    }


# ───────────────────────── 대시보드 ─────────────────────────


@router.get("/dashboard", response_model=List[VerificationDashboardSample])
async def get_verification_dashboard(
    project_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """검증 대시보드 요약"""
    if project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        active_rules = (
            db.query(VerificationRuleModel)
            .filter(VerificationRuleModel.enabled == True)  # noqa: E712
            .filter(
                (VerificationRuleModel.project_id == project_id)
                | (VerificationRuleModel.project_id.is_(None))
            )
            .count()
        )

        statuses = (
            db.query(VerificationStatusModel)
            .filter(VerificationStatusModel.project_id == project_id)
            .all()
        )
        passed_count = sum(1 for s in statuses if s.score >= s.standard)
        pass_rate = (passed_count / len(statuses) * 100) if statuses else 0
        warning_count = sum(1 for s in statuses if s.score < s.standard)

        return [
            {"label": "총 검증 샘플", "count": f"{project.sample_count:,}", "description": project.name},
            {"label": "검증 통과율", "count": f"{pass_rate:.1f}%", "description": "Quality metrics passed"},
            {"label": "경고 샘플", "count": str(warning_count), "description": "Requires attention"},
            {"label": "활성 규칙", "count": str(active_rules), "description": "GENE-QC quality rules"},
        ]

    total_samples = db.query(Project).with_entities(Project.sample_count).all()
    total = sum(s[0] for s in total_samples if s[0])
    active_rules = (
        db.query(VerificationRuleModel)
        .filter(VerificationRuleModel.enabled == True)  # noqa: E712
        .count()
    )

    return [
        {"label": "총 검증 샘플", "count": f"{total:,}", "description": "All projects"},
        {"label": "검증 통과율", "count": "—", "description": "Run validation to see"},
        {"label": "경고 샘플", "count": "—", "description": "Run validation to see"},
        {"label": "활성 규칙", "count": str(active_rules), "description": "GENE-QC quality rules"},
    ]


@router.get("/status", response_model=List[VerificationStatusSchema])
async def get_verification_status(
    project_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """차원별 검증 상태"""
    if not project_id:
        project = db.query(Project).first()
        if project:
            project_id = project.id

    if project_id:
        statuses = (
            db.query(VerificationStatusModel)
            .filter(VerificationStatusModel.project_id == project_id)
            .all()
        )
        return [{"label": s.label, "score": s.score, "standard": s.standard} for s in statuses]

    return []


# ───────────────────────── 규칙 CRUD ─────────────────────────


@router.get("/rules")
async def get_verification_rules(
    project_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """검증 규칙 목록 조회 (명세서 §5 신규 + 옛 필드 모두 포함)"""
    query = db.query(VerificationRuleModel)

    if project_id:
        query = query.filter(
            (VerificationRuleModel.project_id == project_id)
            | (VerificationRuleModel.project_id.is_(None))
        )
    else:
        query = query.filter(VerificationRuleModel.project_id.is_(None))

    rules = query.order_by(VerificationRuleModel.metric_id).all()
    return [_rule_to_response(r) for r in rules]


@router.post("/rules")
async def create_verification_rule(
    rule: VerificationRuleSchema, db: Session = Depends(get_db)
):
    """새 검증 규칙 생성 (신규 또는 옛 필드 모두 허용)"""
    fields = _payload_to_rule_fields(rule)

    db_rule = VerificationRuleModel(project_id=None, **fields)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return _rule_to_response(db_rule)


@router.put("/rules/{rule_id}")
async def update_verification_rule(
    rule_id: int, rule: VerificationRuleSchema, db: Session = Depends(get_db)
):
    """검증 규칙 업데이트"""
    db_rule = db.query(VerificationRuleModel).filter(VerificationRuleModel.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    fields = _payload_to_rule_fields(rule)
    for key, value in fields.items():
        setattr(db_rule, key, value)

    db.commit()
    db.refresh(db_rule)
    return _rule_to_response(db_rule)


@router.delete("/rules/{rule_id}")
async def delete_verification_rule(rule_id: int, db: Session = Depends(get_db)):
    """검증 규칙 삭제"""
    db_rule = db.query(VerificationRuleModel).filter(VerificationRuleModel.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(db_rule)
    db.commit()
    return {"message": "Rule deleted successfully"}
