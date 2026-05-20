from pydantic import BaseModel


class SettingsResponse(BaseModel):
    session_timeout_minutes: int
    refresh_token_days: int
    password_min_length: int
    password_require_uppercase: bool
    password_require_number: bool
    password_require_special: bool
    default_cert_validity_days: int
    default_ca_auto_approve: bool
    audit_retention_days: int
    crl_regen_interval_minutes: int


class SettingsUpdate(BaseModel):
    session_timeout_minutes: int | None = None
    refresh_token_days: int | None = None
    password_min_length: int | None = None
    password_require_uppercase: bool | None = None
    password_require_number: bool | None = None
    password_require_special: bool | None = None
    default_cert_validity_days: int | None = None
    default_ca_auto_approve: bool | None = None
    audit_retention_days: int | None = None
    crl_regen_interval_minutes: int | None = None


class SettingDefinition(BaseModel):
    type: str
    default: int | bool | str
    label: str
    description: str
    category: str
    min: int | None = None
    max: int | None = None


class SettingsDefinitionsResponse(BaseModel):
    definitions: dict[str, SettingDefinition]
    values: dict[str, int | bool | str]
