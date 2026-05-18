"""
Remote Multi-Omics Imputation Service
SSH를 통해 원격 서버에서 MOCHI 모델을 실행하는 서비스
"""

import logging
import json
import shlex
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from app.services.ml_model_client import MLModelClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class RemoteMultiOmicsImputationService:
    """SSH를 통해 원격 서버에서 멀티오믹스 보간을 수행하는 서비스"""
    
    def __init__(self):
        self.ml_client = MLModelClient()
        self.remote_home_dir: Optional[str] = None
        self.remote_data_dir: Optional[str] = None
        self.remote_script_path: Optional[str] = None
        self.remote_model_path: Optional[str] = None
        self._path_initialized = False

    def _initialize_remote_paths(self, ssh) -> None:
        """원격 서버의 HOME 기반으로 실행 경로를 동적 초기화"""
        if self._path_initialized:
            return

        default_home = f"/home/{self.ml_client.final_user or settings.ml_server_final_user or 'humandeep'}"
        remote_home = default_home

        try:
            stdin, stdout, stderr = ssh.exec_command("echo $HOME", timeout=5)
            if stdout.channel.recv_exit_status() == 0:
                detected_home = stdout.read().decode().strip()
                if detected_home:
                    remote_home = detected_home
        except Exception:
            logger.warning("Failed to detect remote HOME, using fallback path")

        model_path = settings.ml_model_path or f"{remote_home}/nmf/mochi_code/results/tri_joint_v2/tri_best.ckpt"
        script_path = f"{remote_home}/nmf/mochi_code/impute_multiomics.py"
        data_dir = f"{remote_home}/data-qc/uploads"

        self.remote_home_dir = remote_home
        self.remote_data_dir = data_dir
        self.remote_script_path = script_path
        self.remote_model_path = model_path
        self._path_initialized = True

        logger.info(
            "Initialized remote paths - home: %s, data_dir: %s, script_path: %s, model_path: %s",
            self.remote_home_dir,
            self.remote_data_dir,
            self.remote_script_path,
            self.remote_model_path,
        )

    def _resolve_remote_model_checkpoint(self, ssh) -> str:
        """체크포인트 경로를 원격 서버에서 검증/보정하여 실제 파일 경로를 반환"""
        if not self.remote_model_path:
            raise RuntimeError("Remote model path is not initialized")

        configured_path = self.remote_model_path.strip()
        quoted_path = shlex.quote(configured_path)

        # 1) 설정값이 이미 파일 경로인 경우 그대로 사용
        stdin, stdout, stderr = ssh.exec_command(
            f"bash -l -c 'if [ -f {quoted_path} ]; then echo FILE; fi'",
            timeout=5,
        )
        stdout.channel.recv_exit_status()
        if stdout.read().decode().strip() == "FILE":
            return configured_path

        # 2) 설정값이 디렉토리인 경우 대표 체크포인트를 우선 검색
        stdin, stdout, stderr = ssh.exec_command(
            f"bash -l -c 'if [ -d {quoted_path} ]; then echo DIR; fi'",
            timeout=5,
        )
        stdout.channel.recv_exit_status()
        is_directory = stdout.read().decode().strip() == "DIR"

        candidates = []
        if is_directory:
            candidates.extend([
                f"{configured_path}/tri_best.ckpt",
                f"{configured_path}/results/tri_joint_v2/tri_best.ckpt",
                f"{configured_path}/mochi_code/results/tri_joint_v2/tri_best.ckpt",
            ])

        # 3) 기본 후보들 (원격 HOME 기준)
        candidates.extend([
            f"{self.remote_home_dir}/nmf/mochi_code/results/tri_joint_v2/tri_best.ckpt",
            f"{self.remote_home_dir}/nmf/mochi_code/results/tri_joint_v2/tri_final.ckpt",
        ])

        # 중복 제거
        unique_candidates = []
        seen = set()
        for candidate in candidates:
            if candidate not in seen:
                unique_candidates.append(candidate)
                seen.add(candidate)

        for candidate in unique_candidates:
            quoted_candidate = shlex.quote(candidate)
            stdin, stdout, stderr = ssh.exec_command(
                f"bash -l -c 'if [ -f {quoted_candidate} ]; then echo {quoted_candidate}; fi'",
                timeout=5,
            )
            stdout.channel.recv_exit_status()
            resolved = stdout.read().decode().strip()
            if resolved:
                if configured_path != resolved:
                    logger.warning(
                        "Configured ML_MODEL_PATH is not a checkpoint file (%s). Using resolved checkpoint: %s",
                        configured_path,
                        resolved,
                    )
                self.remote_model_path = resolved
                return resolved

        raise RuntimeError(
            "Could not resolve checkpoint file on remote server. "
            f"Configured ML_MODEL_PATH={configured_path}. "
            "Please set ML_MODEL_PATH to a .ckpt file path."
        )
    
    def check_connection(self) -> bool:
        """원격 서버 연결 확인"""
        try:
            return self.ml_client.check_connection()
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def check_remote_environment(self) -> Dict[str, Any]:
        """
        원격 서버의 Python 환경 확인
        
        Returns:
            환경 정보 딕셔너리
        """
        try:
            ssh = self.ml_client._connect_via_jump_server()
            self._initialize_remote_paths(ssh)
            
            env_info = {
                "connection": "success",
                "python_environments": [],
                "conda_environments": [],
                "torch_available": False,
                "recommended_python": None,
                "conda_installed": False,
                "system_info": {}
            }
            
            # 시스템 정보 확인
            stdin, stdout, stderr = ssh.exec_command("hostname && whoami && pwd", timeout=5)
            stdout.channel.recv_exit_status()
            env_info["system_info"]["output"] = stdout.read().decode().strip()
            
            # conda 설치 확인
            conda_check_commands = [
                "bash -l -c 'which conda'",
                "bash -l -c 'command -v conda'",
                f"ls -la {self.remote_home_dir}/anaconda3/bin/conda",
                f"ls -la {self.remote_home_dir}/miniconda3/bin/conda"
            ]
            
            for cmd in conda_check_commands:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
                if stdout.channel.recv_exit_status() == 0:
                    conda_path = stdout.read().decode().strip()
                    if conda_path:
                        env_info["conda_installed"] = True
                        env_info["conda_path"] = conda_path
                        break
            
            # conda 환경 목록 확인
            if env_info["conda_installed"]:
                conda_env_commands = [
                    "bash -l -c 'conda env list'",
                    f"bash -l -c 'source {self.remote_home_dir}/anaconda3/bin/activate && conda env list'",
                    f"bash -l -c 'source {self.remote_home_dir}/miniconda3/bin/activate && conda env list'",
                    f"{self.remote_home_dir}/anaconda3/bin/conda env list",
                    f"{self.remote_home_dir}/miniconda3/bin/conda env list"
                ]
                
                for cmd in conda_env_commands:
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                    if stdout.channel.recv_exit_status() == 0:
                        env_list = stdout.read().decode().strip()
                        env_info["conda_environments_raw"] = env_list
                        # 환경 이름 파싱
                        for line in env_list.split('\n'):
                            if line.strip() and not line.startswith('#') and '*' not in line[:5]:
                                parts = line.split()
                                if len(parts) >= 1:
                                    env_info["conda_environments"].append(parts[0])
                        break
            
            # 여러 Python 경로 확인
            python_paths = [
                f"{self.remote_home_dir}/anaconda3/envs/mochi/bin/python",
                f"{self.remote_home_dir}/anaconda3/envs/torch/bin/python",
                f"{self.remote_home_dir}/anaconda3/envs/pytorch/bin/python",
                f"{self.remote_home_dir}/anaconda3/bin/python",
                f"{self.remote_home_dir}/miniconda3/envs/mochi/bin/python",
                f"{self.remote_home_dir}/miniconda3/bin/python",
                f"{self.remote_home_dir}/venv/bin/python",
                "/usr/local/bin/python3",
                "/usr/bin/python3",
                "/usr/bin/python"
            ]
            
            for py_path in python_paths:
                # Python 버전 확인
                cmd = f"bash -l -c '{py_path} --version' 2>&1"
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    version = stdout.read().decode().strip()
                    
                    # torch 설치 여부 확인
                    torch_cmd = f"bash -l -c '{py_path} -c \"import torch; print(torch.__version__)\"' 2>&1"
                    stdin, stdout, stderr = ssh.exec_command(torch_cmd, timeout=5)
                    torch_status = stdout.channel.recv_exit_status()
                    
                    env = {
                        "path": py_path,
                        "version": version,
                        "torch_available": torch_status == 0
                    }
                    
                    if torch_status == 0:
                        torch_version = stdout.read().decode().strip()
                        env["torch_version"] = torch_version
                        env_info["torch_available"] = True
                        if not env_info["recommended_python"]:
                            env_info["recommended_python"] = py_path
                    else:
                        # 에러 메시지도 저장
                        error_msg = stdout.read().decode().strip()
                        if error_msg:
                            env["torch_error"] = error_msg
                    
                    env_info["python_environments"].append(env)
            
            # 직접 which python으로도 확인
            stdin, stdout, stderr = ssh.exec_command("bash -l -c 'which python python3 2>&1'", timeout=5)
            stdout.channel.recv_exit_status()
            env_info["which_python"] = stdout.read().decode().strip()
            
            ssh.close()
            return env_info
            
        except Exception as e:
            logger.error(f"Failed to check remote environment: {e}")
            import traceback
            return {
                "connection": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def upload_data_files(
        self, 
        project_id: int, 
        local_data_dir: Path
    ) -> Tuple[bool, str]:
        """
        로컬의 데이터 파일들을 원격 서버로 업로드
        
        Args:
            project_id: 프로젝트 ID
            local_data_dir: 로컬 데이터 디렉토리 경로
            
        Returns:
            (성공 여부, 메시지)
        """
        try:
            ssh = self.ml_client._connect_via_jump_server()
            self._initialize_remote_paths(ssh)
            sftp = ssh.open_sftp()
            
            # 원격 디렉토리 생성
            remote_project_dir = f"{self.remote_data_dir}/project_{project_id}"
            remote_raw_dir = f"{remote_project_dir}/raw"
            
            # 디렉토리 생성 (존재하지 않는 경우)
            try:
                sftp.stat(remote_project_dir)
            except FileNotFoundError:
                ssh.exec_command(f"mkdir -p {remote_raw_dir}")
                logger.info(f"Created remote directory: {remote_raw_dir}")
            
            # 로컬 프로젝트 디렉토리
            local_project_dir = local_data_dir / f"project_{project_id}" / "raw"
            
            if not local_project_dir.exists():
                return False, f"Local project directory not found: {local_project_dir}"
            
            # TSV/CSV 파일들 업로드 (methylation 등 CSV 포함)
            data_files = list(local_project_dir.glob("*.tsv")) + list(
                local_project_dir.glob("*.csv")
            )
            if not data_files:
                return False, f"No TSV/CSV files found in {local_project_dir}"

            uploaded_files = []
            for local_file in data_files:
                remote_file = f"{remote_raw_dir}/{local_file.name}"
                logger.info(f"Uploading {local_file.name}...")
                sftp.put(str(local_file), remote_file)
                uploaded_files.append(local_file.name)
                logger.info(f"✓ Uploaded: {local_file.name}")
            
            sftp.close()
            ssh.close()
            
            return True, f"Successfully uploaded {len(uploaded_files)} files: {', '.join(uploaded_files)}"
            
        except Exception as e:
            logger.error(f"Failed to upload data files: {e}")
            return False, f"Upload failed: {str(e)}"
    
    def execute_remote_imputation(
        self,
        project_id: int,
        job_id: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        원격 서버에서 멀티오믹스 보간 실행
        
        Args:
            project_id: 프로젝트 ID
            job_id: 작업 ID
            
        Returns:
            (성공 여부, 메시지, 통계 정보)
        """
        try:
            ssh = self.ml_client._connect_via_jump_server()
            self._initialize_remote_paths(ssh)
            
            # 보간 스크립트가 없으면 생성
            self._create_imputation_script(ssh)
            resolved_checkpoint = self._resolve_remote_model_checkpoint(ssh)
            
            # 원격 서버에서 보간 실행
            # 먼저 사용 가능한 Python 환경을 찾기
            remote_data_path = f"{self.remote_data_dir}/project_{project_id}"
            
            # 여러 가능한 Python 경로 시도
            python_paths = [
                f"{self.remote_home_dir}/anaconda3/envs/mochi/bin/python",
                f"{self.remote_home_dir}/anaconda3/envs/torch/bin/python",
                f"{self.remote_home_dir}/anaconda3/envs/pytorch/bin/python",
                f"{self.remote_home_dir}/anaconda3/bin/python",
                f"{self.remote_home_dir}/miniconda3/envs/mochi/bin/python",
                f"{self.remote_home_dir}/miniconda3/bin/python",
                f"{self.remote_home_dir}/venv/bin/python",
                "python3",
                "python"
            ]
            
            # 사용 가능한 Python 찾기 (bash login shell 사용)
            python_cmd = None
            activation_cmd = None
            
            # 1단계: 절대 경로로 Python 시도
            for py_path in python_paths:
                check_cmd = f"bash -l -c '{py_path} -c \"import torch; print(torch.__version__)\" 2>&1'"
                stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=10)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    python_cmd = py_path
                    output = stdout.read().decode().strip()
                    logger.info(f"✓ Found Python with torch {output}: {py_path}")
                    break
            
            # 2단계: conda/virtualenv 활성화 시도
            if not python_cmd:
                logger.info("Trying conda environment activation...")
                conda_activations = [
                    f"source {self.remote_home_dir}/anaconda3/etc/profile.d/conda.sh && conda activate mochi",
                    f"source {self.remote_home_dir}/miniconda3/etc/profile.d/conda.sh && conda activate mochi",
                    f"source {self.remote_home_dir}/anaconda3/bin/activate && conda activate mochi",
                    "source ~/.bashrc && conda activate mochi",
                ]
                
                for activation in conda_activations:
                    check_cmd = f"bash -l -c '{activation} && python -c \"import torch; print(torch.__version__)\" 2>&1'"
                    stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=10)
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status == 0:
                        activation_cmd = activation
                        python_cmd = "python"
                        output = stdout.read().decode().strip()
                        logger.info(f"✓ Found Python via conda activation: {output}")
                        break
            
            if not python_cmd:
                ssh.close()
                return False, "Could not find Python environment with PyTorch on remote server. Please ensure PyTorch is installed in a conda/venv environment.", None
            
            # 명령어 생성 (bash login shell 사용)
            script_cmd = (
                f"cd {Path(self.remote_script_path).parent} && "
                f"{python_cmd} impute_multiomics.py "
                f"--project_id {project_id} "
                f"--data_dir {self.remote_data_dir} "
                f"--job_id {job_id} "
                f"--checkpoint {shlex.quote(resolved_checkpoint)}"
            )
            
            if activation_cmd:
                command = f"bash -l -c '{activation_cmd} && {script_cmd}'"
            else:
                command = f"bash -l -c '{script_cmd}'"
            
            logger.info(f"Executing remote command: {command}")
            stdin, stdout, stderr = ssh.exec_command(command, timeout=600)  # 10분 타임아웃
            
            # 실행 결과 대기
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            logger.info(f"Command output: {output}")
            if error:
                logger.warning(f"Command stderr: {error}")
            
            if exit_status != 0:
                ssh.close()
                return False, f"Remote execution failed (exit code {exit_status}): {error}", None
            
            # 결과 통계 파일 읽기
            result_json_path = f"{remote_data_path}/imputed/{job_id}_statistics.json"
            try:
                sftp = ssh.open_sftp()
                with sftp.file(result_json_path, 'r') as f:
                    statistics = json.loads(f.read().decode())
                sftp.close()
            except Exception as e:
                logger.warning(f"Failed to read statistics file: {e}")
                statistics = None
            
            ssh.close()
            
            return True, "Remote imputation completed successfully", statistics
            
        except Exception as e:
            logger.error(f"Failed to execute remote imputation: {e}")
            return False, f"Remote execution error: {str(e)}", None
    
    def download_results(
        self,
        project_id: int,
        job_id: str,
        local_output_dir: Path
    ) -> Tuple[bool, str, Dict[str, Path]]:
        """
        원격 서버에서 보간 결과 파일들을 다운로드
        
        Args:
            project_id: 프로젝트 ID
            job_id: 작업 ID
            local_output_dir: 로컬 출력 디렉토리
            
        Returns:
            (성공 여부, 메시지, 파일 경로 딕셔너리)
        """
        try:
            ssh = self.ml_client._connect_via_jump_server()
            self._initialize_remote_paths(ssh)
            sftp = ssh.open_sftp()
            
            # 로컬 출력 디렉토리 생성
            local_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 원격 결과 디렉토리
            remote_result_dir = f"{self.remote_data_dir}/project_{project_id}/imputed"
            
            # 다운로드할 파일 목록
            result_files = {
                'rna': f"{job_id}_rna_imputed.tsv",
                'protein': f"{job_id}_protein_imputed.tsv",
                'methyl': f"{job_id}_methyl_imputed.tsv",
            }
            
            downloaded_files = {}
            
            for omics_type, filename in result_files.items():
                remote_file = f"{remote_result_dir}/{filename}"
                local_file = local_output_dir / filename
                
                try:
                    logger.info(f"Downloading {filename}...")
                    sftp.get(remote_file, str(local_file))
                    downloaded_files[omics_type] = local_file
                    logger.info(f"✓ Downloaded: {filename}")
                except FileNotFoundError:
                    logger.warning(f"Remote file not found: {remote_file}")
            
            sftp.close()
            ssh.close()
            
            if len(downloaded_files) == 0:
                return False, "No result files found on remote server", {}
            
            return True, f"Successfully downloaded {len(downloaded_files)} files", downloaded_files
            
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return False, f"Download failed: {str(e)}", {}
    
    def _create_imputation_script(self, ssh):
        """
        원격 서버에 보간 실행 스크립트 생성 (없는 경우)

        스크립트는 입력 데이터의 실제 shape 를 사용하여 MOCHI Generator 를 초기화하며,
        checkpoint 의 차원과 불일치하면 명확히 에러로 실패합니다(기존 하드코딩 제거).
        """
        script_content = '''#!/usr/bin/env python3
"""
Multi-Omics Imputation Script for Remote Execution
원격 서버에서 MOCHI 모델을 사용하여 멀티오믹스 보간 수행

차원(dim_rna/dim_protein/dim_methyl) 은 입력 파일에서 동적으로 결정합니다.
checkpoint 의 가중치 차원과 일치하지 않으면 RuntimeError 로 즉시 실패합니다.
"""

import sys
import argparse
import json
import torch
import numpy as np
import pandas as pd
from pathlib import Path
import logging

sys.path.append("__MOCHI_CODE_DIR__")
from models import Generator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _build_generator(input_size, output_size, target_type, device):
    return Generator(
        input_size=input_size,
        output_size=output_size,
        use_attn=True, n_heads=4, d_head=64,
        target_type=target_type,
        src_size=input_size,
    ).to(device)


def load_model(checkpoint_path, dim_rna, dim_protein, dim_methyl, device):
    """MOCHI 모델 로드 (차원은 데이터로부터 주입)"""
    logger.info(f"Loading model from {checkpoint_path}")
    logger.info(f"Dimensions: rna={dim_rna}, protein={dim_protein}, methyl={dim_methyl}")
    ckpt = torch.load(checkpoint_path, map_location=device)

    Gp = _build_generator(dim_rna + dim_methyl, dim_protein, "protein", device)
    Gr = _build_generator(dim_protein + dim_methyl, dim_rna, "rna", device)
    Gm = _build_generator(dim_rna + dim_protein, dim_methyl, "methyl", device)

    try:
        Gp.load_state_dict(ckpt["Gp"])
        Gr.load_state_dict(ckpt["Gr"])
        Gm.load_state_dict(ckpt["Gm"])
    except RuntimeError as e:
        raise RuntimeError(
            f"Checkpoint dimension mismatch — input data shape "
            f"(rna={dim_rna}, protein={dim_protein}, methyl={dim_methyl}) "
            f"is incompatible with the trained MOCHI weights. {e}"
        )

    Gp.eval(); Gr.eval(); Gm.eval()
    logger.info("Model loaded successfully")
    return Gp, Gr, Gm


def load_data(project_dir):
    """데이터 로드 — TSV / CSV 모두 지원, 파일명 키워드로 RNA/Protein/Methyl 분류"""
    raw_dir = project_dir / "raw"
    files = list(raw_dir.glob("*.tsv")) + list(raw_dir.glob("*.csv"))

    def _read(path):
        delim = "\\t" if path.suffix.lower() == ".tsv" else ","
        return pd.read_csv(path, sep=delim, index_col=0)

    rna_file = protein_file = methyl_file = None
    for f in files:
        name = f.name.lower()
        if any(k in name for k in ("rna", "transcriptom", "expression")):
            rna_file = f
        elif any(k in name for k in ("protein", "proteom")):
            protein_file = f
        elif any(k in name for k in ("methy", "dna", "genomic")):
            methyl_file = f

    if not (rna_file and protein_file and methyl_file):
        raise RuntimeError(
            f"MOCHI requires three omics files (rna/protein/methyl). "
            f"Found: rna={rna_file}, protein={protein_file}, methyl={methyl_file}"
        )

    logger.info(f"Loading RNA from {rna_file}")
    rna_df = _read(rna_file)
    logger.info(f"Loading Protein from {protein_file}")
    protein_df = _read(protein_file)
    logger.info(f"Loading Methyl from {methyl_file}")
    methyl_df = _read(methyl_file)

    return rna_df, protein_df, methyl_df


@torch.no_grad()
def impute_data(rna_df, protein_df, methyl_df, Gp, Gr, Gm, device):
    """데이터 보간 수행"""
    # 공통 샘플
    common_samples = sorted(
        set(rna_df.columns) & set(protein_df.columns) & set(methyl_df.columns)
    )
    logger.info(f"Found {len(common_samples)} common samples")
    
    rna_aligned = rna_df[common_samples]
    protein_aligned = protein_df[common_samples]
    methyl_aligned = methyl_df[common_samples]
    
    # 결측치 마스크
    rna_mask = rna_aligned.isna()
    protein_mask = protein_aligned.isna()
    methyl_mask = methyl_aligned.isna()
    
    # 0으로 채움
    rna_filled = rna_aligned.fillna(0).values.T.astype(np.float32)
    protein_filled = protein_aligned.fillna(0).values.T.astype(np.float32)
    methyl_filled = methyl_aligned.fillna(0).values.T.astype(np.float32)
    
    # Tensor 변환
    rna_t = torch.tensor(rna_filled, dtype=torch.float32, device=device)
    protein_t = torch.tensor(protein_filled, dtype=torch.float32, device=device)
    methyl_t = torch.tensor(methyl_filled, dtype=torch.float32, device=device)
    
    # 예측
    logger.info("Predicting protein...")
    pred_protein = Gp(torch.cat([rna_t, methyl_t], dim=-1), src=None).cpu().numpy()
    
    logger.info("Predicting RNA...")
    pred_rna = Gr(torch.cat([protein_t, methyl_t], dim=-1), src=None).cpu().numpy()
    
    logger.info("Predicting methyl...")
    pred_methyl = Gm(torch.cat([rna_t, protein_t], dim=-1), src=None).cpu().numpy()
    
    # 결측치 채우기
    rna_imputed = rna_aligned.copy()
    protein_imputed = protein_aligned.copy()
    methyl_imputed = methyl_aligned.copy()
    
    rna_mask_T = rna_mask.values.T
    protein_mask_T = protein_mask.values.T
    methyl_mask_T = methyl_mask.values.T
    
    for i, sample in enumerate(common_samples):
        if rna_mask_T[i].any():
            rna_imputed.loc[rna_mask_T[i], sample] = pred_rna[i, rna_mask_T[i]]
        if protein_mask_T[i].any():
            protein_imputed.loc[protein_mask_T[i], sample] = pred_protein[i, protein_mask_T[i]]
        if methyl_mask_T[i].any():
            methyl_imputed.loc[methyl_mask_T[i], sample] = pred_methyl[i, methyl_mask_T[i]]
    
    statistics = {
        'rna_missing_before': int(rna_mask.sum().sum()),
        'protein_missing_before': int(protein_mask.sum().sum()),
        'methyl_missing_before': int(methyl_mask.sum().sum()),
        'rna_missing_after': int(rna_imputed.isna().sum().sum()),
        'protein_missing_after': int(protein_imputed.isna().sum().sum()),
        'methyl_missing_after': int(methyl_imputed.isna().sum().sum()),
        'total_samples': len(common_samples)
    }
    
    return rna_imputed, protein_imputed, methyl_imputed, statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_id', type=int, required=True)
    parser.add_argument('--data_dir', type=str, required=True)
    parser.add_argument('--job_id', type=str, required=True)
    parser.add_argument('--checkpoint', type=str, required=True)
    args = parser.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # 데이터 로드 (모델보다 먼저 — 차원 결정 필요)
    project_dir = Path(args.data_dir) / f"project_{args.project_id}"
    rna_df, protein_df, methyl_df = load_data(project_dir)

    # 입력 데이터에서 차원 동적 추출 (행=feature, 열=sample 가정)
    dim_rna = rna_df.shape[0]
    dim_protein = protein_df.shape[0]
    dim_methyl = methyl_df.shape[0]

    Gp, Gr, Gm = load_model(
        args.checkpoint, dim_rna, dim_protein, dim_methyl, device,
    )
    
    # 보간 수행
    logger.info("Starting imputation...")
    rna_imputed, protein_imputed, methyl_imputed, statistics = impute_data(
        rna_df, protein_df, methyl_df, Gp, Gr, Gm, device
    )
    
    # 결과 저장
    output_dir = project_dir / "imputed"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rna_output = output_dir / f"{args.job_id}_rna_imputed.tsv"
    protein_output = output_dir / f"{args.job_id}_protein_imputed.tsv"
    methyl_output = output_dir / f"{args.job_id}_methyl_imputed.tsv"
    stats_output = output_dir / f"{args.job_id}_statistics.json"
    
    logger.info(f"Saving results to {output_dir}")
    rna_imputed.to_csv(rna_output, sep="\\t")
    protein_imputed.to_csv(protein_output, sep="\\t")
    methyl_imputed.to_csv(methyl_output, sep="\\t")
    
    with open(stats_output, 'w') as f:
        json.dump(statistics, f, indent=2)
    
    logger.info("Imputation completed successfully!")
    logger.info(f"Statistics: {statistics}")


if __name__ == "__main__":
    main()
'''
        script_content = script_content.replace("__MOCHI_CODE_DIR__", str(Path(self.remote_script_path).parent))
        
        try:
            sftp = ssh.open_sftp()
            
            # 스크립트가 이미 존재하는지 확인
            try:
                sftp.stat(self.remote_script_path)
                logger.info("Imputation script already exists on remote server")
                sftp.close()
                return
            except FileNotFoundError:
                pass
            
            # 스크립트 생성
            logger.info(f"Creating imputation script at {self.remote_script_path}")
            with sftp.file(self.remote_script_path, 'w') as f:
                f.write(script_content)
            
            # 실행 권한 부여
            sftp.chmod(self.remote_script_path, 0o755)
            sftp.close()
            
            logger.info("✓ Imputation script created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create imputation script: {e}")
            raise


