from mock import patch
from nose.tools import eq_

import mercurial_reviewboard
from mercurial_reviewboard import createfields
from mercurial_reviewboard.tests import get_initial_opts, get_repo, mock_ui

changesets_string = ('changesets:\n'
                     '\t1:669e757d4a24 "1"\n'
                     '\t0:a8ea53640b24 "0"\n')

def set_up_two_revs():
    ui = mock_ui()
    repo = get_repo(ui, 'two_revs')
    opts = get_initial_opts()
    
    c = repo[1]
    parentc = repo['000000']
    
    return ui, repo, c, parentc, opts

def test_target_people():
    ui, repo, c, parentc, opts = set_up_two_revs()
    opts['target_people'] = 'john, jane'
    fields = createfields(ui, repo, c, parentc, opts)
    eq_('john, jane', fields['target_people'])
    
def test_target_groups():
    ui, repo, c, parentc, opts = set_up_two_revs()
    opts['target_groups'] = 'foo, bar'
    fields = createfields(ui, repo, c, parentc, opts)
    eq_('foo, bar', fields['target_groups'])

def test_branch_description():
    ui = mock_ui()
    repo = get_repo(ui, 'branch')
    opts = get_initial_opts()
    opts['branch'] = True
    
    c = repo[4]
    parentc = repo[0]
    
    fields = createfields(ui, repo, c, parentc, opts)
    
    expected = ('review of branch: the_branch\n\n'
                'changesets:\n'
                '\t4:173fa0623445 "4"\n'
                '\t3:0c15fa2e6ba5 "3"\n')
    
    eq_(expected, fields['description'])

class TestCreateFieldsRevisionDetails:
    
    def setup(self):
        ui, repo, c, parentc, opts = set_up_two_revs()
        
        self.fields = createfields(ui, repo, c, parentc, opts)
    
    def test_createfields_summary(self):
        eq_('1', self.fields['summary'])
        
    def test_createfields_description(self):
        expected = changesets_string
        eq_(expected, self.fields['description'])
        
class TestCreateFieldsRevisionDetailsInteractive:
    
    def setup(self):
        self.ui, self.repo, self.c, self.parentc, self.opts = set_up_two_revs()
        self.opts['interactive'] = True        
    
    @patch.object(mercurial_reviewboard, 'readline')
    def test_createfields_summary(self, mock_read):
        mock_read.side_effect = create_mock_results(['foo', '', 'n'])
        
        fields = self.get_fields()
        eq_('foo', fields['summary'])
    
    @patch.object(mercurial_reviewboard, 'readline')    
    def test_createfields_summary_default(self, mock_read):
        mock_read.side_effect = create_mock_results(['', '', 'n'])
        
        fields = self.get_fields()
        eq_('1', fields['summary'])
        
    def test_createfields_descriptions(self):
        # args = [<summary>, <description>, <include_changesets_flag>]
        args_list = (
            (['', 'foo', 'n'], 'foo'),
            (['', '',    'n'], ''),
            (['', '',    'y'], changesets_string),
            (['', 'foo', 'y'], 'foo\n\n' + changesets_string),
            (['', 'foo', ''], 'foo\n\n' + changesets_string)
        )
        
        for args in args_list:
            yield self.check_createfields_description, args[0], args[1]
    
    @patch.object(mercurial_reviewboard, 'readline')        
    def check_createfields_description(self, results, description, mock_read):
        mock_read.side_effect = create_mock_results(results)
        
        fields = self.get_fields()
        eq_(description, fields['description'])
        
    def get_fields(self):
        return createfields(self.ui, self.repo, self.c, self.parentc,
                                     self.opts)
        
def create_mock_results(results):
    def side_effect(*args, **kwargs):
        return results.pop(0)
    return side_effect
        
