#!/usr/bin/env python3
"""
데이터베이스 테이블 재생성 스크립트
기존 테이블을 삭제하고 새로 생성합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from app.models.base import Base

if __name__ == "__main__":
    print("=" * 60)
    print("GENE-Q Database Table Recreation")
    print("=" * 60)
    print()
    
    # 기존 테이블 삭제
    print("⚠️  Dropping all existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped successfully!")
    print()
    
    # 테이블 재생성
    print("Creating new database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    print()
    
    print("=" * 60)
    print("Table recreation completed!")
    print("Now you can run: python init_database.py")
    print("=" * 60)

