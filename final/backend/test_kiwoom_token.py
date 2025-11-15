#!/usr/bin/env python3
"""
Kiwoom API 토큰 연결 테스트 스크립트
"""
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.kiwoom_client import KiwoomClient

async def test_kiwoom_connection():
    """Kiwoom API 연결 테스트"""
    print("=" * 60)
    print("Kiwoom API 토큰 연결 테스트")
    print("=" * 60)
    
    # 환경변수 확인
    token = os.getenv("KIWOOM_ACCESS_TOKEN", "")
    base_url = os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com")
    
    print(f"\n[환경변수 확인]")
    print(f"KIWOOM_BASE_URL: {base_url}")
    if token:
        print(f"KIWOOM_ACCESS_TOKEN: {token[:10]}... (길이: {len(token)})")
    else:
        print("KIWOOM_ACCESS_TOKEN: (설정되지 않음)")
        print("\n⚠️  경고: KIWOOM_ACCESS_TOKEN이 설정되지 않았습니다!")
        print("   .env 파일에 KIWOOM_ACCESS_TOKEN을 설정하거나")
        print("   환경변수로 설정해주세요.")
        return False
    
    # KiwoomClient 초기화
    print(f"\n[KiwoomClient 초기화]")
    client = KiwoomClient()
    
    # 테스트 종목 코드 (삼성전자)
    test_symbol = "005930"
    print(f"\n[API 호출 테스트]")
    print(f"종목 코드: {test_symbol} (삼성전자)")
    
    try:
        print("API 호출 중...")
        result = await client.ka10001(test_symbol)
        
        # 응답 확인
        if result:
            print("✅ API 호출 성공!")
            print(f"\n[응답 데이터]")
            
            # 주요 필드 확인
            if isinstance(result, dict):
                return_code = result.get("return_code", "N/A")
                return_msg = result.get("return_msg", "N/A")
                cur_prc = result.get("cur_prc", "N/A")
                
                print(f"  return_code: {return_code}")
                print(f"  return_msg: {return_msg}")
                print(f"  cur_prc (현재가): {cur_prc}")
                
                if return_code == 0 or return_code == "0":
                    print("\n✅ 토큰이 정상적으로 연결되어 있습니다!")
                    if cur_prc and cur_prc != "N/A":
                        print(f"✅ 주가 데이터도 정상적으로 받아왔습니다: {cur_prc}원")
                    return True
                else:
                    print(f"\n⚠️  API 호출은 되었지만 오류가 발생했습니다:")
                    print(f"   return_code: {return_code}")
                    print(f"   return_msg: {return_msg}")
                    return False
            else:
                print(f"⚠️  응답 형식이 예상과 다릅니다: {type(result)}")
                print(f"   응답: {result}")
                return False
        else:
            print("⚠️  API 응답이 비어있습니다.")
            return False
            
    except Exception as exc:
        print(f"\n❌ API 호출 실패:")
        print(f"   오류 타입: {type(exc).__name__}")
        print(f"   오류 메시지: {str(exc)}")
        
        # 자세한 오류 정보
        if hasattr(exc, 'response'):
            print(f"\n[HTTP 응답 정보]")
            print(f"   Status Code: {exc.response.status_code if hasattr(exc.response, 'status_code') else 'N/A'}")
            if hasattr(exc.response, 'text'):
                print(f"   Response Text: {exc.response.text[:200]}")
        
        print("\n가능한 원인:")
        print("  1. 토큰이 유효하지 않거나 만료됨")
        print("  2. 네트워크 연결 문제")
        print("  3. API 서버 문제")
        print("  4. 토큰 권한 부족")
        return False
    finally:
        await client.close()

if __name__ == "__main__":
    # .env 파일 로드 (있는 경우)
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일을 로드했습니다: {env_path}")
    else:
        print(f"ℹ️  .env 파일을 찾을 수 없습니다: {env_path}")
        print("   환경변수에서 직접 읽습니다.")
    
    # 비동기 테스트 실행
    result = asyncio.run(test_kiwoom_connection())
    
    print("\n" + "=" * 60)
    if result:
        print("✅ 테스트 완료: 토큰이 정상적으로 연결되어 있습니다!")
    else:
        print("❌ 테스트 실패: 토큰 연결에 문제가 있습니다.")
    print("=" * 60)
    
    sys.exit(0 if result else 1)

