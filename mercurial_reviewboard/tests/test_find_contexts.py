from nose.tools import eq_

from mercurial_reviewboard import find_contexts
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

def test_find_two_contexts():
    repo = get_repo(mock_ui(), 'two_revs')
    
    opts = get_initial_opts()
    contexts = find_contexts(repo, repo['000000'], repo[1], opts)
        
    eq_(2, len(contexts))
    
def test_find_one_context():
    repo = get_repo(mock_ui(), 'two_revs')
    
    opts = get_initial_opts()
    contexts = find_contexts(repo, repo[0], repo[1], opts)
        
    eq_(1, len(contexts))