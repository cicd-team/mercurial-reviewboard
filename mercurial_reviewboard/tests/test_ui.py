from mock import patch
from nose.tools import eq_, raises

import mercurial_reviewboard
from mercurial_reviewboard import postreview
from mercurial_reviewboard import util
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui


class TestChangesetsOutput:
    expected_status = \
        b'changesets:\n\t1:669e757d4a24 "1"\n\t0:a8ea53640b24 "0"\n\n'

    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_shown(self, mock_create_method):
        ui = mock_ui()

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = b'0000000000000000000000000000000000000000'
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)

        eq_(self.expected_status, ui.status.call_args_list[1][0][0])

    @patch.object(mercurial_reviewboard, 'update_review')
    def test_changeset_shown_on_existing(self, mock_create_method):
        ui = mock_ui()

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = b'0000000000000000000000000000000000000000'
        opts['update'] = False
        opts['existing'] = '1'
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)

        eq_(self.expected_status, ui.status.call_args_list[1][0][0])


class TestMerge:

    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_shown(self, mock_create_method):
        """status should show all revisions on all included branches"""
        expected_status = \
            b'changesets:\n\t5:1de20dbad49b "5"' \
            b'\n\t4:d955e65420c8 "4"\n\t3:13a89135f389 "3"' \
            b'\n\t2:e97ab41d91c8 ' \
            b'"2"\n\t1:7051d9f99104 "1"\n\t0:1d4da73b2570 "0"\n\n'

        ui = mock_ui()

        repo = get_repo(ui, 'merge')
        opts = get_initial_opts()
        opts['parent'] = b'0000000000000000000000000000000000000000'
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)

        eq_(expected_status, ui.status.call_args_list[1][0][0])

    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_on_branch(self, mock_create_method):
        """in branch mode only show revisions on branch"""
        expected_status = \
            b'review of branch: b\'default\'\n\nchangesets:\n\t5:1de20dbad49b "5"\n\t2:e97ab41d91c8 "2"\n\t1:7051d9f99104 "1"\n\t0:1d4da73b2570 "0"\n\n'

        ui = mock_ui()

        repo = get_repo(ui, 'merge')
        opts = get_initial_opts()
        opts['branch'] = True
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)

        eq_(expected_status, ui.status.call_args_list[1][0][0])


class TestLaunchBrowser:

    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_default(self, mock_launch, mock_create_method):
        ui = mock_ui()

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)
        assert mock_launch.called == False

    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_false(self, mock_launch, mock_create_method):
        ui = mock_ui()
        ui.setconfig(b'reviewboard', b'launch_webbrowser', b'false')

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)
        assert mock_launch.called == False

    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_true(self, mock_launch, mock_create_method):
        mock_create_method.return_value = '1'

        ui = mock_ui()
        ui.setconfig(b'reviewboard', b'launch_webbrowser', b'true')

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)
        eq_('http://example.com/r/1/', mock_launch.call_args[0][1])

    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_server_arg(self, mock_launch, mock_create_method):
        mock_create_method.return_value = '1'

        ui = mock_ui()
        ui.setconfig(b'reviewboard', b'launch_webbrowser', b'true')

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['server'] = b'example.org/'
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)
        eq_('http://example.org/r/1/', mock_launch.call_args[0][1])


class TestServerConfiguration:

    # @raises(util.Abort)
    @patch.object(mercurial_reviewboard, 'new_review')
    def test_no_reviewboard_configured(self, mock_create_review):
        try:
            ui = mock_ui()
            ui.setconfig(b'reviewboard', b'server', None)
            repo = get_repo(ui, 'two_revs')
            opts = get_initial_opts()
            postreview(ui, repo, **opts)
            assert 0, "Should have raised an Abort."
        except util.error.Abort as e:
            eq_("please specify a reviewboard server in your .hgrc file or using the --server flag", e.__str__())

    @patch.object(mercurial_reviewboard, 'new_review')
    def test_reviewboard_option(self, mock_create_review):
        ui = mock_ui()
        ui.setconfig(b'reviewboard', b'server', None)

        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['server'] = b'example.com'
        opts['outgoingchanges'] = False
        opts['outgoing'] = False
        postreview(ui, repo, **opts)
        assert mock_create_review.called
