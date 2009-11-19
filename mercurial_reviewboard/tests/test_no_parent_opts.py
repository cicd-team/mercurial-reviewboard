from mock import patch
from nose.tools import eq_

from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

@patch('mercurial_reviewboard.send_review')
def test_outgoing(mock_send):
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    postreview(ui, repo, **opts)
    
    expected = open('mercurial_reviewboard/tests/diffs/two_revs_1', 'r').read()
    eq_(expected, mock_send.call_args[0][4])