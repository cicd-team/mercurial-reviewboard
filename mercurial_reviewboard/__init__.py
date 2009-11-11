'''post changesets to a reviewboard server'''

import os, errno, re, sys
import cStringIO
import operator

from mercurial import cmdutil, hg, ui, mdiff, patch, util
from mercurial.i18n import _
from mercurial import demandimport
demandimport.disable()

from reviewboard import ReviewBoard, ReviewBoardError

__version__ = '1.3.0'

def postreview(ui, repo, rev='tip', **opts):
    '''post a changeset to a Review Board server

This command creates a new review request on a Review Board server, or updates
an existing review request, based on a changeset in the repository. If no
revision number is specified the tip revision is used.

By default, the diff uploaded to the server is based on the parent of the
revision to be reviewed. A different parent may be specified using the
--parent option.  Alternatively you may specify --outgoingchanges to calculate
the parent based on the outgoing changesets or --branch to choose the parent
revision of the branch.

If the parent revision is not available to the Review Board server (e.g. it
exists in your local repository but not in the one that Review Board has
access to) you must tell postreview how to determine the base revision
to use for a parent diff. The --outgoing, --outgoingrepo or --master options
may be used for this purpose. The --outgoing option is the simplest of these;
it assumes that the upstream repository specified in .hg/hgrc is the same as
the one known to Review Board. The other two options offer more control if
this is not the case.
'''

    ui.status('postreview plugin, version %s\n' % __version__)
    
    if not ui.config('reviewboard', 'server'):
        raise util.Abort(
                _('please specify a reviewboard server in your .hgrc file') )
    
    check_parent_options(opts)

    outgoing = opts.get('outgoing')
    outgoingrepo = opts.get('outgoingrepo')
    master = opts.get('master')

    if master:
        rparent = repo[master]
    elif outgoingrepo:
        rparent = remoteparent(ui, repo, rev, upstream=outgoingrepo)
    elif outgoing:
        rparent = remoteparent(ui, repo, rev)
    else:
        rparent = None

    c = repo.changectx(rev)
        
    parent = opts.get('parent')
    outgoingchanges = opts.get('outgoingchanges')
    branch = opts.get('branch')
    
    if outgoingchanges:
        parent = rparent
    elif parent:
        parent = repo[parent]
    elif branch:
        parent = find_branch_parent(ui, c)
    else:
        parent = repo[rev].parents()[0]

    ui.debug(_('Parent is %s\n' % parent))
    ui.debug(_('Remote parent is %s\n' % rparent))

    diff = getdiff(ui, repo, c, parent)
    ui.debug('\n=== Diff from parent to rev ===\n')
    ui.debug(diff + '\n')

    if rparent and parent != rparent:
        parentdiff = getdiff(ui, repo, parent, rparent)
        ui.debug('\n=== Diff from rparent to parent ===\n')
        ui.debug(parentdiff + '\n')
    else:
        parentdiff = ''

    send_review(ui, repo, c, parent, diff, parentdiff, opts)
    
def send_review(ui, repo, c, parentc, diff, parentdiff, opts):
    
    fields = createfields(ui, repo, c, parentc, opts)

    request_id = opts['existing']
    if request_id:
        update_review(request_id, ui, fields, diff, parentdiff)
    else:
        request_id = new_review(ui, fields, diff, parentdiff, 
                                   opts)

    request_url = '%s/%s/%s/' % (ui.config('reviewboard', 'server'), 
                                 "r", request_id)

    if not request_url.startswith('http'):
        request_url = 'http://%s' % request_url

    msg = 'review request draft saved: %s\n'
    if opts['publish']:
        msg = 'review request published: %s\n'
    ui.status(msg % request_url)
    
def getdiff(ui, repo, r, parent):
    '''return diff for the specified revision'''
    output = ""
    for chunk in patch.diff(repo, parent.node(), r.node()):
        output += chunk
    return output

def getreviewboard(ui):
    server = ui.config('reviewboard', 'server')
    
    reviewboard = ReviewBoard(server)
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
    
    return reviewboard

def update_review(request_id, ui, fields, diff, parentdiff):
    reviewboard = getreviewboard(ui)
    try:
        reviewboard.update_request(request_id, fields, diff, parentdiff)
    except ReviewBoardError, msg:
        raise util.Abort(_(msg))
    
def new_review(ui, fields, diff, parentdiff, opts):
    reviewboard = getreviewboard(ui)
    try:
        repositories = reviewboard.repositories()
    except ReviewBoardError, msg:
        raise util.Abort(_(msg))

    if not repositories:
        raise util.Abort(_('no repositories configured at %s' % server))

    repositories = sorted(repositories, key=operator.itemgetter('name'),
                          cmp=lambda x, y: cmp(x.lower(), y.lower()))
    
    remotepath = expandpath(ui, opts['outgoingrepo']).lower()
    repo_id = None
    for r in repositories:
        if r['tool'] != 'Mercurial':
            continue
        if r['path'].lower() == remotepath:
            repo_id = r['id']
            ui.status('Using repository: %s\n' % r['name'])
    if repo_id == None:
        ui.status('Repositories:\n')
        repo_ids = set()
        for r in repositories:
            if r['tool'] != 'Mercurial':
                continue
            ui.status('[%s] %s\n' % (r['id'], r['name']) )
            repo_ids.add(str(r['id']))
        if len(repositories) > 1:
            repo_id = ui.prompt('repository id:', 0)
            if not repo_id in repo_ids:
                raise util.Abort(_('invalid repository ID: %s') % repo_id)
        else:
            repo_id = repositories[0]['id']
            ui.status('repository id: %s\n' % repo_id)

    try:
        request_id = reviewboard.new_request(repo_id, fields, diff, parentdiff)
        if opts['publish']:
            reviewboard.publish(request_id)
    except ReviewBoardError, msg:
        raise util.Abort(_(msg))
    
    return request_id

def createfields(ui, repo, c, parentc, opts):
    fields = {}
    
    all_contexts = find_contexts(repo, parentc, c)

    changesets_string = 'changesets:\n'
    changesets_string += \
        ''.join(['\t%s:%s "%s"\n' % (ctx.rev(), ctx, ctx.description()) \
                 for ctx in all_contexts])
    ui.status(changesets_string + '\n')

    interactive = opts['interactive']
    request_id = opts['existing']
    # Don't clobber the summary and description for an existing request
    # unless specifically asked for    
    if opts['update'] or not request_id:
        
        # summary
        default_summary = c.description().splitlines()[0]
        if interactive:
            ui.status('default summary: %s\n' % default_summary)
            ui.status('enter summary (or return for default):\n') 
            summary = readline().strip()
            if summary:
                fields['summary'] = summary
            else:
                fields['summary'] = default_summary
        else:
            fields['summary'] = default_summary

        # description
        if interactive:
            ui.status('enter description:\n')
            description = readline().strip()
            ui.status('append changesets to description? (Y/n):\n')
            choice = readline().strip()
            if choice != 'n':
                if description:
                    description += '\n\n'
                description += changesets_string
        else:
            description = changesets_string
        fields['description'] = description 

    for field in ('target_groups', 'target_people'):
        value = ui.config('reviewboard', field)
        if value:
            fields[field] = value    
    
    return fields

def remoteparent(ui, repo, rev, upstream=None):
    remotepath = expandpath(ui, upstream)
    remoterepo = hg.repository(ui, remotepath)
    out = repo.findoutgoing(remoterepo)
    for o in out:
        orev = repo[o]
        a, b, c = repo.changelog.nodesbetween([orev.node()], [repo[rev].node()])
        if a:
            return orev.parents()[0]

def expandpath(ui, upstream):
    if upstream:
        return ui.expandpath(upstream)
    else:
        return ui.expandpath('default-push', 'default')

def check_parent_options(opts):
    usep = bool(opts['parent'])
    useg = bool(opts['outgoingchanges'])
    useb = bool(opts['branch'])
    
    if (usep or useg or useb) and not (usep ^ useg ^ useb):
        raise util.Abort(_(
           "you cannot combine the --parent, --outgoingchanges "
           "and --branch options"))
        
def find_branch_parent(ui, ctx):
    '''Find the parent revision of the 'ctx' branch.'''
    branchname = ctx.branch()
    
    getparent = lambda ctx: ctx.parents()[0]
    
    currctx = ctx
    while getparent(currctx) and currctx.branch() == branchname:
        currctx = getparent(currctx)
        ui.debug('currctx rev: %s; branch: %s\n' % (currctx.rev(), 
                                            currctx.branch()))
    
    return currctx
  
def find_contexts(repo, parentctx, ctx):
    'Find all context between the contexts, excluding the parent context.'
    contexts = []
    for node in repo.changelog.nodesbetween([parentctx.node()],[ctx.node()])[0]:
        if node != parentctx.node():
            contexts.append(repo[node])
    contexts.reverse()
    return contexts

def readline():
    line = sys.stdin.readline()
    return line

cmdtable = {
    "postreview":
        (postreview,
        [
        ('o', 'outgoing', False,
         _('use upstream repository to determine the parent diff base')),
        ('O', 'outgoingrepo', '',
         _('use specified repository to determine the parent diff base')),
        ('m', 'master', '',
         _('use specified revision as the parent diff base')),
        ('e', 'existing', '', _('existing request ID to update')),
        ('u', 'update', False, _('update the fields of an existing request')),
        ('p', 'publish', None, _('publish request immediately')),
        ('', 'parent', '', _('parent revision for the uploaded diff')),
        ('g', 'outgoingchanges', False, 
            _('create diff with all outgoing changes')),
        ('b', 'branch', False, 
            _('create diff of all revisions on the branch')),
        ('i', 'interactive', False, 
            _('override the default summary and description'))
        ],
        _('hg postreview [OPTION]... [REVISION]')),
}
