from nose.tools import eq_

from mercurial_reviewboard import remoteparent
from mercurial_reviewboard.tests import get_repo, repos_dir, mock_ui

def test_remoteparent_is_empty():
    ui = mock_ui()
    child_repo_path  = '%s/no_revs'  % repos_dir
    
    repo = get_repo(ui, 'two_revs')
    
    parent = remoteparent(ui, repo, repo.changectx(1), upstream=child_repo_path)
    
    eq_('0000000000000000000000000000000000000000', parent.hex())