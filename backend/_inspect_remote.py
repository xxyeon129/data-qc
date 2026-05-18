"""
일회성 진단 스크립트 — 원격 ML 서버(MOCHI)의 소스 코드/구조를 로컬로 가져옵니다.

목적:
  1) /home/humandeep/nmf 디렉토리 구조 트리(파일 크기 포함) 캡처
  2) mochi_code/ 아래 .py / .md / .txt / .yaml / .yml / requirements*.txt 등을
     로컬 .cache/remote_mochi/ 에 그대로 복사
  3) GPU·PyTorch 버전 같은 기본 환경 정보 캡처

원격 자격증명은 backend/.env 의 ML_SERVER_* 값을 그대로 사용합니다.
출력에 자격증명은 절대 포함하지 않습니다.

실행:
  cd backend
  source venv/bin/activate
  python _inspect_remote.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# backend 디렉토리를 import 경로에 추가
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ml_model_client import MLModelClient  # noqa: E402

WORKSPACE_ROOT = BACKEND_DIR.parent
LOCAL_DUMP = WORKSPACE_ROOT / ".cache" / "remote_mochi"
LOCAL_DUMP.mkdir(parents=True, exist_ok=True)

REMOTE_BASE = "/home/humandeep/nmf"
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".cfg", ".ini", ".sh", ".json"}
MAX_BYTES_PER_FILE = 2_000_000  # 2MB 이상 텍스트는 truncate (안전장치)


def _run(ssh, cmd: str, timeout: int = 20) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return exit_status, out, err


def capture_tree(ssh) -> None:
    """원격 디렉토리 구조 + 파일 크기 캡처"""
    cmd_tree = (
        f"bash -l -c '"
        f"find {REMOTE_BASE} -maxdepth 6 -type f "
        f"\\( -name \"*.py\" -o -name \"*.md\" -o -name \"*.txt\" "
        f"-o -name \"*.yaml\" -o -name \"*.yml\" -o -name \"*.ckpt\" "
        f"-o -name \"*.pt\" -o -name \"*.pth\" -o -name \"*.json\" "
        f"-o -name \"*.sh\" -o -name \"*.cfg\" -o -name \"*.ini\" \\) "
        f"-printf \"%s\\t%p\\n\" 2>/dev/null | sort -k2 "
        f"'"
    )
    code, out, err = _run(ssh, cmd_tree, timeout=30)
    (LOCAL_DUMP / "_TREE.txt").write_text(out, encoding="utf-8")
    print(f"[tree] captured {len(out.splitlines())} entries (exit={code})")
    if err.strip():
        print(f"[tree] stderr (suppressed length={len(err)})")


def capture_environment(ssh) -> None:
    """기본 환경 정보(hostname, python, torch, gpu) 캡처"""
    checks = [
        ("hostname", "hostname"),
        ("uname", "uname -a"),
        ("which_python", "bash -l -c 'which python3 python || true'"),
        ("python_version", "bash -l -c 'python3 --version || true'"),
        ("conda_envs", "bash -l -c 'conda env list 2>/dev/null || true'"),
        ("nvidia_smi", "bash -l -c 'nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>/dev/null || true'"),
        ("torch_versions", "bash -l -c '"
                           "for p in $(ls -d /home/humandeep/anaconda3/envs/*/bin/python 2>/dev/null) "
                           "/home/humandeep/anaconda3/bin/python /home/humandeep/miniconda3/bin/python "
                           "/usr/bin/python3; do "
                           "if [ -x \"$p\" ]; then printf \"%s\\t\" \"$p\"; "
                           "\"$p\" -c \"import torch; print(torch.__version__, torch.cuda.is_available())\" 2>&1; "
                           "fi; done'"),
    ]
    lines: list[str] = []
    for label, cmd in checks:
        code, out, err = _run(ssh, cmd, timeout=15)
        lines.append(f"### {label}  (exit={code})\n{out.strip()}\n")
    (LOCAL_DUMP / "_ENV.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"[env] captured {len(checks)} info items")


def fetch_text_files(ssh) -> None:
    """텍스트 소스 파일을 로컬에 복사 (재귀적, 안전 제한)"""
    sftp = ssh.open_sftp()

    # tree 결과를 다시 읽어 파일 목록 추출
    tree_path = LOCAL_DUMP / "_TREE.txt"
    if not tree_path.exists():
        print("[fetch] _TREE.txt missing, skipping fetch")
        return

    fetched = 0
    skipped_binary = 0
    skipped_large = 0
    for line in tree_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            size_str, remote_path = line.split("\t", 1)
            size = int(size_str)
        except ValueError:
            continue

        suffix = Path(remote_path).suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            skipped_binary += 1
            continue
        if size > MAX_BYTES_PER_FILE:
            skipped_large += 1
            continue

        # 원격 절대경로 → 로컬 상대경로
        rel = Path(remote_path).relative_to(REMOTE_BASE)
        local_target = LOCAL_DUMP / rel
        local_target.parent.mkdir(parents=True, exist_ok=True)

        try:
            sftp.get(remote_path, str(local_target))
            fetched += 1
        except Exception as e:
            print(f"[fetch] failed: {remote_path} → {e}")

    sftp.close()
    print(f"[fetch] copied={fetched}, skipped_binary={skipped_binary}, skipped_large={skipped_large}")


def main() -> int:
    print(f"[main] dump dir: {LOCAL_DUMP}")
    client = MLModelClient()

    ssh = client._connect_via_jump_server()
    try:
        print("[main] SSH connected via jump server")
        capture_environment(ssh)
        capture_tree(ssh)
        fetch_text_files(ssh)
    finally:
        ssh.close()
        print("[main] SSH closed")

    print("[main] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
