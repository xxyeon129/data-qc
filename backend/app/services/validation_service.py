"""
GENE-QC Validation Service
OMOP CDM DQM 기반 28개 품질 지표 구현

TODO: 추후 개발 예정
    현재 이 모듈은 HTTP 검증 엔드포인트(POST /api/validation/execute)에 연동되어 있지 않습니다.
    실제 API 동작은 validation.py 라우트 내부의 _evaluate_gene_qc_rules 함수(13개 규칙)로 수행됩니다.
    향후 아래 항목의 구현 및 라우트 연동이 필요합니다.
      - advanced 레벨 크로스 검증 6개 규칙 (comp_X*, plau_X*, conf_X*)
      - basic 레벨 미구현 규칙: comp_C004, plau_V001, plau_V002, plau_V003,
        plau_T001, plau_T002, conf_C004, conf_V001, conf_V002
      - ValidationService 클래스를 validation.py 라우트에서 import하여 사용하도록 통합
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ─── 지표 메타데이터 ────────────────────────────────────────────────────────

METRIC_METADATA: dict[str, dict] = {
    # Completeness — FILE
    "comp_F001": {"name": "파일 헤더 존재 여부", "level": "FILE", "context": "Verification", "severity": "fatal", "dimension": "Completeness", "qualityLevel": "basic"},
    "comp_F003": {"name": "전체 데이터 결측률", "level": "FILE", "context": "Validation", "severity": "warning", "dimension": "Completeness", "qualityLevel": "basic"},
    # Completeness — COLUMN
    "comp_C001": {"name": "샘플 ID 컬럼 필수 존재", "level": "COLUMN", "context": "Verification", "severity": "fatal", "dimension": "Completeness", "qualityLevel": "basic"},
    "comp_C002": {"name": "컬럼별 결측률 검사", "level": "COLUMN", "context": "Verification", "severity": "warning", "dimension": "Completeness", "qualityLevel": "basic"},
    "comp_C003": {"name": "행(샘플) 완전성 검사", "level": "COLUMN", "context": "Verification", "severity": "warning", "dimension": "Completeness", "qualityLevel": "basic"},
    "comp_C004": {"name": "조건부 필수 컬럼 검사", "level": "COLUMN", "context": "Verification", "severity": "error", "dimension": "Completeness", "qualityLevel": "basic"},
    # Completeness — CROSS
    "comp_X001": {"name": "데이터셋 간 샘플 매칭률", "level": "VALUE", "context": "Validation", "severity": "warning", "dimension": "Completeness", "qualityLevel": "advanced"},
    "comp_X002": {"name": "전체 데이터셋 공통 샘플 수", "level": "VALUE", "context": "Validation", "severity": "error", "dimension": "Completeness", "qualityLevel": "advanced"},
    "comp_X003": {"name": "메타데이터-오믹스 샘플 연결성", "level": "VALUE", "context": "Validation", "severity": "warning", "dimension": "Completeness", "qualityLevel": "advanced"},
    # Plausibility — COLUMN (Atemporal)
    "plau_C001": {"name": "발현값 하한 검사", "level": "COLUMN", "context": "Verification", "severity": "characterization", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_C002": {"name": "발현값 상한 검사", "level": "COLUMN", "context": "Verification", "severity": "characterization", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_C003": {"name": "IQR 기반 이상치 검사", "level": "COLUMN", "context": "Verification", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_C004": {"name": "상수값 컬럼 탐지 (분산=0)", "level": "COLUMN", "context": "Verification", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "basic"},
    # Plausibility — VALUE (Atemporal)
    "plau_V001": {"name": "성별 값 허용범위 검사", "level": "VALUE", "context": "Validation", "severity": "error", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_V002": {"name": "연령 값 범위 검사", "level": "VALUE", "context": "Validation", "severity": "error", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_V003": {"name": "수치형 컬럼 음수값 허용 검사", "level": "VALUE", "context": "Verification", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "basic"},
    # Plausibility — COLUMN (Temporal)
    "plau_T001": {"name": "날짜 순서 타당성 (시작 <= 종료)", "level": "COLUMN", "context": "Verification", "severity": "error", "dimension": "Plausibility", "qualityLevel": "basic"},
    "plau_T002": {"name": "진단일-출생일 순서 검사", "level": "COLUMN", "context": "Verification", "severity": "error", "dimension": "Plausibility", "qualityLevel": "basic"},
    # Plausibility — CROSS
    "plau_X001": {"name": "메타데이터-오믹스 subtype 일관성", "level": "VALUE", "context": "Validation", "severity": "convention", "dimension": "Plausibility", "qualityLevel": "advanced"},
    "plau_X002": {"name": "오믹스 간 발현 상관관계", "level": "VALUE", "context": "Validation", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "advanced"},
    # Conformance — FILE
    "conf_F001": {"name": "파일 형식(구분자) 일관성", "level": "FILE", "context": "Verification", "severity": "fatal", "dimension": "Conformance", "qualityLevel": "basic"},
    # Conformance — COLUMN
    "conf_C001": {"name": "샘플 ID 중복 검사", "level": "COLUMN", "context": "Verification", "severity": "fatal", "dimension": "Conformance", "qualityLevel": "basic"},
    "conf_C002": {"name": "수치형 컬럼 데이터 타입 검사", "level": "COLUMN", "context": "Verification", "severity": "error", "dimension": "Conformance", "qualityLevel": "basic"},
    "conf_C003": {"name": "컬럼명 형식 검사 (공백/특수문자)", "level": "COLUMN", "context": "Verification", "severity": "convention", "dimension": "Conformance", "qualityLevel": "basic"},
    "conf_C004": {"name": "샘플 ID 형식 검사 (정규식)", "level": "COLUMN", "context": "Verification", "severity": "convention", "dimension": "Conformance", "qualityLevel": "basic"},
    # Conformance — VALUE
    "conf_V001": {"name": "허용값 목록 준수 검사", "level": "VALUE", "context": "Verification", "severity": "error", "dimension": "Conformance", "qualityLevel": "basic"},
    "conf_V002": {"name": "날짜 형식 표준 검사", "level": "VALUE", "context": "Verification", "severity": "error", "dimension": "Conformance", "qualityLevel": "basic"},
    # Conformance — CROSS
    "conf_X001": {"name": "데이터셋 간 ID 형식 일관성", "level": "VALUE", "context": "Verification", "severity": "error", "dimension": "Conformance", "qualityLevel": "advanced"},
}

OMICS_TYPES = {"genomics", "transcriptomics", "proteomics", "metabolomics"}
ALL_TYPES = OMICS_TYPES | {"metadata"}

# 데이터 타입별 결측률 기본 임계값
DEFAULT_MISSING_THRESHOLDS: dict[str, float] = {
    "genomics": 1.0,
    "transcriptomics": 20.0,
    "proteomics": 25.0,
    "metabolomics": 25.0,
    "metadata": 10.0,
}


# ─── 결과 헬퍼 ──────────────────────────────────────────────────────────────

def _result(
    metric_id: str,
    passed: bool,
    value: float | None,
    details: str,
    filename: str = "",
    data_type: str = "",
    affected_items: list | None = None,
) -> dict:
    meta = METRIC_METADATA[metric_id]
    return {
        "metricId": metric_id,
        "metricName": meta["name"],
        "dimension": meta["dimension"],
        "metricLevel": meta["level"],
        "severity": meta["severity"],
        "qualityLevel": meta["qualityLevel"],
        "filename": filename,
        "dataType": data_type,
        "passed": passed,
        "value": value,
        "details": details,
        "affectedItems": affected_items or [],
    }


def _skip(metric_id: str, reason: str, filename: str = "", data_type: str = "") -> dict:
    meta = METRIC_METADATA[metric_id]
    return {
        "metricId": metric_id,
        "metricName": meta["name"],
        "dimension": meta["dimension"],
        "metricLevel": meta["level"],
        "severity": meta["severity"],
        "qualityLevel": meta["qualityLevel"],
        "filename": filename,
        "dataType": data_type,
        "passed": None,
        "value": None,
        "details": f"[건너뜀] {reason}",
        "affectedItems": [],
    }


# ─── 파일 레벨 지표 ─────────────────────────────────────────────────────────

def check_comp_F001(file_path: Path, data_type: str, raw_content: str) -> dict:
    """파일 헤더 존재 여부 — 최소 2개 컬럼 필요"""
    lines = [l for l in raw_content.split("\n") if l.strip()]
    if not lines:
        return _result("comp_F001", False, 0, "파일이 비어 있습니다.", file_path.name, data_type)
    first_line = lines[0]
    delimiter = "\t" if first_line.count("\t") >= first_line.count(",") else ","
    col_count = len(first_line.split(delimiter))
    passed = col_count >= 2
    return _result(
        "comp_F001", passed, col_count,
        f"헤더 컬럼 수: {col_count}" if passed else f"헤더 컬럼 부족 ({col_count}개, 최소 2개 필요)",
        file_path.name, data_type,
    )


def check_conf_F001(file_path: Path, data_type: str, raw_content: str) -> dict:
    """파일 형식(구분자) 일관성 — 모든 행의 컬럼 수가 동일해야 함"""
    lines = [l for l in raw_content.split("\n") if l.strip()]
    if len(lines) < 2:
        return _result("conf_F001", False, 0, "검증할 데이터 행이 없습니다.", file_path.name, data_type)
    first_line = lines[0]
    delimiter = "\t" if first_line.count("\t") >= first_line.count(",") else ","
    expected_cols = len(first_line.split(delimiter))
    inconsistent = [i + 1 for i, l in enumerate(lines[1:], 1) if len(l.split(delimiter)) != expected_cols]
    passed = len(inconsistent) == 0
    return _result(
        "conf_F001", passed,
        len(inconsistent),
        f"구분자 일관성 정상 ({delimiter!r})" if passed else f"컬럼 수 불일치 행: {inconsistent[:10]}",
        file_path.name, data_type,
        inconsistent[:20] if not passed else [],
    )


def check_comp_F003(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """전체 데이터 결측률 검사 (omics 전용)"""
    if data_type not in OMICS_TYPES:
        return _skip("comp_F003", "omics 전용 지표 (metadata 제외)", file_path.name, data_type)
    threshold = params.get("threshold", DEFAULT_MISSING_THRESHOLDS.get(data_type, 30.0))
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _skip("comp_F003", "수치형 데이터 없음", file_path.name, data_type)
    total_missing_rate = numeric_df.isna().mean().mean() * 100
    passed = total_missing_rate <= threshold
    return _result(
        "comp_F003", passed, round(total_missing_rate, 2),
        f"전체 결측률 {total_missing_rate:.2f}% (임계값: {threshold}%)",
        file_path.name, data_type,
    )


# ─── 컬럼 레벨 지표 ─────────────────────────────────────────────────────────

def check_comp_C001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """샘플 ID 컬럼 필수 존재"""
    target = params.get("targetColumn", "first_column")
    if target == "first_column":
        exists = len(df.columns) > 0
        col_name = df.columns[0] if exists else "(없음)"
    else:
        exists = target in df.columns
        col_name = target
    return _result(
        "comp_C001", exists, int(exists),
        f"샘플 ID 컬럼 '{col_name}' 존재 확인" if exists else f"샘플 ID 컬럼 '{col_name}' 없음",
        file_path.name, data_type,
    )


def check_comp_C002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """컬럼별 결측률 검사"""
    threshold = params.get("threshold", DEFAULT_MISSING_THRESHOLDS.get(data_type, 30.0))
    col_missing = (df.isna().mean() * 100).round(2)
    violating = col_missing[col_missing > threshold]
    passed = len(violating) == 0
    max_rate = float(col_missing.max()) if len(col_missing) > 0 else 0.0
    return _result(
        "comp_C002", passed, round(max_rate, 2),
        f"최대 결측률 {max_rate:.2f}% (임계값: {threshold}%)" if passed else f"임계값 초과 컬럼 {len(violating)}개",
        file_path.name, data_type,
        violating.index.tolist()[:20],
    )


def check_comp_C003(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """행(샘플) 완전성 검사"""
    threshold = params.get("threshold", 50.0)
    row_missing = (df.isna().mean(axis=1) * 100).round(2)
    violating_idx = row_missing[row_missing > threshold].index.tolist()
    passed = len(violating_idx) == 0
    max_rate = float(row_missing.max()) if len(row_missing) > 0 else 0.0
    return _result(
        "comp_C003", passed, round(max_rate, 2),
        f"행 최대 결측률 {max_rate:.2f}% (임계값: {threshold}%)" if passed else f"임계값 초과 샘플 {len(violating_idx)}개",
        file_path.name, data_type,
        [str(i) for i in violating_idx[:20]],
    )


def check_comp_C004(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """조건부 필수 컬럼 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("comp_C004", "metadata 전용 지표", file_path.name, data_type)
    cond_col = params.get("conditionColumn", "")
    req_col = params.get("requiredColumn", "")
    if not cond_col or not req_col:
        return _skip("comp_C004", "conditionColumn / requiredColumn 파라미터 미설정", file_path.name, data_type)
    if cond_col not in df.columns:
        return _skip("comp_C004", f"조건 컬럼 '{cond_col}' 없음", file_path.name, data_type)
    cond_value = params.get("conditionValue")
    if cond_value is None:
        condition_met = df[cond_col].notna()
    else:
        condition_met = df[cond_col] == cond_value
    if condition_met.any():
        exists = req_col in df.columns
        return _result(
            "comp_C004", exists, int(exists),
            f"조건 충족 시 '{req_col}' 컬럼 {'존재' if exists else '부재'}",
            file_path.name, data_type,
        )
    return _skip("comp_C004", f"조건 컬럼 '{cond_col}'의 조건 미충족 → 검사 불필요", file_path.name, data_type)


def check_plau_C001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """발현값 하한 검사"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_C001", "omics 전용 지표", file_path.name, data_type)
    min_val = params.get("min", -np.inf)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _skip("plau_C001", "수치형 데이터 없음", file_path.name, data_type)
    actual_min = float(numeric_df.min().min())
    below = (numeric_df < min_val).any().any()
    return _result(
        "plau_C001", not below, round(actual_min, 4),
        f"최솟값 {actual_min:.4f} (하한: {min_val})",
        file_path.name, data_type,
    )


def check_plau_C002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """발현값 상한 검사"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_C002", "omics 전용 지표", file_path.name, data_type)
    max_val = params.get("max", np.inf)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _skip("plau_C002", "수치형 데이터 없음", file_path.name, data_type)
    actual_max = float(numeric_df.max().max())
    above = (numeric_df > max_val).any().any()
    return _result(
        "plau_C002", not above, round(actual_max, 4),
        f"최댓값 {actual_max:.4f} (상한: {max_val})",
        file_path.name, data_type,
    )


def check_plau_C003(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """IQR 기반 이상치 비율 검사 — 전체 수치형 피처의 열별 IQR 이상치 비율 평균"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_C003", "omics 전용 지표", file_path.name, data_type)
    threshold = params.get("threshold", 10.0)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty or numeric_df.shape[0] < 4:
        return _skip("plau_C003", "데이터 행이 너무 적어 IQR 계산 불가 (최소 4행 필요)", file_path.name, data_type)
    # 대용량 행렬: 샘플(행) 방향으로 IQR 계산 (행 = 샘플, 열 = 피처)
    vals = numeric_df.values
    q1 = np.nanpercentile(vals, 25, axis=0)
    q3 = np.nanpercentile(vals, 75, axis=0)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_mask = (vals < lower[np.newaxis, :]) | (vals > upper[np.newaxis, :])
    valid_mask = ~np.isnan(vals)
    total_valid = valid_mask.sum()
    if total_valid == 0:
        return _skip("plau_C003", "유효한 수치값 없음", file_path.name, data_type)
    outlier_rate = float((outlier_mask & valid_mask).sum() / total_valid * 100)
    passed = outlier_rate <= threshold
    return _result(
        "plau_C003", passed, round(outlier_rate, 2),
        f"IQR 이상치 비율 {outlier_rate:.2f}% (임계값: {threshold}%)",
        file_path.name, data_type,
    )


def check_plau_C004(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """상수값 컬럼 탐지 (분산=0)"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_C004", "omics 전용 지표", file_path.name, data_type)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _skip("plau_C004", "수치형 데이터 없음", file_path.name, data_type)
    zero_var_cols = numeric_df.columns[numeric_df.var(ddof=0) == 0].tolist()
    passed = len(zero_var_cols) == 0
    return _result(
        "plau_C004", passed, len(zero_var_cols),
        f"분산=0 컬럼 없음" if passed else f"분산=0 컬럼 {len(zero_var_cols)}개 발견",
        file_path.name, data_type,
        zero_var_cols[:20],
    )


def check_plau_V001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """성별 값 허용범위 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("plau_V001", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "sex")
    allowed = set(params.get("allowedValues", ["M", "F", "male", "female", "Unknown", "m", "f", "Male", "Female"]))
    gender_col = next((c for c in df.columns if c.lower() in {"sex", "gender", "성별"}), None)
    if target_col != "first_column" and target_col in df.columns:
        gender_col = target_col
    if gender_col is None:
        return _skip("plau_V001", "성별 컬럼 찾을 수 없음 (sex/gender)", file_path.name, data_type)
    col_vals = df[gender_col].dropna().astype(str)
    invalid = col_vals[~col_vals.isin(allowed)].unique().tolist()
    passed = len(invalid) == 0
    return _result(
        "plau_V001", passed, len(invalid),
        f"성별 값 검증 통과" if passed else f"허용되지 않은 값 {len(invalid)}개: {invalid[:5]}",
        file_path.name, data_type,
        invalid[:20],
    )


def check_plau_V002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """연령 값 범위 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("plau_V002", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "age")
    min_age = params.get("min", 0)
    max_age = params.get("max", 120)
    age_col = next((c for c in df.columns if c.lower() in {"age", "나이", "연령"}), None)
    if target_col in df.columns:
        age_col = target_col
    if age_col is None:
        return _skip("plau_V002", "연령 컬럼 찾을 수 없음 (age/나이)", file_path.name, data_type)
    try:
        ages = pd.to_numeric(df[age_col], errors="coerce").dropna()
    except Exception:
        return _skip("plau_V002", f"연령 컬럼 '{age_col}'을 숫자로 변환할 수 없음", file_path.name, data_type)
    out_of_range = ages[(ages < min_age) | (ages > max_age)]
    passed = len(out_of_range) == 0
    return _result(
        "plau_V002", passed, len(out_of_range),
        f"연령 범위 검증 통과 ({min_age}~{max_age})" if passed else f"범위 초과 값 {len(out_of_range)}개",
        file_path.name, data_type,
        [str(v) for v in out_of_range.tolist()[:20]],
    )


def check_plau_V003(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """수치형 컬럼 음수값 허용 검사"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_V003", "omics 전용 지표", file_path.name, data_type)
    allow_negative = params.get("allowNegative", False)
    if allow_negative:
        return _result("plau_V003", True, 0, "음수값 허용 설정됨", file_path.name, data_type)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return _skip("plau_V003", "수치형 데이터 없음", file_path.name, data_type)
    neg_count = int((numeric_df < 0).sum().sum())
    passed = neg_count == 0
    return _result(
        "plau_V003", passed, neg_count,
        "음수값 없음" if passed else f"음수값 {neg_count}개 발견 (음수 불허용 설정)",
        file_path.name, data_type,
    )


def check_plau_T001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """날짜 순서 타당성 (시작 <= 종료) — metadata 전용"""
    if data_type != "metadata":
        return _skip("plau_T001", "metadata 전용 지표", file_path.name, data_type)
    start_col = params.get("startColumn", "")
    end_col = params.get("endColumn", "")
    if not start_col or not end_col:
        return _skip("plau_T001", "startColumn / endColumn 파라미터 미설정", file_path.name, data_type)
    if start_col not in df.columns or end_col not in df.columns:
        return _skip("plau_T001", f"컬럼 없음: {start_col}, {end_col}", file_path.name, data_type)
    try:
        start_dates = pd.to_datetime(df[start_col], errors="coerce")
        end_dates = pd.to_datetime(df[end_col], errors="coerce")
    except Exception:
        return _skip("plau_T001", "날짜 파싱 실패", file_path.name, data_type)
    valid = start_dates.notna() & end_dates.notna()
    violations = int((start_dates[valid] > end_dates[valid]).sum())
    passed = violations == 0
    return _result(
        "plau_T001", passed, violations,
        f"날짜 순서 정상" if passed else f"시작 > 종료인 행 {violations}개",
        file_path.name, data_type,
    )


def check_plau_T002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """진단일-출생일 순서 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("plau_T002", "metadata 전용 지표", file_path.name, data_type)
    birth_col = params.get("birthColumn", "")
    event_col = params.get("eventColumn", "")
    if not birth_col or not event_col:
        return _skip("plau_T002", "birthColumn / eventColumn 파라미터 미설정", file_path.name, data_type)
    if birth_col not in df.columns or event_col not in df.columns:
        return _skip("plau_T002", f"컬럼 없음: {birth_col}, {event_col}", file_path.name, data_type)
    try:
        birth_dates = pd.to_datetime(df[birth_col], errors="coerce")
        event_dates = pd.to_datetime(df[event_col], errors="coerce")
    except Exception:
        return _skip("plau_T002", "날짜 파싱 실패", file_path.name, data_type)
    valid = birth_dates.notna() & event_dates.notna()
    violations = int((event_dates[valid] < birth_dates[valid]).sum())
    passed = violations == 0
    return _result(
        "plau_T002", passed, violations,
        "출생일 이후 이벤트 날짜 정상" if passed else f"출생일 이전 이벤트 {violations}건",
        file_path.name, data_type,
    )


def check_conf_C001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """샘플 ID 중복 검사"""
    id_col = df.columns[0] if len(df.columns) > 0 else None
    custom = params.get("targetColumn", "first_column")
    if custom != "first_column" and custom in df.columns:
        id_col = custom
    if id_col is None:
        return _result("conf_C001", False, 0, "컬럼 없음", file_path.name, data_type)
    duplicates = df[id_col].duplicated()
    dup_count = int(duplicates.sum())
    passed = dup_count == 0
    return _result(
        "conf_C001", passed, dup_count,
        f"샘플 ID 중복 없음" if passed else f"중복 샘플 ID {dup_count}개",
        file_path.name, data_type,
        df[id_col][duplicates].astype(str).unique().tolist()[:20],
    )


def check_conf_C002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """수치형 컬럼 데이터 타입 검사 (omics 전용)"""
    if data_type not in OMICS_TYPES:
        return _skip("conf_C002", "omics 전용 지표", file_path.name, data_type)
    exclude = set(params.get("excludeColumns", [df.columns[0]] if len(df.columns) > 0 else []))
    target_cols = [c for c in df.columns if c not in exclude]
    non_numeric = []
    for col in target_cols:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.isna().all() and df[col].notna().any():
            non_numeric.append(col)
    passed = len(non_numeric) == 0
    return _result(
        "conf_C002", passed, len(non_numeric),
        "수치형 타입 검증 통과" if passed else f"비수치형 컬럼 {len(non_numeric)}개",
        file_path.name, data_type,
        non_numeric[:20],
    )


def check_conf_C003(df: pd.DataFrame, file_path: Path, data_type: str, _params: dict) -> dict:
    """컬럼명 형식 검사 (공백/특수문자)"""
    pattern = re.compile(r'^[a-zA-Z0-9_.가-힣\-]+$')
    bad_cols = [c for c in df.columns if not pattern.match(str(c))]
    passed = len(bad_cols) == 0
    return _result(
        "conf_C003", passed, len(bad_cols),
        "컬럼명 형식 정상" if passed else f"형식 위반 컬럼 {len(bad_cols)}개",
        file_path.name, data_type,
        bad_cols[:20],
    )


def check_conf_C004(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """샘플 ID 형식 검사 (정규식)"""
    pattern_str = params.get("pattern", r"^[A-Za-z0-9_\-]+$")
    id_col = df.columns[0] if len(df.columns) > 0 else None
    if id_col is None:
        return _result("conf_C004", False, 0, "첫 번째 컬럼 없음", file_path.name, data_type)
    try:
        compiled = re.compile(pattern_str)
    except re.error:
        return _skip("conf_C004", f"잘못된 정규식 패턴: {pattern_str}", file_path.name, data_type)
    ids = df[id_col].astype(str)
    invalid = ids[~ids.str.match(compiled)].tolist()
    passed = len(invalid) == 0
    return _result(
        "conf_C004", passed, len(invalid),
        "샘플 ID 형식 정상" if passed else f"형식 위반 ID {len(invalid)}개",
        file_path.name, data_type,
        invalid[:20],
    )


def check_conf_V001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """허용값 목록 준수 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("conf_V001", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "")
    allowed = set(str(v) for v in params.get("allowedValues", []))
    if not target_col or target_col not in df.columns:
        return _skip("conf_V001", f"targetColumn '{target_col}' 없음 또는 미설정", file_path.name, data_type)
    if not allowed:
        return _skip("conf_V001", "allowedValues 파라미터 미설정", file_path.name, data_type)
    vals = df[target_col].dropna().astype(str)
    invalid = vals[~vals.isin(allowed)].unique().tolist()
    passed = len(invalid) == 0
    return _result(
        "conf_V001", passed, len(invalid),
        f"허용값 준수" if passed else f"허용되지 않은 값 {len(invalid)}개: {invalid[:5]}",
        file_path.name, data_type,
        invalid[:20],
    )


def check_conf_V002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """날짜 형식 표준 검사 (metadata 전용)"""
    if data_type != "metadata":
        return _skip("conf_V002", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "")
    date_format = params.get("dateFormat", "%Y-%m-%d")
    if not target_col or target_col not in df.columns:
        return _skip("conf_V002", f"targetColumn '{target_col}' 없음 또는 미설정", file_path.name, data_type)
    col_vals = df[target_col].dropna().astype(str)
    invalid_count = 0
    for val in col_vals:
        try:
            datetime.strptime(val, date_format)
        except ValueError:
            invalid_count += 1
    passed = invalid_count == 0
    return _result(
        "conf_V002", passed, invalid_count,
        f"날짜 형식 '{date_format}' 준수" if passed else f"형식 위반 {invalid_count}건",
        file_path.name, data_type,
    )


# ─── 교차(심화) 지표 ─────────────────────────────────────────────────────────

def check_cross_metrics(
    file_infos: list[dict],
    enabled_metrics: set[str],
    params_map: dict[str, dict],
) -> list[dict]:
    """교차 검증 지표 실행 (다중 파일 필요)"""
    results = []
    if len(file_infos) < 2:
        for mid in ["comp_X001", "comp_X002", "comp_X003", "plau_X001", "plau_X002", "conf_X001"]:
            if mid in enabled_metrics:
                results.append(_skip(mid, "교차 검증은 2개 이상 파일 필요"))
        return results

    # 파일별 샘플 ID 추출
    sample_id_sets: dict[str, set] = {}
    data_type_map: dict[str, str] = {}
    for info in file_infos:
        df = info["df"]
        if len(df.columns) > 0:
            ids = set(df.iloc[:, 0].dropna().astype(str).tolist())
            sample_id_sets[info["filename"]] = ids
            data_type_map[info["filename"]] = info["data_type"]

    all_filenames = list(sample_id_sets.keys())

    # comp_X001: 데이터셋 간 샘플 매칭률 (pairwise)
    if "comp_X001" in enabled_metrics:
        threshold = params_map.get("comp_X001", {}).get("threshold", 80.0)
        pairwise_rates = []
        for i in range(len(all_filenames)):
            for j in range(i + 1, len(all_filenames)):
                f1, f2 = all_filenames[i], all_filenames[j]
                s1, s2 = sample_id_sets[f1], sample_id_sets[f2]
                if not s1 or not s2:
                    continue
                union = s1 | s2
                inter = s1 & s2
                rate = len(inter) / len(union) * 100 if union else 0
                pairwise_rates.append(rate)
        if pairwise_rates:
            min_rate = min(pairwise_rates)
            passed = min_rate >= threshold
            results.append(_result(
                "comp_X001", passed, round(min_rate, 2),
                f"최소 샘플 매칭률 {min_rate:.2f}% (임계값: {threshold}%)",
            ))

    # comp_X002: 공통 샘플 수
    if "comp_X002" in enabled_metrics:
        threshold = params_map.get("comp_X002", {}).get("threshold", 10)
        all_sets = list(sample_id_sets.values())
        common = all_sets[0]
        for s in all_sets[1:]:
            common = common & s
        common_count = len(common)
        passed = common_count >= threshold
        results.append(_result(
            "comp_X002", passed, common_count,
            f"전체 공통 샘플 {common_count}개 (임계값: {threshold}개)",
        ))

    # comp_X003: 메타데이터-오믹스 샘플 연결성
    if "comp_X003" in enabled_metrics:
        threshold = params_map.get("comp_X003", {}).get("threshold", 80.0)
        meta_files = [f for f in all_filenames if data_type_map.get(f) == "metadata"]
        omics_files = [f for f in all_filenames if data_type_map.get(f) in OMICS_TYPES]
        if meta_files and omics_files:
            meta_ids = sample_id_sets[meta_files[0]]
            rates = []
            for of in omics_files:
                omics_ids = sample_id_sets[of]
                if not meta_ids or not omics_ids:
                    continue
                rate = len(meta_ids & omics_ids) / len(meta_ids | omics_ids) * 100
                rates.append(rate)
            if rates:
                min_rate = min(rates)
                passed = min_rate >= threshold
                results.append(_result(
                    "comp_X003", passed, round(min_rate, 2),
                    f"메타데이터-오믹스 연결률 {min_rate:.2f}% (임계값: {threshold}%)",
                ))
        else:
            results.append(_skip("comp_X003", "메타데이터 또는 오믹스 파일 없음"))

    # conf_X001: 데이터셋 간 ID 형식 일관성
    if "conf_X001" in enabled_metrics:
        pattern_str = params_map.get("conf_X001", {}).get("pattern", r"^[A-Za-z0-9_\-]+$")
        try:
            compiled = re.compile(pattern_str)
        except re.error:
            results.append(_skip("conf_X001", f"잘못된 패턴: {pattern_str}"))
            compiled = None
        if compiled:
            inconsistent_files = []
            for fname, ids in sample_id_sets.items():
                invalid = [i for i in ids if not compiled.match(i)]
                if invalid:
                    inconsistent_files.append(fname)
            passed = len(inconsistent_files) == 0
            results.append(_result(
                "conf_X001", passed, len(inconsistent_files),
                "ID 형식 일관성 정상" if passed else f"ID 형식 불일치 파일 {len(inconsistent_files)}개",
                affected_items=inconsistent_files[:10],
            ))

    # plau_X001 / plau_X002: AI 모듈 담당 (stub)
    for mid in ["plau_X001", "plau_X002"]:
        if mid in enabled_metrics:
            results.append(_skip(mid, "[AI 모듈] 별도 구현 필요 — 개발팀장 요청 항목"))

    return results


# ─── 메인 검증 실행 ──────────────────────────────────────────────────────────

def run_validation(
    project_dir: Path,
    file_data_types: dict[str, str],
    enabled_metrics: list[str] | None = None,
    params_overrides: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """
    Parameters
    ----------
    project_dir : raw 파일이 들어있는 프로젝트 디렉토리
    file_data_types : {filename: data_type} 매핑
    enabled_metrics : 활성화할 metricId 목록 (None → 전부)
    params_overrides : {metricId: {param_key: value}} 파라미터 오버라이드

    Returns
    -------
    dict : 검증 결과 (metrics 목록 + 요약 + legacy 포맷)
    """
    enabled = set(enabled_metrics) if enabled_metrics else set(METRIC_METADATA.keys())
    params_map: dict[str, dict] = params_overrides or {}

    # TSV / CSV 파일 탐색
    tsv_files = list(project_dir.glob("*.tsv"))
    csv_files = list(project_dir.glob("*.csv"))
    all_files = tsv_files + csv_files

    if not all_files:
        return {
            "metrics": [],
            "files": [],
            "total_files": 0,
            "passed_files": 0,
            "all_passed": False,
            "pass_count": 0,
            "warning_count": 0,
            "fail_count": 0,
            "completeness_scores": {},
            "error": "검증할 파일을 찾을 수 없습니다.",
        }

    all_metric_results: list[dict] = []
    file_infos: list[dict] = []
    legacy_file_results: list[dict] = []
    completeness_scores: dict[str, float | None] = {t: None for t in ALL_TYPES}

    for file_path in all_files:
        # 데이터 타입 결정: DB 기록 → 파일명 추론 → unknown
        data_type = file_data_types.get(file_path.name) or _infer_data_type(file_path.name)

        # 원본 텍스트 읽기
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            legacy_file_results.append({"filename": file_path.name, "error": str(e), "passed": False})
            continue

        # 구분자 감지 후 DataFrame 로드
        delimiter = _detect_delimiter(raw_content)
        try:
            df = pd.read_csv(file_path, sep=delimiter, index_col=False)
        except Exception as e:
            legacy_file_results.append({"filename": file_path.name, "error": str(e), "passed": False})
            continue

        file_infos.append({"filename": file_path.name, "df": df, "data_type": data_type})

        # 파일 레벨 지표
        for metric_id, check_fn in [
            ("comp_F001", lambda: check_comp_F001(file_path, data_type, raw_content)),
            ("conf_F001", lambda: check_conf_F001(file_path, data_type, raw_content)),
            ("comp_F003", lambda: check_comp_F003(df, file_path, data_type, params_map.get("comp_F003", {}))),
        ]:
            if metric_id in enabled:
                all_metric_results.append(check_fn())

        # 컬럼 레벨 지표
        col_checks: list[tuple[str, Any]] = [
            ("comp_C001", lambda: check_comp_C001(df, file_path, data_type, params_map.get("comp_C001", {}))),
            ("comp_C002", lambda: check_comp_C002(df, file_path, data_type, params_map.get("comp_C002", {}))),
            ("comp_C003", lambda: check_comp_C003(df, file_path, data_type, params_map.get("comp_C003", {}))),
            ("comp_C004", lambda: check_comp_C004(df, file_path, data_type, params_map.get("comp_C004", {}))),
            ("plau_C001", lambda: check_plau_C001(df, file_path, data_type, params_map.get("plau_C001", {}))),
            ("plau_C002", lambda: check_plau_C002(df, file_path, data_type, params_map.get("plau_C002", {}))),
            ("plau_C003", lambda: check_plau_C003(df, file_path, data_type, params_map.get("plau_C003", {}))),
            ("plau_C004", lambda: check_plau_C004(df, file_path, data_type, params_map.get("plau_C004", {}))),
            ("plau_V001", lambda: check_plau_V001(df, file_path, data_type, params_map.get("plau_V001", {}))),
            ("plau_V002", lambda: check_plau_V002(df, file_path, data_type, params_map.get("plau_V002", {}))),
            ("plau_V003", lambda: check_plau_V003(df, file_path, data_type, params_map.get("plau_V003", {}))),
            ("plau_T001", lambda: check_plau_T001(df, file_path, data_type, params_map.get("plau_T001", {}))),
            ("plau_T002", lambda: check_plau_T002(df, file_path, data_type, params_map.get("plau_T002", {}))),
            ("conf_C001", lambda: check_conf_C001(df, file_path, data_type, params_map.get("conf_C001", {}))),
            ("conf_C002", lambda: check_conf_C002(df, file_path, data_type, params_map.get("conf_C002", {}))),
            ("conf_C003", lambda: check_conf_C003(df, file_path, data_type, {})),
            ("conf_C004", lambda: check_conf_C004(df, file_path, data_type, params_map.get("conf_C004", {}))),
            ("conf_V001", lambda: check_conf_V001(df, file_path, data_type, params_map.get("conf_V001", {}))),
            ("conf_V002", lambda: check_conf_V002(df, file_path, data_type, params_map.get("conf_V002", {}))),
        ]
        for metric_id, check_fn in col_checks:
            if metric_id in enabled:
                all_metric_results.append(check_fn())

        # legacy 포맷: 완전성(comp_C002) 결과 활용
        comp_c002 = next((r for r in all_metric_results if r["metricId"] == "comp_C002" and r["filename"] == file_path.name), None)
        nan_pct = comp_c002["value"] if comp_c002 and comp_c002["value"] is not None else 0.0
        completeness = round(100.0 - nan_pct, 2) if nan_pct is not None else 100.0
        if data_type in completeness_scores:
            completeness_scores[data_type] = completeness

        legacy_file_results.append({
            "filename": file_path.name,
            "data_type": data_type,
            "shape": list(df.shape),
            "total_values": int(df.size),
            "nan_count": int(df.isna().sum().sum()),
            "nan_percentage": round(nan_pct, 2),
            "completeness": completeness,
            "passed": comp_c002["passed"] if comp_c002 and comp_c002["passed"] is not None else True,
        })

    # 교차(심화) 지표
    cross_results = check_cross_metrics(file_infos, enabled, params_map)
    all_metric_results.extend(cross_results)

    # 요약 카운트 (skipped 제외)
    executed = [r for r in all_metric_results if r["passed"] is not None]
    pass_count = sum(1 for r in executed if r["passed"] and r["severity"] not in ("warning", "convention", "characterization"))
    warning_count = sum(1 for r in executed if not r["passed"] and r["severity"] in ("warning", "convention", "characterization"))
    fail_count = sum(1 for r in executed if not r["passed"] and r["severity"] in ("fatal", "error"))
    all_passed = fail_count == 0

    return {
        "metrics": all_metric_results,
        # legacy
        "files": legacy_file_results,
        "total_files": len(legacy_file_results),
        "passed_files": sum(1 for r in legacy_file_results if r.get("passed")),
        "all_passed": all_passed,
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "completeness_scores": completeness_scores,
    }


# ─── 유틸리티 ────────────────────────────────────────────────────────────────

def _detect_delimiter(content: str) -> str:
    first_line = content.split("\n")[0]
    tab_count = first_line.count("\t")
    comma_count = first_line.count(",")
    return "\t" if tab_count >= comma_count else ","


def _infer_data_type(filename: str) -> str:
    """
    명세서 §6.4 — 파일명 기반 dataType 자동 추론
    반환값은 명세서 §3 의 5종: genomics, transcriptomics, proteomics, metabolomics, metadata
    """
    lower = filename.lower()
    # 메타데이터 우선 매칭 (clinical/phenotype 등이 다른 키워드보다 먼저 잡혀야 함)
    if any(k in lower for k in ("clinical", "phenotype", "sample_info", "sampleinfo")):
        return "metadata"
    if any(k in lower for k in ("rna", "transcriptom", "expression", "mrna")):
        return "transcriptomics"
    if any(k in lower for k in ("dna", "methylat", "methyl", "snp", "genomic", "genome", "vcf")):
        return "genomics"
    if any(k in lower for k in ("protein", "proteom", "prot")):
        return "proteomics"
    if "metabol" in lower:
        return "metabolomics"
    # 'meta' 부분 매칭은 마지막에 (다른 키워드 우선)
    if "meta" in lower:
        return "metadata"
    return "unknown"


def get_default_rules() -> list[dict]:
    """모든 지표의 기본 규칙 목록 반환"""
    defaults: dict[str, dict] = {
        "comp_F001": {"validationType": "header_exists", "parameters": {"minColumns": 2}},
        "comp_F003": {"validationType": "threshold", "parameters": {"metric": "total_missing_rate", "operator": "<=", "threshold": 30.0}},
        "comp_C001": {"validationType": "column_exists", "parameters": {"targetColumn": "first_column"}},
        "comp_C002": {"validationType": "threshold", "parameters": {"metric": "missing_rate", "operator": "<=", "threshold": 30.0}},
        "comp_C003": {"validationType": "threshold", "parameters": {"metric": "row_completeness", "operator": "<=", "threshold": 50.0}},
        "comp_C004": {"validationType": "conditional_required", "parameters": {"conditionColumn": "", "conditionValue": None, "requiredColumn": ""}},
        "comp_X001": {"validationType": "cross_threshold", "parameters": {"metric": "sample_matching_rate", "operator": ">=", "threshold": 80.0}},
        "comp_X002": {"validationType": "cross_threshold", "parameters": {"metric": "common_sample_count", "operator": ">=", "threshold": 10}},
        "comp_X003": {"validationType": "cross_threshold", "parameters": {"metric": "meta_omics_linkage", "operator": ">=", "threshold": 80.0}},
        "plau_C001": {"validationType": "range", "parameters": {"min": -100.0, "max": None}},
        "plau_C002": {"validationType": "range", "parameters": {"min": None, "max": 100.0}},
        "plau_C003": {"validationType": "threshold", "parameters": {"metric": "outlier_rate_iqr", "operator": "<=", "threshold": 10.0}},
        "plau_C004": {"validationType": "threshold", "parameters": {"metric": "zero_variance_columns", "operator": "==", "threshold": 0}},
        "plau_V001": {"validationType": "value_set", "parameters": {"targetColumn": "sex", "allowedValues": ["M", "F", "male", "female", "Unknown"]}},
        "plau_V002": {"validationType": "column_range", "parameters": {"targetColumn": "age", "min": 0, "max": 120}},
        "plau_V003": {"validationType": "negative_check", "parameters": {"targetColumn": "all_except_first", "allowNegative": False}},
        "plau_T001": {"validationType": "date_order", "parameters": {"startColumn": "", "endColumn": ""}},
        "plau_T002": {"validationType": "date_order", "parameters": {"birthColumn": "", "eventColumn": ""}},
        "plau_X001": {"validationType": "cross_consistency", "parameters": {"matchColumn": "sample_id", "compareColumn": "subtype"}},
        "plau_X002": {"validationType": "cross_correlation", "parameters": {"targetDataTypes": ["transcriptomics", "proteomics"], "minCorrelation": 0.3, "method": "pearson"}},
        "conf_F001": {"validationType": "file_format", "parameters": {"checkDelimiterConsistency": True}},
        "conf_C001": {"validationType": "duplicate_check", "parameters": {"targetColumn": "first_column"}},
        "conf_C002": {"validationType": "datatype_check", "parameters": {"expectedType": "numeric", "targetColumn": "all_except_first"}},
        "conf_C003": {"validationType": "column_format", "parameters": {"allowedPattern": "^[a-zA-Z0-9_.가-힣-]+$"}},
        "conf_C004": {"validationType": "regex_pattern", "parameters": {"targetColumn": "sample_id", "pattern": "^[A-Za-z0-9_-]+$"}},
        "conf_V001": {"validationType": "value_set", "parameters": {"targetColumn": "", "allowedValues": []}},
        "conf_V002": {"validationType": "date_format", "parameters": {"targetColumn": "", "dateFormat": "YYYY-MM-DD"}},
        "conf_X001": {"validationType": "cross_format", "parameters": {"compareColumn": "sample_id"}},
    }

    rules = []
    for metric_id, meta in METRIC_METADATA.items():
        extra = defaults.get(metric_id, {"validationType": "threshold", "parameters": {}})
        data_types = list(ALL_TYPES)
        if "omics" in meta.get("name", "").lower() or metric_id in {
            "plau_C001", "plau_C002", "plau_C003", "plau_C004", "plau_V003",
            "conf_C002", "comp_F003",
        }:
            data_types = list(OMICS_TYPES)
        elif metric_id in {
            "plau_V001", "plau_V002", "plau_T001", "plau_T002",
            "conf_V001", "conf_V002", "comp_C004",
        }:
            data_types = ["metadata"]

        rules.append({
            "metricId": metric_id,
            "name": meta["name"],
            "dimension": meta["dimension"],
            "level": meta["qualityLevel"],
            "metricLevel": meta["level"],
            "severity": meta["severity"],
            "context": meta["context"],
            "description": meta["name"],
            "dataTypes": data_types,
            "enabled": True,
            "isCustom": False,
            **extra,
        })
    return rules
