import os, shutil, subprocess

test_dir    = 'mercurial_reviewboard/tests'
scripts_dir = '%s/scripts/' % test_dir
repos_dir   = '%s/repos'    % test_dir

def setup():
    shutil.rmtree(repos_dir, ignore_errors=True)
    os.mkdir(repos_dir)
    
    no_revs = './create_no_revs'
    subprocess.call([no_revs],  cwd=scripts_dir, shell=True)
    
    two_revs = './create_two_revs'
    subprocess.call([two_revs], cwd=scripts_dir, shell=True)