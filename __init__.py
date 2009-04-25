# reviewboard extension for mercurial

import os, errno, re
import cStringIO
from mercurial import cmdutil, hg, ui, mdiff, patch, util
from mercurial.i18n import _
from mercurial import demandimport
demandimport.disable()

from reviewboard import ReviewBoard, ReviewBoardError

def postreview(ui, repo, rev='tip', **opts):
    '''post changeset to a reviewboard server'''

    server = ui.config('reviewboard', 'server')
    if not server:
        raise util.Abort(
                _('please specify a reviewboard server in your .hgrc file') )

    def getdiff(ui, repo, r, parent):
        '''return diff for the specified revision'''
        output = ""
        for chunk in patch.diff(repo, parent.node(), r.node()):
            output += chunk
        return output

    parent = opts.get('parent')
    if parent:
        parent = repo[parent]
    else:
        parent = repo[rev].parents()[0]

    rparent = remoteparent(ui, repo, rev)

    ui.debug(_('Parent is %s\n' % parent))
    ui.debug(_('Remote parent is %s\n' % rparent))

    fields = {}

    c                       = repo.changectx(rev)
    fields['summary']       = c.description().splitlines()[0]
    fields['description']   = c.description()

    diff = getdiff(ui, repo, c, parent)
    ui.debug('\n=== Diff from parent to rev ===\n')
    ui.debug(diff + '\n')

    if parent != rparent:
        parentdiff = getdiff(ui, repo, parent, rparent)
        ui.debug('\n=== Diff from rparent to parent ===\n')
        ui.debug(parentdiff + '\n')
    else:
        parentdiff = ''

    for field in ('target_groups', 'target_people'):
        value = ui.config('reviewboard', field)
        if value:
            fields[field] = value

    reviewboard = ReviewBoard(server)

    ui.status('changeset:\t%s:%s "%s"\n' % (rev, c, c.description()) )
    ui.status('reviewboard:\t%s\n' % server)
    ui.status('\n')
    username = ui.config('reviewboard', 'user')
    if username:
        ui.status('username: %s\n' % username)
    else:
        username = ui.prompt('username:')
    password = ui.getpass()

    try:
        reviewboard.login(username, password)
    except ReviewBoardError, msg:
        raise util.Abort(_(msg))

    request_id = False

    if opts.get('requestid'):
        request_id = opts.get('requestid')
        try:
            reviewboard.update_request(request_id, fields, diff, parentdiff)
        except ReviewBoardError, msg:
            raise util.Abort(_(msg))
    else:
        try:
            repositories = reviewboard.repositories()
        except ReviewBoardError, msg:
            raise util.Abort(_(msg))

        if not repositories:
            raise util.Abort(_('no repositories configured at %s' % server))

        ui.status('Repositories:\n')
        for r in repositories:
            ui.status('[%s] %s\n' % (r['id'], r['name']) )
        if len(repositories) > 1:
            repo_id = ui.prompt('repository id:', "[0-9]+", 0)
        else:
            repo_id = repositories[0]['id']
            ui.status('repository id: %s\n' % repo_id)

        try:
            request_id = reviewboard.new_request(repo_id, fields, diff, parentdiff)
            if opts.get('publish'):
                reviewboard.publish(request_id)
        except ReviewBoardError, msg:
            raise util.Abort(_(msg))

    request_url = '%s/%s/%s/' % (server, "r", request_id)

    if not request_url.startswith('http'):
        request_url = 'http://%s' % request_url

    msg = 'review request draft saved: %s\n'
    if opts.get('publish'):
        msg = 'review request published: %s\n'
    ui.status(msg % request_url)

def remoteparent(ui, repo, rev):
    remotepath = ui.expandpath('default-push', 'default')
    remoterepo = hg.repository(ui, remotepath)
    out = repo.findoutgoing(remoterepo)
    ancestors = repo.changelog.ancestors([repo.lookup(rev)])
    for o in out:
        orev = repo[o]
        a, b, c = repo.changelog.nodesbetween([orev.node()], [repo[rev].node()])
        if a:
            return orev.parents()[0]

cmdtable = {
    "postreview":
        (postreview,
        [('r', 'requestid', '', _('request ID to update')),
        ('p', 'publish', None, _('publish request immediately')),
        ('', 'parent', '', _('parent revision'))
        ],
         _('hg postreview [OPTION]... [REVISION]')),
}
