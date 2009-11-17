from nose.tools import eq_

from mercurial_reviewboard import find_reviewboard_repo_id
from mercurial_reviewboard.tests import get_initial_opts

def test_repo_id_from_opts():
    opts = get_initial_opts()
    opts['repoid'] = '101'
    eq_(101, find_reviewboard_repo_id(None, None, opts))