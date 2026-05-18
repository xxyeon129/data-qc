"""
Remote AI Cross-Prediction Validation Service

원격 ML 서버의 MOCHI tri-joint 모델을 사용해 사용자 멀티오믹스 데이터에 대한
교차 예측 일관성(Pearson / RMSE / MAE)을 측정합니다. 결과는 명세서 §2.5 의
`plau_X002` 와 짝을 이루는 "AI 일관성 검증"(`plau_X002_ai`) 지표로 반환합니다.

설계 메모:
- `RemoteMultiOmicsImputationService` 의 SSH/SFTP/conda 자동 탐색 로직을
  최대한 재사용해 환경 의존성 분기를 한 곳에 모았습니다.
- 원격 실행 스크립트(`validate_cross_omics.py`)는 매 호출마다 SFTP 로 덮어쓰며,
  Generator 차원은 사용자 데이터의 실제 차원으로 동적 구성합니다. 학습 차원과
  불일치하면 `load_state_dict` 가 즉시 RuntimeError 를 던지도록 두어 silent
  실패를 방지합니다.
- 보간(imputation) 경로와 디렉토리/파일 충돌이 없도록 `validation/` 하위에
  결과를 저장합니다.
"""

from __future__ import annotations

import json
import logging
import shlex
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.services.ml_model_client import MLModelClient

logger = logging.getLogger(__name__)


class RemoteAICrossValidationService:
    """SSH 를 통해 원격 MOCHI 모델로 cross-prediction 일관성을 측정하는 서비스"""

    SCRIPT_FILENAME = "validate_cross_omics.py"

    def __init__(self) -> None:
        self.ml_client = MLModelClient()
        self.remote_home_dir: Optional[str] = None
        self.remote_data_dir: Optional[str] = None
        self.remote_script_path: Optional[str] = None
        self.remote_model_path: Optional[str] = None
        self._path_initialized = False

    # ───────────────── 경로/체크포인트 해석 ─────────────────

    def _initialize_remote_paths(self, ssh) -> None:
        if self._path_initialized:
            return

        default_home = f"/home/{self.ml_client.final_user or settings.ml_server_final_user or 'humandeep'}"
        remote_home = default_home
        try:
            stdin, stdout, _ = ssh.exec_command("echo $HOME", timeout=5)
            if stdout.channel.recv_exit_status() == 0:
                detected = stdout.read().decode().strip()
                if detected:
                    remote_home = detected
        except Exception:
            logger.warning("Failed to detect remote HOME, falling back to %s", default_home)

        self.remote_home_dir = remote_home
        self.remote_data_dir = f"{remote_home}/data-qc/uploads"
        self.remote_script_path = f"{remote_home}/nmf/mochi_code/{self.SCRIPT_FILENAME}"
        self.remote_model_path = settings.ml_model_path or f"{remote_home}/nmf"
        self._path_initialized = True
        logger.info(
            "AI validation remote paths — home=%s, data_dir=%s, script=%s, model=%s",
            self.remote_home_dir, self.remote_data_dir, self.remote_script_path, self.remote_model_path,
        )

    def _resolve_remote_checkpoint(self, ssh) -> str:
        """디렉토리/파일 모두 지원: 최종 .ckpt 절대경로 반환"""
        configured = (self.remote_model_path or "").strip()
        quoted = shlex.quote(configured)

        # 이미 파일이면 그대로 사용
        stdin, stdout, _ = ssh.exec_command(
            f"bash -l -c 'if [ -f {quoted} ]; then echo FILE; fi'", timeout=5,
        )
        stdout.channel.recv_exit_status()
        if stdout.read().decode().strip() == "FILE":
            return configured

        candidates = [
            f"{configured}/tri_best.ckpt",
            f"{configured}/results/tri_joint_v2/tri_best.ckpt",
            f"{configured}/mochi_code/results/tri_joint_v2/tri_best.ckpt",
            f"{self.remote_home_dir}/nmf/mochi_code/results/tri_joint_v2/tri_best.ckpt",
        ]
        for c in dict.fromkeys(candidates):
            q = shlex.quote(c)
            stdin, stdout, _ = ssh.exec_command(
                f"bash -l -c 'if [ -f {q} ]; then echo {q}; fi'", timeout=5,
            )
            stdout.channel.recv_exit_status()
            resolved = stdout.read().decode().strip()
            if resolved:
                return resolved

        raise RuntimeError(
            "Could not resolve MOCHI checkpoint on remote server. "
            f"Configured ML_MODEL_PATH={configured}."
        )

    # ───────────────── Python 환경 탐색 ─────────────────

    def _find_python_with_torch(self, ssh) -> Tuple[Optional[str], Optional[str]]:
        """원격에서 torch 가 사용 가능한 python 실행파일 또는 conda activation 명령을 찾는다."""
        python_candidates = [
            f"{self.remote_home_dir}/anaconda3/envs/mochi/bin/python",
            f"{self.remote_home_dir}/anaconda3/envs/torch/bin/python",
            f"{self.remote_home_dir}/anaconda3/envs/pytorch/bin/python",
            f"{self.remote_home_dir}/anaconda3/bin/python",
            f"{self.remote_home_dir}/miniconda3/envs/mochi/bin/python",
            f"{self.remote_home_dir}/miniconda3/bin/python",
            f"{self.remote_home_dir}/venv/bin/python",
            "/usr/bin/python3",
        ]
        for py in python_candidates:
            cmd = f"bash -l -c '{py} -c \"import torch\" 2>&1 && echo __OK__'"
            stdin, stdout, _ = ssh.exec_command(cmd, timeout=10)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0 and "__OK__" in stdout.read().decode():
                logger.info("AI validation will use python: %s", py)
                return py, None

        # conda activation 시도
        conda_acts = [
            f"source {self.remote_home_dir}/anaconda3/etc/profile.d/conda.sh && conda activate mochi",
            f"source {self.remote_home_dir}/miniconda3/etc/profile.d/conda.sh && conda activate mochi",
            "source ~/.bashrc && conda activate mochi",
        ]
        for act in conda_acts:
            cmd = f"bash -l -c '{act} && python -c \"import torch\" 2>&1 && echo __OK__'"
            stdin, stdout, _ = ssh.exec_command(cmd, timeout=10)
            if stdout.channel.recv_exit_status() == 0 and "__OK__" in stdout.read().decode():
                logger.info("AI validation will activate conda env via: %s", act)
                return "python", act

        return None, None

    # ───────────────── 원격 스크립트 ─────────────────

    def _deploy_remote_script(self, ssh) -> None:
        """매 호출마다 최신 스크립트를 SFTP 로 배포 (idempotent overwrite)"""
        sftp = ssh.open_sftp()
        try:
            mochi_code_dir = str(Path(self.remote_script_path).parent)
            script_content = _REMOTE_SCRIPT.replace("__MOCHI_CODE_DIR__", mochi_code_dir)
            with sftp.file(self.remote_script_path, "w") as f:
                f.write(script_content)
            sftp.chmod(self.remote_script_path, 0o755)
            logger.info("Deployed AI validation script to %s", self.remote_script_path)
        finally:
            sftp.close()

    # ───────────────── 메인 진입점 ─────────────────

    def execute(self, project_id: int, job_id: str, local_data_dir: Path) -> Dict[str, Any]:
        """
        원격 MOCHI 모델로 사용자 데이터에 cross-prediction 일관성 검증을 수행하고
        Pearson/RMSE/MAE 지표를 dict 로 반환한다.

        반환 dict 스키마는 ValidationJob.results 로 저장될 수 있도록 한 곳에서
        프론트엔드 `rule_results` 와 호환되는 평탄한 형태를 유지한다.
        """
        from app.services.remote_multiomics_service import (  # noqa: WPS433
            RemoteMultiOmicsImputationService,
        )

        upload_helper = RemoteMultiOmicsImputationService()
        # 데이터 업로드는 기존 서비스 재사용 (raw/ 디렉토리 동일 사용)
        ok, msg = upload_helper.upload_data_files(project_id, local_data_dir)
        if not ok:
            raise RuntimeError(f"Data upload to remote failed: {msg}")

        ssh = self.ml_client._connect_via_jump_server()
        try:
            self._initialize_remote_paths(ssh)
            checkpoint = self._resolve_remote_checkpoint(ssh)
            self._deploy_remote_script(ssh)

            python_cmd, activation = self._find_python_with_torch(ssh)
            if not python_cmd:
                raise RuntimeError(
                    "원격 서버에서 PyTorch 가 설치된 Python 환경을 찾지 못했습니다."
                )

            remote_project_dir = f"{self.remote_data_dir}/project_{project_id}"
            script_cmd = (
                f"cd {Path(self.remote_script_path).parent} && "
                f"{python_cmd} {self.SCRIPT_FILENAME} "
                f"--project_id {project_id} "
                f"--data_dir {shlex.quote(self.remote_data_dir)} "
                f"--job_id {job_id} "
                f"--checkpoint {shlex.quote(checkpoint)}"
            )
            command = (
                f"bash -l -c '{activation} && {script_cmd}'"
                if activation
                else f"bash -l -c '{script_cmd}'"
            )
            logger.info("Running AI validation: %s", script_cmd)

            stdin, stdout, stderr = ssh.exec_command(command, timeout=1800)  # 최대 30분
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if exit_status != 0:
                raise RuntimeError(
                    f"Remote AI validation failed (exit={exit_status}). stderr={err[-2000:]}"
                )
            logger.info("AI validation stdout (last 500 chars): %s", out[-500:])

            # 결과 JSON 가져오기
            result_path = f"{remote_project_dir}/validation/{job_id}_ai_consistency.json"
            sftp = ssh.open_sftp()
            try:
                with sftp.file(result_path, "r") as f:
                    payload = json.loads(f.read().decode("utf-8"))
            finally:
                sftp.close()
            return payload
        finally:
            ssh.close()


# ───────────────────── 원격 실행 스크립트 본문 ─────────────────────
# __MOCHI_CODE_DIR__ 는 deploy 시점에 실제 경로로 치환됩니다.
_REMOTE_SCRIPT = '''#!/usr/bin/env python3
"""
MOCHI Cross-Prediction Consistency Validator (원격 실행)

원격 서버에서 사용자의 RNA/Protein/Methyl 데이터를 MOCHI tri-joint 모델로
교차 예측한 뒤, 관측치와의 Pearson/RMSE/MAE 를 계산해 JSON 으로 반환합니다.

- 학습 체크포인트와 입력 차원이 다르면 load_state_dict 가 즉시 RuntimeError
  를 던집니다 (silent failure 방지).
- 결과는 project_<id>/validation/<job_id>_ai_consistency.json 으로 저장됩니다.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.append("__MOCHI_CODE_DIR__")
from models import Generator  # noqa: E402


def _build_generator(input_size, output_size, target_type, device):
    return Generator(
        input_size=input_size,
        output_size=output_size,
        use_attn=True, n_heads=4, d_head=64,
        target_type=target_type,
        src_size=input_size,
    ).to(device).eval()


def _read_omics(path: Path) -> pd.DataFrame:
    delim = "\\t" if path.suffix.lower() == ".tsv" else ","
    return pd.read_csv(path, sep=delim, index_col=0)


def _detect_files(raw_dir: Path):
    rna_file = protein_file = methyl_file = None
    for f in list(raw_dir.glob("*.tsv")) + list(raw_dir.glob("*.csv")):
        name = f.name.lower()
        if any(k in name for k in ("rna", "transcriptom", "expression")):
            rna_file = rna_file or f
        elif any(k in name for k in ("protein", "proteom")):
            protein_file = protein_file or f
        elif any(k in name for k in ("methy", "dna", "genomic")):
            methyl_file = methyl_file or f
    return rna_file, protein_file, methyl_file


@torch.no_grad()
def _predict(model, src_tensor):
    return model(src_tensor, src=None).cpu().numpy()


def _metric_pair(observed: np.ndarray, predicted: np.ndarray):
    """
    관측-예측 일치도 (Pearson / RMSE / MAE).
    NaN 위치는 제외하고 평탄화한 1D 비교.
    """
    obs = observed.reshape(-1)
    pred = predicted.reshape(-1)
    mask = np.isfinite(obs) & np.isfinite(pred)
    if mask.sum() < 3:
        return {"pearson": None, "rmse": None, "mae": None, "n": int(mask.sum())}
    obs = obs[mask]; pred = pred[mask]
    obs_centered = obs - obs.mean()
    pred_centered = pred - pred.mean()
    denom = (np.linalg.norm(obs_centered) * np.linalg.norm(pred_centered))
    pearson = float(obs_centered @ pred_centered / denom) if denom else None
    rmse = float(np.sqrt(np.mean((obs - pred) ** 2)))
    mae = float(np.mean(np.abs(obs - pred)))
    return {"pearson": pearson, "rmse": rmse, "mae": mae, "n": int(mask.sum())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_id", type=int, required=True)
    parser.add_argument("--data_dir", type=str, required=True)
    parser.add_argument("--job_id", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, required=True)
    args = parser.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    project_dir = Path(args.data_dir) / f"project_{args.project_id}"
    raw_dir = project_dir / "raw"

    rna_file, protein_file, methyl_file = _detect_files(raw_dir)
    if not (rna_file and protein_file and methyl_file):
        raise RuntimeError(
            "AI 일관성 검증에는 RNA / Protein / Methyl 세 오믹스 파일이 모두 필요합니다. "
            f"발견: rna={rna_file}, protein={protein_file}, methyl={methyl_file}"
        )

    rna_df = _read_omics(rna_file)
    protein_df = _read_omics(protein_file)
    methyl_df = _read_omics(methyl_file)

    common = sorted(set(rna_df.columns) & set(protein_df.columns) & set(methyl_df.columns))
    if len(common) < 3:
        raise RuntimeError(f"세 오믹스 모두에 공통인 샘플이 부족합니다 (n={len(common)})")

    rna_aligned = rna_df[common]
    protein_aligned = protein_df[common]
    methyl_aligned = methyl_df[common]

    rna_mask = rna_aligned.isna(); protein_mask = protein_aligned.isna(); methyl_mask = methyl_aligned.isna()
    rna_filled = rna_aligned.fillna(0).values.T.astype(np.float32)
    protein_filled = protein_aligned.fillna(0).values.T.astype(np.float32)
    methyl_filled = methyl_aligned.fillna(0).values.T.astype(np.float32)

    rna_t = torch.tensor(rna_filled, dtype=torch.float32, device=device)
    protein_t = torch.tensor(protein_filled, dtype=torch.float32, device=device)
    methyl_t = torch.tensor(methyl_filled, dtype=torch.float32, device=device)

    dim_rna = rna_aligned.shape[0]
    dim_protein = protein_aligned.shape[0]
    dim_methyl = methyl_aligned.shape[0]

    # 모델 로드 — 차원 불일치는 load_state_dict 에서 RuntimeError
    ckpt = torch.load(args.checkpoint, map_location=device)
    Gp = _build_generator(dim_rna + dim_methyl, dim_protein, "protein", device)
    Gr = _build_generator(dim_protein + dim_methyl, dim_rna, "rna", device)
    Gm = _build_generator(dim_rna + dim_protein, dim_methyl, "methyl", device)
    try:
        Gp.load_state_dict(ckpt["Gp"])
        Gr.load_state_dict(ckpt["Gr"])
        Gm.load_state_dict(ckpt["Gm"])
    except RuntimeError as e:
        raise RuntimeError(
            f"체크포인트 차원이 입력 데이터와 호환되지 않습니다 "
            f"(rna={dim_rna}, protein={dim_protein}, methyl={dim_methyl}). {e}"
        )

    pred_protein = _predict(Gp, torch.cat([rna_t, methyl_t], dim=-1))
    pred_rna = _predict(Gr, torch.cat([protein_t, methyl_t], dim=-1))
    pred_methyl = _predict(Gm, torch.cat([rna_t, protein_t], dim=-1))

    # 관측값(NaN 제외)과 예측값을 비교. 학습/원리상 "결측이 아닌 위치"에서의
    # 일치도를 일관성으로 본다 — 결측 위치는 정답이 없어 비교 불가.
    rna_obs = rna_aligned.values.T  # [n_samples, n_features]
    protein_obs = protein_aligned.values.T
    methyl_obs = methyl_aligned.values.T

    # NaN 위치는 그대로 두고 _metric_pair 에서 mask 처리
    metrics_rna = _metric_pair(rna_obs, pred_rna)
    metrics_protein = _metric_pair(protein_obs, pred_protein)
    metrics_methyl = _metric_pair(methyl_obs, pred_methyl)

    overall_pearson = [
        m["pearson"] for m in (metrics_rna, metrics_protein, metrics_methyl)
        if m["pearson"] is not None
    ]
    overall = (sum(overall_pearson) / len(overall_pearson)) if overall_pearson else None

    output_dir = project_dir / "validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{args.job_id}_ai_consistency.json"

    result_payload = {
        "device": str(device),
        "dimensions": {"rna": dim_rna, "protein": dim_protein, "methyl": dim_methyl},
        "common_samples": len(common),
        "per_modality": {
            "rna": metrics_rna,
            "protein": metrics_protein,
            "methyl": metrics_methyl,
        },
        "overall_pearson": overall,
        "files": {
            "rna": rna_file.name,
            "protein": protein_file.name,
            "methyl": methyl_file.name,
        },
    }

    # NaN/Inf → None (JSON 안전)
    def _safe(o):
        if isinstance(o, float) and not math.isfinite(o):
            return None
        if isinstance(o, dict):
            return {k: _safe(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_safe(v) for v in o]
        return o

    with open(out_path, "w") as f:
        json.dump(_safe(result_payload), f, indent=2, ensure_ascii=False)
    print(f"[ai_validate] wrote {out_path}")


if __name__ == "__main__":
    main()
'''
