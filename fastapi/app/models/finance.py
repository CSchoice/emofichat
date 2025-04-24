from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Float, String

Base = declarative_base()

class FinanceMetric(Base):
    """
    개인별 핵심 재무 지표 테이블 (샘플)
    """
    __tablename__ = "finance_metric"

    user_id:      Mapped[str]   = mapped_column(String(32), primary_key=True)
    liquidity:    Mapped[float] = mapped_column(Float)     # 유동성 점수
    stress:       Mapped[float] = mapped_column(Float)     # 스트레스 인덱스
    debt_ratio:   Mapped[float] = mapped_column(Float)
    credit_usage: Mapped[float] = mapped_column(Float)
    # …필요 컬럼 추가

    def __repr__(self):
        return f"<FinanceMetric {self.user_id}>"
