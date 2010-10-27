from mock import Mock, patch
from nose.tools import eq_

import mercurial_reviewboard
from mercurial_reviewboard import postreview
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

class TestChangesetsOutput:
    
    expected_status = \
        'changesets:\n\t1:669e757d4a24 "1"\n\t0:a8ea53640b24 "0"\n\n'

    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_shown(self, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = '000000'
        postreview(ui, repo, **opts)
        
        eq_(self.expected_status, ui.status.call_args_list[1][0][0])
        
    @patch.object(mercurial_reviewboard, 'update_review')
    def test_changeset_shown_on_existing(self, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        opts['parent'] = '000000'
        opts['update'] = False
        opts['existing'] = '1'
        postreview(ui, repo, **opts)
        
        eq_(self.expected_status, ui.status.call_args_list[1][0][0])


class TestMerge:
    
    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_shown(self, mock_create_method):
        """status should show all revisions on all included branches"""
        expected_status = \
            'changesets:\n\t5:1de20dbad49b "5"'\
            '\n\t4:d955e65420c8 "4"\n\t3:13a89135f389 "3"'\
            '\n\t2:e97ab41d91c8 "2"'\
            '\n\t1:7051d9f99104 "1"\n\t0:1d4da73b2570 "0"\n\n'
        
        ui = mock_ui()
        
        repo = get_repo(ui, 'merge')
        opts = get_initial_opts()
        opts['parent'] = '000000'
        postreview(ui, repo, **opts)
        
        eq_(expected_status, ui.status.call_args_list[1][0][0])
        
    @patch.object(mercurial_reviewboard, 'new_review')
    def test_changeset_on_branch(self, mock_create_method):
        """in branch mode only show revisions on branch"""
        expected_status = \
            'review of branch: default\n\n'\
            'changesets:\n\t5:1de20dbad49b "5"'\
            '\n\t2:e97ab41d91c8 "2"'\
            '\n\t1:7051d9f99104 "1"\n\t0:1d4da73b2570 "0"\n\n'

        ui = mock_ui()

        repo = get_repo(ui, 'merge')
        opts = get_initial_opts()
        opts['branch'] = True
        postreview(ui, repo, **opts)

        eq_(expected_status, ui.status.call_args_list[1][0][0])


class TestLaunchBrowser:

    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_default(self, mock_launch, mock_create_method):
        ui = mock_ui()
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_launch.called == False
        
    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_false(self, mock_launch, mock_create_method):
        ui = mock_ui()
        ui.setconfig('reviewboard', 'launch_webbrowser', 'false')
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_launch.called == False
        
    @patch.object(mercurial_reviewboard, 'new_review')
    @patch.object(mercurial_reviewboard, 'launch_webbrowser')
    def test_browser_launch_true(self, mock_launch, mock_create_method):
        ui = mock_ui()
        ui.setconfig('reviewboard', 'launch_webbrowser', 'true')
        
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        postreview(ui, repo, **opts)
        assert mock_launch.called
        
