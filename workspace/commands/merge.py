from __future__ import absolute_import

import logging
import sys
import textwrap

import click
import git
from utils.process import run as process_run
from workspace.commands import AbstractCommand
from workspace.config import config
from workspace.scm import checkout_branch, current_branch, merge_branch, repo_path

log = logging.getLogger(__name__)


class NotAllowedCommit(Exception):
    """ Raised when a commit is not allowed to be merged """
    pass


class Merge(AbstractCommand):
    """
    Merge changes from branch to current branch
    :param str branch: The branch to merge from.
    :param bool downstreams: Merge current branch to downstream branches defined in config merge.branches
                             that are on the right side of the current branch value and pushes them to all remotes.
                             Branches on the left side are ignored and not merged.
    :param str merge_branches: List of branches used to perform merge operations on. This overrides values set in config
                               merge.branches and is used with :param:`downstreams` to compute the list of merges from
                               the current branch, which must be in the list as well. Use quotes and seperate multiple
                               values using a space.  E.g. "1.0.0 1.0.2 1.0.x master"
    :param str strategy: The merge strategy to pass to git merge
    :param list allow_commits: Patterns to allow commits to be merged.
    :param bool quiet: Don't print merging if there are no commits to merge
    :param bool dry_run: Print out what will happen without making changes.
    :param str validation: A command to run after the merge and before a push to validate the change.
    :param str skip_commits: [Optional] Enables per commit based merge. Accepts a list of string or substrings from a
    commit message used to skip the commits during pint merge. Commits that matches the list of strings are skipped
    using merge with 'ours' strategy.
    :param str user: [Optional] Name of the user to be appended to merge commit message ("Merge...by <user>")
    """

    @classmethod
    def arguments(cls):
        _, docs = cls.docs()
        return [
            cls.make_args('branch', nargs='?', help=docs['branch']),
            cls.make_args('-d', '--downstreams', action='store_true', help=docs['downstreams']),
            cls.make_args('--merge-branches', help=docs['merge_branches']),
            cls.make_args('-s', '--strategy', help=docs['strategy']),
            cls.make_args('-a', '--allow-commits', help=docs['allow_commits']),
            cls.make_args('--quiet', action='store_true', help=docs['quiet']),
            cls.make_args('-n', '--dry-run', action='store_true', help=docs['dry_run']),
            cls.make_args('--validation', help=docs['validation']),
            cls.make_args('--skip-commits', nargs='*', help=docs['skip_commits']),
            cls.make_args('-u', '--user', help=docs['user'])
        ]

    def run(self):
        current = current_branch()
        repo = git.Repo(path=repo_path())

        if self.branch and self.downstreams:
            log.error('Branch and --downstreams are mutually exclusive. Please use one or the other.')
            sys.exit(1)

        if repo.is_dirty(untracked_files=True):
            log.error(
                'Your repo has untracked or modified files in working dir or in staging index. Please cleanup before doing merge')
            sys.exit(1)

        if not self.skip_update:
            self.commander.run('update', quiet=True)

        if self.branch:
            click.echo('Merging {} into {}'.format(self.branch, current))

            if not self.skip_update:
                checkout_branch(self.branch)
                self.commander.run('update', quiet=True)
                checkout_branch(current)

            all_commits = self.get_unmerged_commits(repo, self.branch, current)
            self.merge_commits(self.branch, all_commits, self.skip_commits, self.user)

        elif self.downstreams:
            if not self.merge_branches:
                self.merge_branches = config.merge.branches

            if not self.merge_branches:
                log.error('Config merge.branches must be configured with a list of branches to merge to, or '
                          'use --merge-branches to provide a list')
                sys.exit(1)

            branches = self.merge_branches.split()

            if current not in branches:
                log.error('Current branch %s not found in config merge.branches (%s)', current, self.merge_branches)
                sys.exit(1)

            last = current
            downstream_branches = branches[branches.index(last) + 1:]

            if not downstream_branches:
                click.echo('You are currently on the last branch, so no downstream branches to merge.')
                click.echo('Switch to the branch that you want to merge from first, and then re-run')
                sys.exit(0)

            for branch in downstream_branches:
                checkout_branch(branch)

                commits = self._unmerged_commits(repo, last, branch)

                if self.quiet and not commits:
                    last = branch
                    continue

                click.echo('Merging {} into {}'.format(last, branch))

                if not self.skip_update:
                    self.commander.run('update', quiet=True)

                if self.dry_run:
                    self.get_unmerged_commits(repo, last, branch)

                else:
                    if self.allow_commits:
                        if commits:
                            for commit in commits:
                                # Not performant / ok as # of allow_commits should be low
                                allowed_commit = (' Merge branch ' in commit
                                                  or ' Merge commit ' in commit
                                                  or ' Merge pull request ' in commit
                                                  or any(allow_commit in commit for allow_commit in self.allow_commits))
                                if not allowed_commit:
                                    click.echo('Found a commit that was not allowed to be merged:'.format(last))
                                    click.echo('  {}'.format(commit))
                                    raise NotAllowedCommit(commit)

                    self.merge_commits(last, commits, self.skip_commits, self.user)

                    if self.validation:
                        process_run(self.validation)

                    if self.validation:
                      process_run(self.validation)

                    self.commander.run('push', all_remotes=True, skip_style_check=True)

                last = branch

        else:
            log.error(
                'Please specify either a branch to merge from or --downstreams to merge to all downstream branches')
            sys.exit(1)

    def merge_commits(self, branch_name, unmerged_commits, skip_commits=None, user=None):
        """
        Function to merge the unmerged commits. If  skip_commits is empty, it will merge using the heads
        of the source and destination(current) branch.

        If skip_commits is present, then we will inspect the list of commits for a match with the text
        from skip_commits. If match is not found the commit will be merged with whatever strategy passed
        to the class else if a match is found it will merge that specific commit with `ours` strategy.

        :param branch_name: Name of the source branch
        :param unmerged_commits: List of unmerged_commits
        :param skip_commits: [Optional] Enables per commit based merge. Accepts a list of string or substrings from a
        commit message used to skip the commits during pint merge. Commits that matches the list of strings are skipped
        using merge with 'ours' strategy.
        :param str user: [Optional] Name of the user to be appended to merge commit message ("Merge...by <user>")
        """
        if not unmerged_commits:
            return

        if skip_commits is None:
            merge_branch(branch_name, strategy=self.strategy, user=user)
            return

        # we should merge from the oldest commit to the newest
        unmerged_commits_list = reversed(unmerged_commits)

        # For each commit, inspect the message and accordingly run the merge strategy
        for unmerged_commit in unmerged_commits_list:
            commit_hash = unmerged_commit.split()[0]
            if self.should_use_ours_strategy(unmerged_commit, skip_commits):
                merge_branch(branch_name, commit=commit_hash, strategy="ours", user=user)
            else:
                merge_branch(branch_name, commit=commit_hash, strategy=self.strategy, user=user)

    def should_use_ours_strategy(self, commit_message, skip_commits):
        log.info("skip_commits:{}".format(skip_commits))
        for ours_commit_whitelist in skip_commits:
            log.info("Verifying commit:`{}` with ours text:`{}`".format(commit_message, ours_commit_whitelist))
            if ours_commit_whitelist in commit_message:
                return True
        return False

    def get_unmerged_commits(self, repo, source_branch, target_branch):
        """ Show commit diffs between from_branch to target_branch """
        commits = self._unmerged_commits(repo, source_branch, target_branch)
        if commits:
            click.echo('The following commit(s) would be merged:')
            click.echo(textwrap.indent('\n'.join(commits), '  '))
        else:
            click.echo('Already up-to-date.')
        return commits

    def _unmerged_commits(self, repo, from_branch, target_branch):
        unmerged_commits = []
        commits = repo.git.log('{}..{}'.format(target_branch, from_branch), oneline=True)
        for commit in commits.split('\n'):
            # Skip on 'Merge' commits to prevent merge of merge commits
            if not ('Merge branch' in commit or 'Merge commit' in commit or 'Merge pull request' in commit):
                unmerged_commits.append(commit)
        return unmerged_commits
