"""
GENE-QC Validation Service
OMOP CDM DQM 기반 28개 품질 지표 구현
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
    # Plausibility — BATCH (명세서 v2.0 §5 신규)
    "plau_B001": {"name": "배치 레이블 컬럼 존재 및 분포", "level": "COLUMN", "context": "Verification", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "advanced"},
    "plau_B002": {"name": "배치별 발현값 평균 편차 (CV%)", "level": "VALUE", "context": "Verification", "severity": "warning", "dimension": "Plausibility", "qualityLevel": "advanced"},
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


# ─── 공통 유틸리티 ──────────────────────────────────────────────────────────

# pandas 기본 NA 인식에 잡히지 않는 문자열 표현들.
# `engine.py` 의 NA_VALUES 와 동등 — TCGA / GDC 데이터에서 자주 등장한다.
NA_STRINGS: list[str] = [
    "", "NA", "na", "Na", "null", "NULL", "Null", "NaN", "nan", "None", "none",
    ".", "N/A", "n/a", "-", "--", "?", "missing", "MISSING", "not reported",
    "Not Reported", "not available", "Not Available", "unknown", "Unknown",
]


def _replace_string_nas(df: pd.DataFrame) -> pd.DataFrame:
    """문자열 형태의 NA 표현을 numpy.nan 으로 정규화한 사본을 반환.

    `df.select_dtypes(include="number")` 가 비수치 NA 표현을 만난 컬럼을 통째로
    제외해버리는 문제를 회피하기 위해 결측률/수치 검사 전에 호출한다.
    """
    return df.replace(NA_STRINGS, np.nan)


def _to_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """모든 컬럼을 수치형으로 강제 변환한다(에러는 NaN).

    NA 문자열이 섞여 있어 dtype 이 object 로 잡힌 컬럼을 IQR/하한/상한 등
    수치 검사 대상에 포함시킬 수 있게 한다.
    """
    return df.apply(pd.to_numeric, errors="coerce")


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """후보 컬럼명을 케이스 비민감 + 점(.) 접미/접두 표기 부분일치로 탐색한다.

    예) 후보 ``"gender"`` 가 데이터에서 ``"gender.demographic"`` 으로 존재해도
    매칭된다. TCGA/GDC 다운로드본의 ``age_at_index.demographic`` 같은 컬럼
    이름을 자동으로 잡기 위한 헬퍼.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    # 1단계: 정확 일치 (case-insensitive)
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    # 2단계: 점(.) 표기 부분일치
    for cand in candidates:
        cand_l = cand.lower()
        for cl, orig in cols_lower.items():
            if cl == cand_l or cl.startswith(cand_l + ".") or cl.endswith("." + cand_l):
                return orig
    return None


# 배치/플레이트 후보 컬럼 — TCGA/GDC + 일반 LIMS 명명규칙 망라
BATCH_CANDIDATE_COLUMNS: list[str] = [
    "batch", "batch_id", "batchid", "batch_number",
    "plate", "plate_id", "plateid",
    "run", "run_id", "center", "center_id", "centre", "centre_id",
    "tss", "tss_code", "platform", "sequencing_platform",
]

# TCGA 바코드의 TSS(Tissue Source Site) 코드 추출 패턴
_TCGA_TSS_PATTERN = re.compile(r"^TCGA-([A-Za-z0-9]{2})-")


def _extract_tcga_tss(sample_ids: pd.Series, coverage_threshold: float = 0.7) -> pd.Series | None:
    """샘플 ID 시리즈에서 TCGA TSS 코드를 추출해 프록시 배치 레이블로 반환.

    바코드 매칭 비율이 ``coverage_threshold`` 미만이면 None 을 돌려 잘못된
    프록시 추론을 차단한다.
    """
    if sample_ids is None or len(sample_ids) == 0:
        return None
    ids = sample_ids.astype(str)
    matched = 0
    vals: list[Any] = []
    for s in ids:
        m = _TCGA_TSS_PATTERN.match(s)
        if m:
            matched += 1
            vals.append(m.group(1).upper())
        else:
            vals.append(np.nan)
    if matched / len(ids) < coverage_threshold:
        return None
    return pd.Series(vals, index=ids.index, dtype="object")


def _get_batch_labels(
    df: pd.DataFrame,
    sample_id_series: pd.Series | None = None,
) -> tuple[pd.Series | None, str, str]:
    """배치 레이블을 (메타데이터 컬럼 → TCGA TSS 프록시) 순으로 추출한다.

    Returns
    -------
    (labels, source, column_name)
        - labels: 배치 레이블 Series (없으면 None)
        - source: "metadata" | "tcga_proxy_tss" | "none"
        - column_name: 추출에 사용된 컬럼명 또는 "sample_id"
    """
    colmap = {c.lower(): c for c in df.columns}
    for cand in BATCH_CANDIDATE_COLUMNS:
        if cand in colmap:
            col = colmap[cand]
            labels = df[col].astype(str).str.strip().replace(NA_STRINGS, np.nan)
            if labels.notna().sum() > 0:
                return labels, "metadata", col

    # TCGA TSS proxy — 첫 컬럼이 샘플 ID 라는 가정 (메타데이터/오믹스 공통)
    if sample_id_series is None and len(df.columns) > 0:
        sample_id_series = df.iloc[:, 0]
    tss = _extract_tcga_tss(sample_id_series) if sample_id_series is not None else None
    if tss is not None and tss.notna().sum() > 0:
        return tss, "tcga_proxy_tss", "sample_id"
    return None, "none", ""


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
    """전체 데이터 결측률 검사 (omics 전용)

    "NA"/"."/"-" 등 문자열 NA 가 섞여 있어도 결측으로 카운트하기 위해
    수치형 변환 전에 :func:`_replace_string_nas` 로 정규화한다.
    """
    if data_type not in OMICS_TYPES:
        return _skip("comp_F003", "omics 전용 지표 (metadata 제외)", file_path.name, data_type)
    threshold = params.get("threshold", DEFAULT_MISSING_THRESHOLDS.get(data_type, 30.0))
    # 첫 컬럼(샘플 ID)은 결측률 계산에서 제외, 나머지를 NA 정규화 후 수치형으로 변환
    feature_df = df.iloc[:, 1:] if df.shape[1] > 1 else df
    numeric_df = _to_numeric_df(_replace_string_nas(feature_df))
    if numeric_df.empty or numeric_df.size == 0:
        return _skip("comp_F003", "수치형 데이터 없음", file_path.name, data_type)
    total_missing_rate = float(numeric_df.isna().sum().sum() / numeric_df.size * 100)
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
    """컬럼별 결측률 검사 — 문자열 NA 표현도 결측으로 카운트"""
    threshold = params.get("threshold", DEFAULT_MISSING_THRESHOLDS.get(data_type, 30.0))
    normalized = _replace_string_nas(df)
    col_missing = (normalized.isna().mean() * 100).round(2)
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
    """행(샘플) 완전성 검사 — 문자열 NA 표현도 결측으로 카운트"""
    threshold = params.get("threshold", 50.0)
    normalized = _replace_string_nas(df)
    row_missing = (normalized.isna().mean(axis=1) * 100).round(2)
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


def _omics_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """오믹스 검사를 위해 NA 정규화 + 수치형 강제 변환된 피처 행렬을 반환.

    - 첫 컬럼은 샘플 ID 로 보고 제외
    - 문자열 NA 표현은 NaN 으로 정규화 후 모두 수치형으로 변환
    - 전부 NaN 인 컬럼은 제거
    """
    feature_df = df.iloc[:, 1:] if df.shape[1] > 1 else df
    numeric = _to_numeric_df(_replace_string_nas(feature_df))
    return numeric.dropna(axis=1, how="all")


def check_plau_C001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """발현값 하한 검사"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_C001", "omics 전용 지표", file_path.name, data_type)
    min_val = params.get("min", -np.inf)
    numeric_df = _omics_numeric(df)
    if numeric_df.empty or numeric_df.count().sum() == 0:
        return _skip("plau_C001", "수치형 데이터 없음", file_path.name, data_type)
    actual_min = float(np.nanmin(numeric_df.values))
    below = bool((numeric_df < min_val).any().any())
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
    numeric_df = _omics_numeric(df)
    if numeric_df.empty or numeric_df.count().sum() == 0:
        return _skip("plau_C002", "수치형 데이터 없음", file_path.name, data_type)
    actual_max = float(np.nanmax(numeric_df.values))
    above = bool((numeric_df > max_val).any().any())
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
    numeric_df = _omics_numeric(df)
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
    numeric_df = _omics_numeric(df)
    if numeric_df.empty:
        return _skip("plau_C004", "수치형 데이터 없음", file_path.name, data_type)
    variances = numeric_df.var(ddof=0)
    zero_var_cols = variances[variances.fillna(0) == 0].index.tolist()
    passed = len(zero_var_cols) == 0
    return _result(
        "plau_C004", passed, len(zero_var_cols),
        f"분산=0 컬럼 없음" if passed else f"분산=0 컬럼 {len(zero_var_cols)}개 발견",
        file_path.name, data_type,
        [str(c) for c in zero_var_cols[:20]],
    )


# 성별/연령/날짜 컬럼 자동 탐색 후보 — TCGA/GDC 명명규칙 포함
GENDER_CANDIDATES: list[str] = [
    "gender.demographic", "gender", "sex", "성별",
    "sex_at_birth", "Sex", "Gender",
]
AGE_CANDIDATES: list[str] = [
    "age_at_index.demographic", "age_at_diagnosis.diagnoses",
    "age_at_index", "age_at_diagnosis", "age_at_earliest_diagnosis_in_years.diagnoses.xena_derived",
    "age", "나이", "연령",
]
DATE_START_CANDIDATES: list[str] = [
    "start_date", "date_of_diagnosis", "diagnosis_date",
    "days_to_birth.demographic", "days_to_birth",
]
DATE_END_CANDIDATES: list[str] = [
    "end_date", "date_of_death", "date_of_last_follow_up",
    "days_to_death.demographic", "days_to_death",
    "days_to_last_follow_up.diagnoses", "days_to_last_follow_up", "days_to_last_known_alive",
]
BIRTH_CANDIDATES: list[str] = [
    "birth_date", "date_of_birth", "days_to_birth.demographic", "days_to_birth",
]
EVENT_CANDIDATES: list[str] = [
    "diagnosis_date", "date_of_diagnosis", "age_at_diagnosis.diagnoses", "age_at_diagnosis",
    "days_to_diagnosis", "event_date",
]


def check_plau_V001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """성별 값 허용범위 검사 (metadata 전용)

    TCGA/GDC 의 ``gender.demographic`` 처럼 점(.) 접미가 붙은 컬럼명도
    :func:`_find_column` 으로 자동 탐색한다.
    """
    if data_type != "metadata":
        return _skip("plau_V001", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "")
    allowed = set(params.get("allowedValues", [
        "M", "F", "m", "f", "male", "female", "Male", "Female",
        "남", "여", "Unknown", "unknown",
    ]))

    gender_col: str | None = None
    if target_col and target_col != "first_column" and target_col in df.columns:
        gender_col = target_col
    else:
        gender_col = _find_column(df, GENDER_CANDIDATES)
    if gender_col is None:
        return _skip("plau_V001", "성별 컬럼 찾을 수 없음 (sex/gender/gender.demographic)", file_path.name, data_type)

    # 'not reported' 류는 NA_STRINGS 로 이미 정규화되므로 검증 대상에서 자연스럽게 제외
    col_vals = df[gender_col].replace(NA_STRINGS, np.nan).dropna().astype(str).str.strip()
    invalid = col_vals[~col_vals.isin(allowed)].unique().tolist()
    passed = len(invalid) == 0
    return _result(
        "plau_V001", passed, len(invalid),
        f"'{gender_col}' 성별 값 검증 통과 ({len(col_vals)}건)"
        if passed else f"허용되지 않은 값 {len(invalid)}개: {invalid[:5]}",
        file_path.name, data_type,
        invalid[:20],
    )


def check_plau_V002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """연령 값 범위 검사 (metadata 전용)

    - TCGA ``age_at_index.demographic`` / ``age_at_diagnosis`` 등 점(.) 접미
      컬럼명을 자동 탐색한다.
    - 중앙값이 365 보다 크면 일(day) 단위로 보고 365.25 로 나눠 연(year) 단위로
      자동 변환한다 (TCGA 의 ``age_at_diagnosis`` 는 일 단위).
    """
    if data_type != "metadata":
        return _skip("plau_V002", "metadata 전용 지표", file_path.name, data_type)
    target_col = params.get("targetColumn", "")
    min_age = params.get("min", 0)
    max_age = params.get("max", 120)

    age_col: str | None = None
    if target_col and target_col != "first_column" and target_col in df.columns:
        age_col = target_col
    else:
        age_col = _find_column(df, AGE_CANDIDATES)
    if age_col is None:
        return _skip("plau_V002", "연령 컬럼 찾을 수 없음 (age/age_at_index/age_at_diagnosis)", file_path.name, data_type)

    raw = df[age_col].replace(NA_STRINGS, np.nan)
    ages = pd.to_numeric(raw, errors="coerce").dropna()
    if len(ages) == 0:
        return _skip("plau_V002", f"연령 컬럼 '{age_col}' 에 유효 수치값 없음", file_path.name, data_type)

    unit_note = f" (col='{age_col}')"
    if float(ages.median()) > 365:
        ages = ages / 365.25
        unit_note = f" (col='{age_col}', day→year 자동 변환)"

    out_of_range = ages[(ages < min_age) | (ages > max_age)]
    passed = len(out_of_range) == 0
    return _result(
        "plau_V002", passed, len(out_of_range),
        f"연령 범위 [{min_age}, {max_age}] 검증 통과{unit_note}"
        if passed else f"범위 초과 값 {len(out_of_range)}개{unit_note}",
        file_path.name, data_type,
        [str(round(float(v), 1)) for v in out_of_range.tolist()[:20]],
    )


def check_plau_V003(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """수치형 컬럼 음수값 허용 검사"""
    if data_type not in OMICS_TYPES:
        return _skip("plau_V003", "omics 전용 지표", file_path.name, data_type)
    allow_negative = params.get("allowNegative", False)
    if allow_negative:
        return _result("plau_V003", True, 0, "음수값 허용 설정됨", file_path.name, data_type)
    numeric_df = _omics_numeric(df)
    if numeric_df.empty or numeric_df.count().sum() == 0:
        return _skip("plau_V003", "수치형 데이터 없음", file_path.name, data_type)
    neg_count = int((numeric_df < 0).sum().sum())
    passed = neg_count == 0
    return _result(
        "plau_V003", passed, neg_count,
        "음수값 없음" if passed else f"음수값 {neg_count}개 발견 (음수 불허용 설정)",
        file_path.name, data_type,
    )


def _parse_temporal_series(s: pd.Series) -> tuple[pd.Series, str]:
    """날짜 / 일수(days_to_*) 시리즈를 통일된 정렬 가능 수치로 변환.

    - 컬럼명이 ``days_to_*`` 로 시작하거나 ``days`` 를 포함하면 정수 일수로 간주
    - 그 외에는 ``pd.to_datetime`` 시도, 실패한 셀은 NaN
    """
    cleaned = s.replace(NA_STRINGS, np.nan)
    name = str(s.name).lower()
    if name.startswith("days_to_") or "days_to" in name or name.endswith("_days") or name == "days":
        return pd.to_numeric(cleaned, errors="coerce"), "days"
    parsed = pd.to_datetime(cleaned, errors="coerce")
    if parsed.notna().sum() == 0:
        # 날짜로 못 잡으면 마지막으로 수치형으로 시도
        return pd.to_numeric(cleaned, errors="coerce"), "numeric"
    return parsed, "datetime"


def check_plau_T001(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """날짜 순서 타당성 (시작 <= 종료) — metadata 전용

    파라미터로 ``startColumn``/``endColumn`` 이 명시되면 우선 사용하고,
    없으면 TCGA/GDC 의 ``days_to_birth`` / ``days_to_death`` /
    ``days_to_last_follow_up`` 등을 자동 탐색한다.
    """
    if data_type != "metadata":
        return _skip("plau_T001", "metadata 전용 지표", file_path.name, data_type)
    start_param = params.get("startColumn", "")
    end_param = params.get("endColumn", "")

    if start_param and start_param in df.columns:
        start_col: str | None = start_param
    else:
        start_col = _find_column(df, DATE_START_CANDIDATES)
    if end_param and end_param in df.columns:
        end_col: str | None = end_param
    else:
        end_col = _find_column(df, DATE_END_CANDIDATES)

    if start_col is None or end_col is None:
        return _skip(
            "plau_T001",
            "날짜/시간 컬럼 자동 탐색 실패 (start/end_date 또는 days_to_birth/days_to_death)",
            file_path.name, data_type,
        )

    starts, start_kind = _parse_temporal_series(df[start_col])
    ends, end_kind = _parse_temporal_series(df[end_col])
    if start_kind != end_kind and not (start_kind in ("days", "numeric") and end_kind in ("days", "numeric")):
        return _skip(
            "plau_T001",
            f"날짜 단위 불일치 (start={start_kind}, end={end_kind})",
            file_path.name, data_type,
        )

    valid = starts.notna() & ends.notna()
    if int(valid.sum()) == 0:
        return _skip("plau_T001", "유효 비교 가능 행 없음", file_path.name, data_type)
    violations = int((starts[valid] > ends[valid]).sum())
    passed = violations == 0
    return _result(
        "plau_T001", passed, violations,
        f"날짜 순서 정상 ('{start_col}' ≤ '{end_col}', {int(valid.sum())}건 비교)"
        if passed else f"'{start_col}' > '{end_col}' 인 행 {violations}개",
        file_path.name, data_type,
    )


def check_plau_T002(df: pd.DataFrame, file_path: Path, data_type: str, params: dict) -> dict:
    """출생-진단(이벤트) 날짜 순서 검사 (metadata 전용).

    파라미터로 ``birthColumn``/``eventColumn`` 이 명시되면 우선 사용하고,
    없으면 TCGA 의 ``days_to_birth`` 와 ``age_at_diagnosis`` /
    ``date_of_diagnosis`` 류를 자동 탐색한다.

    참고: TCGA 의 ``days_to_birth`` 는 진단 시점 기준 음수(과거)이므로
    의미상 "출생이 진단보다 앞선다" 는 사실은 ``days_to_birth < 0`` 으로
    표현된다. 같은 단위(연/일)로 환산해 비교한다.
    """
    if data_type != "metadata":
        return _skip("plau_T002", "metadata 전용 지표", file_path.name, data_type)
    birth_param = params.get("birthColumn", "")
    event_param = params.get("eventColumn", "")

    birth_col = birth_param if birth_param and birth_param in df.columns else _find_column(df, BIRTH_CANDIDATES)
    event_col = event_param if event_param and event_param in df.columns else _find_column(df, EVENT_CANDIDATES)
    if birth_col is None or event_col is None:
        return _skip(
            "plau_T002",
            "출생/진단 컬럼 자동 탐색 실패 (birth_date/days_to_birth, date_of_diagnosis/age_at_diagnosis)",
            file_path.name, data_type,
        )

    birth_vals, birth_kind = _parse_temporal_series(df[birth_col])
    event_vals, event_kind = _parse_temporal_series(df[event_col])
    valid = birth_vals.notna() & event_vals.notna()
    if int(valid.sum()) == 0:
        return _skip("plau_T002", "유효 비교 가능 행 없음", file_path.name, data_type)

    # 두 컬럼 모두 datetime 이면 일반 날짜 비교
    if birth_kind == "datetime" and event_kind == "datetime":
        violations = int((event_vals[valid] < birth_vals[valid]).sum())
        details_extra = ""
    else:
        # days_to_birth(음수=과거) + age_at_diagnosis(양수=경과일) 같은 케이스
        # → "이벤트가 출생보다 늦다" 만 확인.
        b_name = str(birth_col).lower()
        if "days_to_birth" in b_name:
            # days_to_birth 는 보통 음수가 정상
            violations = int(((birth_vals[valid] > 0) & (event_vals[valid] > 0)).sum())
            details_extra = " (days_to_birth 양수 + 양수 진단경과 케이스 검사)"
        else:
            violations = int((event_vals[valid] < birth_vals[valid]).sum())
            details_extra = ""

    passed = violations == 0
    return _result(
        "plau_T002", passed, violations,
        f"출생→이벤트 순서 정상 ('{birth_col}' → '{event_col}', {int(valid.sum())}건 비교){details_extra}"
        if passed else f"출생일 이후 발생해야 할 이벤트 {violations}건 위반{details_extra}",
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
    """수치형 컬럼 데이터 타입 검사 (omics 전용)

    문자열 NA 표현(``NA``, ``.``, ``-`` 등)은 결측으로 보고 검증에서 제외한다.
    """
    if data_type not in OMICS_TYPES:
        return _skip("conf_C002", "omics 전용 지표", file_path.name, data_type)
    exclude = set(params.get("excludeColumns", [df.columns[0]] if len(df.columns) > 0 else []))
    target_cols = [c for c in df.columns if c not in exclude]
    non_numeric = []
    for col in target_cols:
        series = df[col].replace(NA_STRINGS, np.nan)
        non_na = series.dropna()
        if len(non_na) == 0:
            continue
        converted = pd.to_numeric(non_na, errors="coerce")
        if converted.isna().any():
            non_numeric.append(col)
    passed = len(non_numeric) == 0
    return _result(
        "conf_C002", passed, len(non_numeric),
        "수치형 타입 검증 통과" if passed else f"비수치형 컬럼 {len(non_numeric)}개",
        file_path.name, data_type,
        [str(c) for c in non_numeric[:20]],
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
    """교차 검증 지표 실행 (다중 파일 필요).

    plau_B001/B002 (배치) 는 단일 파일에서도 동작하지만 메타데이터+오믹스
    조합이 있을 때 더 의미가 있어 여기서 함께 처리한다.
    """
    results = []

    # 배치 지표는 단일 파일에서도 평가 가능 — 별도로 실행
    if "plau_B001" in enabled_metrics:
        results.append(_check_plau_B001(file_infos, params_map.get("plau_B001", {})))
    if "plau_B002" in enabled_metrics:
        results.append(_check_plau_B002(file_infos, params_map.get("plau_B002", {})))

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

    # plau_X001: 메타데이터-오믹스 subtype 일관성
    # 명세서 §2.5 + §4.2 cross_consistency — matchColumn/compareColumn 기반
    if "plau_X001" in enabled_metrics:
        results.append(
            _check_plau_X001(file_infos, params_map.get("plau_X001", {}))
        )

    # plau_X002: 오믹스 간 발현 상관관계
    # 명세서 §2.5 + §4.2 cross_correlation — targetDataTypes / minCorrelation / method
    if "plau_X002" in enabled_metrics:
        results.append(
            _check_plau_X002(file_infos, params_map.get("plau_X002", {}))
        )

    return results


# ─── 배치 효과 지표 구현 (plau_B001 / plau_B002) ───────────────────────────


def _check_plau_B001(file_infos: list[dict], params: dict) -> dict:
    """배치 레이블 컬럼 존재 및 분포 균형 검사 (명세서 §5).

    - 메타데이터 파일에서 ``batch``/``plate``/``run``/``tss`` 등 명시적 컬럼을
      우선 찾는다. 없으면 임의의 오믹스 파일 첫 컬럼(샘플 ID)에서 TCGA TSS
      코드를 프록시 배치 레이블로 추출한다.
    - 모든 배치 그룹 크기가 ``minGroupSize`` 이상이면 PASS, 일부 그룹이 작으면
      WARNING.
    """
    min_group_size = int(params.get("minGroupSize", 3))

    # 1) 메타데이터 우선
    labels: pd.Series | None = None
    source = "none"
    column = ""
    source_file = ""
    for info in file_infos:
        if info.get("data_type") == "metadata" and info.get("df") is not None:
            labels, source, column = _get_batch_labels(info["df"], info["df"].iloc[:, 0] if info["df"].shape[1] > 0 else None)
            if labels is not None:
                source_file = info["filename"]
                break

    # 2) 메타데이터에 없으면 오믹스 파일의 샘플 ID에서 TSS 추출 시도
    if labels is None:
        for info in file_infos:
            if info.get("data_type") in OMICS_TYPES and info.get("df") is not None and info["df"].shape[1] > 0:
                tss = _extract_tcga_tss(info["df"].iloc[:, 0])
                if tss is not None and tss.notna().sum() > 0:
                    labels = tss
                    source = "tcga_proxy_tss"
                    column = "sample_id"
                    source_file = info["filename"]
                    break

    if labels is None:
        return _skip(
            "plau_B001",
            "배치 컬럼(batch/plate/run/tss) 및 TCGA 바코드 프록시 모두 사용 불가 — 배치 평가 생략",
            filename="",
            data_type="",
        )

    valid_labels = labels.dropna()
    counts = valid_labels.value_counts()
    n_batches = int(counts.size)
    small_groups = int((counts < min_group_size).sum())

    if n_batches < 2:
        return _result(
            "plau_B001", False, n_batches,
            f"배치 그룹이 1개({list(counts.index)[:3]}) — 분포 평가 불가 (source={source})",
            filename=source_file, data_type="metadata" if source == "metadata" else "all",
        )

    passed = small_groups == 0
    details = (
        f"배치 {n_batches}개 감지 (source={source}, column={column}), "
        f"소규모 그룹(<{min_group_size}) {small_groups}개"
    )
    return _result(
        "plau_B001", passed, n_batches, details,
        filename=source_file, data_type="metadata" if source == "metadata" else "all",
        affected_items=[str(k) for k in counts[counts < min_group_size].index[:20].tolist()],
    )


def _build_sample_to_batch(file_infos: list[dict]) -> tuple[pd.Series | None, str, str]:
    """샘플 ID → 배치 레이블 매핑을 만든다.

    - 메타데이터에 배치 컬럼이 있으면 (sample_id 첫 컬럼, batch 컬럼) 으로 매핑
    - 없으면 임의 오믹스 파일의 샘플 ID 에서 TCGA TSS 프록시 시도
    """
    for info in file_infos:
        if info.get("data_type") == "metadata" and info.get("df") is not None:
            df = info["df"]
            if df.shape[1] < 2:
                continue
            labels, source, column = _get_batch_labels(df, df.iloc[:, 0])
            if labels is None:
                continue
            sample_ids = df.iloc[:, 0].astype(str)
            mapping = pd.Series(labels.values, index=sample_ids).dropna()
            mapping = mapping[mapping.astype(str) != ""]
            if len(mapping) > 0:
                return mapping, source, column

    # 메타데이터에 없으면 오믹스 파일에서 TSS 프록시
    for info in file_infos:
        if info.get("data_type") in OMICS_TYPES and info.get("df") is not None and info["df"].shape[1] > 0:
            sample_ids = info["df"].iloc[:, 0].astype(str)
            tss = _extract_tcga_tss(sample_ids)
            if tss is not None:
                mapping = pd.Series(tss.values, index=sample_ids).dropna()
                if len(mapping) > 0:
                    return mapping, "tcga_proxy_tss", "sample_id"
    return None, "none", ""


def _check_plau_B002(file_infos: list[dict], params: dict) -> dict:
    """배치별 발현값 평균 편차 검사 (명세서 §5, 오믹스 전용).

    각 오믹스 파일에 대해 sample-level 평균 발현을 구한 뒤, 배치 레이블별
    그룹 평균의 변동계수(CV%, σ/|μ|×100) 가 ``maxCV`` 이하인지 평가한다.
    """
    max_cv = float(params.get("maxCV", 15.0))

    mapping, source, column = _build_sample_to_batch(file_infos)
    if mapping is None:
        return _skip(
            "plau_B002",
            "샘플→배치 매핑을 만들 수 없음 (메타데이터 배치 컬럼/TCGA 프록시 없음)",
        )

    omics_infos = [i for i in file_infos if i.get("data_type") in OMICS_TYPES and i.get("df") is not None]
    if not omics_infos:
        return _skip("plau_B002", "오믹스 파일이 없음")

    per_file_cv: list[tuple[str, float, int]] = []
    for info in omics_infos:
        df = info["df"]
        if df.shape[1] < 2:
            continue
        sample_ids = df.iloc[:, 0].astype(str)
        feature_df = df.iloc[:, 1:]
        numeric = _to_numeric_df(_replace_string_nas(feature_df))
        if numeric.shape[1] == 0:
            continue
        # 첫 컬럼이 sample id 인 long-format(행=샘플)을 가정
        sample_mean = numeric.mean(axis=1, skipna=True)
        sample_mean.index = sample_ids

        common = sample_mean.index.intersection(mapping.index)
        if len(common) < 6:
            continue
        means = sample_mean.loc[common]
        labels = mapping.loc[common]
        # 그룹당 최소 2개 샘플이 있어야 평균 의미 있음
        valid_groups = labels.value_counts()
        valid_groups = valid_groups[valid_groups >= 2]
        if len(valid_groups) < 2:
            continue
        mask = labels.isin(valid_groups.index)
        batch_means = means[mask].groupby(labels[mask]).mean()
        overall = float(means[mask].mean())
        if not np.isfinite(overall) or abs(overall) < 1e-12:
            continue
        cv = float(batch_means.std(ddof=0) / abs(overall) * 100)
        per_file_cv.append((info["filename"], cv, int(mask.sum())))

    if not per_file_cv:
        return _skip(
            "plau_B002",
            "유효한 오믹스↔배치 매칭 샘플이 부족해 CV 계산 불가",
        )

    # 가장 큰 CV (최악 모달리티) 를 기준으로 판정
    worst_file, worst_cv, sample_n = max(per_file_cv, key=lambda x: x[1])
    passed = worst_cv <= max_cv
    return _result(
        "plau_B002", passed, round(worst_cv, 2),
        f"배치 간 평균 CV(최악) {worst_cv:.2f}% (임계값: {max_cv}%, source={source}, "
        f"기준 파일: {worst_file}, n={sample_n})",
        filename=worst_file,
        data_type="omics",
        affected_items=[f"{fn}: CV={cv:.2f}% (n={n})" for fn, cv, n in per_file_cv[:10]],
    )


# ─── 심화 Plausibility 교차 지표 구현 ──────────────────────────────────────

def _omics_sample_mean_series(df: pd.DataFrame) -> pd.Series:
    """
    오믹스 DataFrame(행=feature, 열=sample)에서 sample별 평균 발현치를 반환.
    NaN은 평균 계산에서 제외하고, 비어 있는 sample은 NaN으로 남는다.
    """
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        # 첫 컬럼이 sample id로 들어와 모두 비수치로 잡혔을 가능성
        numeric = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    return numeric.mean(axis=0, skipna=True)


def _check_plau_X002(file_infos: list[dict], params: dict) -> dict:
    """
    오믹스 간 발현 상관관계 (plau_X002, 명세서 §4.2 cross_correlation).
    targetDataTypes 에 지정된 두 오믹스의 공통 샘플에 대해 sample-level 평균
    발현치를 Pearson 또는 Spearman 상관계수로 평가한다.
    """
    target_types = params.get("targetDataTypes") or ["transcriptomics", "proteomics"]
    min_corr = float(params.get("minCorrelation", 0.3))
    method = str(params.get("method", "pearson")).lower()
    if method not in ("pearson", "spearman"):
        method = "pearson"

    candidates = [
        info for info in file_infos
        if info.get("data_type") in target_types and info.get("df") is not None
    ]
    if len(candidates) < 2:
        return _skip(
            "plau_X002",
            f"targetDataTypes={target_types} 중 2개 이상의 오믹스 파일이 필요",
        )

    # 명세서가 두 dataType 비교를 가정하므로 dataType 단위로 묶음
    by_type: dict[str, dict] = {}
    for info in candidates:
        by_type.setdefault(info["data_type"], info)  # 동일 dataType 다수면 첫 파일 사용

    if len(by_type) < 2:
        return _skip(
            "plau_X002",
            f"두 개의 서로 다른 dataType이 필요. 현재: {sorted(by_type.keys())}",
        )

    types_used = list(by_type.keys())[:2]
    info_a, info_b = by_type[types_used[0]], by_type[types_used[1]]
    sample_a = _omics_sample_mean_series(info_a["df"]).dropna()
    sample_b = _omics_sample_mean_series(info_b["df"]).dropna()
    common = sample_a.index.intersection(sample_b.index)
    if len(common) < 3:
        return _skip(
            "plau_X002",
            f"공통 샘플이 부족합니다 (n={len(common)}, 최소 3개 필요)",
        )

    vec_a = sample_a.loc[common]
    vec_b = sample_b.loc[common]

    # 분산이 0이면 상관관계 정의 불가
    if vec_a.var(ddof=0) == 0 or vec_b.var(ddof=0) == 0:
        return _skip(
            "plau_X002",
            "공통 샘플의 발현 분산이 0이라 상관관계를 계산할 수 없습니다",
        )

    if method == "spearman":
        corr_value = float(vec_a.corr(vec_b, method="spearman"))
    else:
        corr_value = float(vec_a.corr(vec_b, method="pearson"))

    if np.isnan(corr_value):
        return _skip("plau_X002", "상관계수 계산 결과 NaN")

    passed = abs(corr_value) >= min_corr
    details = (
        f"{method.title()} 상관계수 {corr_value:.3f} "
        f"({types_used[0]}↔{types_used[1]}, 공통 샘플 {len(common)}개, 임계값: {min_corr})"
    )
    return _result(
        "plau_X002",
        passed,
        round(corr_value, 4),
        details,
        filename=f"{info_a['filename']} ↔ {info_b['filename']}",
        data_type="+".join(types_used),
    )


def _check_plau_X001(file_infos: list[dict], params: dict) -> dict:
    """
    메타데이터-오믹스 subtype 일관성 (plau_X001, 명세서 §4.2 cross_consistency).
    메타데이터의 `compareColumn`(기본 subtype) 그룹 간 오믹스 sample-level
    평균 발현이 유의하게 분리되는지를 일원 ANOVA F-statistic 으로 평가한다.
    """
    match_col = params.get("matchColumn", "sample_id")  # 현재 구현은 첫 컬럼=샘플ID 가정
    compare_col_param = params.get("compareColumn", "subtype")
    p_threshold = float(params.get("pValueThreshold", 0.05))
    min_group_size = int(params.get("minGroupSize", 3))

    meta_infos = [i for i in file_infos if i.get("data_type") == "metadata"]
    omics_infos = [i for i in file_infos if i.get("data_type") in OMICS_TYPES]
    if not meta_infos or not omics_infos:
        return _skip("plau_X001", "메타데이터와 오믹스 파일이 모두 필요")

    meta_df: pd.DataFrame = meta_infos[0]["df"]
    if meta_df is None or meta_df.empty:
        return _skip("plau_X001", "메타데이터가 비어 있음")

    # subtype 컬럼 탐색 (대소문자 무시 + 동의어)
    candidate_names = {compare_col_param.lower(), "subtype", "pam50", "group", "class", "label", "type"}
    compare_col = next(
        (c for c in meta_df.columns if c.lower() in candidate_names),
        None,
    )
    if compare_col is None:
        return _skip(
            "plau_X001",
            f"메타데이터에서 비교 컬럼을 찾을 수 없음 (탐색 후보: {sorted(candidate_names)})",
        )

    # 메타데이터의 sample_id → subtype 매핑 (첫 컬럼을 샘플 ID로 가정)
    if meta_df.shape[1] < 2:
        return _skip("plau_X001", "메타데이터 컬럼이 부족함")
    sample_ids = meta_df.iloc[:, 0].astype(str)
    subtype_series = meta_df[compare_col].astype(str)
    subtype_map = pd.Series(subtype_series.values, index=sample_ids).dropna()
    subtype_map = subtype_map[subtype_map != ""]

    # 각 오믹스에 대해 ANOVA F-statistic 으로 검정 후 최소 p-value 채택
    try:
        from scipy import stats  # noqa: WPS433  (지연 import — 선택적 의존성)
    except ImportError:
        return _skip("plau_X001", "scipy 가 설치되어 있지 않아 분산 분석 불가")

    omics_pvalues: list[tuple[str, float]] = []
    for info in omics_infos:
        sample_mean = _omics_sample_mean_series(info["df"]).dropna()
        common = sample_mean.index.intersection(subtype_map.index)
        if len(common) < min_group_size * 2:
            continue
        subtype_for_common = subtype_map.loc[common]
        groups = [
            sample_mean.loc[common][subtype_for_common == s].values
            for s in subtype_for_common.unique()
            if (subtype_for_common == s).sum() >= min_group_size
        ]
        if len(groups) < 2:
            continue
        f_stat, p_value = stats.f_oneway(*groups)
        if not np.isnan(p_value):
            omics_pvalues.append((info["filename"], float(p_value)))

    if not omics_pvalues:
        return _skip(
            "plau_X001",
            "subtype 그룹 크기/매칭 샘플이 부족해 ANOVA 를 실행하지 못함",
        )

    # 가장 분리도가 큰(=p-value 가장 작은) 오믹스 결과로 평가
    omics_pvalues.sort(key=lambda x: x[1])
    best_file, best_p = omics_pvalues[0]
    passed = best_p < p_threshold
    details = (
        f"subtype='{compare_col}' 그룹별 발현 분리 ANOVA p-value={best_p:.4f} "
        f"(임계값 < {p_threshold}, 기준 파일: {best_file})"
    )
    return _result(
        "plau_X001",
        passed,
        round(best_p, 6),
        details,
        filename=best_file,
        data_type="metadata+omics",
    )


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
        "plau_B001": {"validationType": "batch_distribution", "parameters": {"minGroupSize": 3}},
        "plau_B002": {"validationType": "batch_cv", "parameters": {"maxCV": 15.0}},
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
            "conf_C002", "comp_F003", "plau_B002",
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
