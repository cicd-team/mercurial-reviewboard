from mercurial import fancyopts
from nose.tools import eq_

from mercurial_reviewboard import cmdtable


def test_existing():
    opts = {}
    fancyopts.fancyopts([b'-e', b'101'], cmdtable[b'postreview'][1], opts, True)
    eq_(b'101', opts[b'existing'])


def test_update():
    opts = {}
    args = fancyopts.fancyopts([b'-u'], cmdtable[b'postreview'][1], opts, True)
    eq_(True, opts[b'update'])


def test_target_groups():
    opts = {}
    args = fancyopts.fancyopts([b'-G', b'foo, bar'], cmdtable[b'postreview'][1],
                               opts, True)
    eq_(b'foo, bar', opts[b'target_groups'])


def test_target_people():
    opts = {}
    args = fancyopts.fancyopts([b'-U', b'john, jane'], cmdtable[b'postreview'][1],
                               opts, True)
    eq_(b'john, jane', opts[b'target_people'])


def test_repoid():
    opts = {}
    args = fancyopts.fancyopts([b'-i', b'101'], cmdtable[b'postreview'][1], opts, True)
    eq_(b'101', opts[b'repoid'])
