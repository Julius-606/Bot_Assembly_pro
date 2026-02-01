import os
import json
import streamlit as st
from dotenv import load_dotenv

# 🔐 THE HYBRID LOADER
# Sniffs for .env locally. Streamlit Cloud ignores this and uses its own Secrets.
load_dotenv(override=True)

def get_secret(key, default=None):
    """Hybrid getter: Checks Streamlit Secrets first (Cloud), then Environment (Local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return os.getenv(key, default)

# ==============================================================================
# ---- Darwin Backtest Lab Config ----
# ==============================================================================

MT5_LOGIN_RAW = get_secret("MT5_LOGIN", "0")
MT5_LOGIN = int(MT5_LOGIN_RAW) if str(MT5_LOGIN_RAW).isdigit() else 0

MT5_PASSWORD = get_secret("MT5_PASSWORD")
MT5_SERVER = get_secret("MT5_SERVER")
MT5_PATH = get_secret("MT5_PATH")

SHEET_URL = get_secret("GOOGLE_SHEET_URL")

# --- SIMULATION CONSTANTS ---
HARDCODED_LOT_SIZE = 0.01
CONTRACT_SIZE = 100000 

# --- GOOGLE CREDS (Now hardcoded inside the app) ---
# No cap, we put the keys directly in the engine now. 🚀
GOOGLE_CREDS_DICT = {
    "type": "service_account",
    "project_id": "mt5-algo-bot-logger",
    "private_key_id": "204abac9e2fe692a4d0542ec0cf3940d8141fb6c",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDeJXo05nj5XHsy\nh7Z4kicOxbnk0N+OeKeE4Y2NuAAq9P5qWjMX7sTxwAQj8aAwu5FkjB2zOstihJJH\nou2iYKGpedLPdunYK5FpgT3smM0T4g1XHrnCfY5wxJih1YaUD/zGZlxzLQEN5E+h\nLObmpzbONYOxym99YUDDe7Ip5xfFcTwR6svwpkcGG8lqfM/lc/cSrcR/2z35q8ZV\nJN6uD89uBB3jBPJa+Z5n/xpGY5NoE1cQQpJVBviN8E+zNRzqVc5jWo5fUtUDQibB\nA/ZJxKxeMLw7lu0UZUoay7X7FsirqIkCSpAuylAN2kXYUV8p6xVof0VaOnJZ4cj4\naDqpfYlXAgMBAAECggEAEnFoGPY9eu5rqAFOa+ouZfKSgWW5+bkYp1aWivqIwQhA\nCxJcBZOkNDHt5hIMa59W7dMYMCYkdpRtFJd5RS7inRBpKSJFPdY4J1s8ieURuaHd\n26rIX1ZPOhuIVH9GwgolwU8EQ+erm7ylw8rXjLS7PxmASoV1BiLJ3rDpVMND3Pdn\nFImFmt1MGg/t+Az+1tZwlQ2GyYdzfLLDp0avQSDkSA9pbNdqeWPp+IfC1s+VfoCl\npyPjukC6iFjLO4zy7wMmc8XZy6y+7SFChN1OALpI/Jyq6Bzqr6u7Zd7Noz2CloL+\nvWEct+PPfgAhqEoTsZBkjojpM1tntHXupO9axUQMiQKBgQD4n416ggVvwrOLKW6p\n4vmADEJEQaqnyVSq45ifYzuSaRAuZ6VnoXIAd8ym24Suaj9vwBju4Saae5OkMxfu\nEETWR+X0S/8hExChEAPUdMZfiHfWsNvrUbdmjF5YPI7kA5MO48uMQ1j20UKJpQhf\nG0kKTl9p5ukll8nF7gLmlV/qFQKBgQDkvNEOCcHfJpxrnIXBVIVQU5/H/eh1PyY0\nnQ2oRSENUA8zpU1pqFaS3E6162RQf0GR+WBpPrAyvCaU/od+XlIEiDiiGKpLQeks\n8u0VRKE/klDMGRzVaVu8bef0fbBRP1KhY25/ALtLIWpZC7p8bXto1FO4Dl3P8LzS\n3hMZPJZcuwKBgBO996oGsQ/S0hb2z0bGMzGrx4dL/5UbM5HuSKw/YPebSCGnMUct\nVrQazzFgtQR0g10IT/KIBly1+19Kf1f0CsNJKkVf03542RUxBFzWePoVCA8QNCZX\ncsy90LAI/v+0GPVRuVQF9QaET1hGtod2zzH2TzVFlLXbe7Yv1CMjMV6RAoGAbqEH\n92MuulABXWaxpmTLqaMYZ3Ddij+FqfK/1T/CEZ9ECvWLMGvzm0okY4Y62VgDDafw\nQlbIf3FSs8M7IxpZTsnXokaNrqJtNYk0s5Gi741DuML4mBtB/CuoAS79JP6cZ2Qg\n4Bope9foiLLMeju1cWkoKKACLX1AxjgUQqN0EdsCgYBMQT5c0Exv8nt6ZY5LzK3d\ncfZ3e1yC1n/XGkZk58njNx1V93XXLr5ECUAzk1++Mq/fuhtibq49CEYZ2cUkcYNd\nDTOlUoiDtjIKNrhYtDTYfxLxs3u3f1mN6550dAjVwnZTpR270TCNaWqYpY3HwCQ1\nrA6xE2a/MenoqHGBkagX2w==\n-----END PRIVATE KEY-----\n",
    "client_email": "mt5-logger-sa@mt5-algo-bot-logger.iam.gserviceaccount.com",
    "client_id": "101479527830343877881",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mt5-logger-sa%40mt5-algo-bot-logger.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# 💎 THE MARKET LIST
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "LTCUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDNZD"
]