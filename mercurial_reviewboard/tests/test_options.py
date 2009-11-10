from nose.tools import raises

from mercurial import util
from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, mock_ui

@raises(util.Abort)
def test_no_parent_combo():
    "You cannot have more than one parent revision."
    
    opts = get_initial_opts()
    opts['parent'] = 1
    opts['outgoingchanges'] = True
    postreview(mock_ui(), None, **opts)