"""后端配置。"""

from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = ROOT


class Settings(BaseSettings):
    app_name: str = "茅台抢单管理 API"
    api_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    admin_username: str = "admin"
    admin_password: str = "admin123"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'admin.db'}"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    config_yaml: Path = ROOT / "config.yaml"

    # Android 应用内更新（见 deploy/.env.example）
    app_latest_version_code: int = 2
    app_latest_version_name: str = "1.1.0"
    app_download_url: str = ""
    app_release_notes: str = ""
    app_force_update: bool = False

    # 服务器定时任务
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Asia/Shanghai"
    lottery_check_time: str = "18:03:00"
    token_check_time: str = "07:00:00"
    weekend_reserve_enabled: bool = True
    weekend_reserve_time: str = "15:05:00"

    class Config:
        env_prefix = "MT_"
        env_file = ROOT / ".env"


settings = Settings()
