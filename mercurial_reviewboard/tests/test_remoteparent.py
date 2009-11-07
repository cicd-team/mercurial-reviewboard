from nose.tools import eq_

from mercurial import ui as hg_ui, hg
from mercurial_reviewboard import remoteparent
from mercurial_reviewboard.tests import repos_dir 

def test_remoteparent_is_empty():
    parent_repo_path = '%s/two_revs' % repos_dir
    child_repo_path  = '%s/no_revs'  % repos_dir
    
    ui = hg_ui.ui()
    repo = hg.repository(ui, parent_repo_path)
    
    parent = remoteparent(ui, repo, 1, upstream=child_repo_path)
    
    eq_('0000000000000000000000000000000000000000', parent.hex())