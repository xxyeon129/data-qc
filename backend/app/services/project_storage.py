"""
프로젝트 원본 데이터(raw) 디렉터리 해석 및 복구.

업로드 API로 저장된 파일은 `uploads/project_<id>/raw/` 에 있어야 하며,
DB `DataFile.file_path` 가 가리키는 실제 파일이 있으면 raw 디렉터리로
복사해 검증·보간·원격 업로드가 동일 경로를 사용하도록 합니다.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import UPLOADS_DIR
from app.models.base import DataFile as DataFileModel


class ProjectDataNotFoundError(Exception):
    """프로젝트 raw 데이터를 디스크에서 찾을 수 없을 때"""


def expected_raw_dir(project_id: int) -> Path:
    return UPLOADS_DIR / f"project_{project_id}" / "raw"


def list_omics_files(raw_dir: Path) -> List[Path]:
    return sorted(raw_dir.glob("*.tsv")) + sorted(raw_dir.glob("*.csv"))


def detect_modality_files(raw_dir: Path) -> Dict[str, Optional[Path]]:
    """원격 MOCHI 스크립트와 동일한 파일명 휴리스틱으로 오믹스 파일을 식별한다."""
    rna_file: Optional[Path] = None
    protein_file: Optional[Path] = None
    methyl_file: Optional[Path] = None

    for f in list_omics_files(raw_dir):
        name = f.name.lower()
        if any(k in name for k in ("rna", "transcriptom", "expression")):
            rna_file = rna_file or f
        elif any(k in name for k in ("protein", "proteom")):
            protein_file = protein_file or f
        elif any(k in name for k in ("methy", "dna", "genomic")):
            methyl_file = methyl_file or f

    return {"rna": rna_file, "protein": protein_file, "methyl": methyl_file}


def ensure_project_raw_dir(project_id: int, db: Session) -> Path:
    """
    프로젝트 raw 디렉터리를 반환한다. 디렉터리가 비어 있으면 DB file_path 에서
    존재하는 파일을 raw 로 복사해 복구를 시도한다.
    """
    raw_dir = expected_raw_dir(project_id)

    if raw_dir.exists() and list_omics_files(raw_dir):
        return raw_dir

    raw_dir.mkdir(parents=True, exist_ok=True)

    db_files = (
        db.query(DataFileModel)
        .filter(DataFileModel.project_id == project_id)
        .all()
    )

    for df in db_files:
        if not df.name:
            continue
        dest = raw_dir / df.name
        if dest.exists():
            continue
        if df.file_path:
            src = Path(df.file_path)
            if src.is_file():
                shutil.copy2(src, dest)

    if list_omics_files(raw_dir):
        return raw_dir

    registered = [f.name for f in db_files if f.name]
    raise ProjectDataNotFoundError(
        f"프로젝트 {project_id}의 원본 데이터 파일을 찾을 수 없습니다. "
        "데이터셋 관리에서 RNA / Protein / Methyl 파일을 업로드해 주세요. "
        f"(등록된 파일: {', '.join(registered) or '없음'})"
    )


def validate_ai_validation_prerequisites(project_id: int, db: Session) -> Path:
    """AI 일관성 검증에 필요한 RNA·Protein·Methyl 세 파일이 있는지 확인한다."""
    raw_dir = ensure_project_raw_dir(project_id, db)
    modalities = detect_modality_files(raw_dir)

    missing = [k for k, path in modalities.items() if path is None]
    if missing:
        found = ", ".join(f.name for f in modalities.values() if f)
        raise ProjectDataNotFoundError(
            "AI 일관성 검증에는 RNA / Protein / Methyl 세 오믹스 파일이 모두 필요합니다. "
            f"부족한 유형: {', '.join(missing)}. "
            f"(현재 raw 디렉터리: {found or '파일 없음'})"
        )

    return raw_dir
