#!/usr/bin/env python3
"""
GENE-QC 명세서 v2.0 적용을 위한 DB 마이그레이션 스크립트

기능:
  1) projects 테이블에 5종 dataType 점수 컬럼 + legacy_validation_thresholds 추가
  2) data_files 테이블에 data_type 컬럼 추가
  3) verification_rules 테이블 재생성 (명세서 §5 신규 11컬럼 적용)
  4) validation_jobs 테이블 신규 생성
  5) GENE-QC 기본 규칙 28개 시드 (멱등적, metric_id 중복 시 건너뜀)

기존 프로젝트/파일/결측치 데이터는 유지됩니다.
verification_rules 의 옛 데이터(category/metric/condition/threshold)는 손실되며,
시스템 기본 GENE-QC 규칙 28개로 재시드됩니다.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app.db.session import engine, SessionLocal
from app.models.base import Base, ValidationJob, VerificationRule


# ────────────────────────────────────────────────────────────
# 1) projects 테이블에 추가될 컬럼 정의
# ────────────────────────────────────────────────────────────
PROJECTS_NEW_COLUMNS = [
    ("genomics_quality_score",       "FLOAT NULL"),
    ("transcriptomics_quality_score","FLOAT NULL"),
    ("proteomics_quality_score",     "FLOAT NULL"),
    ("metabolomics_quality_score",   "FLOAT NULL"),
    ("metadata_quality_score",       "FLOAT NULL"),
    ("legacy_validation_thresholds", "JSON NULL"),
]

# ────────────────────────────────────────────────────────────
# 2) data_files 테이블에 추가될 컬럼 정의
# ────────────────────────────────────────────────────────────
DATA_FILES_NEW_COLUMNS = [
    ("data_type", "VARCHAR(50) NULL"),
]


def _get_existing_columns(conn, table: str) -> set[str]:
    """information_schema 에서 테이블의 컬럼 목록 조회"""
    rows = conn.execute(
        text(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t
            """
        ),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t
            """
        ),
        {"t": table},
    ).scalar()
    return bool(row)


def add_missing_columns(conn, table: str, columns: list[tuple[str, str]]) -> int:
    """누락된 컬럼만 ADD"""
    if not _table_exists(conn, table):
        print(f"  · table '{table}' does not exist yet — will be created by Base.metadata")
        return 0

    existing = _get_existing_columns(conn, table)
    added = 0
    for col_name, col_type in columns:
        if col_name in existing:
            continue
        sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
        print(f"  + {sql}")
        conn.execute(text(sql))
        added += 1
    if not added:
        print(f"  · '{table}' already has all required columns")
    return added


def drop_table_if_exists(conn, table: str) -> None:
    if _table_exists(conn, table):
        print(f"  - DROP TABLE {table}")
        conn.execute(text(f"DROP TABLE {table}"))


def seed_gene_qc_rules() -> int:
    """명세서 §2의 28개 GENE-QC 기본 규칙 시드 (멱등적)"""
    from app.services.validation_service import METRIC_METADATA, get_default_rules

    db = SessionLocal()
    try:
        existing_ids = {r.metric_id for r in db.query(VerificationRule.metric_id).all()}
        inserted = 0
        for rule_def in get_default_rules():
            if rule_def["metricId"] in existing_ids:
                continue
            meta = METRIC_METADATA[rule_def["metricId"]]
            db.add(
                VerificationRule(
                    project_id=None,
                    metric_id=rule_def["metricId"],
                    name=rule_def["name"],
                    dimension=rule_def["dimension"],
                    quality_level=rule_def["level"],
                    severity=rule_def["severity"],
                    description=rule_def["description"],
                    data_types=rule_def["dataTypes"],
                    validation_type=rule_def["validationType"],
                    parameters=rule_def["parameters"],
                    metric_level=meta["level"],
                    context=meta["context"],
                    is_custom=False,
                    enabled=True,
                    author="system",
                )
            )
            inserted += 1
        if inserted:
            db.commit()
        return inserted
    finally:
        db.close()


def main() -> None:
    print("=" * 60)
    print("GENE-Q DB Migration v2 (non-destructive for projects/data_files)")
    print("=" * 60)

    with engine.begin() as conn:
        # 1) projects 컬럼 추가
        print("\n[1/4] Adding new columns to 'projects' table ...")
        add_missing_columns(conn, "projects", PROJECTS_NEW_COLUMNS)

        # 2) data_files 컬럼 추가
        print("\n[2/4] Adding new columns to 'data_files' table ...")
        add_missing_columns(conn, "data_files", DATA_FILES_NEW_COLUMNS)

        # 3) verification_rules 재생성
        #    옛 컬럼 체계와 새 컬럼 체계가 호환되지 않아 단순 ADD COLUMN 불가.
        #    옛 데이터는 손실되며, 이후 seed 단계에서 GENE-QC 28개 기본 규칙으로 재시드.
        print("\n[3/4] Recreating 'verification_rules' table ...")
        drop_table_if_exists(conn, "verification_rules")

        # 4) validation_jobs 생성 (새 테이블)
        print("\n[4/4] Ensuring 'validation_jobs' / 'verification_rules' tables exist ...")
        # Base.metadata.create_all 은 누락된 테이블만 생성
        Base.metadata.create_all(bind=conn, tables=[
            VerificationRule.__table__,
            ValidationJob.__table__,
        ])
        print("  · verification_rules / validation_jobs tables ready")

    # 5) GENE-QC 기본 규칙 시드
    print("\n[seed] Seeding 28 default GENE-QC rules ...")
    seeded = seed_gene_qc_rules()
    print(f"  · inserted {seeded} rules (existing rules untouched)")

    print()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
