from nose.tools import eq_

from mercurial import ui as hg_ui
from mercurial_reviewboard import createfields
from mercurial_reviewboard.tests import get_initial_opts, get_repo

class TestCreateFields:
    
    def setup(self):
        ui = hg_ui.ui()
        repo = get_repo(ui, 'two_revs')
        opts = get_initial_opts()
        
        c = repo[1]
        parentc = repo['000000']
        
        self.fields = createfields(ui, repo, c, parentc, opts)
    
    def test_createfields_summary(self):
        eq_('1', self.fields['summary'])
        
    def test_createfields_description(self):
        expected = "-- 0\n-- 1\n"
        eq_(expected, self.fields['description'])