from app.services.global_learning_service import sanitise_observation, global_fingerprint

def test_sanitise_removes_paths_urls_emails_and_hashes():
    raw='See https://acme.example/x user@acme.com src/payments/refund.py commit ' + ('a'*40)
    out=sanitise_observation(raw)
    assert 'acme.example' not in out
    assert 'user@acme.com' not in out
    assert 'src/payments/refund.py' not in out
    assert 'a'*40 not in out
    assert '[repository-path]' in out

def test_global_fingerprint_is_cross_tenant_by_design():
    a=global_fingerprint('procedural','Protect configuration files from writes')
    b=global_fingerprint('procedural','Protect configuration files from writes')
    assert a == b
