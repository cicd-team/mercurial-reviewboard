from nose.tools import eq_

from mercurial import fancyopts
from mercurial_reviewboard import cmdtable

def test_existing():
    opts = {}
    fancyopts.fancyopts(['-e', '101'], cmdtable['postreview'][1], opts, True)
    eq_('101', opts['existing'])
    
def test_update():
    opts = {}
    args = fancyopts.fancyopts(['-u'], cmdtable['postreview'][1], opts, True)
    eq_(True, opts['update'])    
    
def test_target_groups():
    opts = {}
    args = fancyopts.fancyopts(['-G', 'foo, bar'], cmdtable['postreview'][1], 
                               opts, True)
    eq_('foo, bar', opts['target_groups'])

def test_target_people():
    opts = {}
    args = fancyopts.fancyopts(['-U', 'john, jane'], cmdtable['postreview'][1], 
                               opts, True)
    eq_('john, jane', opts['target_people'])