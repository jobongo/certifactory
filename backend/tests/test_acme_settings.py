from app.services.settings_service import SettingsService

svc = SettingsService()


def test_acme_settings_defaults(db):
    assert svc.get(db, "acme_enabled") is False
    assert svc.get(db, "acme_default_ca_id") == ""
    assert svc.get(db, "acme_registration_open") is True
    assert svc.get(db, "acme_allowed_domains") == ""


def test_acme_settings_in_category(db):
    defs = svc.get_definitions()
    assert defs["acme_enabled"]["category"] == "acme"
    assert defs["acme_default_ca_id"]["type"] == "string"
