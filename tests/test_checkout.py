import os

from test_stubs import temp_dir


def test_checkout_with_http_git(wst):
    with temp_dir():
        wst('checkout https://github.com/maxzheng/clicast.git')
        assert os.path.exists('clicast/README.rst')


def test_checkout_with_git(wst):
    with temp_dir():
        wst('checkout git@github.com:maxzheng/clicast.git')
        assert os.path.exists('clicast/README.rst')


def test_checkout_with_multiple_repos(wst):
    with temp_dir():
        wst('checkout https://github.com/maxzheng/localconfig.git https://github.com/maxzheng/remoteconfig.git')
        assert os.path.exists('localconfig/README.rst')
        assert os.path.exists('remoteconfig/README.rst')
