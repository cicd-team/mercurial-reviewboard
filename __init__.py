'''reviewboard extension for mercurial

This extension adds a new command 'postreview' to post changesets for
review to a reviewboard server.

For more information about Review Board see: http://www.review-board.org/


CONFIGURATION:

Configure your .hgrc to enable the extension by adding following lines:

--- ~/.hgrc ---
[extensions]
reviewboard = /path/to/reviewboard

[reviewboard]
# REQUIRED ITEMS:
server          = http://reviewboard.example.com/

# OPTIONAL ITEMS:
# user            = ... # username for login
# target_groups   = ... # default review groups
# target_people   = ... # default review people
--- ~/.hgrc ---


USAGE:

To post the tip changeset to the Review board server:

$ hg postreview tip
login to http://reviewboard.example.com
username: ...
password:
Repositories:
[1] Stuff
[2] miscrepo
repository id: 1
review request draft saved: http://reviewboard.example.com/r/366/

To update the review request ID 12 with the tip changeset:

$ hg postreview -r 12 tip
login to http://reviewboard.example.com
username: ...
password:
review request draft saved: http://reviewboard.example.com/r/12/

Copyright (C) 2008 Dennis Schoen <dennis.schoen@epublica.de>
'''



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

    def getdiff(repo, r):
        '''return diff for the specified revision'''
        output = cStringIO.StringIO()
        p = patch.export(repo, [r], fp=output, opts=mdiff.diffopts())
        return output.getvalue()

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
            repo_id = ui.prompt('repository id:', "[0-9]+", 0)
        else:
            repo_id = repositories[0]['id']
            ui.status('repository id: %s\n' % repo_id)

        try:
            request_id = reviewboard.new_request(repo_id, fields)
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

cmdtable = {
    "postreview":
        (postreview,
        [('r', 'requestid', '', _('request ID to update')),
        ('p', 'publish', None, _('publish request immediately')),
        ],
         _('hg postreview [OPTION]... [REVISION]')),
}
