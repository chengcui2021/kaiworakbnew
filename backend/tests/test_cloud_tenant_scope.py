from types import SimpleNamespace
from app.services.tenant_scope import entry_is_authorized, validate_entry_ownership


def e(scope, tenant=None, workspace=None, repository=None):
    return SimpleNamespace(owner_scope=scope, tenant_id=tenant, workspace_id=workspace, repository_id=repository)


def test_global_is_visible_to_every_tenant():
    assert entry_is_authorized(e("global"), tenant_id="a", workspace_id="w", repository_id="r")


def test_tenant_entry_cannot_cross_tenant_boundary():
    row = e("tenant", "a")
    assert entry_is_authorized(row, tenant_id="a", workspace_id="w", repository_id="r")
    assert not entry_is_authorized(row, tenant_id="b", workspace_id="w", repository_id="r")


def test_repository_entry_requires_exact_scope():
    row = e("repository", "a", "w1", "r1")
    assert entry_is_authorized(row, tenant_id="a", workspace_id="w1", repository_id="r1")
    assert not entry_is_authorized(row, tenant_id="a", workspace_id="w1", repository_id="r2")
    assert not entry_is_authorized(row, tenant_id="a", workspace_id="w2", repository_id="r1")


def test_repository_ownership_validation_fails_closed():
    try:
        validate_entry_ownership("repository", "a", "w", None)
    except ValueError:
        pass
    else:
        raise AssertionError("repository scope without repository_id must fail")
