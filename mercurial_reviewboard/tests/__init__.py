import os, os.path, shutil, tarfile

from mercurial import fancyopts, hg
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
