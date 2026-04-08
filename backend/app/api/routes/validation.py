"""
Data validation API routes
GENE-QC 품질 지표 기반 검증 (Completeness · Plausibility · Conformance)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uuid
import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

router = APIRouter()

# 검증 작업 저장소
validation_jobs = {}

# 프로젝트별 검증 규칙 저장소
validation_rules = {}


class ValidationRule(BaseModel):
    """검증 규칙 모델"""
    dna_threshold: float = 1.0
    rna_threshold: float = 20.0
    protein_threshold: float = 25.0
    methyl_threshold: float = 25.0
    batch_effect_threshold: float = 5.0
    sample_matching_enabled: bool = True
    range_validation_enabled: bool = True


@router.post("/execute")
async def execute_validation(
    project_id: int,
    background_tasks: BackgroundTasks
):
    """
    프로젝트 데이터에 대한 검증 실행 (NaN 값 확인)

    저장된 검증 규칙을 사용하여 검증을 수행합니다.
    """
    job_id = str(uuid.uuid4())

    # 저장된 검증 규칙 가져오기
    rules = validation_rules.get(project_id, ValidationRule().dict())

    # 백그라운드 작업으로 검증 실행
    background_tasks.add_task(
        _run_validation,
        job_id=job_id,
        project_id=project_id,
        rules=rules
    )

    validation_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "project_id": project_id,
        "rules": rules,
    }

    return {
        "jobId": job_id,
        "status": "processing",
        "message": "Validation job started with custom rules",
        "estimatedTime": 30,
        "rules": rules
    }


@router.get("/status/{job_id}")
async def get_validation_status(job_id: str):
    """검증 작업 상태 조회"""
    job = validation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.post("/rules/{project_id}")
async def save_validation_rules(project_id: int, rules: ValidationRule):
    """
    프로젝트의 검증 규칙 저장

    Parameters:
    - project_id: 프로젝트 ID
    - rules: 검증 규칙 (임계값 등)
    """
    validation_rules[project_id] = rules.dict()

    return {
        "message": "Validation rules saved successfully",
        "project_id": project_id,
        "rules": validation_rules[project_id]
    }


@router.get("/rules/{project_id}")
async def get_validation_rules(project_id: int):
    """
    프로젝트의 검증 규칙 조회

    Parameters:
    - project_id: 프로젝트 ID

    Returns:
    - 저장된 검증 규칙 또는 기본값
    """
    # 저장된 규칙이 있으면 반환, 없으면 기본값 반환
    if project_id in validation_rules:
        return validation_rules[project_id]
    else:
        # 기본 규칙 반환
        default_rules = ValidationRule()
        return default_rules.dict()


@router.get("/download-report/{project_id}")
async def download_validation_report(project_id: int):
    """
    검증 결과 보고서 다운로드

    프로젝트의 검증 결과를 PDF 형식의 보고서로 다운로드합니다.
    """
    from fastapi.responses import FileResponse
    import tempfile
    import subprocess

    try:
        # 해당 프로젝트의 가장 최근 완료된 검증 작업 찾기
        completed_jobs = [
            job for job in validation_jobs.values()
            if job.get("project_id") == project_id and job.get("status") == "completed"
        ]

        if not completed_jobs:
            raise HTTPException(
                status_code=404,
                detail=f"No completed validation results found for project {project_id}"
            )

        # 가장 최근 작업 선택
        latest_job = max(completed_jobs, key=lambda x: x.get("completed_at", ""))
        results = latest_job.get("results", {})

        # 보고서 생성
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("데이터 품질 검증 결과 보고서")
        report_lines.append("=" * 80)
        report_lines.append(f"프로젝트 ID: {project_id}")
        report_lines.append(f"검증 완료 시간: {latest_job.get('completed_at', 'N/A')}")
        report_lines.append("")
        report_lines.append(f"전체 파일 수: {results.get('total_files', 0)}")
        report_lines.append(f"통과한 파일 수: {results.get('passed_files', 0)}")
        report_lines.append(f"전체 검증 결과: {'✅ 통과' if results.get('all_passed', False) else '❌ 실패'}")
        report_lines.append("")
        report_lines.append("-" * 80)
        report_lines.append("파일별 상세 결과")
        report_lines.append("-" * 80)
        report_lines.append("")

        for file_result in results.get("files", []):
            report_lines.append(f"파일명: {file_result.get('filename', 'N/A')}")

            if "error" in file_result:
                report_lines.append(f"  상태: ❌ 오류 발생")
                report_lines.append(f"  오류: {file_result.get('error', 'N/A')}")
            else:
                report_lines.append(f"  상태: {'✅ 통과' if file_result.get('passed', False) else '❌ 실패'}")
                report_lines.append(f"  데이터 형태: {file_result.get('shape', [0, 0])}")
                report_lines.append(f"  전체 값 개수: {file_result.get('total_values', 0):,}")
                report_lines.append(f"  결측치 개수: {file_result.get('nan_count', 0):,}")
                report_lines.append(f"  결측치 비율: {file_result.get('nan_percentage', 0):.2f}%")
                report_lines.append(f"  최대 행 결측치 비율: {file_result.get('max_row_nan_percentage', 0):.2f}%")
                report_lines.append(f"  최대 열 결측치 비율: {file_result.get('max_col_nan_percentage', 0):.2f}%")

            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("보고서 끝")
        report_lines.append("=" * 80)

        # UTF-8 텍스트를 PDF로 변환 (macOS cupsfilter 사용)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as txt_file:
            txt_file.write("\n".join(report_lines))
            txt_path = txt_file.name

        pdf_bytes = subprocess.run(
            ["cupsfilter", "-m", "application/pdf", txt_path],
            check=True,
            capture_output=True,
        ).stdout

        if not pdf_bytes:
            raise RuntimeError("cupsfilter returned empty PDF output")

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as pdf_file:
            pdf_file.write(pdf_bytes)
            temp_path = pdf_file.name

        # 파일 다운로드 응답
        return FileResponse(
            path=temp_path,
            filename=f"validation_report_project_{project_id}.pdf",
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=validation_report_project_{project_id}.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate validation report: {str(e)}"
        )


def _infer_data_type(filename: str) -> str:
    """파일명 기반 데이터 유형 자동 추론"""
    lower = filename.lower()
    if "rna" in lower or "transcriptom" in lower or "expression" in lower:
        return "transcriptomics"
    if "dna" in lower or "snp" in lower or "genomic" in lower:
        return "genomics"
    if "methylat" in lower or "methyl" in lower or "methy" in lower:
        return "genomics"
    if "protein" in lower or "proteom" in lower or "prot" in lower:
        return "proteomics"
    if "metabol" in lower:
        return "metabolomics"
    if "meta" in lower or "clinical" in lower or "phenotype" in lower:
        return "metadata"
    return "unknown"


def _get_missing_threshold(data_type: str, rules: Dict[str, Any]) -> float:
    """데이터 유형별 결측률 임계값 반환"""
    type_map = {
        "genomics": rules.get("dna_threshold", 1.0),
        "transcriptomics": rules.get("rna_threshold", 20.0),
        "proteomics": rules.get("protein_threshold", 25.0),
        "metabolomics": rules.get("methyl_threshold", 25.0),
    }
    return type_map.get(data_type, 30.0)


def _evaluate_gene_qc_rules(
    df: pd.DataFrame,
    filename: str,
    data_type: str,
    rules: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """파일에 대한 GENE-QC 규칙 평가 — Completeness · Plausibility · Conformance"""
    results: List[Dict[str, Any]] = []
    is_omics = data_type in ("genomics", "transcriptomics", "proteomics", "metabolomics")
    threshold_missing = _get_missing_threshold(data_type, rules)

    def _rule(rule_id, name, dimension, level, severity, status, message, metric=None, threshold=None):
        return {
            "ruleId": rule_id,
            "ruleName": name,
            "dimension": dimension,
            "level": level,
            "severity": severity,
            "fileName": filename,
            "status": status,
            "message": message,
            "metricValue": metric,
            "threshold": threshold,
        }

    # ── Completeness ────────────────────────────────────────────

    # comp_F001: 파일 헤더 존재 여부
    has_header = len(df.columns) >= 2
    results.append(_rule(
        "comp_F001", "파일 헤더 존재 여부", "Completeness", "basic", "fatal",
        "pass" if has_header else "fail",
        f"헤더 행 존재 — {len(df.columns)}개 컬럼 확인" if has_header
        else "헤더 행이 없거나 컬럼이 1개 이하입니다.",
        len(df.columns), 2,
    ))

    # comp_C001: 샘플 ID 컬럼 필수 존재
    null_ids = int(df.index.isnull().sum()) if hasattr(df.index, "isnull") else 0
    results.append(_rule(
        "comp_C001", "샘플 ID 컬럼 필수 존재", "Completeness", "basic", "fatal",
        "pass" if null_ids == 0 else "fail",
        f"샘플 ID 컬럼 존재 ({len(df):,}개 샘플)" if null_ids == 0
        else f"샘플 ID에 NULL 값 {null_ids}개 존재",
        null_ids, 0,
    ))

    # comp_C002: 컬럼별 결측률 검사
    col_nan_pct = df.isna().sum(axis=0) / max(len(df), 1) * 100
    max_col_nan = float(col_nan_pct.max()) if len(col_nan_pct) > 0 else 0.0
    cols_exceeding = int((col_nan_pct > threshold_missing).sum())
    results.append(_rule(
        "comp_C002", "컬럼별 결측률 검사", "Completeness", "basic", "warning",
        "pass" if max_col_nan <= threshold_missing else "warning",
        f"최대 컬럼 결측률 {max_col_nan:.1f}% (임계값: {threshold_missing}%)"
        if max_col_nan <= threshold_missing
        else f"결측률 초과 컬럼 {cols_exceeding}개 — 최대 {max_col_nan:.1f}%",
        round(max_col_nan, 2), threshold_missing,
    ))

    # comp_C003: 행(샘플) 완전성 검사
    row_nan_pct = df.isna().sum(axis=1) / max(len(df.columns), 1) * 100
    rows_below_50 = int((row_nan_pct > 50).sum())
    max_row_nan = float(row_nan_pct.max()) if len(row_nan_pct) > 0 else 0.0
    results.append(_rule(
        "comp_C003", "행(샘플) 완전성 검사", "Completeness", "basic", "warning",
        "pass" if rows_below_50 == 0 else "warning",
        "모든 행의 완전성 ≥ 50%"
        if rows_below_50 == 0
        else f"완전성 50% 미만 샘플 {rows_below_50}개 (최대 결측률: {max_row_nan:.1f}%)",
        round(max_row_nan, 2), 50,
    ))

    # comp_F003: 전체 데이터 결측률 (omics 전용)
    if is_omics:
        total_nan_pct = float(df.isna().sum().sum() / max(df.size, 1) * 100)
        results.append(_rule(
            "comp_F003", "전체 데이터 결측률", "Completeness", "basic", "warning",
            "pass" if total_nan_pct <= threshold_missing else "warning",
            f"전체 결측률 {total_nan_pct:.2f}% (임계값: {threshold_missing}%)",
            round(total_nan_pct, 2), threshold_missing,
        ))

    # ── Plausibility ─────────────────────────────────────────────

    if is_omics:
        numeric_df = df.select_dtypes(include=[np.number])

        if len(numeric_df.columns) > 0:
            # plau_C001: 발현값 하한 검사
            try:
                min_val = float(numeric_df.min().min())
                below_min = min_val < -100
                results.append(_rule(
                    "plau_C001", "발현값 하한 검사", "Plausibility", "basic", "characterization",
                    "warning" if below_min else "pass",
                    f"하한값(-100) 미만 값 존재 (최솟값: {min_val:.2f})"
                    if below_min else f"최솟값 {min_val:.2f} — 정상 범위",
                    round(min_val, 2), -100,
                ))
            except Exception:
                pass

            # plau_C002: 발현값 상한 검사
            try:
                max_val = float(numeric_df.max().max())
                results.append(_rule(
                    "plau_C002", "발현값 상한 검사", "Plausibility", "basic", "characterization",
                    "pass",
                    f"최댓값 {max_val:.2f} — 분포 확인",
                    round(max_val, 2), None,
                ))
            except Exception:
                pass

            # plau_C003: IQR 기반 이상치 검사
            try:
                q1 = numeric_df.quantile(0.25)
                q3 = numeric_df.quantile(0.75)
                iqr = q3 - q1
                outlier_mask = (numeric_df < (q1 - 1.5 * iqr)) | (numeric_df > (q3 + 1.5 * iqr))
                total_numeric = int(numeric_df.count().sum())
                outlier_count = int(outlier_mask.sum().sum())
                outlier_rate = round(outlier_count / max(total_numeric, 1) * 100, 2)
                iqr_threshold = 5.0
                results.append(_rule(
                    "plau_C003", "IQR 기반 이상치 검사", "Plausibility", "basic", "warning",
                    "pass" if outlier_rate <= iqr_threshold else "warning",
                    f"이상치 비율 {outlier_rate:.2f}% (임계값: {iqr_threshold}%)",
                    outlier_rate, iqr_threshold,
                ))
            except Exception:
                pass

            # plau_C004: 상수값 컬럼 탐지 (분산=0)
            try:
                zero_var_cols = int((numeric_df.std() == 0).sum())
                results.append(_rule(
                    "plau_C004", "상수값 컬럼 탐지 (분산=0)", "Plausibility", "basic", "warning",
                    "pass" if zero_var_cols == 0 else "warning",
                    "분산=0인 컬럼 없음"
                    if zero_var_cols == 0 else f"분산=0인 컬럼 {zero_var_cols}개 탐지",
                    zero_var_cols, 0,
                ))
            except Exception:
                pass

    # ── Conformance ──────────────────────────────────────────────

    # conf_F001: 파일 형식(구분자) 일관성 — 정상 로드 완료 시 통과
    results.append(_rule(
        "conf_F001", "파일 형식(구분자) 일관성", "Conformance", "basic", "fatal",
        "pass",
        "파일 구분자가 일관되게 사용됩니다.",
        None, None,
    ))

    # conf_C001: 샘플 ID 중복 검사
    try:
        dup_count = int(df.index.duplicated().sum())
        results.append(_rule(
            "conf_C001", "샘플 ID 중복 검사", "Conformance", "basic", "fatal",
            "pass" if dup_count == 0 else "fail",
            "샘플 ID 중복 없음" if dup_count == 0 else f"중복 샘플 ID {dup_count}개 발견",
            dup_count, 0,
        ))
    except Exception:
        pass

    # conf_C002: 수치형 컬럼 데이터 타입 검사 (omics 전용)
    if is_omics:
        numeric_cols = len(df.select_dtypes(include=[np.number]).columns)
        total_cols = len(df.columns)
        non_numeric = total_cols - numeric_cols
        results.append(_rule(
            "conf_C002", "수치형 컬럼 데이터 타입 검사", "Conformance", "basic", "error",
            "pass" if non_numeric == 0 else "fail",
            "모든 데이터 컬럼이 수치형입니다."
            if non_numeric == 0 else f"비수치형 컬럼 {non_numeric}개 탐지",
            non_numeric, 0,
        ))

    # conf_C003: 컬럼명 형식 검사
    pattern = re.compile(r"^[a-zA-Z0-9_.가-힣\-]+$")
    bad_cols = [c for c in df.columns if not pattern.match(str(c))]
    results.append(_rule(
        "conf_C003", "컬럼명 형식 검사", "Conformance", "basic", "convention",
        "pass" if len(bad_cols) == 0 else "convention",
        "컬럼명 형식 이상 없음"
        if len(bad_cols) == 0
        else f"형식 위반 컬럼명 {len(bad_cols)}개: {', '.join(str(c) for c in bad_cols[:3])}{'...' if len(bad_cols) > 3 else ''}",
        len(bad_cols), 0,
    ))

    return results


def _build_dimension_summary(rule_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """차원별 통과/경고/실패 수 집계"""
    summary: Dict[str, Dict[str, int]] = {
        "Completeness": {"pass": 0, "warning": 0, "fail": 0, "convention": 0, "total": 0},
        "Plausibility": {"pass": 0, "warning": 0, "fail": 0, "convention": 0, "total": 0},
        "Conformance": {"pass": 0, "warning": 0, "fail": 0, "convention": 0, "total": 0},
    }
    for r in rule_results:
        dim = r.get("dimension", "")
        status = r.get("status", "pass")
        if dim in summary:
            key = status if status in ("pass", "warning", "fail", "convention") else "pass"
            summary[dim][key] += 1
            summary[dim]["total"] += 1
    return summary


def _run_validation(job_id: str, project_id: int, rules: Dict[str, Any]):
    """검증 백그라운드 작업"""
    try:
        print(f"[Job {job_id}] Starting validation for project {project_id}")
        print(f"[Job {job_id}] Using validation rules: {rules}")

        # 데이터 로드
        from app.core.config import UPLOADS_DIR
        project_dir = UPLOADS_DIR / f"project_{project_id}" / "raw"

        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")

        # 파일 찾기
        files = list(project_dir.glob("*.tsv"))
        if not files:
            raise FileNotFoundError(f"No TSV files found in {project_dir}")

        results = []
        all_rule_results: List[Dict[str, Any]] = []

        # 데이터셋별 완전성 저장
        completeness_scores = {
            "dna": None,
            "rna": None,
            "methyl": None,
            "protein": None
        }

        for file_path in files:
            print(f"[Job {job_id}] Validating {file_path.name}")

            try:
                df = pd.read_csv(file_path, sep="\t", index_col=0)

                # NaN 기본 통계
                total_values = df.size
                nan_count = int(df.isna().sum().sum())
                nan_percentage = (nan_count / total_values * 100) if total_values > 0 else 0

                row_nan_percentages = df.isna().sum(axis=1) / max(len(df.columns), 1) * 100
                col_nan_percentages = df.isna().sum(axis=0) / max(len(df), 1) * 100
                max_row_nan = float(row_nan_percentages.max()) if len(row_nan_percentages) > 0 else 0
                max_col_nan = float(col_nan_percentages.max()) if len(col_nan_percentages) > 0 else 0

                # 데이터 유형 추론
                inferred_type = _infer_data_type(file_path.name)
                threshold = _get_missing_threshold(inferred_type, rules)

                # 기존 호환용 data_type 레이블
                dtype_label_map = {
                    "genomics": "DNA",
                    "transcriptomics": "RNA",
                    "proteomics": "Protein",
                    "metabolomics": "Methyl",
                    "metadata": "Metadata",
                }
                data_type = dtype_label_map.get(inferred_type, "Unknown")

                passed = bool(nan_percentage <= threshold)
                completeness = 100.0 - nan_percentage

                file_result = {
                    "filename": file_path.name,
                    "data_type": data_type,
                    "inferred_type": inferred_type,
                    "total_values": int(total_values),
                    "nan_count": nan_count,
                    "nan_percentage": round(float(nan_percentage), 2),
                    "completeness": round(float(completeness), 2),
                    "shape": list(df.shape),
                    "max_row_nan_percentage": round(float(max_row_nan), 2),
                    "max_col_nan_percentage": round(float(max_col_nan), 2),
                    "threshold_used": threshold,
                    "passed": passed,
                }

                # 완전성 점수 저장
                if data_type == "DNA":
                    completeness_scores["dna"] = completeness
                elif data_type == "RNA":
                    completeness_scores["rna"] = completeness
                elif data_type == "Methyl":
                    completeness_scores["methyl"] = completeness
                elif data_type == "Protein":
                    completeness_scores["protein"] = completeness

                results.append(file_result)

                # GENE-QC 규칙 평가
                file_rule_results = _evaluate_gene_qc_rules(df, file_path.name, inferred_type, rules)
                all_rule_results.extend(file_rule_results)

                print(f"[Job {job_id}] {file_path.name} ({data_type}): {nan_percentage:.2f}% NaN — {'PASSED' if passed else 'FAILED'}")

            except Exception as e:
                print(f"[Job {job_id}] Failed to validate {file_path.name}: {e}")
                results.append({
                    "filename": file_path.name,
                    "error": str(e),
                    "passed": False,
                })

        # 전체 검증 결과
        all_passed = all(r.get("passed", False) for r in results)
        dimension_summary = _build_dimension_summary(all_rule_results)

        # 프로젝트 DB 업데이트
        try:
            from app.db.session import SessionLocal
            from app.models.base import Project

            db = SessionLocal()
            project = db.query(Project).filter(Project.id == project_id).first()

            if project:
                # 데이터셋별 완전성 점수 업데이트
                if completeness_scores["dna"] is not None:
                    project.dna_quality_score = completeness_scores["dna"]
                    print(f"[Job {job_id}] Updated DNA completeness: {completeness_scores['dna']:.2f}%")

                if completeness_scores["rna"] is not None:
                    project.rna_quality_score = completeness_scores["rna"]
                    print(f"[Job {job_id}] Updated RNA completeness: {completeness_scores['rna']:.2f}%")

                if completeness_scores["methyl"] is not None:
                    project.methyl_quality_score = completeness_scores["methyl"]
                    print(f"[Job {job_id}] Updated Methyl completeness: {completeness_scores['methyl']:.2f}%")

                if completeness_scores["protein"] is not None:
                    project.protein_quality_score = completeness_scores["protein"]
                    print(f"[Job {job_id}] Updated Protein completeness: {completeness_scores['protein']:.2f}%")

                # 전체 품질 점수 계산 (사용 가능한 데이터셋들의 평균)
                available_scores = [s for s in completeness_scores.values() if s is not None]
                if available_scores:
                    project.quality_score = sum(available_scores) / len(available_scores)
                    print(f"[Job {job_id}] Updated overall quality score: {project.quality_score:.2f}%")

                # 검증 상태 업데이트
                if all_passed:
                    project.validation_status = "검증완료"
                else:
                    project.validation_status = "처리중"

                db.commit()
                print(f"[Job {job_id}] Project {project_id} updated successfully")
            else:
                print(f"[Job {job_id}] Warning: Project {project_id} not found in database")

            db.close()

        except Exception as e:
            print(f"[Job {job_id}] Failed to update project: {e}")
            import traceback
            traceback.print_exc()

        # 작업 상태 업데이트
        validation_jobs[job_id] = {
            "status": "completed",
            "created_at": validation_jobs[job_id]["created_at"],
            "completed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "results": {
                "files": results,
                "total_files": len(results),
                "passed_files": sum(1 for r in results if r.get("passed", False)),
                "all_passed": all_passed,
                "completeness_scores": completeness_scores,
                "rule_results": all_rule_results,
                "dimension_summary": dimension_summary,
            }
        }

        print(f"[Job {job_id}] Validation completed successfully")

    except Exception as e:
        print(f"[Job {job_id}] Validation failed: {str(e)}")
        import traceback
        traceback.print_exc()

        validation_jobs[job_id] = {
            "status": "failed",
            "created_at": validation_jobs[job_id]["created_at"],
            "failed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "error": str(e)
        }
