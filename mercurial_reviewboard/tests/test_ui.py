from mock import Mock, patch_object
from nose.tools import eq_

from mercurial import ui as hg_ui
import mercurial_reviewboard
from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo

expected_status = 'changesets:\n\t1:669e757d4a24 "1"\n\t0:a8ea53640b24 "0"\n\n'

@patch_object(mercurial_reviewboard, 'create_review')
def test_changeset_shown(mock_create_method):
    ui = hg_ui.ui()
    ui.status = Mock()
    
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    opts['parent'] = '000000'
    postreview(ui, repo, **opts)
    
    eq_(expected_status, ui.status.call_args_list[1][0][0])
    
@patch_object(mercurial_reviewboard, 'update_review')
def test_changeset_shown_on_existing(mock_create_method):
    ui = hg_ui.ui()
    ui.status = Mock()
    
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    opts['parent'] = '000000'
    opts['update'] = False
    opts['existing'] = '1'
    postreview(ui, repo, **opts)
    
    eq_(expected_status, ui.status.call_args_list[1][0][0])
