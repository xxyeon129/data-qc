from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging
import sys
from pathlib import Path
from urllib.parse import quote_plus

# backend/ 디렉토리 기준 업로드 경로 (로컬)
UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
  mysql_host: str = '127.0.0.1'
  mysql_port: int = 3306
  mysql_user: str = 'root'
  mysql_password: str = 'Mysql1234'
  mysql_db: str = 'data_qc'
  mysql_echo: bool = False
  
  # SSH 연결 타임아웃 (초)
  ssh_timeout: int = 30
  
  # ML 서버 SSH Jump Host 설정 (.env 파일에서 로드)
  ml_server_jump_host: Optional[str] = None
  ml_server_jump_port: int = 22
  ml_server_jump_user: Optional[str] = None
  ml_server_jump_password: Optional[str] = None
  
  # ML 서버 최종 호스트 설정 (.env 파일에서 로드)
  ml_server_final_host: Optional[str] = None
  ml_server_final_user: Optional[str] = None
  ml_server_final_password: Optional[str] = None
  
  # ML 모델 경로 (.env 파일에서 로드)
  ml_model_path: Optional[str] = None

  model_config = SettingsConfigDict(
    env_file=".env", 
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore"
  )
  
  @property
  def database_url(self):
    return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"

settings = Settings()

# MySQL 데이터베이스 설정 로깅
logger.info("=" * 60)
logger.info("MySQL Database Configuration")
logger.info("=" * 60)
logger.info(f"MYSQL_HOST: {settings.mysql_host}")
logger.info(f"MYSQL_PORT: {settings.mysql_port}")
logger.info(f"MYSQL_USER: {settings.mysql_user}")
logger.info(f"MYSQL_PASSWORD: {'***SET***' if settings.mysql_password else 'NOT SET'}")
logger.info(f"MYSQL_DB: {settings.mysql_db}")
logger.info(f"DATABASE_URL: mysql+pymysql://{settings.mysql_user}:***@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}")
logger.info("=" * 60)
logger.info("")

# ML 서버 설정 로깅
logger.info("=" * 60)
logger.info("ML Server Configuration Loaded from .env")
logger.info("=" * 60)
logger.info(f"ML_SERVER_JUMP_HOST: {settings.ml_server_jump_host or 'NOT SET'}")
logger.info(f"ML_SERVER_JUMP_PORT: {settings.ml_server_jump_port}")
logger.info(f"ML_SERVER_JUMP_USER: {settings.ml_server_jump_user or 'NOT SET'}")
logger.info(f"ML_SERVER_JUMP_PASSWORD: {'***SET***' if settings.ml_server_jump_password else 'NOT SET'}")
logger.info(f"ML_SERVER_FINAL_HOST: {settings.ml_server_final_host or 'NOT SET'}")
logger.info(f"ML_SERVER_FINAL_USER: {settings.ml_server_final_user or 'NOT SET'}")
logger.info(f"ML_SERVER_FINAL_PASSWORD: {'***SET***' if settings.ml_server_final_password else 'NOT SET'}")
logger.info(f"ML_MODEL_PATH: {settings.ml_model_path or 'NOT SET'}")
logger.info("=" * 60)

# 필수 설정값 체크
missing_configs = []
if not settings.ml_server_jump_host:
    missing_configs.append("ML_SERVER_JUMP_HOST")
if not settings.ml_server_jump_user:
    missing_configs.append("ML_SERVER_JUMP_USER")
if not settings.ml_server_jump_password:
    missing_configs.append("ML_SERVER_JUMP_PASSWORD")
if not settings.ml_server_final_host:
    missing_configs.append("ML_SERVER_FINAL_HOST")
if not settings.ml_server_final_user:
    missing_configs.append("ML_SERVER_FINAL_USER")
if not settings.ml_server_final_password:
    missing_configs.append("ML_SERVER_FINAL_PASSWORD")
if not settings.ml_model_path:
    missing_configs.append("ML_MODEL_PATH")

if missing_configs:
    logger.warning(f"⚠️  Missing ML server configurations: {', '.join(missing_configs)}")
    logger.warning("⚠️  Please set these values in your .env file")
else:
    logger.info("✅ All ML server configurations loaded successfully")