import subprocess
import sys
import json

def check_docker_status():
    """도커 컨테이너 상태 및 네트워크 확인"""
    
    print("===== 도커 컨테이너 상태 확인 =====")
    try:
        # 실행 중인 모든 컨테이너 확인
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("실행 중인 컨테이너:")
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("실행 중인 컨테이너가 없습니다.")
            
        # mysql_emofinance 컨테이너 자세히 확인
        print("\n===== MySQL 컨테이너 상세 정보 =====")
        try:
            inspect_result = subprocess.run(
                ["docker", "inspect", "mysql_emofinance"],
                capture_output=True,
                text=True,
                check=True
            )
            
            container_info = json.loads(inspect_result.stdout)[0]
            
            # 네트워크 정보
            networks = container_info.get("NetworkSettings", {}).get("Networks", {})
            print("네트워크 정보:")
            for network_name, network_config in networks.items():
                print(f"  네트워크: {network_name}")
                print(f"  IP 주소: {network_config.get('IPAddress', 'N/A')}")
            
            # 포트 매핑
            ports = container_info.get("NetworkSettings", {}).get("Ports", {})
            print("\n포트 매핑:")
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    for binding in host_bindings:
                        print(f"  컨테이너 {container_port} -> 호스트 {binding.get('HostIp', '0.0.0.0')}:{binding.get('HostPort', 'N/A')}")
                else:
                    print(f"  컨테이너 {container_port} -> 매핑 없음")
            
            # 상태 정보
            state = container_info.get("State", {})
            print(f"\n상태: {state.get('Status', 'N/A')}")
            print(f"실행 중: {state.get('Running', False)}")
            
            if not state.get("Running", False):
                print(f"오류 메시지: {state.get('Error', 'N/A')}")
                
        except subprocess.CalledProcessError:
            print("MySQL 컨테이너 정보를 가져올 수 없습니다.")
            
        # 네트워크 확인 - 호스트에서 MySQL 포트 접속 가능 여부
        print("\n===== MySQL 포트 연결 테스트 =====")
        import socket
        
        host = 'localhost'
        port = 5432
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((host, port))
            print(f"✅ {host}:{port}로 연결 성공!")
            s.close()
        except Exception as e:
            print(f"❌ {host}:{port}로 연결 실패: {e}")
        
    except subprocess.CalledProcessError as e:
        print(f"도커 명령 실행 중 오류: {e}")
        print(f"오류 출력: {e.stderr}")

if __name__ == "__main__":
    check_docker_status()
