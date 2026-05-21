"""
GENE-QC Validation Engine
Actual validation logic ported to Python for server-side execution.
Clinical Data Life Cycle DQM (An et al., JMIR 2025): Completeness / Plausibility / Conformance
"""

import re
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

BATCH_CANDIDATE_COLUMNS = [
    "batch", "batch_id", "batchid",
    "plate", "plate_id", "plateid",
    "run", "run_id", "center", "center_id",
    "tss", "tss_code",
]


# ── Rule Definitions ───────────────────────────────────────────
RULES = {
    # === COMPLETENESS (Basic) ===
    "comp_F001": {
        "name": "File Header Existence",
        "name_ko": "파일 헤더 존재 여부",
        "dimension": "Completeness", "level": "basic", "severity": "fatal",
        "data_types": ["all"],
        "description": "Verifies that the file contains a header row with at least 2 columns."
    },
    "comp_C001": {
        "name": "Required Sample ID Column",
        "name_ko": "샘플 ID 컬럼 필수 존재",
        "dimension": "Completeness", "level": "basic", "severity": "fatal",
        "data_types": ["all"],
        "description": "Checks that the index (sample ID) exists without NULL values."
    },
    "comp_C002": {
        "name": "Column-level Missing Rate",
        "name_ko": "컬럼별 결측률 검사",
        "dimension": "Completeness", "level": "basic", "severity": "warning",
        "data_types": ["all"],
        "params": {"threshold": 30}
    },
    "comp_C003": {
        "name": "Row (Sample) Completeness",
        "name_ko": "행(샘플) 완전성 검사",
        "dimension": "Completeness", "level": "basic", "severity": "warning",
        "data_types": ["all"],
        "params": {"threshold": 50}
    },
    "comp_F003": {
        "name": "Overall Data Missing Rate",
        "name_ko": "전체 데이터 결측률",
        "dimension": "Completeness", "level": "basic", "severity": "warning",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
        "params": {"threshold": 20}
    },
    # === COMPLETENESS (Advanced - Cross) ===
    "comp_X001": {
        "name": "Cross-Dataset Sample Matching Rate",
        "name_ko": "데이터셋 간 샘플 매칭률",
        "dimension": "Completeness", "level": "advanced", "severity": "warning",
        "data_types": ["all"],
        "params": {"threshold": 80}
    },
    "comp_X002": {
        "name": "Common Sample Count",
        "name_ko": "전체 데이터셋 공통 샘플 수",
        "dimension": "Completeness", "level": "advanced", "severity": "error",
        "data_types": ["all"],
        "params": {"threshold": 10}
    },
    # === PLAUSIBILITY (Basic) ===
    "plau_C001": {
        "name": "Expression Value Lower Bound",
        "name_ko": "발현값 하한 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "characterization",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
        "params": {"min": -100}
    },
    "plau_C002": {
        "name": "Expression Value Upper Bound",
        "name_ko": "발현값 상한 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "characterization",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
        "params": {"max": 100}
    },
    "plau_C003": {
        "name": "IQR-Based Outlier Detection",
        "name_ko": "IQR 기반 이상치 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "warning",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
        "params": {"threshold": 5, "iqr_multiplier": 1.5}
    },
    "plau_C004": {
        "name": "Zero-Variance Column Detection",
        "name_ko": "상수값 컬럼 탐지 (분산=0)",
        "dimension": "Plausibility", "level": "basic", "severity": "warning",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
    },
    "plau_V001": {
        "name": "Sex/Gender Value Set Check",
        "name_ko": "성별 값 허용범위 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "error",
        "data_types": ["metadata", "survival"],
        "description": "Auto-detects gender/sex column (gender.demographic, gender, sex). Validates values belong to allowed set.",
        "params": {
            "allowed": ["M", "F", "male", "female", "Male", "Female", "남", "여", "Unknown", "unknown", "not reported", "Not Reported"]
        }
    },
    "plau_V002": {
        "name": "Age Value Range Check",
        "name_ko": "연령 값 범위 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "error",
        "data_types": ["metadata", "survival"],
        "description": "Auto-detects age column (age_at_index.demographic, age_at_diagnosis, age). Auto-converts days to years if needed.",
        "params": {"min": 0, "max": 120}
    },
    "plau_T001": {
        "name": "Temporal Plausibility Check",
        "name_ko": "시간 순서 타당성 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "characterization",
        "data_types": ["metadata", "survival"],
        "description": "Auto-detects temporal columns (days_to_birth, days_to_death, days_to_last_follow_up). Checks logical consistency.",
        "params": {}
    },
    "plau_V003": {
        "name": "Vital Status Value Set Check",
        "name_ko": "생존 상태 값 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "characterization",
        "data_types": ["metadata", "survival"],
        "description": "Auto-detects vital_status column. Validates values (Alive, Dead, Not Reported, etc.).",
        "params": {}
    },
    "plau_V004": {
        "name": "Survival Time Plausibility",
        "name_ko": "생존 시간 타당성 검사",
        "dimension": "Plausibility", "level": "basic", "severity": "warning",
        "data_types": ["survival"],
        "description": "Auto-detects survival time columns (OS.time, PFS.time, days_to_death). Validates non-negative and plausible range.",
        "params": {"max_days": 36500}
    },
    "plau_B001": {
        "name": "Exploratory Batch Separation (PC1/PC2)",
        "name_ko": "탐색적 배치 분리도 (PC1/PC2)",
        "dimension": "Plausibility", "level": "advanced", "severity": "characterization",
        "data_types": ["all"],
        "description": "If batch labels are available, evaluates exploratory batch separation on PC1/PC2. If unavailable, this check is skipped.",
        "params": {"warn_threshold": 0.2, "min_group_size": 3, "max_features": 2000}
    },
    # === CONFORMANCE (Basic) ===
    "conf_F001": {
        "name": "File Format Consistency",
        "name_ko": "파일 형식 일관성 검사",
        "dimension": "Conformance", "level": "basic", "severity": "error",
        "data_types": ["all"],
    },
    "conf_C001": {
        "name": "Primary Key Uniqueness",
        "name_ko": "고유 식별자 유일성 검사",
        "dimension": "Conformance", "level": "basic", "severity": "error",
        "data_types": ["all"],
    },
    "conf_C002": {
        "name": "Expression Data Type Check",
        "name_ko": "발현값 데이터 타입 검사",
        "dimension": "Conformance", "level": "basic", "severity": "error",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
    },
    "conf_V001": {
        "name": "Sample ID Format Pattern",
        "name_ko": "샘플 ID 형식 패턴 검사",
        "dimension": "Conformance", "level": "basic", "severity": "convention",
        "data_types": ["all"],
        "params": {"pattern": r"^[A-Za-z0-9_.\-]+$"}
    },
    "conf_V002": {
        "name": "Negative Value Check (Raw Count)",
        "name_ko": "음수값 존재 여부 (Raw count)",
        "dimension": "Conformance", "level": "basic", "severity": "warning",
        "data_types": ["genomics", "methylation", "transcriptomics", "proteomics", "metabolomics"],
    },
    "conf_B001": {
        "name": "Batch Label Availability",
        "name_ko": "배치 레이블 가용성",
        "dimension": "Conformance", "level": "basic", "severity": "convention",
        "data_types": ["all"],
        "description": "Checks batch label availability from metadata columns or TCGA barcode proxy (TSS). If unavailable, batch evaluation is skipped."
    },
    # === CONFORMANCE (Advanced - Cross) ===
    "conf_X001": {
        "name": "Cross-Dataset ID Format Consistency",
        "name_ko": "데이터셋 간 ID 형식 일관성",
        "dimension": "Conformance", "level": "advanced", "severity": "warning",
        "data_types": ["all"],
    },
}


# ── Validation Functions ───────────────────────────────────────
def _to_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame to numeric, coercing errors."""
    return df.apply(pd.to_numeric, errors='coerce')


NA_VALUES = ['', 'NA', 'na', 'null', 'NULL', 'NaN', 'nan', 'None', 'none',
             '.', 'N/A', 'n/a', '-', '--', '?', 'missing', 'MISSING']

def _replace_string_nas(df: pd.DataFrame) -> pd.DataFrame:
    """Replace string representations of NA."""
    return df.replace(NA_VALUES, np.nan)

def _extract_tcga_tss_from_index(df: pd.DataFrame) -> Optional[pd.Series]:
    """Extract TCGA TSS code (e.g., TCGA-XX-*) from index as a proxy batch label."""
    idx = df.index.astype(str)
    pattern = re.compile(r"^TCGA-([A-Za-z0-9]{2})-")
    vals = []
    matched = 0
    for s in idx:
        m = pattern.match(s)
        if m:
            matched += 1
            vals.append(m.group(1).upper())
        else:
            vals.append(np.nan)
    if len(idx) == 0:
        return None
    # Require sufficient barcode coverage to avoid false proxy inference.
    if matched / len(idx) < 0.7:
        return None
    return pd.Series(vals, index=df.index, dtype="object")

def _get_batch_labels(df: pd.DataFrame) -> Tuple[Optional[pd.Series], str, str]:
    """Get batch labels from explicit metadata columns or TCGA TSS proxy."""
    colmap = {c.lower(): c for c in df.columns}
    for cand in BATCH_CANDIDATE_COLUMNS:
        if cand in colmap:
            col = colmap[cand]
            labels = df[col].astype(str).str.strip()
            labels = labels.replace(["", "nan", "None", "none", "NA", "null", "NULL"], np.nan)
            if labels.notna().sum() > 0:
                return labels, "metadata", col

    tss = _extract_tcga_tss_from_index(df)
    if tss is not None and tss.notna().sum() > 0:
        return tss, "tcga_proxy_tss", "index"
    return None, "none", ""


def validate_comp_F001(df: pd.DataFrame, **kw) -> dict:
    ok = len(df.columns) >= 2
    return {
        "status": "pass" if ok else "fail",
        "message": f"Header verified ({len(df.columns)} columns)" if ok else f"Insufficient columns ({len(df.columns)})"
    }


def validate_comp_C001(df: pd.DataFrame, **kw) -> dict:
    idx = df.index
    null_count = idx.isna().sum()
    ok = null_count == 0 and len(idx) > 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"Sample ID column OK ({len(idx)} samples, {null_count} nulls)" if ok else f"Sample ID has {null_count} null values"
    }


def validate_comp_C002(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 30)
    df2 = _replace_string_nas(df)
    col_missing = (df2.isna().sum() / len(df2) * 100)
    bad_cols = col_missing[col_missing > threshold]
    ok = len(bad_cols) == 0
    return {
        "status": "pass" if ok else "warning",
        "message": f"All columns within {threshold}% missing threshold" if ok else f"{len(bad_cols)} column(s) exceed {threshold}% missing rate",
        "details": {"worst_columns": bad_cols.nlargest(5).to_dict()} if not ok else {}
    }


def validate_comp_C003(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 50)
    df2 = _replace_string_nas(df)
    row_complete = ((~df2.isna()).sum(axis=1) / len(df2.columns) * 100)
    bad_rows = row_complete[row_complete < threshold]
    ok = len(bad_rows) == 0
    return {
        "status": "pass" if ok else "warning",
        "message": f"All rows meet {threshold}% completeness" if ok else f"{len(bad_rows)} row(s) below {threshold}% completeness"
    }


def validate_comp_F003(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 20)
    df2 = _replace_string_nas(df)
    rate = df2.isna().sum().sum() / df2.size * 100
    ok = rate <= threshold
    return {
        "status": "pass" if ok else "warning",
        "message": f"Overall missing rate: {rate:.1f}% (threshold ≤ {threshold}%)",
        "details": {"missing_rate": round(rate, 2)}
    }


def validate_plau_C001(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    min_val = params.get("min", -100)
    df_num = _to_numeric_df(_replace_string_nas(df))
    total = df_num.count().sum()
    below = (df_num < min_val).sum().sum()
    rate = below / total * 100 if total > 0 else 0
    return {
        "status": "pass" if rate < 5 else "warning",
        "message": f"Values below {min_val}: {rate:.2f}% ({below}/{total})"
    }


def validate_plau_C002(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    max_val = params.get("max", 100)
    df_num = _to_numeric_df(_replace_string_nas(df))
    total = df_num.count().sum()
    above = (df_num > max_val).sum().sum()
    rate = above / total * 100 if total > 0 else 0
    return {
        "status": "pass" if rate < 5 else "warning",
        "message": f"Values above {max_val}: {rate:.2f}% ({above}/{total})"
    }


def validate_plau_C003(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 5)
    mult = params.get("iqr_multiplier", 1.5)
    df_num = _to_numeric_df(_replace_string_nas(df))

    outlier_count = 0
    total_count = 0

    for col in df_num.columns:
        vals = df_num[col].dropna()
        if len(vals) < 4:
            continue
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - mult * iqr, q3 + mult * iqr
        outliers = ((vals < lower) | (vals > upper)).sum()
        outlier_count += outliers
        total_count += len(vals)

    rate = outlier_count / total_count * 100 if total_count > 0 else 0
    ok = rate <= threshold
    return {
        "status": "pass" if ok else "warning",
        "message": f"IQR outlier rate: {rate:.2f}% (threshold ≤ {threshold}%)",
        "details": {"outlier_count": int(outlier_count), "total_values": int(total_count)}
    }


def validate_plau_C004(df: pd.DataFrame, **kw) -> dict:
    df_num = _to_numeric_df(_replace_string_nas(df))
    zero_var = (df_num.std() == 0).sum()
    ok = zero_var == 0
    return {
        "status": "pass" if ok else "warning",
        "message": f"{zero_var} zero-variance column(s) detected"
    }


def _find_column(df: pd.DataFrame, candidates: list) -> str:
    """Find the first matching column from a list of candidate names (case-insensitive, partial match)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        cand_l = cand.lower()
        if cand_l in cols_lower:
            return cols_lower[cand_l]
        for cl, orig in cols_lower.items():
            if cand_l in cl or cl.endswith('.' + cand_l):
                return orig
    return ""


def validate_plau_V001(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    data_type = str(kw.get("data_type", "")).lower()
    if data_type == "survival":
        return {
            "status": "pass",
            "message": "Skipped for survival-only table: Sex/Gender check is not applicable",
            "details": {"skipped": True, "reason": "not_applicable_for_survival"}
        }
    gender_candidates = [
        "gender.demographic", "gender", "sex", "sex_at_birth",
        "gender.demographics", "Sex", "Gender"
    ]
    allowed = params.get("allowed", [
        "M", "F", "male", "female", "Male", "Female",
        "남", "여", "Unknown", "unknown", "not reported", "Not Reported"
    ])

    col = _find_column(df, gender_candidates)
    if not col:
        return {"status": "warning", "message": "Gender/sex column not found (tried: gender.demographic, gender, sex)"}

    values = df[col].dropna().astype(str).str.strip()
    invalid = values[~values.isin(allowed)]
    ok = len(invalid) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"'{col}' value set check passed ({len(values)} values)" if ok else f"{len(invalid)} invalid value(s) in '{col}': {invalid.unique()[:5].tolist()}"
    }


def validate_plau_V002(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    data_type = str(kw.get("data_type", "")).lower()
    if data_type == "survival":
        return {
            "status": "pass",
            "message": "Skipped for survival-only table: Age range check is not applicable",
            "details": {"skipped": True, "reason": "not_applicable_for_survival"}
        }
    age_candidates = [
        "age_at_index.demographic", "age_at_diagnosis.diagnoses",
        "age_at_index", "age_at_diagnosis", "age",
        "age_at_earliest_diagnosis_in_years.diagnoses.xena_derived",
    ]
    min_v, max_v = params.get("min", 0), params.get("max", 120)

    col = _find_column(df, age_candidates)
    if not col:
        return {"status": "warning", "message": "Age column not found (tried: age_at_index.demographic, age_at_diagnosis, age)"}

    vals = pd.to_numeric(df[col], errors='coerce').dropna()
    if len(vals) == 0:
        return {"status": "warning", "message": f"'{col}' has no numeric values"}

    # age_at_diagnosis in TCGA is in days; convert to years
    if vals.median() > 365:
        vals = vals / 365.25
        unit_note = f" (converted from days, col='{col}')"
    else:
        unit_note = f" (col='{col}')"

    oor = vals[(vals < min_v) | (vals > max_v)]
    ok = len(oor) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"Age range [{min_v}, {max_v}] check passed ({len(vals)} values){unit_note}" if ok else f"{len(oor)} out-of-range value(s){unit_note}",
        "details": {"min": round(float(vals.min()), 1), "max": round(float(vals.max()), 1), "median": round(float(vals.median()), 1)}
    }


def validate_plau_T001(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    data_type = str(kw.get("data_type", "")).lower()
    if data_type == "survival":
        return {
            "status": "pass",
            "message": "Skipped for survival-only table: Temporal plausibility check is not applicable",
            "details": {"skipped": True, "reason": "not_applicable_for_survival"}
        }
    birth_candidates = ["days_to_birth.demographic", "days_to_birth", "start_date", "date_of_diagnosis"]
    death_candidates = ["days_to_death.demographic", "days_to_death", "end_date", "date_of_death"]
    followup_candidates = ["days_to_last_follow_up.diagnoses", "days_to_last_follow_up", "days_to_last_followup"]

    birth_col = _find_column(df, birth_candidates)
    death_col = _find_column(df, death_candidates)
    followup_col = _find_column(df, followup_candidates)

    if not birth_col and not death_col:
        start_col = params.get("start_col", "start_date")
        end_col = params.get("end_col", "end_date")
        s_matches = [c for c in df.columns if c.lower() == start_col.lower()]
        e_matches = [c for c in df.columns if c.lower() == end_col.lower()]
        if not s_matches or not e_matches:
            return {"status": "warning", "message": "Date/temporal columns not found (tried: days_to_birth, days_to_death, start_date, end_date)"}
        starts = pd.to_datetime(df[s_matches[0]], errors='coerce')
        ends = pd.to_datetime(df[e_matches[0]], errors='coerce')
        valid_mask = starts.notna() & ends.notna()
        reversals = (starts[valid_mask] > ends[valid_mask]).sum()
        ok = reversals == 0
        return {"status": "pass" if ok else "fail", "message": f"Date order valid" if ok else f"{reversals} date reversal(s) found"}

    checks = []
    if birth_col:
        birth_vals = pd.to_numeric(df[birth_col], errors='coerce').dropna()
        if len(birth_vals) > 0:
            negative_count = (birth_vals > 0).sum()
            checks.append(f"'{birth_col}': {len(birth_vals)} values, {negative_count} positive (expect negative for days_to_birth)")
            if negative_count > len(birth_vals) * 0.5:
                checks.append("WARNING: days_to_birth should be negative")

    if death_col and followup_col:
        death_vals = pd.to_numeric(df[death_col], errors='coerce')
        fu_vals = pd.to_numeric(df[followup_col], errors='coerce')
        both_mask = death_vals.notna() & fu_vals.notna()
        if both_mask.sum() > 0:
            reversals = (death_vals[both_mask] < fu_vals[both_mask]).sum()
            if reversals > 0:
                checks.append(f"WARNING: {reversals} cases where days_to_death < days_to_follow_up")

    ok = not any("WARNING" in c for c in checks)
    return {
        "status": "pass" if ok else "warning",
        "message": f"Temporal plausibility check: {'; '.join(checks)}" if checks else "Temporal columns found, no issues detected"
    }


def validate_plau_V003(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    data_type = str(kw.get("data_type", "")).lower()
    vital_candidates = [
        "vital_status.demographic", "vital_status", "vitalstatus",
        "os_status", "overall_survival_status", "os"
    ]
    allowed = ["Alive", "Dead", "Not Reported", "not reported", "Unknown",
               "0", "1", "alive", "dead", "LIVING", "DECEASED",
               "0:LIVING", "1:DECEASED"]

    col = _find_column(df, vital_candidates)
    if not col:
        return {"status": "warning", "message": "Vital status column not found (tried: vital_status.demographic, vital_status)"}

    values = df[col].dropna().astype(str).str.strip()
    lower_values = values.str.lower()
    counts = values.value_counts().to_dict()

    # Survival tables: OS column is authoritative with 1=deceased, 0=alive.
    if data_type == "survival" and str(col).lower() in {"os", "os_status", "overall_survival_status"}:
        allowed_survival = {"0", "1", "0.0", "1.0"}
        invalid = values[~values.isin(allowed_survival)]
        ok = len(invalid) == 0
        alive_n = int(values.isin({"0", "0.0"}).sum())
        dead_n = int(values.isin({"1", "1.0"}).sum())
        return {
            "status": "pass" if ok else "fail",
            "message": (
                f"'{col}' OS mapping check passed (1=deceased, 0=alive; alive={alive_n}, deceased={dead_n})"
                if ok else
                f"{len(invalid)} invalid OS value(s) in '{col}' (allowed: 0/1): {invalid.unique()[:5].tolist()}"
            ),
            "details": {"value_counts": counts, "os_mapping": {"0": "alive", "1": "deceased"}}
        }

    # Metadata or generic fallback
    invalid = values[
        ~values.isin(allowed) &
        ~lower_values.isin({"alive", "dead", "living", "deceased", "not reported", "unknown"})
    ]
    ok = len(invalid) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"'{col}' value set check passed ({counts})" if ok else f"{len(invalid)} invalid value(s) in '{col}': {invalid.unique()[:5].tolist()}",
        "details": {"value_counts": counts}
    }


def validate_plau_V004(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    survival_time_candidates = [
        "os.time", "os_time", "pfs.time", "pfs_time", "dfs.time", "dfs_time",
        "rfs.time", "rfs_time", "overall_survival_time",
        "days_to_death.demographic", "days_to_death",
        "days_to_last_follow_up.diagnoses", "days_to_last_follow_up",
        "days_to_last_known_alive",
    ]
    max_days = params.get("max_days", 36500)

    col = _find_column(df, survival_time_candidates)
    if not col:
        return {"status": "warning", "message": "Survival time column not found (tried: OS.time, PFS.time, days_to_death, etc.)"}

    vals = pd.to_numeric(df[col], errors='coerce').dropna()
    if len(vals) == 0:
        return {"status": "warning", "message": f"'{col}' has no numeric values"}

    abs_vals = vals.abs()
    negatives = (vals < 0).sum()
    too_large = (abs_vals > max_days).sum()

    issues = []
    if negatives > 0:
        issues.append(f"{negatives} negative value(s)")
    if too_large > 0:
        issues.append(f"{too_large} value(s) > {max_days} days (~{max_days//365}yrs)")

    ok = len(issues) == 0
    return {
        "status": "pass" if ok else "warning",
        "message": f"'{col}' survival time check passed ({len(vals)} values, range: {abs_vals.min():.0f}–{abs_vals.max():.0f} days)" if ok
                   else f"'{col}': {'; '.join(issues)} (range: {vals.min():.0f}–{vals.max():.0f})",
        "details": {"column": col, "count": len(vals), "min": float(vals.min()), "max": float(vals.max()), "median": float(vals.median())}
    }


def validate_conf_F001(df: pd.DataFrame, filepath: str = "", **kw) -> dict:
    """Check if all rows have consistent column count (already handled by pandas)."""
    return {"status": "pass", "message": f"File format consistent ({len(df.columns)} columns, {len(df)} rows)"}


def validate_conf_C001(df: pd.DataFrame, **kw) -> dict:
    idx = df.index
    dupes = idx[idx.duplicated()]
    ok = len(dupes) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"No duplicate IDs" if ok else f"{len(dupes)} duplicate ID(s): {dupes[:5].tolist()}"
    }


def validate_conf_C002(df: pd.DataFrame, **kw) -> dict:
    df2 = _replace_string_nas(df)
    non_numeric_cols = []
    for col in df2.columns:
        vals = df2[col].dropna()
        if len(vals) == 0:
            continue
        numeric = pd.to_numeric(vals, errors='coerce')
        if numeric.isna().sum() > 0:
            non_numeric_cols.append(col)
    ok = len(non_numeric_cols) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"Numeric type check passed" if ok else f"{len(non_numeric_cols)} non-numeric column(s): {non_numeric_cols[:5]}"
    }


def validate_conf_V001(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    pattern = params.get("pattern", r"^[A-Za-z0-9_.\-]+$")
    pat = re.compile(pattern)
    idx_str = df.index.astype(str)
    bad = [v for v in idx_str if not pat.match(v)]
    ok = len(bad) == 0
    return {
        "status": "pass" if ok else "fail",
        "message": f"ID pattern check passed" if ok else f"{len(bad)} ID(s) don't match pattern: {bad[:5]}"
    }


def validate_conf_V002(df: pd.DataFrame, **kw) -> dict:
    df_num = _to_numeric_df(_replace_string_nas(df))
    neg_count = (df_num < 0).sum().sum()
    ok = neg_count == 0
    return {
        "status": "pass" if ok else "warning",
        "message": f"No negative values" if ok else f"{neg_count} negative value(s) detected"
    }

def validate_conf_B001(df: pd.DataFrame, **kw) -> dict:
    labels, source, col = _get_batch_labels(df)
    if labels is None:
        return {
            "status": "pass",
            "message": "Skipped: batch label not found (metadata column or TCGA TSS proxy unavailable)",
            "details": {"skipped": True, "batch_source": "none"}
        }
    n = int(labels.dropna().nunique())
    return {
        "status": "pass",
        "message": f"Batch labels detected ({n} groups; source={source}, column={col})",
        "details": {"skipped": False, "batch_source": source, "batch_column_used": col, "n_batches": n}
    }

def _eta_squared(values: np.ndarray, groups: pd.Series) -> float:
    """One-way ANOVA effect size (eta^2) for exploratory separation."""
    g = pd.Series(groups).astype(str)
    x = pd.Series(values)
    mask = x.notna() & g.notna()
    x = x[mask]
    g = g[mask]
    if len(x) < 3 or g.nunique() < 2:
        return 0.0
    grand = float(x.mean())
    ss_total = float(((x - grand) ** 2).sum())
    if ss_total <= 0:
        return 0.0
    ss_between = 0.0
    for _, xv in x.groupby(g):
        n = len(xv)
        if n == 0:
            continue
        ss_between += n * float((xv.mean() - grand) ** 2)
    return max(0.0, min(1.0, ss_between / ss_total))

def validate_plau_B001(df: pd.DataFrame, params: dict = {}, **kw) -> dict:
    warn_threshold = float(params.get("warn_threshold", 0.2))
    min_group_size = int(params.get("min_group_size", 3))
    max_features = int(params.get("max_features", 2000))

    labels, source, col = _get_batch_labels(df)
    if labels is None:
        return {
            "status": "pass",
            "message": "Skipped: no batch labels available for exploratory batch assessment",
            "details": {"skipped": True, "batch_source": "none"}
        }

    labels = labels.dropna()
    if labels.nunique() < 2:
        return {
            "status": "pass",
            "message": "Skipped: fewer than 2 batch groups",
            "details": {"skipped": True, "batch_source": source, "batch_column_used": col}
        }

    batch_counts = labels.value_counts()
    small_groups = int((batch_counts < min_group_size).sum())

    df_num = _to_numeric_df(_replace_string_nas(df))
    # If batch label came from metadata column inside this table, remove it from feature matrix.
    if source == "metadata" and col in df_num.columns:
        df_num = df_num.drop(columns=[col], errors="ignore")
    df_num = df_num.loc[labels.index]
    df_num = df_num.dropna(axis=1, how="all")

    if df_num.shape[0] < 5 or df_num.shape[1] < 2:
        return {
            "status": "pass",
            "message": "Skipped: insufficient numeric matrix for PCA-based batch assessment",
            "details": {"skipped": True, "batch_source": source, "batch_column_used": col}
        }

    X = df_num.copy()
    med = X.median(axis=0, skipna=True)
    X = X.fillna(med).fillna(0.0)
    variances = X.var(axis=0)
    keep = variances[variances > 0].index
    X = X[keep]
    if X.shape[1] < 2:
        return {
            "status": "pass",
            "message": "Skipped: no variable numeric features after preprocessing",
            "details": {"skipped": True, "batch_source": source, "batch_column_used": col}
        }

    if X.shape[1] > max_features:
        top_cols = X.var(axis=0).sort_values(ascending=False).head(max_features).index
        X = X[top_cols]

    Xv = X.values.astype(float)
    Xv = Xv - np.nanmean(Xv, axis=0, keepdims=True)
    sd = np.nanstd(Xv, axis=0, keepdims=True)
    sd[sd == 0] = 1.0
    Xv = Xv / sd

    try:
        _, s, vt = np.linalg.svd(Xv, full_matrices=False)
    except Exception:
        return {
            "status": "warning",
            "message": "Batch assessment warning: SVD failed on current matrix",
            "details": {"batch_source": source, "batch_column_used": col}
        }

    if len(s) < 2 or vt.shape[0] < 2:
        return {
            "status": "pass",
            "message": "Skipped: insufficient principal components for assessment",
            "details": {"skipped": True, "batch_source": source, "batch_column_used": col}
        }

    # Compute PC scores from right singular vectors on sample rows.
    # For X = U S V^T where X is n_samples x n_features, sample scores = U S.
    U = Xv @ vt.T
    pc1 = U[:, 0]
    pc2 = U[:, 1]
    eta1 = _eta_squared(pc1, labels)
    eta2 = _eta_squared(pc2, labels)
    eta_avg = float((eta1 + eta2) / 2.0)

    status = "warning" if eta_avg >= warn_threshold else "pass"
    if small_groups > 0 and status == "pass":
        status = "warning"
    note = f"Exploratory batch separation eta^2 avg={eta_avg:.3f} (PC1={eta1:.3f}, PC2={eta2:.3f})"
    if small_groups > 0:
        note += f"; {small_groups} batch group(s) have < {min_group_size} samples"

    return {
        "status": status,
        "message": note,
        "details": {
            "batch_source": source,
            "batch_column_used": col,
            "n_batches": int(labels.nunique()),
            "batch_counts": batch_counts.to_dict(),
            "eta2_pc1": round(float(eta1), 4),
            "eta2_pc2": round(float(eta2), 4),
            "eta2_avg": round(eta_avg, 4),
            "small_groups_lt_min": small_groups,
            "exploratory_note": "Proxy labels (e.g., TCGA TSS) may confound technical and biological variation."
        }
    }


# ── Cross-validation functions ─────────────────────────────────
def validate_comp_X001(dfs: dict, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 80)
    all_ids = [set(df.index.astype(str)) for df in dfs.values()]
    if len(all_ids) < 2:
        return {"status": "pass", "message": "Need 2+ files for cross-validation"}
    
    common = set.intersection(*all_ids)
    union = set.union(*all_ids)
    rate = len(common) / len(union) * 100 if len(union) > 0 else 0
    ok = rate >= threshold
    return {
        "status": "pass" if ok else "warning",
        "message": f"Sample matching rate: {rate:.1f}% (common {len(common)} / total {len(union)})"
    }


def validate_comp_X002(dfs: dict, params: dict = {}, **kw) -> dict:
    threshold = params.get("threshold", 10)
    all_ids = [set(df.index.astype(str)) for df in dfs.values()]
    if len(all_ids) < 2:
        return {"status": "pass", "message": "Need 2+ files"}
    common = len(set.intersection(*all_ids))
    ok = common >= threshold
    return {
        "status": "pass" if ok else "fail",
        "message": f"Common samples: {common} (threshold ≥ {threshold})"
    }


def validate_conf_X001(dfs: dict, **kw) -> dict:
    def _shape_token(v: str) -> str:
        s = str(v)
        s = re.sub(r"[A-Za-z]+", "A", s)
        s = re.sub(r"[0-9]+", "N", s)
        s = re.sub(r"[^AN._:\-]+", "X", s)
        return s

    patterns = {}
    dominance = {}
    for fname, df in dfs.items():
        ids = df.index.astype(str)
        if len(ids) == 0:
            continue
        shaped = ids.map(_shape_token)
        counts = shaped.value_counts()
        top_shape = str(counts.index[0])
        top_ratio = float(counts.iloc[0] / len(shaped))
        patterns[fname] = top_shape
        dominance[fname] = round(top_ratio, 4)

    unique_patterns = set(patterns.values())
    min_dominance = min(dominance.values()) if dominance else 0.0
    ok = len(unique_patterns) <= 1 and min_dominance >= 0.8
    return {
        "status": "pass" if ok else "warning",
        "message": (
            "ID format consistent across datasets"
            if ok else
            f"ID format mismatch detected (dominant patterns={patterns}, min_dominance={min_dominance:.2f})"
        ),
        "details": {"dominant_patterns": patterns, "dominance_ratio": dominance}
    }


# ── Dispatcher ─────────────────────────────────────────────────
VALIDATORS = {
    "comp_F001": validate_comp_F001, "comp_C001": validate_comp_C001,
    "comp_C002": validate_comp_C002, "comp_C003": validate_comp_C003,
    "comp_F003": validate_comp_F003, "plau_C001": validate_plau_C001,
    "plau_C002": validate_plau_C002, "plau_C003": validate_plau_C003,
    "plau_C004": validate_plau_C004, "plau_V001": validate_plau_V001,
    "plau_V002": validate_plau_V002, "plau_V003": validate_plau_V003,
    "plau_V004": validate_plau_V004, "plau_T001": validate_plau_T001,
    "plau_B001": validate_plau_B001,
    "conf_F001": validate_conf_F001, "conf_C001": validate_conf_C001,
    "conf_C002": validate_conf_C002, "conf_V001": validate_conf_V001,
    "conf_V002": validate_conf_V002, "conf_B001": validate_conf_B001,
}

CROSS_VALIDATORS = {
    "comp_X001": validate_comp_X001, "comp_X002": validate_comp_X002,
    "conf_X001": validate_conf_X001,
}


def run_custom_validation(df: pd.DataFrame, rule_config: dict) -> dict:
    """Run a single custom validation rule against a DataFrame."""
    vtype = rule_config.get("validationType", "")
    params = rule_config.get("parameters", {})

    try:
        if vtype == "threshold":
            metric = params.get("metric", "missing_rate")
            threshold = float(params.get("threshold", 30))
            operator = params.get("operator", "<=")
            df2 = _replace_string_nas(df)
            if metric == "missing_rate":
                val = df2.isna().sum().sum() / df2.size * 100 if df2.size > 0 else 0
            elif metric == "row_completeness":
                row_comp = (~df2.isna()).sum(axis=1) / len(df2.columns) * 100
                val = row_comp.min()
            elif metric == "outlier_rate_iqr":
                df_num = _to_numeric_df(df2)
                total, outliers = 0, 0
                for col in df_num.columns:
                    v = df_num[col].dropna()
                    if len(v) < 4: continue
                    q1, q3 = v.quantile(0.25), v.quantile(0.75)
                    iqr = q3 - q1
                    outliers += ((v < q1 - 1.5*iqr) | (v > q3 + 1.5*iqr)).sum()
                    total += len(v)
                val = outliers / total * 100 if total > 0 else 0
            elif metric == "zero_variance_columns":
                df_num = _to_numeric_df(df2)
                val = (df_num.std() == 0).sum()
            else:
                val = 0
            import operator as _op
            _OPS = {"<=": _op.le, ">=": _op.ge, "<": _op.lt, ">": _op.gt, "==": _op.eq}
            cmp_fn = _OPS.get(operator, _op.le)
            ok = cmp_fn(val, threshold)
            return {"status": "pass" if ok else "warning", "message": f"{metric}: {val:.2f} (threshold {operator} {threshold})"}

        elif vtype == "range":
            min_v = params.get("min")
            max_v = params.get("max")
            df_num = _to_numeric_df(_replace_string_nas(df))
            issues = 0
            total = df_num.count().sum()
            if min_v is not None:
                issues += (df_num < float(min_v)).sum().sum()
            if max_v is not None:
                issues += (df_num > float(max_v)).sum().sum()
            rate = issues / total * 100 if total > 0 else 0
            return {"status": "pass" if rate < 5 else "warning", "message": f"Out-of-range values: {rate:.2f}%"}

        elif vtype == "value_set":
            col = params.get("targetColumn", "")
            allowed = params.get("allowedValues", [])
            matches = [c for c in df.columns if c.lower() == col.lower()]
            if not matches:
                return {"status": "warning", "message": f"Column '{col}' not found"}
            vals = df[matches[0]].dropna().astype(str).str.strip()
            invalid = vals[~vals.isin(allowed)]
            return {"status": "pass" if len(invalid) == 0 else "fail",
                    "message": f"Value set check passed" if len(invalid) == 0 else f"{len(invalid)} invalid value(s)"}

        elif vtype == "pattern" or vtype == "regex_pattern":
            col_target = params.get("targetColumn", "first_column")
            pattern = params.get("pattern", r"^[A-Za-z0-9_.\-]+$")
            if col_target == "first_column":
                vals = df.index.astype(str)
            else:
                matches = [c for c in df.columns if c.lower() == col_target.lower()]
                if not matches:
                    return {"status": "warning", "message": f"Column '{col_target}' not found"}
                vals = df[matches[0]].dropna().astype(str)
            pat = re.compile(pattern)
            bad = [v for v in vals if not pat.match(v)]
            return {"status": "pass" if len(bad) == 0 else "fail",
                    "message": f"Pattern check passed" if len(bad) == 0 else f"{len(bad)} value(s) don't match pattern"}

        elif vtype == "categorical":
            col = params.get("targetColumn", "")
            max_cat = int(params.get("maxCategories", 50))
            matches = [c for c in df.columns if c.lower() == col.lower()]
            if not matches:
                return {"status": "warning", "message": f"Column '{col}' not found"}
            n = df[matches[0]].nunique()
            return {"status": "pass" if n <= max_cat else "warning",
                    "message": f"{n} unique values (max {max_cat})"}

        elif vtype == "column_range":
            col = params.get("targetColumn", "")
            min_v = float(params.get("min", 0))
            max_v = float(params.get("max", 120))
            matches = [c for c in df.columns if c.lower() == col.lower()]
            if not matches:
                return {"status": "warning", "message": f"Column '{col}' not found"}
            vals = pd.to_numeric(df[matches[0]], errors='coerce').dropna()
            oor = vals[(vals < min_v) | (vals > max_v)]
            return {"status": "pass" if len(oor) == 0 else "fail",
                    "message": f"Range check passed" if len(oor) == 0 else f"{len(oor)} out-of-range value(s)"}

        else:
            return {"status": "warning", "message": f"Unknown validation type: {vtype}"}

    except Exception as e:
        return {"status": "fail", "message": f"Custom rule error: {str(e)}"}


def run_all_validations(files_data: dict, rule_ids: list, custom_rules: dict = None) -> list:
    """
    Run selected validation rules on uploaded files.
    
    files_data: {file_id: {"df": DataFrame, "filename": str, "data_type": str}}
    rule_ids: list of rule IDs to run
    """
    results = []

    # Single-file validations
    for rule_id in rule_ids:
        if rule_id in CROSS_VALIDATORS:
            continue  # Handle cross-validators separately
        
        if rule_id not in RULES or rule_id not in VALIDATORS:
            continue

        rule = RULES[rule_id]
        validator = VALIDATORS[rule_id]

        for fid, fdata in files_data.items():
            dtype = fdata["data_type"]
            rule_types = rule.get("data_types", ["all"])

            if "all" not in rule_types and dtype not in rule_types:
                continue

            try:
                result = validator(
                    fdata["df"],
                    params=rule.get("params", {}),
                    filepath=fdata.get("filepath", ""),
                    data_type=dtype,
                )
            except Exception as e:
                result = {"status": "fail", "message": f"Validation error: {str(e)}"}

            results.append({
                "rule_id": rule_id,
                "rule_name": rule["name"],
                "dimension": rule["dimension"],
                "severity": rule["severity"],
                "level": rule["level"],
                "file_name": fdata["filename"],
                **result
            })

    # Cross-file validations (advanced)
    if len(files_data) >= 2:
        dfs_map = {fdata["filename"]: fdata["df"] for fdata in files_data.values()}
        
        for rule_id in rule_ids:
            if rule_id not in CROSS_VALIDATORS:
                continue
            
            rule = RULES[rule_id]
            validator = CROSS_VALIDATORS[rule_id]

            try:
                result = validator(dfs_map, params=rule.get("params", {}))
            except Exception as e:
                result = {"status": "fail", "message": f"Cross-validation error: {str(e)}"}

            results.append({
                "rule_id": rule_id,
                "rule_name": rule["name"],
                "dimension": rule["dimension"],
                "severity": rule["severity"],
                "level": rule["level"],
                "file_name": "Multi-dataset",
                **result
            })

    # Custom rule validations
    if custom_rules:
        for rule_id in rule_ids:
            if rule_id not in custom_rules:
                continue
            rule = custom_rules[rule_id]
            for fid, fdata in files_data.items():
                dtype = fdata["data_type"]
                rule_types = rule.get("data_types", rule.get("dataTypes", ["all"]))
                if "all" not in rule_types and dtype not in rule_types:
                    continue
                try:
                    result = run_custom_validation(fdata["df"], rule)
                except Exception as e:
                    result = {"status": "fail", "message": f"Custom rule error: {str(e)}"}
                results.append({
                    "rule_id": rule_id,
                    "rule_name": rule.get("name", rule_id),
                    "dimension": rule.get("dimension", "Custom"),
                    "severity": rule.get("severity", "warning"),
                    "level": rule.get("level", "custom"),
                    "file_name": fdata["filename"],
                    **result
                })

    return results
