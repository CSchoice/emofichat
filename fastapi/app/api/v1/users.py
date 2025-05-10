"""
사용자 관리 API 엔드포인트

사용자 정보를 조회하고 관리하는 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, List, Any, Optional
import logging

from app.services.database.db_service import get_db_service
from app.models.database import User

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users", response_model=List[Dict[str, Any]])
async def list_users(request: Request, limit: int = 10):
    """
    데이터베이스에 있는 사용자 목록을 조회합니다.
    테스트 및 디버깅 용도로 사용됩니다.
    
    - **limit**: 조회할 최대 사용자 수
    """
    try:
        db_service = get_db_service()
        
        # 사용자 목록 조회
        users = await db_service.list_users(limit=limit)
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자가 없습니다."
            )
        
        # 응답 구성
        return [
            {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            } for user in users
        ]
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 목록을 조회하는 중 오류가 발생했습니다."
        )


@router.get("/users/any", response_model=Dict[str, Any])
async def get_any_user(request: Request):
    """
    데이터베이스에서 아무 사용자나 한 명 조회합니다.
    테스트 및 디버깅 용도로 사용됩니다.
    """
    try:
        db_service = get_db_service()
        
        # 사용자 조회
        user = await db_service.get_any_user()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자가 없습니다."
            )
        
        # 응답 구성
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
        
    except Exception as e:
        logger.error(f"사용자 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user(user_id: str, request: Request):
    """
    특정 사용자 정보를 조회합니다.
    
    - **user_id**: 사용자 ID
    """
    try:
        db_service = get_db_service()
        
        # 사용자 조회
        user = await db_service.get_or_create_user(user_id)
        
        # 응답 구성
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
        
    except Exception as e:
        logger.error(f"사용자 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자를 조회하는 중 오류가 발생했습니다."
        )
