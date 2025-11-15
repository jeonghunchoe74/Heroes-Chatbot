import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    BASE_NEWS_URL = "https://newsapi.org/v2/top-headlines"

settings = Settings()

