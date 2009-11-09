from mock import patch
from nose.tools import eq_

from mercurial import ui as hg_ui
from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo

@patch('mercurial_reviewboard.send_review')
def test_outgoing(mock_send):
    ui = hg_ui.ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    opts['outgoingrepo'] = 'mercurial_reviewboard/tests/repos/no_revs'
    opts['outgoingchanges'] = True
    postreview(ui, repo, **opts)
    
    expected = open('mercurial_reviewboard/tests/diffs/outgoing', 'r').read()
    eq_(expected, mock_send.call_args[0][4])