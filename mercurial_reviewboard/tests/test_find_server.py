from nose.tools import eq_, raises

from mercurial_reviewboard import find_server, util
from mercurial_reviewboard.tests import get_initial_opts, mock_ui


def test_find_server_from_hgrc():
    ui = mock_ui()
    opts = get_initial_opts()
    
    server = find_server(ui, opts)
    eq_('http://example.com', server)


def test_find_server_from_command_line():
    ui = mock_ui()
    opts = get_initial_opts()
    opts['server'] = 'http://example.org'
    
    server = find_server(ui, opts)
    eq_('http://example.org', server)


def test_find_server_from_command_line_no_hgrc():
    ui = mock_ui()
    ui.setconfig('reviewboard', 'server', None)
    opts = get_initial_opts()
    opts['server'] = 'http://example.org'

    server = find_server(ui, opts)
    eq_('http://example.org', server)


@raises(util.Abort)
def test_find_server_not_defined():
    ui = mock_ui()
    ui.setconfig('reviewboard', 'server', None)
    opts = get_initial_opts()

    find_server(ui, opts)