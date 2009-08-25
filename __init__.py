'''post changesets to a reviewboard server'''

import os, errno, re
import cStringIO
from mercurial import cmdutil, hg, ui, mdiff, patch, util
from mercurial.i18n import _
from mercurial import demandimport
demandimport.disable()

from reviewboard import ReviewBoard, ReviewBoardError

def postreview(ui, repo, rev='tip', **opts):
    '''post a changeset to a Review Board server

This command creates a new review request on a Review Board server, or updates
an existing review request, based on a changeset in the repository. If no
revision number is specified the tip revision is used.

By default, the diff uploaded to the server is based on the parent of the
revision to be reviewed. A different parent may be specified using the
--parent option.

If the parent revision is not available to the Review Board server (e.g. it
exists in your local repository but not in the one that Review Board has
access to) you must tell postreview how to determine the base revision
to use for a parent diff. The --outgoing, --outgoingrepo or --master options
may be used for this purpose. The --outgoing option is the simplest of these;
it assumes that the upstream repository specified in .hg/hgrc is the same as
the one known to Review Board. The other two options offer more control if
this is not the case.
'''

    outgoing = opts.get('outgoing')
    outgoingrepo = opts.get('outgoingrepo')
    master = opts.get('master')
    
    if outgoingrepo:
        rrepo = remoterepo(ui, outgoingrepo)
    else:
        rrepo = remoterepo(ui)

    if rev.find(':') != -1:
        # we accept the standard range format, where the lower bound is 
        # exclusive, and translate it to the first included revision (rev1)
        lower_bound, rev2 = rev.split(':')
        rev1 = repo.changectx(lower_bound).rev() + 1
    elif rev == 'outgoing':
        ui.status('inferring revision range from outgoing changes\n')
        out = repo.findoutgoing(rrepo)
        out = repo.changelog.nodesbetween(out, [repo.changectx('tip').node()])[0]
        rev1 = repo[out[0]].rev()
        rev2 = repo[out[-1]].rev()
    else:
        rev1 = rev
        rev2 = rev

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
        parent = repo[rev1].parents()[0]

    if master:
        rparent = repo[master]
    elif outgoingrepo or outgoing:
        rparent = remoteparent(ui, repo, rev1, rrepo)
    else:
        rparent = None

    ui.debug(_('Parent is %s\n' % parent))
    ui.debug(_('Remote parent is %s\n' % rparent))

    request_id = None

    if opts.get('existing'):
        request_id = opts.get('existing')

    fields = {}

    c1 = repo.changectx(rev1)
    c2 = repo.changectx(rev2)
    all_contexts = _find_contexts(repo, c1, c2)

    # Don't clobber the summary and description for an existing request
    # unless specifically asked for    
    if opts.get('update') or not request_id:
        fields['summary']       = c2.description().splitlines()[0]
        fields['description']   = _create_description(all_contexts)

    diff = getdiff(ui, repo, c2, parent)
    ui.debug('\n=== Diff from parent to rev2 ===\n')
    ui.debug(diff + '\n')

    if rparent and parent != rparent:
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

    # TODO: add all changesets
    ui.status('changesets:\n')
    for ctx in all_contexts:
        ui.status('\t%s:%s "%s"\n' % (ctx.rev(), ctx, ctx.description()))
        
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

    if request_id:
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
        repo_ids = set()
        for r in repositories:
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

def remoterepo(ui, upstream=None):
    if upstream:
        remotepath = ui.expandpath(upstream)
    else:
        remotepath = ui.expandpath('default-push', 'default')
    rrepo = hg.repository(ui, remotepath)
    return rrepo

def remoteparent(ui, repo, rev, remoterepo):
    out = repo.findoutgoing(remoterepo)
    ancestors = repo.changelog.ancestors([repo.lookup(rev)])
    for o in out:
        orev = repo[o]
        a, b, c = repo.changelog.nodesbetween([orev.node()], [repo[rev].node()])
        if a:
            return orev.parents()[0]
        
def _find_contexts(repo, ctx1, ctx2):
    contexts = []
    for node in repo.changelog.nodesbetween([ctx1.node()],[ctx2.node()])[0]:
        contexts.append(repo[node])
    return contexts

def _create_description(contexts):
    description = ''
    for context in contexts:
        description += "-- %s\n" % context.description()
    return description

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
        ('', 'parent', '', _('parent revision for the uploaded diff'))
        ],
        _('hg postreview [OPTION]... [REVISION]')),
}
