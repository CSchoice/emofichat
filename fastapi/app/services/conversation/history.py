"""
대화 이력 관리

사용자와의 대화 이력을 저장하고 조회합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)

# 최대 이력 수
MAX_HISTORY = 10

class ConversationHistory:
    """대화 이력 관리 클래스"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        self.memory_cache = {}  # 메모리 캐시 (DB 없을 경우 사용)
        
    async def save_history(self, user_id: str, user_message: str, system_message: str) -> bool:
        """
        대화 이력 저장
        
        Args:
            user_id: 사용자 ID
            user_message: 사용자 메시지
            system_message: 시스템 응답
            
        Returns:
            저장 성공 여부
        """
        try:
            # 저장할 데이터 구성
            history_item = {
                "user_id": user_id,
                "timestamp": datetime.now(),
                "user_message": user_message,
                "system_message": system_message
            }
            
            # DB 연결이 있는 경우 DB에 저장
            if self.db:
                await self.db.conversation_history.insert_one(history_item)
                logger.debug(f"대화 이력 DB 저장 완료: {user_id}")
                return True
            else:
                # DB 연결이 없는 경우 메모리 캐시에 저장
                if user_id not in self.memory_cache:
                    self.memory_cache[user_id] = []
                
                # 최대 이력 수 제한
                if len(self.memory_cache[user_id]) >= MAX_HISTORY:
                    self.memory_cache[user_id].pop(0)  # 가장 오래된 이력 제거
                
                self.memory_cache[user_id].append((user_message, system_message))
                logger.info(f"대화 이력 메모리 저장 완료: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"대화 이력 저장 실패: {str(e)}")
            return False
            
    async def load_history(self, user_id: str, limit: int = MAX_HISTORY) -> List[Tuple[str, str]]:
        """
        대화 이력 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 최대 이력 수
            
        Returns:
            대화 이력 목록 [(사용자 메시지, 시스템 응답), ...]
        """
        try:
            # DB 연결이 있는 경우 DB에서 조회
            if self.db:
                cursor = self.db.conversation_history.find(
                    {"user_id": user_id},
                    sort=[("timestamp", -1)],
                    limit=limit
                )
                
                history = []
                async for doc in cursor:
                    history.append((doc["user_message"], doc["system_message"]))
                
                # 시간순으로 정렬 (오래된 순)
                history.reverse()
                return history
            else:
                # DB 연결이 없는 경우 메모리 캐시에서 조회
                return self.memory_cache.get(user_id, [])[-limit:]
                
        except Exception as e:
            logger.error(f"대화 이력 조회 실패: {str(e)}")
            return []
            
    async def clear_history(self, user_id: str) -> bool:
        """
        대화 이력 삭제
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            삭제 성공 여부
        """
        try:
            # DB 연결이 있는 경우 DB에서 삭제
            if self.db:
                result = await self.db.conversation_history.delete_many({"user_id": user_id})
                logger.info(f"대화 이력 DB 삭제 완료: {user_id}, {result.deleted_count}건")
                return result.acknowledged
            else:
                # DB 연결이 없는 경우 메모리 캐시에서 삭제
                if user_id in self.memory_cache:
                    del self.memory_cache[user_id]
                    logger.info(f"대화 이력 메모리 삭제 완료: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"대화 이력 삭제 실패: {str(e)}")
            return False
            
    async def get_summary(self, user_id: str, max_length: int = 5) -> str:
        """
        대화 이력 요약
        
        Args:
            user_id: 사용자 ID
            max_length: 요약할 대화 수
            
        Returns:
            대화 이력 요약 문자열
        """
        history = await self.load_history(user_id, limit=max_length)
        
        if not history:
            return ""
            
        # 대화 이력 요약
        summary_lines = []
        for i, (user_msg, system_msg) in enumerate(history):
            # 사용자 메시지 요약 (최대 30자)
            user_summary = user_msg[:30] + "..." if len(user_msg) > 30 else user_msg
            
            # 시스템 응답 요약 (최대 30자)
            system_summary = system_msg[:30] + "..." if len(system_msg) > 30 else system_msg
            
            summary_lines.append(f"대화 {i+1}: Q[{user_summary}] / A[{system_summary}]")
            
        return "\n".join(summary_lines)

# 싱글톤 인스턴스
_history_manager = None

def get_history_manager(db_client=None) -> ConversationHistory:
    """대화 이력 관리자 싱글톤 인스턴스 반환"""
    global _history_manager
    if _history_manager is None:
        _history_manager = ConversationHistory(db_client)
    return _history_manager

# 기존 코드와의 호환성을 위한 함수들
async def save_history(user_id: str, user_message: str, system_message: str) -> bool:
    """대화 이력 저장 (호환성 함수)"""
    history_manager = get_history_manager()
    return await history_manager.save_history(user_id, user_message, system_message)
    
async def load_history(user_id: str, limit: int = MAX_HISTORY) -> List[Tuple[str, str]]:
    """대화 이력 조회 (호환성 함수)"""
    history_manager = get_history_manager()
    return await history_manager.load_history(user_id, limit)
