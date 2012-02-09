from mock import patch
from nose.tools import eq_

from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

@patch('mercurial_reviewboard.send_review')
def test_branch(mock_send):
    ui = mock_ui()

    repo = get_repo(ui, 'branch')
    opts = get_initial_opts()
    opts['branch'] = True
    opts['outgoingchanges'] = False
    opts['outgoing'] = False
    
    postreview(ui, repo, **opts)
    
    expected = open('mercurial_reviewboard/tests/diffs/branch', 'r').read()
    eq_(expected, mock_send.call_args[0][4])
