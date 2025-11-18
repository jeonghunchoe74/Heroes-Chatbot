import os, requests, json

AUTH_URL = "https://api.kiwoom.com/oauth2/token"  # 모의투자면 mockapi로 교체
APP_KEY = "jKb_2kmu3pV9jLVxOEIktVbThmIZX6cvRHrB-zC9AdM"
SECRET_KEY = "jPWGvx2PQFPPHkgzrTsjyDYCrLw4FXaO3F3GpEfDML4"

payload = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "secretkey": SECRET_KEY,
}
r = requests.post(AUTH_URL, json=payload, headers={"Content-Type":"application/json;charset=UTF-8"}, timeout=15)
r.raise_for_status()
data = r.json()
print("RAW:", json.dumps(data, ensure_ascii=False))

token = data.get("token")
if not token:
    raise SystemExit("❌ token 필드가 없습니다. (응답/자격증명/URL 확인)")

print("\nTOKEN =", token[:60], "...")

# 현재 프로세스 환경변수에 주입(임시)
os.environ["KIWOOM_ACCESS_TOKEN"] = token
print("env set -> KIWOOM_ACCESS_TOKEN")