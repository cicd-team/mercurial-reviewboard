from mock import Mock
from nose.tools import eq_

from mercurial_reviewboard import find_reviewboard_repo_id
from mercurial_reviewboard.reviewboard import Repository
from mercurial_reviewboard.tests import get_initial_opts, mock_ui


def test_repo_id_autodetect():
    opts = get_initial_opts()
    opts['outgoingrepo'] = b'http://b.example.org'

    mock_reviewboard = Mock()
    repositories = [Repository(1, 'a', 'Mercurial', 'http://a.example.org'),
                    Repository(2, 'b', 'Mercurial', 'http://b.example.org')]
    mock_reviewboard.repositories.return_value = repositories

    eq_('2', find_reviewboard_repo_id(mock_ui(), mock_reviewboard, opts))


def test_repo_id_autodetect_fuzzy1():
    opts = get_initial_opts()
    opts['outgoingrepo'] = b'http://b.example.org/'

    mock_reviewboard = Mock()
    repositories = [Repository(1, 'a', 'Mercurial', 'http://a.example.org'),
                    Repository(2, 'b', 'Mercurial', 'http://b.example.org')]
    mock_reviewboard.repositories.return_value = repositories

    eq_('2', find_reviewboard_repo_id(mock_ui(), mock_reviewboard, opts))


def test_repo_id_autodetect_fuzzy2():
    opts = get_initial_opts()
    opts['outgoingrepo'] = b'http://b.example.org'

    mock_reviewboard = Mock()
    repositories = [Repository(1, 'a', 'Mercurial', 'http://a.example.org'),
                    Repository(2, 'b', 'Mercurial', 'http://b.example.org/')]
    mock_reviewboard.repositories.return_value = repositories

    eq_('2', find_reviewboard_repo_id(mock_ui(), mock_reviewboard, opts))


def test_repo_id_from_opts():
    opts = get_initial_opts()
    opts['repoid'] = '101'
    eq_('101', find_reviewboard_repo_id(None, None, opts))
