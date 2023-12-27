from nose.tools import eq_

from mercurial_reviewboard import remoteparent
from mercurial_reviewboard.tests import get_repo, repos_dir, mock_ui, get_initial_opts


def test_remoteparent_is_empty():
    ui = mock_ui()
    child_repo_path = str.encode('%s/no_revs' % repos_dir)
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    parent = remoteparent(ui, repo, opts, repo[repo.revs('.').first()], upstream=child_repo_path)

    eq_(b'0000000000000000000000000000000000000000', parent.hex())
