"""
Pydantic schemas for request/response models
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# Project Models
class ProjectBase(BaseModel):
    name: str
    data_type: List[str] = Field(..., alias="dataType")
    quality_score: float = Field(..., alias="qualityScore")
    validation_status: str = Field(..., alias="validationStatus")
    last_update: str = Field(..., alias="lastUpdate")
    description: str
    sample_count: int = Field(..., alias="sampleCount")
    status: str
    dna_quality_score: Optional[float] = Field(None, alias="DNA_qualityScore")
    rna_quality_score: Optional[float] = Field(None, alias="RNA_qualityScore")
    methyl_quality_score: Optional[float] = Field(None, alias="Methyl_qualityScore")
    protein_quality_score: Optional[float] = Field(None, alias="Protein_qualityScore")
    sample_accuracy: Optional[float] = Field(None, alias="sample_accuracy")
    created_at: Optional[str] = Field(None, alias="createdAt")
    total_size: Optional[str] = Field(None, alias="totalSize")


class ProjectCreate(BaseModel):
    name: str
    description: str
    data_type: List[str] = Field(..., alias="dataType")
    quality_score: float = Field(0.0, alias="qualityScore")
    validation_status: str = Field("작성중", alias="validationStatus")
    last_update: str = Field("방금 전", alias="lastUpdate")
    sample_count: int = Field(0, alias="sampleCount")
    status: str = "활성"
    dna_quality_score: Optional[float] = Field(None, alias="DNA_qualityScore")
    rna_quality_score: Optional[float] = Field(None, alias="RNA_qualityScore")
    methyl_quality_score: Optional[float] = Field(None, alias="Methyl_qualityScore")
    protein_quality_score: Optional[float] = Field(None, alias="Protein_qualityScore")
    sample_accuracy: Optional[float] = Field(None, alias="sample_accuracy")

    class Config:
        populate_by_name = True


class ProjectNameUpdate(BaseModel):
    name: str


class Project(ProjectBase):
    id: int

    class Config:
        populate_by_name = True


class ProjectBulkUploadResponse(BaseModel):
    message: str
    created_count: int = Field(..., alias="createdCount")
    total_rows: int = Field(..., alias="totalRows")
    projects: List[Project]
    errors: Optional[List[str]] = None

    class Config:
        populate_by_name = True


# Data Models
class DataFileBase(BaseModel):
    name: str
    size: str
    created_at: str = Field(..., alias="createdAt")


class DataFileCreate(DataFileBase):
    pass


class DataFile(DataFileBase):
    id: int

    class Config:
        populate_by_name = True


# Missing Value Models
class MissingValueProject(BaseModel):
    label: str
    sample_count: int = Field(..., alias="sampleCount")
    current_missing_value_rate: float = Field(..., alias="currentMissingValueRate")


class MissingValueSummary(BaseModel):
    type: Literal["all", "sample", "gene"]
    title: str
    value: float
    description: str


class MissingValueDistribution(BaseModel):
    range: Literal["0-10%", "10-20%", "20-30%", "30-50%", "50%+"]
    sample_count: int = Field(..., alias="sampleCount")
    gene_count: int = Field(..., alias="geneCount")


class MissingValueAnalysis(BaseModel):
    summary: List[MissingValueSummary]
    distribution: List[MissingValueDistribution]


# Verification Models
class VerificationDashboardSample(BaseModel):
    label: str
    count: str
    description: str


class VerificationStatus(BaseModel):
    label: str
    score: int
    standard: int


class VerificationRule(BaseModel):
    """
    GENE-QC 지표설계 명세서 v2.0 §5 기준 검증 규칙 스키마

    신규(명세서) 필드와 옛 필드(label/category/metric/condition/threshold)를
    모두 받아 처리할 수 있도록 모두 Optional 로 정의합니다.
    응답에는 두 체계의 필드를 함께 반환합니다.
    """
    # 명세서 §5.3 — 내부 지표 ID
    metric_id: Optional[str] = Field(None, alias="metricId")
    # 명세서 §5.1 — 확정 필드
    name: Optional[str] = None
    dimension: Optional[Literal["Completeness", "Plausibility", "Conformance"]] = None
    quality_level: Optional[Literal["basic", "advanced"]] = Field(None, alias="qualityLevel")
    severity: Optional[Literal["fatal", "error", "warning", "convention", "characterization"]] = None
    description: Optional[str] = None
    data_types: Optional[List[str]] = Field(None, alias="dataTypes")
    # 명세서 §5.2 — 검증 수행 필드
    validation_type: Optional[str] = Field(None, alias="validationType")
    parameters: Optional[dict] = None
    # 명세서 §5.3 — OMOP 추적 필드
    metric_level: Optional[Literal["FILE", "COLUMN", "VALUE"]] = Field(None, alias="metricLevel")
    context: Optional[Literal["Verification", "Validation"]] = None
    is_custom: Optional[bool] = Field(False, alias="isCustom")
    enabled: Optional[bool] = True

    # 옛 필드 (프론트엔드 하위 호환)
    label: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = "active"
    category: Optional[str] = None
    metric: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None

    class Config:
        populate_by_name = True


# Imputation Models
class ImputationMethod(BaseModel):
    value: str
    label: str
    description: Optional[str] = None
    accuracy: Optional[str] = None


class ImputationRequest(BaseModel):
    project_id: int = Field(..., alias="projectId")
    method: str
    threshold: float = 30.0
    quality_threshold: float = 85.0
    options: Optional[dict] = None

    class Config:
        populate_by_name = True


class ImputationResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str
    message: str
    estimated_time: Optional[int] = Field(None, alias="estimatedTime")


# Statistics Models
class DashboardStats(BaseModel):
    active_projects: int = Field(..., alias="activeProjects")
    avg_quality: str = Field(..., alias="avgQuality")
    processed_datasets: int = Field(..., alias="processedDatasets")
    avg_missing_rate: str = Field(..., alias="avgMissingRate")

