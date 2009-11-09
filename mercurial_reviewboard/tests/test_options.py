from nose.tools import raises

from mercurial import ui, util
from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts

@raises(util.Abort)
def test_no_parent_combo():
    "You cannot have more than one parent revision."
    
    initial_opts = get_initial_opts()
    initial_opts['parent'] = 1
    initial_opts['outgoingchanges'] = True
    postreview(ui.ui(), None, **initial_opts)