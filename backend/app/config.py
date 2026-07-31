import os
import sys
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./foodtrack.db"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")

    # External service URLs — override via environment variables
    EMAIL_API_URL: str = os.getenv("EMAIL_API_URL", "")
    EMAIL_API_KEY: str = os.getenv("EMAIL_API_KEY", "")
    SMS_API_URL: str = os.getenv("SMS_API_URL", "")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")

    # SSO client identifiers (used by the frontend OAuth flows)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    SSO_REDIRECT_URI: str = os.getenv("SSO_REDIRECT_URI", "")

    # When true (and no email/SMS service is configured) OTP codes are
    # returned in the API response so demo/testing flows can complete.
    RETURN_OTP_IN_DEV: bool = os.getenv("RETURN_OTP_IN_DEV", "true").lower() in ("1", "true", "yes")

    def validate_production(self) -> None:
        """Raise at startup if critical secrets are still at insecure defaults."""
        is_sqlite = self.DATABASE_URL.startswith("sqlite")
        if not is_sqlite and self.SECRET_KEY == "change-me":
            print(
                "FATAL: SECRET_KEY is set to the insecure default 'change-me'. "
                "Set the SECRET_KEY environment variable before starting the server.",
                file=sys.stderr,
            )
            sys.exit(1)


settings = Settings()
# Validate on import (exits if SECRET_KEY == "change-me" with a non-SQLite DB)
settings.validate_production()
