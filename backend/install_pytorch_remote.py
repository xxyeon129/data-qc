#!/usr/bin/env python3
"""
원격 서버에 PyTorch 자동 설치 스크립트
Auto Install PyTorch on Remote Server
"""

import sys
sys.path.insert(0, '/Users/bstore/Downloads/04_test/gene/backend')

from app.services.ml_model_client import MLModelClient
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def install_pytorch(ssh):
    """원격 서버에 PyTorch 설치"""
    print("\n" + "="*80)
    print("PyTorch 설치 시작...")
    print("="*80)
    
    # CPU 버전의 PyTorch 설치 (CUDA가 없는 경우)
    install_commands = [
        # 1. user site로 설치 (권한 문제 없음)
        "python3 -m pip install --user torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
    ]
    
    for cmd in install_commands:
        print(f"\n실행 중: {cmd}")
        print("-" * 80)
        
        stdin, stdout, stderr = ssh.exec_command(f"bash -l -c '{cmd}'", timeout=600)
        
        # 실시간 출력
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line.rstrip())
        
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error = stderr.read().decode('utf-8', errors='ignore')
            print(f"\n❌ 설치 실패 (exit code: {exit_status})")
            print(f"에러: {error}")
            return False
        
        print("\n✓ 설치 명령 완료")
    
    return True


def verify_installation(ssh):
    """설치 확인"""
    print("\n" + "="*80)
    print("설치 확인 중...")
    print("="*80)
    
    verify_commands = [
        ("PyTorch 버전", "python3 -c 'import torch; print(f\"PyTorch {torch.__version__}\")'"),
        ("CUDA 사용 가능 여부", "python3 -c 'import torch; print(f\"CUDA available: {torch.cuda.is_available()}\")'"),
        ("설치 위치", "python3 -c 'import torch; print(f\"Location: {torch.__file__}\")'"),
    ]
    
    all_passed = True
    
    for name, cmd in verify_commands:
        print(f"\n{name}:")
        stdin, stdout, stderr = ssh.exec_command(f"bash -l -c '{cmd}'", timeout=10)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            output = stdout.read().decode().strip()
            print(f"  ✓ {output}")
        else:
            error = stderr.read().decode().strip()
            print(f"  ❌ {error}")
            all_passed = False
    
    return all_passed


def main():
    print("=" * 80)
    print("원격 서버에 PyTorch 자동 설치")
    print("Auto Install PyTorch on Remote Server")
    print("=" * 80)
    
    client = MLModelClient()
    
    try:
        print("\n1. 원격 서버에 연결 중...")
        ssh = client._connect_via_jump_server()
        print("✓ 연결 성공!")
        
        # PyTorch 설치
        if install_pytorch(ssh):
            print("\n✅ PyTorch 설치 성공!")
            
            # 설치 확인
            time.sleep(2)  # 잠시 대기
            if verify_installation(ssh):
                print("\n" + "="*80)
                print("✅ 모든 검증 완료! PyTorch가 정상적으로 설치되었습니다.")
                print("="*80)
                print("\n이제 결측치 보간을 실행할 수 있습니다:")
                print("  curl -X POST 'http://localhost:8005/api/imputation/execute-multiomics?project_id=1'")
            else:
                print("\n⚠️ PyTorch 설치는 완료되었으나 일부 검증에 실패했습니다.")
                print("수동으로 확인이 필요할 수 있습니다.")
        else:
            print("\n❌ PyTorch 설치 실패")
            print("\n수동 설치 방법:")
            print("  1. SSH로 접속:")
            print("     ssh -J humandeep@210.102.178.234 humandeep@192.9.203.83")
            print("  2. PyTorch 설치:")
            print("     python3 -m pip install --user torch")
        
        ssh.close()
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


