"""
Application settings.

Values come from the environment or ``backend/.env``. Note that pydantic
only reads a variable if it is *declared as a field here* — an undeclared
name in ``.env`` is silently ignored. That bit us before: ``PROJECT_ROOT``
was documented and read via ``getattr(settings, ...)`` but never declared,
so setting it had no effect at all.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import default_roots, parse_roots


class Settings(BaseSettings):

    APP_NAME: str = "Orion"

    VERSION: str = "1.0.0"

    DEBUG: bool = True

    #
    # Project analysed by the startup scan. When empty, Orion falls back to
    # analysing its own backend package, which makes a fresh checkout
    # immediately explorable without configuration.
    #
    PROJECT_ROOT: str | None = None

    #
    # Directories the /graph/browse and /graph/scan endpoints may read.
    # Separate with the OS path separator or commas. Empty falls back to the
    # user's home directory — see app.core.paths for why this exists.
    #
    ALLOWED_ROOTS: str | None = None

    # Development-only escape hatch for scanning a local directory outside
    # ALLOWED_ROOTS. Keep this false in production; it bypasses the filesystem
    # containment boundary for the scan endpoint.
    ALLOW_UNSAFE_SCAN_PATHS: bool = False

    #
    # Browser origins permitted to call the API. The bundled frontend is
    # served same-origin from /app so it needs no entry here; this is for
    # running a separate dev server, or add "null" to allow a file:// page.
    #
    ALLOW_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    #
    # SQLite database used for persisted graph snapshots, scan jobs and
    # project metadata. When empty, Orion stores data under backend/.orion.
    #
    PERSISTENCE_DB: str | None = None

    #
    # Authentication toggle.  Set to ``true`` in production so every request
    # must carry a valid ``X-API-Key`` header.  Defaults to ``false`` for a
    # frictionless local-dev experience.
    #
    AUTH_ENABLED: bool = False

    # Auth0/OIDC is introduced alongside the existing API-key path. Keep this
    # false for local development until both sides share the same Auth0 tenant.
    AUTH0_ENABLED: bool = False
    AUTH0_ISSUER_BASE_URL: str | None = None
    AUTH0_AUDIENCE: str | None = None
    AUTH0_ALGORITHMS: str = "RS256"
    ORION_IDENTITY_BRIDGE_SECRET: str | None = None
    ORION_IDENTITY_BRIDGE_MAX_AGE_SECONDS: int = 300

    # Optional local LLM inference. Keep disabled for the lightweight
    # deployment; enable only when the model runtime and adapter are present.
    ORION_LLM_ENABLED: bool = False

    #
    # Optional bootstrap admin key.  When set, a key with this exact value
    # and admin role is auto-created on first startup so you always have a
    # way in.  After that you should create dedicated keys and remove this.
    #
    ADMIN_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    def __repr__(self) -> str:
        fields = []
        for name in self.__class__.model_fields:
            val = getattr(self, name)
            if name == "ADMIN_API_KEY" and val is not None:
                val = "***REDACTED***"
            fields.append(f"{name}={val!r}")
        return f"{self.__class__.__name__}({', '.join(fields)})"

    @property
    def allowed_roots(self) -> list[Path]:
        """
        Resolved allowlist for client-supplied paths.

        This deliberately does **not** constrain PROJECT_ROOT: that value comes
        from the operator's own .env, whereas browse/scan paths arrive over
        HTTP. Only the untrusted ones need fencing.
        """
        return parse_roots(self.ALLOWED_ROOTS) or default_roots()

    @property
    def allow_origins(self) -> list[str]:
        """
        ALLOW_ORIGINS split into the list CORSMiddleware expects.
        """
        return [
            origin.strip()
            for origin in self.ALLOW_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def persistence_db_path(self) -> Path:
        """
        SQLite file used for durable Orion state.
        """
        if self.PERSISTENCE_DB and self.PERSISTENCE_DB.strip():
            return Path(self.PERSISTENCE_DB).expanduser().resolve()

        return Path(__file__).resolve().parents[2] / ".orion" / "orion.db"


settings = Settings()
