"""
SQLAlchemy Base and Model Definitions
"""

from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Project(Base):
    """프로젝트 모델"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    data_type = Column(JSON, nullable=False, default=list)  # ["전사체", "대사체"] 등
    quality_score = Column(Float, default=0.0)
    validation_status = Column(String(50), default="작성중")  # 작성중, 처리중, 검증완료
    last_update = Column(String(100), default="방금 전")
    sample_count = Column(Integer, default=0)
    status = Column(String(50), default="활성")  # 활성, 비활성, 완료

    # 품질 점수 (5종 dataType 기준)
    # 명세서 §3: genomics, transcriptomics, proteomics, metabolomics, metadata
    # 옛 라벨 호환을 위해 dna/rna/methyl/protein 컬럼도 유지
    genomics_quality_score = Column(Float, nullable=True)
    transcriptomics_quality_score = Column(Float, nullable=True)
    proteomics_quality_score = Column(Float, nullable=True)
    metabolomics_quality_score = Column(Float, nullable=True)
    metadata_quality_score = Column(Float, nullable=True)
    # 옛 컬럼 (하위 호환)
    dna_quality_score = Column(Float, nullable=True)
    rna_quality_score = Column(Float, nullable=True)
    methyl_quality_score = Column(Float, nullable=True)
    protein_quality_score = Column(Float, nullable=True)
    sample_accuracy = Column(Float, nullable=True)

    # 하위 호환용: 옛 ValidationRule(7필드 임계값)을 프로젝트 단위로 영속화
    legacy_validation_thresholds = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    data_files = relationship("DataFile", back_populates="project", cascade="all, delete-orphan")
    missing_values = relationship("MissingValue", back_populates="project", cascade="all, delete-orphan")
    verification_rules = relationship("VerificationRule", back_populates="project", cascade="all, delete-orphan")
    validation_jobs = relationship("ValidationJob", back_populates="project", cascade="all, delete-orphan")


class DataFile(Base):
    """데이터 파일 모델"""
    __tablename__ = "data_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    size = Column(String(50), nullable=True)  # "1.2 GB", "856 MB" 등
    file_path = Column(String(500), nullable=True)  # 실제 파일 저장 경로
    # 명세서 §3 dataType (genomics/transcriptomics/proteomics/metabolomics/metadata)
    # NULL이면 파일명 기반 자동 추론 사용
    data_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="data_files")


class MissingValue(Base):
    """결측치 분석 모델"""
    __tablename__ = "missing_values"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    total_missing_rate = Column(Float, default=0.0)
    missing_sample_count = Column(Integer, default=0)
    missing_gene_count = Column(Integer, default=0)
    total_cells = Column(Integer, default=0)

    distribution_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="missing_values")


class VerificationRule(Base):
    """
    검증 규칙 모델 — GENE-QC 지표설계 명세서 v2.0 §5 기준

    필드 구성:
      §5.1 확정: name, dimension, quality_level, severity, description, data_types
      §5.2 검증 수행: validation_type, parameters
      §5.3 OMOP CDM DQM 확장: metric_id, metric_level, context, is_custom, enabled
    """
    __tablename__ = "verification_rules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # NULL이면 전역 규칙

    # 명세서 §5.3 — 내부 지표 ID (comp_F001, plau_C001, conf_V001 등)
    metric_id = Column(String(50), nullable=False, index=True)

    # 명세서 §5.1 — 확정 필드
    name = Column(String(255), nullable=False)
    dimension = Column(String(30), nullable=False)         # Completeness | Plausibility | Conformance
    quality_level = Column(String(20), nullable=False, default="basic")  # basic | advanced
    severity = Column(String(30), nullable=False)          # fatal | error | warning | convention | characterization
    description = Column(Text, nullable=True)
    data_types = Column(JSON, nullable=False, default=list)  # ["genomics", "transcriptomics", ...]

    # 명세서 §5.2 — 검증 수행 필드
    validation_type = Column(String(50), nullable=False)   # threshold, range, value_set, ...
    parameters = Column(JSON, nullable=False, default=dict)

    # 명세서 §5.3 — OMOP 추적 필드
    metric_level = Column(String(20), nullable=True)       # FILE | COLUMN | VALUE
    context = Column(String(30), nullable=True)            # Verification | Validation
    is_custom = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = Column(String(100), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="verification_rules")


class VerificationStatus(Base):
    """검증 상태 모델 (대시보드 차원별 점수)"""
    __tablename__ = "verification_status"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    label = Column(String(100), nullable=False)  # Completeness/Plausibility/Conformance
    score = Column(Integer, nullable=False)
    standard = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ValidationJob(Base):
    """
    검증 작업 영속 저장 모델
    검증 결과/상태를 메모리가 아닌 DB에 저장하여 서버 재시작에도 보존
    """
    __tablename__ = "validation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    status = Column(String(20), default="processing", index=True)  # processing|completed|failed
    enabled_metrics = Column(JSON, nullable=True)
    params_overrides = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="validation_jobs")


class ImputationJob(Base):
    """보간 작업 모델"""
    __tablename__ = "imputation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    method = Column(String(50), nullable=False)
    threshold = Column(Float, default=30.0)
    quality_threshold = Column(Float, default=85.0)
    options = Column(JSON, nullable=True)

    status = Column(String(50), default="processing")
    progress = Column(Float, default=0.0)

    imputed_samples = Column(Integer, nullable=True)
    imputed_features = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    output_file = Column(String(500), nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
