from test_stubs import temp_git_repo
from utils.process import run
import logging

from workspace.config import config
log = logging.getLogger(__name__)

def test_merge_downstream(wst, capsys):
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'

    with temp_git_repo():
        run('git commit --allow-empty -m dummy-commit')
        run('git branch 3.0.x')
        run('git checkout -b 2.0.x')

        run('git commit --allow-empty -m new-commit')

        wst('merge --downstream')

        branches = run('git branch', return_output=True)
        changes = run('git log --oneline', return_output=True)

    out, _ = capsys.readouterr()

    assert out == """\
Merging 2.0.x into 3.0.x
Pushing 3.0.x
Merging 3.0.x into master
Pushing master
"""

    assert '* master' in branches
    assert 'new-commit' in changes


def test_merge_branch(wst, capsys):
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'

    with temp_git_repo():
        run('git commit --allow-empty -m dummy-commit')

        run('git checkout -b 3.0.x')
        run('git commit --allow-empty -m new-commit')

        run('git checkout master')

        wst('merge 3.0.x')

        changes = run('git log --oneline', return_output=True)
        assert 'new-commit' in changes

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_with_whitelist(wst, capsys):
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'

    with temp_git_repo():
        run('git commit --allow-empty -m dummy-commit')

        run('git checkout -b 3.0.x')
        run('git commit --allow-empty -m skip-new-commit')

        run('git checkout master')

        wst('merge 3.0.x --whitelist-commit-text-for-ours skip')

        changes = run('git log --oneline', return_output=True)
        log.info("---viks changes:{}".format(changes))
        # Should have skipped adding new log entry as the new-commit
        # because the commit message has 'skip' in the message
        assert 'new-commit' not in changes

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'

