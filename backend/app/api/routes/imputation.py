"""
Imputation API routes
Handles missing value imputation with ML model support
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import uuid
from datetime import datetime
from app.models.schemas import (
    ImputationMethod,
    ImputationRequest,
    ImputationResponse
)
from app.services.imputation_service import ImputationService
from app.services.ml_model_client import MLModelClient
from app.services.multiomics_imputation_service import MultiOmicsImputationService
from pathlib import Path

router = APIRouter()
imputation_service = ImputationService()
ml_client = MLModelClient()

# 멀티오믹스 서비스 (싱글톤)
multiomics_service = None

def get_multiomics_service():
    """멀티오믹스 서비스 인스턴스 가져오기 (lazy loading)"""
    global multiomics_service
    if multiomics_service is None:
        try:
            from app.services.multiomics_imputation_service import MultiOmicsImputationService
            multiomics_service = MultiOmicsImputationService()
        except Exception as e:
            print(f"Failed to initialize MultiOmicsImputationService: {e}")
            multiomics_service = None
    return multiomics_service

# Mock imputation methods
MOCK_IMPUTATION_METHODS = [
    {
        "value": "mochi",
        "label": "🚀 MOCHI: Imputation Model (추천)",
        "description": "멀티오믹스 데이터의 특성을 고려한 최신 AI 기반 보간 모델입니다.",
        "accuracy": "~97.3%"
    },
    {
        "value": "mean",
        "label": "Mean/Median Imputation",
        "description": "가장 간단한 통계적 방법으로, 각 변수의 평균 또는 중앙값으로 결측치를 대체합니다.",
        "accuracy": "~75%"
    },
    {
        "value": "knn",
        "label": "KNN (K-Nearest Neighbors) Imputation",
        "description": "유사한 샘플들의 값을 기반으로 결측치를 추정합니다.",
        "accuracy": "~88%"
    },
    # TODO: MICE는 대용량 데이터(특성 수 > 10,000)에 대해 계산 시간이 매우 오래 걸림 (수 시간)
    # 추후 샘플링 또는 PCA 기반 차원 축소 등의 최적화 필요
    # {
    #     "value": "mice",
    #     "label": "MICE (Multiple Imputation by Chained Equations)",
    #     "description": "다중 대체 방법으로 여러 개의 완전한 데이터셋을 생성합니다.",
    #     "accuracy": "~92%"
    # },
    {
        "value": "missforest",
        "label": "MissForest",
        "description": "Random Forest 알고리즘을 사용한 비모수적 보간 방법입니다.",
        "accuracy": "~91%"
    },
    {
        "value": "gain",
        "label": "GAIN (Generative Adversarial Imputation)",
        "description": "GAN 기반의 생성 모델로 결측치를 보간합니다.",
        "accuracy": "~94%"
    },
    {
        "value": "vae",
        "label": "VAE (Variational Autoencoder)",
        "description": "딥러닝 기반의 생성 모델로, 데이터의 잠재 표현을 학습하여 결측치를 추정합니다.",
        "accuracy": "~93%"
    },
]


imputation_jobs = {}


@router.get("/methods", response_model=List[ImputationMethod])
async def get_imputation_methods():
    """사용 가능한 보간 방법 목록 조회"""
    return MOCK_IMPUTATION_METHODS


@router.post("/execute", response_model=ImputationResponse)
async def execute_imputation(
    request: ImputationRequest,
    background_tasks: BackgroundTasks
):
    """결측치 보간 실행"""
    job_id = str(uuid.uuid4())
    
    # 백그라운드 작업으로 보간 실행
    background_tasks.add_task(
        imputation_service.run_imputation,
        job_id=job_id,
        project_id=request.project_id,
        method=request.method,
        threshold=request.threshold,
        quality_threshold=request.quality_threshold,
        options=request.options or {}
    )
    
    imputation_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "request": request.model_dump()
    }
    
    return ImputationResponse(
        jobId=job_id,
        status="processing",
        message="Imputation job started",
        estimatedTime=300  # 5분 예상
    )


@router.get("/status/{job_id}")
async def get_imputation_status(job_id: str):
    """보간 작업 상태 조회"""
    # imputation_service의 jobs 딕셔너리에서 상태 확인
    job = imputation_service.jobs.get(job_id)
    if job:
        # 서비스에서 완료/실패 상태가 업데이트되었으면 로컬 딕셔너리도 업데이트
        imputation_jobs[job_id] = job
        return job

    # 서비스에 없으면 로컬 딕셔너리에서 확인 (초기 processing 상태)
    job = imputation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/results/{job_id}")
async def get_imputation_results(job_id: str):
    """보간 결과 조회"""
    # imputation_service의 jobs 딕셔너리에서 확인
    job = imputation_service.jobs.get(job_id)
    if not job:
        job = imputation_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # 실제 결과 데이터 반환
    return {
        "job_id": job_id,
        "status": "completed",
        "method": job.get("method"),
        "results": job.get("results", {})
    }


@router.get("/ml-model/connection-test")
async def test_ml_model_connection():
    """ML 모델 서버 연결 테스트"""
    try:
        is_connected = ml_client.check_connection()
        if is_connected:
            return {
                "status": "success",
                "message": "Successfully connected to ML model server",
                "connected": True
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to connect to ML model server",
                "connected": False
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {str(e)}"
        )


@router.get("/ml-model/list")
async def list_ml_models():
    """원격 서버의 ML 모델 목록 조회"""
    try:
        models = ml_client.list_models()
        return {
            "status": "success",
            "models": models,
            "count": len(models)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )



@router.post("/execute-multiomics")
async def execute_multiomics_imputation(
    project_id: int,
    threshold: float = 30.0,
    quality_threshold: float = 85.0,
    background_tasks: BackgroundTasks = None
):
    """
    멀티오믹스 데이터 보간 실행 (RNA, Protein, Methyl)

    프로젝트에 업로드된 3종류의 omics 데이터에 대해
    MOCHI tri-joint 모델을 사용하여 결측치 보간을 수행합니다.

    Parameters:
    - project_id: 프로젝트 ID
    - threshold: 보간 임계값 (%) - 이 비율 이하의 결측만 보간
    - quality_threshold: 품질 기준 (%) - 보간 후 최소 품질 점수
    """
    job_id = str(uuid.uuid4())

    # 백그라운드 작업으로 보간 실행
    background_tasks.add_task(
        _run_multiomics_imputation,
        job_id=job_id,
        project_id=project_id,
        threshold=threshold,
        quality_threshold=quality_threshold
    )

    imputation_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "project_id": project_id,
        "method": "mochi_multiomics",
        "threshold": threshold,
        "quality_threshold": quality_threshold
    }

    return {
        "jobId": job_id,
        "status": "processing",
        "message": "Multi-omics imputation job started",
        "estimatedTime": 180
    }


def _run_multiomics_imputation(job_id: str, project_id: int, threshold: float = 30.0, quality_threshold: float = 85.0):
    """멀티오믹스 보간 백그라운드 작업"""
    try:
        print(f"[Job {job_id}] Starting multi-omics imputation for project {project_id}")
        print(f"[Job {job_id}] Parameters - threshold: {threshold}%, quality_threshold: {quality_threshold}%")

        # 서비스 인스턴스 가져오기
        service = get_multiomics_service()
        if service is None:
            raise RuntimeError("Failed to initialize MultiOmicsImputationService")

        # 데이터 로드
        from app.core.config import UPLOADS_DIR
        rna_df, protein_df, methyl_df = service.load_multiomics_data(project_id, UPLOADS_DIR)

        if rna_df is None or protein_df is None or methyl_df is None:
            missing = []
            if rna_df is None:
                missing.append("RNA")
            if protein_df is None:
                missing.append("Protein")
            if methyl_df is None:
                missing.append("Methyl")
            raise ValueError(f"Missing required omics data: {', '.join(missing)}")

        print(f"[Job {job_id}] Data loaded - RNA: {rna_df.shape}, Protein: {protein_df.shape}, Methyl: {methyl_df.shape}")

        # 보간 수행
        results = service.impute_multiomics(rna_df, protein_df, methyl_df)

        # 보간 결과 저장
        output_dir = data_dir / f"project_{project_id}" / "imputed"
        output_dir.mkdir(parents=True, exist_ok=True)

        rna_output = output_dir / f"{job_id}_rna_imputed.tsv"
        protein_output = output_dir / f"{job_id}_protein_imputed.tsv"
        methyl_output = output_dir / f"{job_id}_methyl_imputed.tsv"

        results['rna'].to_csv(rna_output, sep="\t")
        results['protein'].to_csv(protein_output, sep="\t")
        results['methyl'].to_csv(methyl_output, sep="\t")

        print(f"[Job {job_id}] Results saved to {output_dir}")

        # 작업 상태 업데이트
        stats = results['statistics']
        imputation_jobs[job_id] = {
            "status": "completed",
            "created_at": imputation_jobs[job_id]["created_at"],
            "completed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "method": "mochi_multiomics",
            "results": {
                "rna_missing_imputed": int(stats['rna_missing_before']),
                "protein_missing_imputed": int(stats['protein_missing_before']),
                "methyl_missing_imputed": int(stats['methyl_missing_before']),
                "total_samples": int(stats['total_samples']),
                "output_files": {
                    "rna": str(rna_output),
                    "protein": str(protein_output),
                    "methyl": str(methyl_output)
                }
            }
        }

        print(f"[Job {job_id}] Multi-omics imputation completed successfully")

    except Exception as e:
        print(f"[Job {job_id}] Multi-omics imputation failed: {str(e)}")
        import traceback
        traceback.print_exc()

        imputation_jobs[job_id] = {
            "status": "failed",
            "created_at": imputation_jobs[job_id]["created_at"],
            "failed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "error": str(e)
        }


@router.get("/download/{job_id}/{omics_type}")
async def download_imputed_data(job_id: str, omics_type: str):
    """
    보간된 데이터 다운로드

    Parameters:
    - job_id: 보간 작업 ID
    - omics_type: 오믹스 타입 (rna, protein, methyl)
    """
    from fastapi.responses import FileResponse

    job = imputation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # 파일 경로 가져오기
    output_files = job.get("results", {}).get("output_files", {})
    file_path = output_files.get(omics_type)

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"{omics_type} imputed data file not found")

    # 파일명 생성
    filename = f"{omics_type}_imputed_{job_id}.tsv"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/tab-separated-values"
    )
