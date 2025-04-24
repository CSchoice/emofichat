import logging
import sys
from pathlib import Path
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    """애플리케이션 로깅 설정
    
    - 콘솔 출력
    - 파일 로깅 (로테이션)
    - 로그 레벨: 개발(DEBUG) / 운영(INFO)
    """
    root_logger = logging.getLogger()
    
    # 이미 핸들러가 설정되어 있으면 중복 방지
    if root_logger.handlers:
        return
    
    # 로그 레벨 설정
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level)
    root_logger.setLevel(log_level)
    
    # 포맷 설정
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 콘솔 핸들러 (에러는 stderr로)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 (로테이션)
    logs_dir = Path(__file__).resolve().parents[3] / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 민감 정보 필터 (개인정보 보호)
    class PiiFilter(logging.Filter):
        def filter(self, record):
            # 민감 정보가 포함된 메시지 필터링
            sensitive_patterns = ["password", "card", "주민", "계좌", "번호"]
            for pattern in sensitive_patterns:
                if pattern in str(record.msg).lower():
                    # 민감 정보 마스킹 (실제 환경에서는 더 정교한 정규식 필요)
                    record.msg = str(record.msg).replace(pattern, "***")
            return True
    
    # 필터 적용
    pii_filter = PiiFilter()
    console_handler.addFilter(pii_filter)
    file_handler.addFilter(pii_filter)
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    root_logger.debug("로깅 시스템 초기화 완료")
