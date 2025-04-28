"""
감정 분석 모델 파일 복사 스크립트

model.safetensors, config.json, training_args.bin 파일을 
감정 분석 모델 디렉토리로 복사합니다.
"""

import os
import shutil
from pathlib import Path
import argparse

def copy_model_files(source_dir, target_dir=None):
    """
    모델 파일들을 지정된 대상 디렉토리로 복사합니다.
    
    Args:
        source_dir: 모델 파일이 있는 소스 디렉토리
        target_dir: 파일을 복사할 대상 디렉토리 (기본값: app/models/emotion)
    """
    # 소스 디렉토리 확인
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"오류: 소스 디렉토리를 찾을 수 없습니다: {source_path}")
        return False
    
    # 대상 디렉토리 설정
    if target_dir is None:
        script_dir = Path(__file__).parent
        target_path = script_dir / "app" / "models" / "emotion"
    else:
        target_path = Path(target_dir)
    
    # 대상 디렉토리 확인 및 생성
    if not target_path.exists():
        os.makedirs(target_path, exist_ok=True)
        print(f"대상 디렉토리를 생성했습니다: {target_path}")
    
    # 필요한 파일 목록
    required_files = ["model.safetensors", "config.json", "training_args.bin"]
    
    # 파일 복사
    copied_files = []
    for filename in required_files:
        source_file = source_path / filename
        if source_file.exists():
            target_file = target_path / filename
            shutil.copy2(source_file, target_file)
            copied_files.append(filename)
            print(f"파일을 복사했습니다: {filename}")
        else:
            print(f"경고: 소스 디렉토리에서 {filename} 파일을 찾을 수 없습니다.")
    
    # 선택적 파일 복사 (토크나이저 등)
    optional_files = ["tokenizer.json", "vocab.txt", "special_tokens_map.json", 
                     "tokenizer_config.json"]
    
    for filename in optional_files:
        source_file = source_path / filename
        if source_file.exists():
            target_file = target_path / filename
            shutil.copy2(source_file, target_file)
            copied_files.append(filename)
            print(f"선택적 파일을 복사했습니다: {filename}")
    
    # 결과 보고
    if all(f in copied_files for f in required_files):
        print(f"\n성공: 모든 필수 모델 파일을 {target_path}로 복사했습니다.")
        return True
    else:
        print("\n경고: 일부 필수 파일이 복사되지 않았습니다.")
        print(f"복사된 파일: {', '.join(copied_files)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="감정 분석 모델 파일 복사 도구")
    parser.add_argument("source_dir", help="모델 파일이 있는 소스 디렉토리 경로")
    parser.add_argument("-t", "--target-dir", help="파일을 복사할 대상 디렉토리 경로")
    
    args = parser.parse_args()
    copy_model_files(args.source_dir, args.target_dir)

if __name__ == "__main__":
    main()
