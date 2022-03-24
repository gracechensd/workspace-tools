import os
from test_stubs import temp_git_repo
from utils.process import run
from workspace.config import config


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


def make_commit(name, skip=False):
    """
        Function to create a temporary file in current directory, and commit it using name as the commit message
        unless skip is True (in which case the commit message will have [skip] appended to the front of the commit name.
        Returns the SHA1 of the commit created.

        :param skip: [Optional] Append "[skip]" to the front of the commit message, for use in --skip-commits
    """
    run('touch {}.xml'.format(name))
    run('git add -A')
    msg = name

    if skip:
        msg = "[skip] {}".format(msg)

    run(['git', 'commit', '-m', msg])
    sha = run('git rev-parse --verify HEAD', return_output=True).strip()
    return sha


# For all test_merge_branch tests below, we cannot assert commits in the log line-by-line because the ordering of the
# commit messages is not guaranteed because the timestamps on the commits are all the same. Adding sleep statements
# allows the order to be guaranteed and repeatable but will slow down the tests.


def test_merge_branch_skip_last(wst, capsys):
    """
        Test to check if merge_branch works when three commits are created, with the last commit being skipped.
        Fourth commit used so that all 3 commits on 3.0.x create merge commits.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        run('git checkout master')
        make_commit("commit4")
        run('git checkout 3.0.x')
        commit1_sha = make_commit("commit1")
        commit2_sha = make_commit("commit2")
        skipped_sha = make_commit("commit3", skip=True)
        run('git checkout master')
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        assert f'Merge commit \'{commit1_sha[0:7]}\'' in changes
        assert f'Merge commit \'{commit2_sha[0:7]}\'' in changes
        assert f'Merge commit \'{skipped_sha[0:7]}\' into master (using strategy ours)' in changes
        assert 'commit1' in changes
        assert 'commit2' in changes
        assert '[skip]' in changes
        assert 'commit4' in changes

        temp_git_dir_path = os.getcwd()
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_skip_middle(wst, capsys):
    """
        Test to check if merge_branch works when three commits are created, with the middle commit being skipped.
        Fourth commit used so that all 3 commits on 3.0.x create merge commits.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        commit1_sha = make_commit("commit1")
        skipped_sha = make_commit("commit2", skip=True)
        commit3_sha = make_commit("commit3")
        run('git checkout master')
        make_commit("commit4")
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        assert f'Merge commit \'{commit1_sha[0:7]}\'' in changes
        assert f'Merge commit \'{skipped_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{commit3_sha[0:7]}\'' in changes
        assert 'commit1' in changes
        assert '[skip]' in changes
        assert 'commit3' in changes
        assert 'commit4' in changes

        temp_git_dir_path = os.getcwd()
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_skip_none(wst, capsys):
    """
        Test to check if merge_branch works when three commits are created, with no commits skipped.
        Fourth commit used so that all 3 commits on 3.0.x create merge commits.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        commit1_sha = make_commit("commit1")
        commit2_sha = make_commit("commit2")
        commit3_sha = make_commit("commit3")
        run('git checkout master')
        make_commit("commit4")
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        assert f'Merge commit \'{commit1_sha[0:7]}\'' in changes
        assert f'Merge commit \'{commit2_sha[0:7]}\'' in changes
        assert f'Merge commit \'{commit3_sha[0:7]}\'' in changes
        assert 'commit1' in changes
        assert 'commit2' in changes
        assert 'commit3' in changes

        temp_git_dir_path = os.getcwd()
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_skip_first(wst, capsys):
    """
        Test to check if merge_branch works with three commits created on 3.0.x, with the first commit being skipped.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        skipped_sha = make_commit("commit1", skip=True)
        commit2_sha = make_commit("commit2")
        commit3_sha = make_commit("commit3")
        run('git checkout master')
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        assert f'Merge commit \'{skipped_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{commit2_sha[0:7]}\'' in changes
        assert f'Merge commit \'{commit3_sha[0:7]}\'' in changes
        assert '[skip]' in changes
        assert 'commit2' in changes
        assert 'commit3' in changes

        temp_git_dir_path = os.getcwd()
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_skip_first_two(wst, capsys):
    """
        Test to check if merge_branch works with three commits created on 3.0.x, with the first two commits
        being skipped.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        skipped1_sha = make_commit("commit1", skip=True)
        skipped2_sha = make_commit("commit2", skip=True)
        commit3_sha = make_commit("commit3")
        run('git checkout master')
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        # Change should have been in the log entry
        assert f'Merge commit \'{skipped1_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{skipped2_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{commit3_sha[0:7]}\'' in changes
        assert '[skip]' in changes
        assert '[skip]' in changes
        assert 'commit3' in changes

        temp_git_dir_path = os.getcwd()
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_skip_all(wst, capsys):
    """
        Test to check if merge_branch works with three commits created on 3.0.x, with the all commits  skipped.
    """
    config.merge.branches = '1.0.x 2.0.x 3.0.x master'
    with temp_git_repo():
        # Dummy commit
        run('git commit --allow-empty -m dummy-commit')
        run('git checkout -b 3.0.x')
        skipped1_sha = make_commit("commit1", skip=True)
        skipped2_sha = make_commit("commit2", skip=True)
        skipped3_sha = make_commit("commit3", skip=True)
        run('git checkout master')
        wst('merge 3.0.x --skip-commits \'skip\' \'space separated example\'')

        changes = run('git log --oneline', return_output=True)
        # Change should have been in the log entry
        assert f'Merge commit \'{skipped1_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{skipped2_sha[0:7]}\' into master (using strategy ours)' in changes
        assert f'Merge commit \'{skipped3_sha[0:7]}\' into master (using strategy ours)' in changes
        assert '[skip]' in changes
        assert '[skip]' in changes
        assert '[skip]' in changes

        temp_git_dir_path = os.getcwd()
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit1.xml"))
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit2.xml"))
        assert not os.path.isfile(os.path.join(temp_git_dir_path, "commit3.xml"))

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 3.0.x into master'


def test_merge_branch_with_user(wst, capsys):
    """
        Test to check if merge_branch works with user option
    """
    with temp_git_repo():
        run('git commit --allow-empty -m init')
        run('git checkout -b 1.0.x')
        _ = make_commit("commit 1")
        run('git checkout master')
        run('git checkout -b 2.0.x')
        _ = make_commit("commit 2")
        wst('merge 1.0.x --user devprod')

        changes = run('git log --oneline', return_output=True)
        assert "Merge branch '1.0.x' into 2.0.x by devprod" in changes

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 1.0.x into 2.0.x'


def test_merge_branch_with_user_and_strategy(wst, capsys):
    """
        Test to check if merge_branch works with user and strategy options
    """
    with temp_git_repo():
        run('git commit --allow-empty -m init')
        run('git checkout -b 1.0.x')
        _ = make_commit("commit 1")
        run('git checkout master')
        run('git checkout -b 2.0.x')
        _ = make_commit("commit 2")
        wst('merge 1.0.x --user devprod -s ours')

        changes = run('git log --oneline', return_output=True)
        assert "Merge branch '1.0.x' into 2.0.x by devprod (using strategy ours)" in changes

    out, _ = capsys.readouterr()
    assert out.split('\n')[0] == 'Merging 1.0.x into 2.0.x'
