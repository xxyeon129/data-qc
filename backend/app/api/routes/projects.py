"""
Projects API routes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List
from sqlalchemy.orm import Session
import pandas as pd
import io
from datetime import datetime
from app.models.schemas import Project, ProjectCreate, ProjectNameUpdate
from app.models.base import Project as ProjectModel
from app.db.session import get_db

router = APIRouter()


def project_to_dict(project: ProjectModel) -> dict:
    """SQLAlchemy 모델을 딕셔너리로 변환"""
    return {
        "id": project.id,
        "name": project.name,
        "dataType": project.data_type,
        "qualityScore": project.quality_score,
        "validationStatus": project.validation_status,
        "lastUpdate": project.last_update,
        "description": project.description,
        "sampleCount": project.sample_count,
        "status": project.status,
        "DNA_qualityScore": project.dna_quality_score,
        "RNA_qualityScore": project.rna_quality_score,
        "Methyl_qualityScore": project.methyl_quality_score,
        "Protein_qualityScore": project.protein_quality_score,
        "sample_accuracy": project.sample_accuracy,
    }


@router.get("", response_model=List[Project])
async def get_projects(db: Session = Depends(get_db)):
    """프로젝트 목록 조회"""
    projects = db.query(ProjectModel).all()
    return [project_to_dict(p) for p in projects]


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """특정 프로젝트 조회"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_dict(project)


@router.post("", response_model=Project)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """새 프로젝트 생성"""
    db_project = ProjectModel(
        name=project.name,
        description=project.description,
        data_type=project.data_type,
        quality_score=project.quality_score,
        validation_status=project.validation_status,
        last_update=project.last_update,
        sample_count=project.sample_count,
        status=project.status,
        dna_quality_score=project.dna_quality_score,
        rna_quality_score=project.rna_quality_score,
        methyl_quality_score=project.methyl_quality_score,
        protein_quality_score=project.protein_quality_score,
        sample_accuracy=project.sample_accuracy,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return project_to_dict(db_project)


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: int, project: ProjectCreate, db: Session = Depends(get_db)):
    """프로젝트 업데이트"""
    db_project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_project.name = project.name
    db_project.description = project.description
    db_project.data_type = project.data_type
    db_project.quality_score = project.quality_score
    db_project.validation_status = project.validation_status
    db_project.last_update = project.last_update
    db_project.sample_count = project.sample_count
    db_project.status = project.status
    db_project.dna_quality_score = project.dna_quality_score
    db_project.rna_quality_score = project.rna_quality_score
    db_project.methyl_quality_score = project.methyl_quality_score
    db_project.protein_quality_score = project.protein_quality_score
    db_project.sample_accuracy = project.sample_accuracy
    db_project.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_project)
    return project_to_dict(db_project)


@router.patch("/{project_id}/name", response_model=Project)
async def update_project_name(project_id: int, name_update: ProjectNameUpdate, db: Session = Depends(get_db)):
    """프로젝트 이름만 수정"""
    db_project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not name_update.name.strip():
        raise HTTPException(status_code=400, detail="프로젝트 이름은 비어있을 수 없습니다.")
    
    db_project.name = name_update.name.strip()
    db_project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_project)
    return project_to_dict(db_project)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """프로젝트 삭제"""
    db_project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/upload-csv")
async def upload_projects_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV/TSV 파일을 업로드하여 여러 프로젝트를 일괄 생성
    
    파일 형식:
    - CSV: 쉼표로 구분
    - TSV: 탭으로 구분
    
    필수 컬럼:
    - 프로젝트 이름 (또는 name, 프로젝트명)
    - 프로젝트 설명 (또는 description, 설명)
    - 샘플 개수 (또는 sampleCount, sample_count)
    - updatedAt (또는 updated_at, 업데이트일)
    """
    try:
        # 파일 확장자 확인
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다")
        
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in ['csv', 'tsv', 'txt']:
            raise HTTPException(
                status_code=400, 
                detail="지원하지 않는 파일 형식입니다. CSV 또는 TSV 파일을 업로드해주세요."
            )
        
        # 파일 내용 읽기
        contents = await file.read()
        
        # 인코딩 처리 (UTF-8, CP949 시도)
        try:
            content_str = contents.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content_str = contents.decode('cp949')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="파일 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949 인코딩을 사용해주세요."
                )
        
        # pandas로 파일 파싱
        delimiter = '\t' if file_extension == 'tsv' else ','
        df = pd.read_csv(io.StringIO(content_str), delimiter=delimiter)
        
        # 컬럼명 정규화 (다양한 이름 지원)
        column_mapping = {
            '프로젝트 이름': 'name',
            '프로젝트명': 'name',
            'name': 'name',
            'Name': 'name',
            '프로젝트 설명': 'description',
            '설명': 'description',
            'description': 'description',
            'Description': 'description',
            '샘플 개수': 'sampleCount',
            '샘플개수': 'sampleCount',
            'sampleCount': 'sampleCount',
            'sample_count': 'sampleCount',
            'Sample Count': 'sampleCount',
            'updatedAt': 'updatedAt',
            'updated_at': 'updatedAt',
            'UpdatedAt': 'updatedAt',
            '업데이트일': 'updatedAt',
            '수정일': 'updatedAt',
        }
        
        # 컬럼명 변경
        df.columns = [column_mapping.get(col, col) for col in df.columns]
        
        # 필수 컬럼 확인
        required_columns = ['name', 'description', 'sampleCount', 'updatedAt']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"필수 컬럼이 누락되었습니다: {', '.join(missing_columns)}\n" + 
                       f"파일에 있는 컬럼: {', '.join(df.columns.tolist())}"
            )
        
        # 빈 행 제거
        df = df.dropna(subset=['name'], how='all')
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="파일에 유효한 데이터가 없습니다")
        
        # 프로젝트 생성
        created_projects = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # 데이터 추출 및 변환
                name = str(row['name']).strip()
                description = str(row['description']).strip() if pd.notna(row['description']) else ""
                sample_count = int(row['sampleCount']) if pd.notna(row['sampleCount']) else 0
                updated_at = str(row['updatedAt']).strip() if pd.notna(row['updatedAt']) else datetime.now().strftime("%Y-%m-%d")
                
                # 새 프로젝트 생성
                db_project = ProjectModel(
                    name=name,
                    description=description,
                    sample_count=sample_count,
                    last_update=updated_at,
                    data_type=["기타"],
                    quality_score=0.0,
                    validation_status="작성중",
                    status="활성",
                )
                
                db.add(db_project)
                db.commit()
                db.refresh(db_project)
                
                created_projects.append(project_to_dict(db_project))
                
            except Exception as e:
                db.rollback()
                errors.append(f"행 {idx + 2}: {str(e)}")
        
        response = {
            "message": f"{len(created_projects)}개의 프로젝트가 생성되었습니다",
            "createdCount": len(created_projects),
            "totalRows": len(df),
            "projects": created_projects
        }
        
        if errors:
            response["errors"] = errors
            response["message"] += f" ({len(errors)}개 오류 발생)"
        
        return response
        
    except HTTPException:
        raise
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=400,
            detail=f"파일 파싱 오류: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}"
        )

