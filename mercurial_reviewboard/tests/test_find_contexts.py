from nose.tools import eq_

from mercurial import ui as hg_ui, hg
from mercurial_reviewboard import find_contexts
from mercurial_reviewboard.tests import repos_dir 

def get_repo():
    repo_path = '%s/two_revs' % repos_dir
    ui = hg_ui.ui()
    repo = hg.repository(ui, repo_path)
    return repo

def test_find_two_contexts():
    repo = get_repo()
    
    contexts = find_contexts(repo, repo['000000'], repo[1])
        
    eq_(2, len(contexts))
    
def test_find_one_context():
    repo = get_repo()
    
    contexts = find_contexts(repo, repo[0], repo[1])
        
    eq_(1, len(contexts))