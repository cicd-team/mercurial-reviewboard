import os, os.path, shutil, tarfile

from mock import Mock

from mercurial import fancyopts, hg, ui
from mercurial_reviewboard import cmdtable

test_dir  = 'mercurial_reviewboard/tests'
tar_dir   = '%s/repo_tars' % test_dir
repos_dir = '%s/repos'     % test_dir

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
    initial_opts = {}
    fancyopts.fancyopts([], cmdtable['postreview'][1], initial_opts)
    return initial_opts

def get_repo(ui, name):
    repo_path = '%s/%s' % (repos_dir, name)
    repo = hg.repository(ui, repo_path)
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
        mock.setconfig('reviewboard', 'server',   'http://rb')
        mock.setconfig('reviewboard', 'user',     'foo')
        mock.setconfig('reviewboard', 'password', 'bar')
        
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
