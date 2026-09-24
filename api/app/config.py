from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- infra ---
    DATABASE_URL: str = "sqlite:///./data/app.db"
    STORAGE_BACKEND: str = "local"
    STORAGE_ROOT: str = "./data/files"
    JWT_SECRET: str = "change-me"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-me"
    CORS_ORIGINS: str = "http://localhost:3000"
    MEDIA_URL_TTL_SECONDS: int = 3600

    # --- detection ---
    DET_SIZE: int = 1280
    MIN_DET_SCORE: float = 0.6
    MIN_FACE_PX: int = 40
    TILE_IF_LONG_SIDE_GT: int = 2000
    TILE_SIZE: int = 1280
    TILE_STRIDE: int = 960
    NMS_IOU: float = 0.4

    # --- matching ---
    T_HIGH: float = 0.50
    T_LOW: float = 0.35
    T_CLUSTER: float = 0.50
    MIN_AUTO_PHOTOS: int = 1

    # --- enrollment gate ---
    ENROLL_MIN_DET: float = 0.80
    ENROLL_MIN_FACE_PX: int = 112
    ENROLL_MAX_YAW_ASYM: float = 0.40
    ENROLL_MIN_BLUR: float = 60
    MAX_REFS_PER_MEMBER: int = 8


settings = Settings()
