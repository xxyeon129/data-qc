"""
Data management API routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
import os
from app.models.schemas import DataFile, DataFileCreate
from app.models.base import DataFile as DataFileModel
from app.db.session import get_db
from app.services.validation_service import _infer_data_type

router = APIRouter()


def datafile_to_dict(datafile: DataFileModel) -> dict:
    """SQLAlchemy 모델을 딕셔너리로 변환"""
    return {
        "id": datafile.id,
        "name": datafile.name,
        "size": datafile.size,
        "dataType": datafile.data_type,
        "createdAt": datafile.created_at.strftime("%Y-%m-%d") if datafile.created_at else None,
    }


@router.get("", response_model=List[DataFile])
async def get_data_files(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    """데이터 파일 목록 조회"""
    query = db.query(DataFileModel)
    if project_id:
        query = query.filter(DataFileModel.project_id == project_id)
    
    data_files = query.all()
    return [datafile_to_dict(df) for df in data_files]


@router.get("/{file_id}", response_model=DataFile)
async def get_data_file(file_id: int, db: Session = Depends(get_db)):
    """특정 데이터 파일 조회"""
    data_file = db.query(DataFileModel).filter(DataFileModel.id == file_id).first()
    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")
    return datafile_to_dict(data_file)


@router.post("/upload")
async def upload_data_file(
    file: UploadFile = File(...),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    데이터 파일 업로드

    멀티오믹스 데이터 (RNA, Protein, Methyl)를 업로드하고 저장합니다.
    """
    try:
        # 파일 읽기
        content = await file.read()
        file_size = len(content)
        size_str = f"{file_size / (1024**3):.2f} GB" if file_size > 1024**3 else f"{file_size / (1024**2):.2f} MB"

        # 업로드 디렉토리 생성
        from app.core.config import UPLOADS_DIR
        project_dir = UPLOADS_DIR / f"project_{project_id or 1}" / "raw"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 파일 저장 경로
        safe_filename = file.filename or "uploaded_file"
        file_path = project_dir / safe_filename

        # 파일을 디스크에 저장
        with open(file_path, "wb") as f:
            f.write(content)

        # DB에 파일 정보 저장 (dataType 자동 추론)
        inferred_type = _infer_data_type(safe_filename)
        db_file = DataFileModel(
            project_id=project_id or 1,
            name=safe_filename,
            size=size_str,
            file_path=str(file_path),
            data_type=inferred_type if inferred_type != "unknown" else None,
        )

        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return {
            "message": "File uploaded successfully",
            "file": datafile_to_dict(db_file),
            "path": str(file_path)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


@router.delete("/{file_id}")
async def delete_data_file(file_id: int, db: Session = Depends(get_db)):
    """데이터 파일 삭제"""
    data_file = db.query(DataFileModel).filter(DataFileModel.id == file_id).first()
    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")
    
    db.delete(data_file)
    db.commit()
    return {"message": "Data file deleted successfully"}

