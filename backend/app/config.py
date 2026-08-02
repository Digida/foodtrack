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
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    )
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")
    ENV: str = os.getenv("ENV", "development")

    # External service URLs — override via environment variables
    EMAIL_API_URL: str = os.getenv("EMAIL_API_URL", "")
    EMAIL_API_KEY: str = os.getenv("EMAIL_API_KEY", "")
    SMS_API_URL: str = os.getenv("SMS_API_URL", "")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")

    # SMTP fallback for transactional email (used when EMAIL_API_URL is empty)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_SENDER: str = os.getenv("SMTP_SENDER", "noreply@foodtrack.ae")

    # Developer / operations contact (API-key notifications, footer credits)
    DEV_EMAIL: str = os.getenv("DEV_EMAIL", "digikiminvest@gmail.com")
    DEV_PHONE: str = os.getenv("DEV_PHONE", "+256700677543")
    DEV_WHATSAPP: str = os.getenv("DEV_WHATSAPP", "+256700677543")

    # SSO client identifiers (used by the frontend OAuth flows)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    # Apple "Sign in with Apple" — ES256 client-secret signing keys (P8)
    APPLE_CLIENT_ID: str = os.getenv("APPLE_CLIENT_ID", "")
    APPLE_TEAM_ID: str = os.getenv("APPLE_TEAM_ID", "")
    APPLE_KEY_ID: str = os.getenv("APPLE_KEY_ID", "")
    APPLE_PRIVATE_KEY: str = os.getenv("APPLE_PRIVATE_KEY", "")
    # GitHub OAuth App
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    # Backend callback URI that providers redirect the browser to after
    # the user approves the authorization-code request.
    SSO_REDIRECT_URI: str = os.getenv("SSO_REDIRECT_URI", "")

    # When true (and no email/SMS service is configured) OTP codes are
    # returned in the API response so demo/testing flows can complete.
    # Defaults to FALSE — production must never echo OTP codes.
    RETURN_OTP_IN_DEV: bool = os.getenv("RETURN_OTP_IN_DEV", "false").lower() in ("1", "true", "yes")

    def validate_production(self) -> None:
        """Raise at startup if critical secrets are still at insecure defaults.

        Gated on the deployment environment (ENV), not the database type, so
        a SQLite-backed production-ish deployment is still caught.
        """
        if self.ENV != "development" and self.SECRET_KEY == "change-me":
            print(
                "FATAL: SECRET_KEY is set to the insecure default 'change-me'. "
                "Set the SECRET_KEY environment variable before starting the server.",
                file=sys.stderr,
            )
            sys.exit(1)


settings = Settings()
# Validate on import (exits if SECRET_KEY == "change-me" with a non-SQLite DB)
settings.validate_production()
