"""
Multi-Omics Imputation Service
Handles tri-joint imputation for RNA, Protein, and Methyl data using MOCHI model
"""

import sys
import torch
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

# Generator 클래스를 lazy import로 처리
Generator = None

def _import_generator():
    """Generator 클래스를 lazy import"""
    global Generator
    if Generator is not None:
        return Generator
    
    # MOCHI 모델 경로 설정 (환경 변수 또는 기본값)
    mochi_code_path = os.getenv("MOCHI_CODE_PATH", "/home/humandeep/nmf/mochi_code")
    
    if not os.path.exists(mochi_code_path):
        raise ImportError(
            f"MOCHI code path not found: {mochi_code_path}. "
            f"Please set MOCHI_CODE_PATH environment variable or ensure the path exists."
        )
    
    # 경로 추가
    if mochi_code_path not in sys.path:
        sys.path.append(mochi_code_path)
    
    try:
        from models import Generator as Gen
        Generator = Gen
        return Generator
    except ImportError as e:
        raise ImportError(
            f"Failed to import Generator from models module. "
            f"Please ensure MOCHI code is available at {mochi_code_path}. "
            f"Original error: {str(e)}"
        )


class MultiOmicsImputationService:
    """멀티오믹스 데이터 보간 서비스"""

    def __init__(self, checkpoint_path: str = "/home/humandeep/nmf/mochi_code/results/tri_joint_v2/tri_best.ckpt"):
        """
        Args:
            checkpoint_path: MOCHI 모델 체크포인트 경로
        """
        self.checkpoint_path = checkpoint_path
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        # 모델 차원 (BRCA PAM50 데이터 기준)
        self.dim_rna = 60660
        self.dim_protein = 487
        self.dim_methyl = 10000

        # 모델 초기화
        self._load_model()

    def _load_model(self):
        """MOCHI tri-joint 모델 로드"""
        try:
            logger.info(f"Loading MOCHI model from {self.checkpoint_path}")
            self.ckpt = torch.load(self.checkpoint_path, map_location=self.device)
            logger.info(f"Model loaded from epoch {self.ckpt.get('epoch', 'N/A')}")

            if 'val_rmse' in self.ckpt:
                logger.info(f"Validation RMSE: {self.ckpt['val_rmse']}")

            # Generator 초기화
            self._init_generators()

        except Exception as e:
            logger.error(f"Failed to load MOCHI model: {str(e)}")
            raise

    def _init_generators(self):
        """Generator 모델 초기화"""
        # Generator 클래스 import
        Generator = _import_generator()

        # Gp: [RNA + Methyl] -> Protein
        self.Gp = Generator(
            input_size=self.dim_rna + self.dim_methyl,
            output_size=self.dim_protein,
            use_attn=True,
            n_heads=4,
            d_head=64,
            target_type="protein",
            src_size=self.dim_rna + self.dim_methyl
        ).to(self.device)
        self.Gp.load_state_dict(self.ckpt['Gp'])
        self.Gp.eval()

        # Gr: [Protein + Methyl] -> RNA
        self.Gr = Generator(
            input_size=self.dim_protein + self.dim_methyl,
            output_size=self.dim_rna,
            use_attn=True,
            n_heads=4,
            d_head=64,
            target_type="rna",
            src_size=self.dim_protein + self.dim_methyl
        ).to(self.device)
        self.Gr.load_state_dict(self.ckpt['Gr'])
        self.Gr.eval()

        # Gm: [RNA + Protein] -> Methyl
        self.Gm = Generator(
            input_size=self.dim_rna + self.dim_protein,
            output_size=self.dim_methyl,
            use_attn=True,
            n_heads=4,
            d_head=64,
            target_type="methyl",
            src_size=self.dim_rna + self.dim_protein
        ).to(self.device)
        self.Gm.load_state_dict(self.ckpt['Gm'])
        self.Gm.eval()

        logger.info("All generators loaded successfully!")

    def load_multiomics_data(self, project_id: int, data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        프로젝트의 멀티오믹스 데이터 로드

        Args:
            project_id: 프로젝트 ID
            data_dir: 데이터 디렉토리 경로

        Returns:
            (rna_df, protein_df, methyl_df) 튜플
        """
        project_dir = data_dir / f"project_{project_id}" / "raw"

        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")

        # 파일 찾기
        files = list(project_dir.glob("*.tsv"))
        if not files:
            raise FileNotFoundError(f"No TSV files found in {project_dir}")

        rna_file = None
        protein_file = None
        methyl_file = None

        for f in files:
            name_lower = f.name.lower()
            if 'rna' in name_lower:
                rna_file = f
            elif 'protein' in name_lower:
                protein_file = f
            elif 'methy' in name_lower or 'methyl' in name_lower:
                methyl_file = f

        # 파일 로드
        dataframes = {}

        if rna_file:
            logger.info(f"Loading RNA data from {rna_file}")
            dataframes['rna'] = pd.read_csv(rna_file, sep="\t", index_col=0)

        if protein_file:
            logger.info(f"Loading Protein data from {protein_file}")
            dataframes['protein'] = pd.read_csv(protein_file, sep="\t", index_col=0)

        if methyl_file:
            logger.info(f"Loading Methyl data from {methyl_file}")
            dataframes['methyl'] = pd.read_csv(methyl_file, sep="\t", index_col=0)

        if len(dataframes) < 3:
            available = list(dataframes.keys())
            logger.warning(f"Only {len(dataframes)} omics types found: {available}")
            logger.warning("MOCHI tri-joint model requires all 3 types (RNA, Protein, Methyl)")

        return (
            dataframes.get('rna'),
            dataframes.get('protein'),
            dataframes.get('methyl')
        )

    @torch.no_grad()
    def impute_multiomics(
        self,
        rna_df: Optional[pd.DataFrame],
        protein_df: Optional[pd.DataFrame],
        methyl_df: Optional[pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        멀티오믹스 데이터 보간

        Args:
            rna_df: RNA 데이터 (features × samples)
            protein_df: Protein 데이터
            methyl_df: Methyl 데이터

        Returns:
            보간된 데이터 딕셔너리 {'rna': ..., 'protein': ..., 'methyl': ...}
        """
        results = {}

        if rna_df is None or protein_df is None or methyl_df is None:
            raise ValueError("All three omics types (RNA, Protein, Methyl) are required")

        # 공통 샘플 추출
        common_samples = sorted(
            set(rna_df.columns) & set(protein_df.columns) & set(methyl_df.columns)
        )

        if len(common_samples) == 0:
            raise ValueError("No common samples found across RNA, Protein, and Methyl data")

        logger.info(f"Found {len(common_samples)} common samples")

        # 공통 샘플로 필터링
        rna_aligned = rna_df[common_samples]
        protein_aligned = protein_df[common_samples]
        methyl_aligned = methyl_df[common_samples]

        # 결측치 마스크 생성
        rna_mask = rna_aligned.isna()
        protein_mask = protein_aligned.isna()
        methyl_mask = methyl_aligned.isna()

        # 결측치를 0으로 채움 (모델 입력용)
        rna_filled = rna_aligned.fillna(0).values.T.astype(np.float32)  # (samples, features)
        protein_filled = protein_aligned.fillna(0).values.T.astype(np.float32)
        methyl_filled = methyl_aligned.fillna(0).values.T.astype(np.float32)

        logger.info(f"Data shapes - RNA: {rna_filled.shape}, Protein: {protein_filled.shape}, Methyl: {methyl_filled.shape}")

        # 예측 수행
        logger.info("Predicting protein from RNA + Methyl...")
        pred_protein = self._predict_protein(rna_filled, methyl_filled)

        logger.info("Predicting RNA from Protein + Methyl...")
        pred_rna = self._predict_rna(protein_filled, methyl_filled)

        logger.info("Predicting methyl from RNA + Protein...")
        pred_methyl = self._predict_methyl(rna_filled, protein_filled)

        # 결측치 위치에만 예측값 채우기
        rna_imputed = rna_aligned.copy()
        protein_imputed = protein_aligned.copy()
        methyl_imputed = methyl_aligned.copy()

        # 결측치 위치에 예측값 할당
        rna_mask_T = rna_mask.values.T
        protein_mask_T = protein_mask.values.T
        methyl_mask_T = methyl_mask.values.T

        for i, sample in enumerate(common_samples):
            # RNA 보간
            if rna_mask_T[i].any():
                rna_imputed.loc[rna_mask_T[i], sample] = pred_rna[i, rna_mask_T[i]]

            # Protein 보간
            if protein_mask_T[i].any():
                protein_imputed.loc[protein_mask_T[i], sample] = pred_protein[i, protein_mask_T[i]]

            # Methyl 보간
            if methyl_mask_T[i].any():
                methyl_imputed.loc[methyl_mask_T[i], sample] = pred_methyl[i, methyl_mask_T[i]]

        results['rna'] = rna_imputed
        results['protein'] = protein_imputed
        results['methyl'] = methyl_imputed

        # 통계 계산
        results['statistics'] = {
            'rna_missing_before': rna_mask.sum().sum(),
            'protein_missing_before': protein_mask.sum().sum(),
            'methyl_missing_before': methyl_mask.sum().sum(),
            'rna_missing_after': rna_imputed.isna().sum().sum(),
            'protein_missing_after': protein_imputed.isna().sum().sum(),
            'methyl_missing_after': methyl_imputed.isna().sum().sum(),
            'total_samples': len(common_samples)
        }

        logger.info(f"Imputation statistics: {results['statistics']}")

        return results

    def _predict_protein(self, rna: np.ndarray, methyl: np.ndarray) -> np.ndarray:
        """RNA + Methyl -> Protein 예측"""
        rna_t = self._to_tensor(rna)
        methyl_t = self._to_tensor(methyl)
        x = torch.cat([rna_t, methyl_t], dim=-1)
        pred = self.Gp(x, src=None)
        return pred.cpu().numpy()

    def _predict_rna(self, protein: np.ndarray, methyl: np.ndarray) -> np.ndarray:
        """Protein + Methyl -> RNA 예측"""
        protein_t = self._to_tensor(protein)
        methyl_t = self._to_tensor(methyl)
        x = torch.cat([protein_t, methyl_t], dim=-1)
        pred = self.Gr(x, src=None)
        return pred.cpu().numpy()

    def _predict_methyl(self, rna: np.ndarray, protein: np.ndarray) -> np.ndarray:
        """RNA + Protein -> Methyl 예측"""
        rna_t = self._to_tensor(rna)
        protein_t = self._to_tensor(protein)
        x = torch.cat([rna_t, protein_t], dim=-1)
        pred = self.Gm(x, src=None)
        return pred.cpu().numpy()

    def _to_tensor(self, arr: np.ndarray) -> torch.Tensor:
        """numpy array를 tensor로 변환"""
        if arr.ndim == 1:
            arr = arr[np.newaxis, :]
        return torch.tensor(arr, dtype=torch.float32, device=self.device)
