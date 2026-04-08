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
from app.services.remote_multiomics_service import RemoteMultiOmicsImputationService
from pathlib import Path

router = APIRouter()
imputation_service = ImputationService()
ml_client = MLModelClient()

# 멀티오믹스 서비스 (싱글톤)
multiomics_service = None
multiomics_service_init_error = None

def get_multiomics_service():
    """원격 멀티오믹스 서비스 인스턴스 가져오기 (lazy loading)"""
    global multiomics_service, multiomics_service_init_error
    if multiomics_service is None:
        try:
            multiomics_service = RemoteMultiOmicsImputationService()
            multiomics_service_init_error = None
        except Exception as e:
            multiomics_service_init_error = str(e)
            print(f"Failed to initialize RemoteMultiOmicsImputationService: {multiomics_service_init_error}")
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
    """원격 서버 기반 멀티오믹스 보간 백그라운드 작업"""
    try:
        print(f"[Job {job_id}] Starting multi-omics imputation for project {project_id}")
        print(f"[Job {job_id}] Parameters - threshold: {threshold}%, quality_threshold: {quality_threshold}%")

        # 서비스 인스턴스 가져오기
        service = get_multiomics_service()
        if service is None:
            detail = multiomics_service_init_error or "unknown initialization error"
            raise RuntimeError(f"Failed to initialize RemoteMultiOmicsImputationService: {detail}")

        # 로컬 원본 데이터를 원격 서버로 업로드
        from app.core.config import UPLOADS_DIR
        upload_ok, upload_msg = service.upload_data_files(project_id, UPLOADS_DIR)
        if not upload_ok:
            raise RuntimeError(upload_msg)
        print(f"[Job {job_id}] Upload completed: {upload_msg}")

        # 원격 서버에서 보간 실행
        remote_ok, remote_msg, statistics = service.execute_remote_imputation(
            project_id=project_id,
            job_id=job_id
        )
        if not remote_ok:
            raise RuntimeError(remote_msg)
        print(f"[Job {job_id}] Remote imputation completed: {remote_msg}")

        # 원격 결과를 로컬로 다운로드
        output_dir = UPLOADS_DIR / f"project_{project_id}" / "imputed"
        output_dir.mkdir(parents=True, exist_ok=True)

        download_ok, download_msg, downloaded_files = service.download_results(
            project_id=project_id,
            job_id=job_id,
            local_output_dir=output_dir
        )
        if not download_ok:
            raise RuntimeError(download_msg)
        print(f"[Job {job_id}] Download completed: {download_msg}")

        print(f"[Job {job_id}] Results saved to {output_dir}")

        # 작업 상태 업데이트
        stats = statistics or {}
        rna_output = downloaded_files.get("rna")
        protein_output = downloaded_files.get("protein")
        methyl_output = downloaded_files.get("methyl")
        imputation_jobs[job_id] = {
            "status": "completed",
            "created_at": imputation_jobs[job_id]["created_at"],
            "completed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "method": "mochi_multiomics",
            "results": {
                "rna_missing_imputed": int(stats.get('rna_missing_before', 0)),
                "protein_missing_imputed": int(stats.get('protein_missing_before', 0)),
                "methyl_missing_imputed": int(stats.get('methyl_missing_before', 0)),
                "total_samples": int(stats.get('total_samples', 0)),
                "output_files": {
                    "rna": str(rna_output) if rna_output else None,
                    "protein": str(protein_output) if protein_output else None,
                    "methyl": str(methyl_output) if methyl_output else None,
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
