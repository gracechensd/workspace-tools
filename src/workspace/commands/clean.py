import logging
import os
import shutil
from time import time

from workspace.commands.helpers import expand_product_groups
from workspace.config import config
from workspace.scm import workspace_path, product_name, repos, stat_repo
from workspace.utils import silent_run

log = logging.getLogger(__name__)


def setup_clean_parser(subparsers):
  clean_parser = subparsers.add_parser('clean', description=clean.__doc__, help=clean.__doc__)
  clean_parser.set_defaults(command=clean)

  return clean_parser


def clean(**kwargs):
  """ Clean workspace by removing build, dist, and .pyc files """

  path = workspace_path()
  log.info('Cleaning %s', path)

  log.info('Removing build/dist folders')
  silent_run("rm -rf */build */dist */docs/_build */*/build", cwd=path, shell=True)

  log.info('Removing *.pyc files')
  silent_run("find . -type d \( -path '*/.tox' -o -path '*/mppy-*' \) -prune -o -name *.pyc -exec rm {} \;", cwd=path, shell=True)

  if config.clean.remove_products_older_than_days or config.clean.remove_all_products_except:
    keep_time = 0
    keep_products = []

    if config.clean.remove_all_products_except:
      log.info('Removing all products except: %s', config.clean.remove_all_products_except)
      keep_products = expand_product_groups(config.clean.remove_all_products_except.split())

    if config.clean.remove_products_older_than_days:
      log.info('Removing products older than %s days', config.clean.remove_products_older_than_days)
      keep_time = time() - config.clean.remove_products_older_than_days * 86400

    removed_products = []

    for repo in repos(path):
      name = product_name(repo)
      modified_time = os.stat(repo).st_mtime
      if name not in keep_products or keep_time and modified_time < keep_time:
        status = stat_repo(repo, return_output=True)
        if not status or 'nothing to commit' in status and 'working directory clean' in status:
          shutil.rmtree(repo)
          removed_products.append(name)
        else:
          log.info('  - Skipping "%s" as it has changes that may not be committed', name)

    if removed_products:
      log.info('Removed %s', ', '.join(removed_products))
