"""
데이터베이스 초기화 및 샘플 데이터 생성
GENE-QC 지표설계 명세서 v2.0 기준
"""

from app.db.session import engine
from app.models.base import (
    Base,
    Project,
    DataFile,
    MissingValue,
    VerificationRule,
    VerificationStatus,
)
from app.services.validation_service import METRIC_METADATA, get_default_rules
from sqlalchemy.orm import Session


def init_db():
    """데이터베이스 테이블 생성"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def _seed_verification_rules(db: Session) -> int:
    """
    명세서 §2 의 28개 GENE-QC 지표를 전역 규칙으로 시드.
    이미 같은 metric_id 가 존재하면 건너뜀.
    """
    existing_ids = {
        r.metric_id for r in db.query(VerificationRule.metric_id).all()
    }

    inserted = 0
    for rule_def in get_default_rules():
        if rule_def["metricId"] in existing_ids:
            continue
        meta = METRIC_METADATA[rule_def["metricId"]]
        db.add(
            VerificationRule(
                project_id=None,  # 전역 규칙
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


def seed_data(db: Session):
    """샘플 데이터 생성"""
    print("Seeding sample data...")

    # 전역 규칙은 항상 보강 (이미 있으면 건너뜀)
    rule_count = _seed_verification_rules(db)
    if rule_count:
        print(f"Created {rule_count} GENE-QC default rules")

    # 기존 프로젝트가 있는지 확인
    existing_projects = db.query(Project).count()
    if existing_projects > 0:
        print(f"Database already has {existing_projects} projects. Skipping seed.")
        return

    # 프로젝트 생성
    projects = [
        Project(
            id=1,
            name="암 유전체 프로젝트",
            description="대규모 암 유전체 데이터 분석",
            data_type=["transcriptomics", "metabolomics"],
            quality_score=95.8,
            validation_status="검증완료",
            last_update="10분 전",
            sample_count=450,
            status="활성",
            genomics_quality_score=99.0,
            transcriptomics_quality_score=80.0,
            proteomics_quality_score=75.0,
            sample_accuracy=98.5,
        ),
        Project(
            id=2,
            name="알츠하이머 연구",
            description="신경퇴행성 질환 바이오마커 발굴",
            data_type=["genomics", "transcriptomics"],
            quality_score=87.2,
            validation_status="처리중",
            last_update="3시간 전",
            sample_count=280,
            status="활성",
            genomics_quality_score=98.0,
            transcriptomics_quality_score=70.0,
            proteomics_quality_score=65.0,
            sample_accuracy=100.0,
        ),
        Project(
            id=3,
            name="심혈관 질환 코호트",
            description="다중 오믹스 통합 분석",
            data_type=["metabolomics", "proteomics", "transcriptomics"],
            quality_score=92.4,
            validation_status="검증완료",
            last_update="3일 전",
            sample_count=620,
            status="활성",
            genomics_quality_score=88.0,
            transcriptomics_quality_score=90.0,
            proteomics_quality_score=95.0,
            sample_accuracy=99.2,
        ),
    ]

    db.add_all(projects)
    db.commit()

    # 데이터 파일 생성
    data_files = [
        DataFile(id=101, project_id=1, name="BRCA_RNA_seq.tsv",
                 size="1.2 GB", data_type="transcriptomics"),
        DataFile(id=102, project_id=1, name="BRCA_DNA_methylation.csv",
                 size="856 MB", data_type="genomics"),
        DataFile(id=103, project_id=1, name="BRCA_protein.tsv",
                 size="234 MB", data_type="proteomics"),
    ]
    db.add_all(data_files)
    db.commit()

    # 결측치 데이터 생성
    missing_values = [
        MissingValue(
            project_id=1,
            total_missing_rate=18.7,
            missing_sample_count=156,
            missing_gene_count=4523,
            total_cells=13876348,
            distribution_data={"ranges": [
                {"range": "0-10%", "sampleCount": 645, "geneCount": 42135},
                {"range": "10-20%", "sampleCount": 289, "geneCount": 12458},
                {"range": "20-30%", "sampleCount": 136, "geneCount": 3867},
                {"range": "30-50%", "sampleCount": 98, "geneCount": 1845},
                {"range": "50%+", "sampleCount": 58, "geneCount": 678},
            ]},
        ),
    ]
    db.add_all(missing_values)
    db.commit()

    # 차원별 검증 상태 (Completeness/Plausibility/Conformance)
    verification_statuses = [
        VerificationStatus(project_id=1, label="Completeness", score=95, standard=90),
        VerificationStatus(project_id=1, label="Plausibility", score=87, standard=85),
        VerificationStatus(project_id=1, label="Conformance", score=91, standard=88),
    ]
    db.add_all(verification_statuses)
    db.commit()

    print(f"Created {len(projects)} projects")
    print(f"Created {len(data_files)} data files")
    print(f"Created {len(missing_values)} missing value records")
    print(f"Created {len(verification_statuses)} verification statuses")
    print("Sample data seeded successfully!")


if __name__ == "__main__":
    from app.db.session import SessionLocal

    init_db()
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
