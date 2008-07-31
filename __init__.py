# reviewboard extension for mercurial

import os, errno, re
from mercurial import cmdutil, hg, ui, patch, util
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

    def getdiff(repo, rev):
        '''return diff for the specified revision'''
        patches = []

        class exportee:
            def __init__(self, container):
                self.lines = []
                self.container = container
                self.name = 'memory'

            def write(self, data):
                self.lines.append(data)

            def close(self):
                self.container.append(''.join(self.lines).split('\n'))
                self.lines = []

        patch.export(repo, [rev], template=exportee(patches))

        return '\n'.join(patches[0])

    fields = {}

    c                       = repo.changectx(rev)
    fields['summary']       = c.description().splitlines()[0]
    fields['description']   = c.description()
    fields['diff']          = getdiff(repo, rev)
    for field in ('target_groups', 'target_people'):
        value = ui.config('reviewboard', field)
        if value:
            fields[field] = value

    reviewboard = ReviewBoard(server)

    ui.status('changeset:\t%s:%s "%s"\n' % (rev, c, c.description()) )
    ui.status('revieboard:\t%s\n' % server)
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
            reviewboard.update_request(request_id, fields)
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
            repo_id = ui.prompt('repository id:', '\d+')
        else:
            repo_id = repositories[0]['id']
            ui.status('repository id: %s\n' % repo_id)

        try:
            request_id = reviewboard.new_request(repo_id, fields)
        except ReviewBoardError, msg:
            raise util.Abort(_(msg))

    request_url = '%s/%s/%s/' % (server, "r", request_id)

    if not request_url.startswith('http'):
        request_url = 'http://%s' % request_url

    ui.status('review request draft saved: %s\n' % request_url)

cmdtable = {
    "postreview":
        (postreview,
        [('r', 'requestid', '', _('request ID to update')),
        ],
         _('hg postreview [OPTION]... [REVISION]')),
}