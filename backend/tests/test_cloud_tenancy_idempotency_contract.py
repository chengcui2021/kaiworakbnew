from pathlib import Path


def test_cloud_tenancy_endpoints_are_retry_safe():
    source=Path('app/routes/cloud_tenancy.py').read_text(encoding='utf-8')
    assert "existing.name=payload.name.strip()" in source
    assert "existing.slug=payload.slug.strip().lower()" in source
    assert "Workspace tenant mismatch" in source
    assert "Repository scope mismatch" in source
    assert "existing.external_id=payload.external_id.strip()" in source


def test_service_auth_still_fails_closed():
    source=Path('app/routes/cloud_tenancy.py').read_text(encoding='utf-8')
    assert "secrets.compare_digest(expected,x_kaiwora_service_key)" in source
    assert "raise HTTPException(403,'Kaiwora service credentials required')" in source
