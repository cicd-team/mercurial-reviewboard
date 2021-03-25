import os
import os.path
import shutil
import tarfile

from mercurial import fancyopts, hg, ui
from mock import Mock

from mercurial_reviewboard import cmdtable

test_dir = 'mercurial_reviewboard/tests'
tar_dir = '%s/repo_tars' % test_dir
repos_dir = '%s/repos' % test_dir


def untar(tar_file):
    tar_path = os.path.join(tar_dir, tar_file)
    tar = tarfile.open(tar_path)
    tar.extractall(repos_dir)
    tar.close()


def setup():
    if os.path.exists(repos_dir):
        shutil.rmtree(repos_dir)
    os.mkdir(repos_dir)

    for tar in os.listdir(tar_dir):
        untar(tar)


def get_initial_opts():
    prev_initial_opts = {}
    fancyopts.fancyopts([], cmdtable[b'postreview'][1], prev_initial_opts)
    initial_opts = {}
    for key in prev_initial_opts.keys():
        initial_opts[key.decode("utf-8")] = prev_initial_opts[key]
    return initial_opts


def get_repo(ui, name):
    if type(name) == bytes:
        name = name.decode("utf-8")
    repo_path = '%s/%s' % (repos_dir, name)
    repo = hg.repository(ui, str.encode(repo_path))
    return repo


def mock_ui():
    def create_mock(ui):
        mock = Mock(wraps=ui)

        # used by diff in patch.py
        mock.quiet = False
        mock.debugflag = False

        # suppress the loading of extensions in extensions.py
        configitems_mock = Mock()
        configitems_mock.return_value = []
        mock.configitems = configitems_mock

        # set some default config values
        mock.setconfig(b'reviewboard', b'server', b'http://example.com/')
        mock.setconfig(b'reviewboard', b'user', b'foo')
        mock.setconfig(b'reviewboard', b'password', b'bar')
        # probably best to prevent reading from the user's 
        # hgrc but this should do for now
        mock.setconfig(b'reviewboard', b'repoid', None);
        mock.setconfig(b'reviewboard', b'launch_webbrowser', b'false')

        def copy_side_effect():
            copy = ui.copy()
            return create_mock(copy)

        copy_mock = Mock()
        copy_mock.side_effect = copy_side_effect
        mock.copy = copy_mock

        # block out command line interaction
        mock.prompt = Mock()
        mock.getpass = Mock()

        return mock

    return create_mock(ui.ui())
