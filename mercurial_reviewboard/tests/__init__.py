import os, os.path, shutil, tarfile

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
