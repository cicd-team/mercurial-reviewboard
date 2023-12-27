from mercurial import util
from nose.tools import eq_, raises

from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, mock_ui


# @raises(util.Abort)
def test_no_parent_combo():
    try:
        "You cannot have more than one parent revision."
        opts = get_initial_opts()
        opts['parent'] = 1
        opts['outgoingchanges'] = True
        postreview(mock_ui(), None, **opts)
    except util.error.Abort as e:
        eq_("you cannot combine the --parent, --outgoingchanges and --branch options", e.__str__())
