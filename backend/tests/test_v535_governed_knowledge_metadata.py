from app.persistence.models import Entry, EntryStatus, EntryType, ComponentName
from app.persistence.schemas import EntryCreate
from app.schemas.context_assembly import RepositoryAnalysisInput
from app.services.knowledge_resolver import _governed_policy_applies


def test_policy_metadata_is_first_class():
    payload = EntryCreate.model_validate({
        'type':'constraint', 'component':'admin', 'title':'Default stack', 'content':'Use approved stack',
        'author':'admin', 'owner_scope':'global', 'knowledge_kind':'policy',
        'applies_to':'bootstrap_project', 'priority':200,
    })
    assert payload.knowledge_kind == 'policy'
    assert payload.owner_scope == 'global'
    assert payload.applies_to == 'bootstrap_project'
    assert payload.priority == 200


def test_bootstrap_policy_is_deterministically_applicable():
    entry = Entry(
        entry_type=EntryType.CONSTRAINT, component_name=ComponentName.ADMIN,
        title='Default stack', content='Use approved stack', author='admin',
        status=EntryStatus.RESOLVED, owner_scope='global', knowledge_kind='policy',
        applies_to='bootstrap_project', priority=200,
    )
    repo = RepositoryAnalysisInput(name='todoapp', commit_sha='1234567', relevant_files=[], architecture_context=[], analysis_evidence=[])
    assert _governed_policy_applies(entry, repo) is True
