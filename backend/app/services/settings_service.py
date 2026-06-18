import json
from sqlalchemy.orm import Session

from app.models.setting import Setting

SETTINGS_DEFINITIONS = {
    "session_timeout_minutes": {
        "type": "int",
        "default": 30,
        "min": 5,
        "max": 1440,
        "label": "Session Timeout",
        "description": "Minutes of inactivity before users are logged out",
        "category": "security",
    },
    "refresh_token_days": {
        "type": "int",
        "default": 7,
        "min": 1,
        "max": 90,
        "label": "Refresh Token Lifetime",
        "description": "Days before refresh tokens expire",
        "category": "security",
    },
    "password_min_length": {
        "type": "int",
        "default": 8,
        "min": 4,
        "max": 128,
        "label": "Minimum Password Length",
        "description": "Minimum number of characters required for passwords",
        "category": "security",
    },
    "password_require_uppercase": {
        "type": "bool",
        "default": False,
        "label": "Require Uppercase",
        "description": "Require at least one uppercase letter in passwords",
        "category": "security",
    },
    "password_require_number": {
        "type": "bool",
        "default": False,
        "label": "Require Number",
        "description": "Require at least one number in passwords",
        "category": "security",
    },
    "password_require_special": {
        "type": "bool",
        "default": False,
        "label": "Require Special Character",
        "description": "Require at least one special character in passwords",
        "category": "security",
    },
    "default_cert_validity_days": {
        "type": "int",
        "default": 365,
        "min": 1,
        "max": 3650,
        "label": "Default Certificate Validity",
        "description": "Default validity period in days for new certificates",
        "category": "certificates",
    },
    "default_ca_auto_approve": {
        "type": "bool",
        "default": False,
        "label": "Default CA Auto-Approve",
        "description": "Whether new CAs default to auto-approve certificate requests",
        "category": "certificates",
    },
    "audit_retention_days": {
        "type": "int",
        "default": 365,
        "min": 30,
        "max": 3650,
        "label": "Audit Log Retention",
        "description": "Days to retain audit log entries before cleanup",
        "category": "maintenance",
    },
    "crl_regen_interval_minutes": {
        "type": "int",
        "default": 60,
        "min": 5,
        "max": 1440,
        "label": "CRL Regeneration Interval",
        "description": "Minutes between automatic CRL regeneration cycles",
        "category": "maintenance",
    },
    "mcp_enabled": {
        "type": "bool",
        "default": True,
        "label": "MCP Server Enabled",
        "description": "Allow AI agents to access the PKI server via MCP",
        "category": "mcp",
    },
    "mcp_allow_approval": {
        "type": "bool",
        "default": False,
        "label": "MCP Allow Approval",
        "description": "Allow AI agents to approve or deny certificate requests via MCP",
        "category": "mcp",
    },
    "acme_enabled": {
        "type": "bool",
        "default": False,
        "label": "ACME Server Enabled",
        "description": "Allow ACME clients (certbot, Caddy) to request certificates",
        "category": "acme",
    },
    "acme_default_ca_id": {
        "type": "string",
        "default": "",
        "label": "ACME Default CA",
        "description": "CA used for the default /acme/directory endpoint",
        "category": "acme",
    },
    "acme_registration_open": {
        "type": "bool",
        "default": True,
        "label": "ACME Open Registration",
        "description": "Allow new ACME accounts to register",
        "category": "acme",
    },
    "acme_allowed_domains": {
        "type": "string",
        "default": "",
        "label": "ACME Allowed Domains",
        "description": "Comma-separated domain patterns (e.g. *.example.com). Empty allows all.",
        "category": "acme",
    },
}


class SettingsService:
    def _cast(self, key: str, raw: str):
        defn = SETTINGS_DEFINITIONS[key]
        if defn["type"] == "int":
            return int(raw)
        if defn["type"] == "bool":
            return raw.lower() in ("true", "1", "yes")
        return raw

    def _serialize(self, key: str, value) -> str:
        defn = SETTINGS_DEFINITIONS[key]
        if defn["type"] == "bool":
            return "true" if value else "false"
        return str(value)

    def _validate(self, key: str, value):
        if key not in SETTINGS_DEFINITIONS:
            raise ValueError(f"Unknown setting: {key}")
        defn = SETTINGS_DEFINITIONS[key]
        if defn["type"] == "int":
            value = int(value)
            if "min" in defn and value < defn["min"]:
                raise ValueError(f"{defn['label']} must be at least {defn['min']}")
            if "max" in defn and value > defn["max"]:
                raise ValueError(f"{defn['label']} must be at most {defn['max']}")
        return value

    def get(self, db: Session, key: str):
        if key not in SETTINGS_DEFINITIONS:
            raise ValueError(f"Unknown setting: {key}")
        try:
            row = db.query(Setting).filter(Setting.key == key).first()
        except Exception:
            db.rollback()
            return SETTINGS_DEFINITIONS[key]["default"]
        if row:
            return self._cast(key, row.value)
        return SETTINGS_DEFINITIONS[key]["default"]

    def get_all(self, db: Session) -> dict:
        try:
            rows = {s.key: s.value for s in db.query(Setting).all()}
        except Exception:
            db.rollback()
            rows = {}
        result = {}
        for key, defn in SETTINGS_DEFINITIONS.items():
            if key in rows:
                result[key] = self._cast(key, rows[key])
            else:
                result[key] = defn["default"]
        return result

    def update(self, db: Session, updates: dict) -> dict:
        for key, value in updates.items():
            self._validate(key, value)

        for key, value in updates.items():
            serialized = self._serialize(key, value)
            row = db.query(Setting).filter(Setting.key == key).first()
            if row:
                row.value = serialized
            else:
                db.add(Setting(key=key, value=serialized))
        db.commit()
        return self.get_all(db)

    def get_definitions(self) -> dict:
        return SETTINGS_DEFINITIONS

    def validate_password(self, db: Session, password: str) -> list[str]:
        errors = []
        min_len = self.get(db, "password_min_length")
        if len(password) < min_len:
            errors.append(f"Password must be at least {min_len} characters")
        if self.get(db, "password_require_uppercase") and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        if self.get(db, "password_require_number") and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        if self.get(db, "password_require_special") and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        return errors
