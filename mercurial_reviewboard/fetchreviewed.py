"""
Command to fetch approved changes from reviewboard and apply to relevant
repository.
"""

from pprint import pprint

from mercurial.i18n import _

from mercurial import hg
from mercurial import repair
from mercurial import discovery
from mercurial import scmutil
from mercurial import commands
from mercurial import util

import reviewboard

def fetchreviewed(ui, repo, rev='.', **opts):
    """fetch approved changes from reviewboard and apply to relevant repository.

    This command is intended to be run as part of automated process, that
    imports approved changes from review board.

    It will download bundles, attached to review requests, marked as 'ship-it'
    and import them into working repository. If import results in additional
    head, automatic merge will be attempted.

    If any problems are encountered during bundle import, review request will
    be updated with problem description and further import will not be
    attempted until problem is fixed.

    Operation supports reviews from multiple repositories (of mercurial type).

    Note, that this command will strip all outgoing changes out of working
    repo. This is required  to get a clean clone of remote repo before import.
    """
    from . import find_server, getreviewboard
    find_server(ui, opts)
    reviewboard = getreviewboard(ui, opts)

    rbrepos = get_repositories(ui, reviewboard)

    dryrun = opts.get('dry_run', False)

    lock = repo.lock()
    try:
        for r in rbrepos:
            try:
                switch_to_repo(ui, repo, r)
            except util.Abort, e:
                ui.warn(_("Warning: cannot switch to %s: %s\n") % (r.path, e.message))
                continue
            fetch_for_repo(ui, repo, r, reviewboard, dryrun)
    finally:
        lock.release()

def submit_processed_requests(reviewboard, request):
    for r in requests:
        reviewboard.submit(re.id)

def get_repositories(ui, reviewboard):
    """Return list of registered mercurial repositories"""

    repos = reviewboard.repositories()
    return [r for r in repos if r.tool == 'Mercurial']

def switch_to_repo(ui, repo, rbrepo):
    """Pull changes from repo into local repository, strip all outgoing changes"""
    ui.status(_("Switching to %s\n") % rbrepo.path)
    remoterepo = hg.repository(ui, rbrepo.path)


    ui.pushbuffer()
    try:
        res = repo.pull(remoterepo)
    finally:
        ui.popbuffer()

    clean_working_copy(ui, repo, rbrepo)

def clean_working_copy(ui, repo, rbrepo):
    strip_outgoing(ui, repo, rbrepo.path)

    ui.pushbuffer()
    try:
        commands.update(ui, repo, clean=True)
    finally:
        ui.popbuffer()

def strip_outgoing(ui, repo, remotepath):
    from . import findoutgoing
    remoterepo = hg.repository(ui, remotepath)
    out = findoutgoing(repo, remoterepo)
    if not out:
        return

    cl = repo.changelog
    revs = set([cl.rev(r) for r in out])
    descendants = set(cl.descendants(*revs))
    roots = revs.difference(descendants)

    roots = list(roots)
    roots.sort()
    roots.reverse()
    ui.status("Stripping local revisions %s\n" % roots)

    for node in roots:
        ui.note("Stripping revision %s...\n" % node)
        ui.pushbuffer()
        try:
            repair.strip(ui, repo, cl.node(node), backup='none')
        finally:
            ui.popbuffer()

def fetch_for_repo(ui, repo, rbrepo, reviewboard, dryrun):
    """Fetch changes into given repo"""
    shipable = reviewboard.shipable_requests(rbrepo.name)
    for request in shipable:
        ui.status(_("Processing review request %s\n") % request.id)
        try:
            fetched = fetch_review_request(ui, repo, reviewboard, request)
            if fetched and not dryrun:
                report_success(ui, repo, reviewboard, request)

        except util.Abort, e:
            ui.status(_("Processing of request %s failed (%s)\n") % (request.id, e.message))
            if not dryrun:
                report_failure(ui, repo, reviewboard, request, e)

        clean_working_copy(ui, repo, rbrepo)

def report_success(ui, repo, reviewboard, request):
    push_reviewed(ui, repo, rbrepo)
    reviewboard.rename_attachments_with_caption(request.id,
                                                BUNDLE_ATTACHMENT_CAPTION,
                                                _("%s (submitted)") % BUNDLE_ATTACHMENT_CAPTION)
    reviewboard.publish(request.id)
    reviewboard.submit(request.id)

def report_failure(ui, repo, reviewboard, request, exception):
    ui.status(_("Reporting failure to review request %s\n") % request.id)
    from . import BUNDLE_ATTACHMENT_CAPTION
    reviewmsg = _("Automatic process was unable to add reviewed changesets into "
                  "the mercurial repository: \n\n    %s.\n\nResolve the problem "
                  "and resubmit review.") % exception.message
    reviewboard.rename_attachments_with_caption(request.id,
                                                BUNDLE_ATTACHMENT_CAPTION,
                                                _("%s (failed)") % BUNDLE_ATTACHMENT_CAPTION)
    reviewboard.publish(request.id)
    reviewboard.review(request.id, reviewmsg)

def fetch_review_request(ui, repo, reviewboard, request):
    bundles = reviewboard.download_attachement_with_given_caption(request.id, 'changeset bundle')
    if not bundles:
        ui.warn(_("Warning: no mercurial bundles were found in review request %s\n") % request.id)
        return False

    ui.pushbuffer()
    try:
        try:
            commands.unbundle(ui, repo, *bundles)
        except LookupError, e:
            raise util.Abort("Cannot unbundle: %s" % e.message)
    finally:
        ui.popbuffer()

    # find and merge any heads, introduced by importing bundle
    heads = repo.heads()
    branchheads = {}
    for head in heads:
        ctx = repo[head]
        branch = ctx.branch()
        if branch not in branchheads:
            branchheads[branch] = []
        branchheads[branch].append(ctx)

    for branch, heads in branchheads.items():
        merge_heads(ui, repo, branch, heads, request.id)

    return True



def merge_heads(ui, repo, branch, heads, requestid):
    if len(heads) == 1:
        return  # nothing to merge

    if len(heads) > 2:
        raise util.Abort(_("Review request bundle import resulted in more than two heads on branch %s") % branch)

    ui.status(_("Merging heads for branch %s\n") % branch)
    ui.pushbuffer()
    try:
        commands.update(ui, repo, heads[0].rev())
        commands.merge(ui, repo, tool="internal:merge")

        message = _("Automatic merge after review request %s fetch") % requestid
        commands.commit(ui, repo, message=message)
    finally:
        ui.popbuffer()

def push_reviewed(ui, repo, rbrepo):
    commands.push(ui, repo, rbrepo.path) # hg.repository(ui, rbrepo.path))
