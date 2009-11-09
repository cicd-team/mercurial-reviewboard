from nose.tools import eq_

from mercurial import ui as hg_ui
from mercurial_reviewboard import remoteparent
from mercurial_reviewboard.tests import get_repo, repos_dir

def test_remoteparent_is_empty():
    ui = hg_ui.ui()
    child_repo_path  = '%s/no_revs'  % repos_dir
    
    repo = get_repo(ui, 'two_revs')
    
    parent = remoteparent(ui, repo, 1, upstream=child_repo_path)
    
    eq_('0000000000000000000000000000000000000000', parent.hex())