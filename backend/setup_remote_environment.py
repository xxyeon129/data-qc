#!/usr/bin/env python3
"""
원격 서버 환경 진단 및 설정 스크립트
Remote Server Environment Diagnostic and Setup Script
"""

import sys
sys.path.insert(0, '/Users/bstore/Downloads/04_test/gene/backend')

from app.services.ml_model_client import MLModelClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_remote_commands(ssh, commands, description=""):
    """원격 서버에서 명령어 실행"""
    if description:
        print(f"\n{'='*60}")
        print(f"{description}")
        print(f"{'='*60}")
    
    for cmd in commands:
        print(f"\n$ {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(output)
        if error and exit_status != 0:
            print(f"ERROR: {error}")
        print(f"Exit code: {exit_status}")


def main():
    print("=" * 80)
    print("원격 서버 환경 진단 도구")
    print("Remote Server Environment Diagnostic Tool")
    print("=" * 80)
    
    client = MLModelClient()
    
    try:
        print("\n1. 원격 서버에 연결 중...")
        ssh = client._connect_via_jump_server()
        print("✓ 연결 성공!")
        
        # 기본 시스템 정보
        run_remote_commands(ssh, [
            "hostname",
            "whoami",
            "pwd",
            "uname -a",
            "cat /etc/os-release | head -5"
        ], "시스템 정보")
        
        # Python 관련
        run_remote_commands(ssh, [
            "bash -l -c 'which python python3 python2'",
            "bash -l -c 'python3 --version'",
            "bash -l -c 'python3 -m pip --version'",
            "bash -l -c 'python3 -m site'",
        ], "Python 정보")
        
        # Python 패키지 확인
        run_remote_commands(ssh, [
            "bash -l -c 'python3 -m pip list | grep -i torch'",
            "bash -l -c 'python3 -m pip list | grep -i numpy'",
            "bash -l -c 'python3 -m pip list | grep -i pandas'",
        ], "설치된 Python 패키지")
        
        # Conda 관련
        run_remote_commands(ssh, [
            "bash -l -c 'which conda'",
            "bash -l -c 'conda --version'",
            "bash -l -c 'conda env list'",
            "ls -la ~/anaconda3/bin/conda 2>&1 || echo 'anaconda3 not found'",
            "ls -la ~/miniconda3/bin/conda 2>&1 || echo 'miniconda3 not found'",
        ], "Conda 환경 정보")
        
        # 가상환경 확인
        run_remote_commands(ssh, [
            "ls -la ~/.local/lib/python*/site-packages/ 2>&1 | head -20",
            "ls -la ~/venv/ 2>&1 || echo 'venv not found'",
            "ls -la ~/.virtualenvs/ 2>&1 || echo 'virtualenvs not found'",
        ], "가상환경 확인")
        
        # 프로젝트 디렉토리 확인
        run_remote_commands(ssh, [
            "ls -la /home/humandeep/nmf/",
            "ls -la /home/humandeep/nmf/mochi_code/ 2>&1 | head -20",
            "ls -la /home/humandeep/nmf/mochi_code/models.py 2>&1",
            "ls -la /home/humandeep/nmf/mochi_code/results/tri_joint_v2/tri_best.ckpt 2>&1",
        ], "MOCHI 프로젝트 디렉토리")
        
        # 환경 변수
        run_remote_commands(ssh, [
            "bash -l -c 'echo $PATH'",
            "bash -l -c 'echo $PYTHONPATH'",
            "bash -l -c 'env | grep -i python'",
        ], "환경 변수")
        
        print("\n" + "="*80)
        print("진단 완료!")
        print("="*80)
        
        print("\n다음 단계:")
        print("1. 원격 서버에 PyTorch를 설치해야 합니다:")
        print("   $ ssh humandeep@192.9.203.83")
        print("   $ python3 -m pip install --user torch numpy pandas")
        print()
        print("2. 또는 conda 환경을 생성하여 설치:")
        print("   $ conda create -n mochi python=3.9")
        print("   $ conda activate mochi")
        print("   $ pip install torch numpy pandas")
        
        ssh.close()
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


