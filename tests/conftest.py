import logging
import shlex

import pytest
from mock import Mock
from workspace.controller import Commander

log = logging.getLogger(__name__)


@pytest.fixture()
def wst(monkeypatch):
    def _run(cmd):
        log.info("-----viks ----- cmd:{}".format(shlex.split('wst --debug ' + cmd)))
        monkeypatch.setattr('sys.argv', shlex.split('wst --debug ' + cmd))
        return Commander().run(skip_style_check=True)

    return _run


# checkout_branch, remove_branch, current_branch, all_remotes,
# push_repo, merge_branch, update_branch, parent_branch, default_remote

@pytest.fixture()
def mock_run(monkeypatch):
    r = Mock()
    monkeypatch.setattr('utils.process.run', r)
    monkeypatch.setattr('workspace.utils.run', r)
    monkeypatch.setattr('workspace.scm.run', r)
    r.stat_repo.return_value = ['new_file']
    monkeypatch.setattr('workspace.commands.test.run', r)
    return r
