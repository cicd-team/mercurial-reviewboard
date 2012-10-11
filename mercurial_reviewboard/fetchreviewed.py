"""
Command to fetch approved changes from reviewboard and apply to relevant
repository.
"""
import os

from pprint import pprint

from mercurial.i18n import _

from mercurial import hg
from mercurial import repair
from mercurial import discovery
from mercurial import scmutil
from mercurial import commands
from mercurial import util

import reviewboard

def fetchreviewed(ui, repo, **opts):
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

    rbrepos = get_repositories(reviewboard)

    for r in rbrepos:
        rf = ReviewFetcher(ui, reviewboard, r, opts)
        rf.fetch_reviewed()

def get_repositories(reviewboard):
    """Return list of registered mercurial repositories"""

    repos = reviewboard.repositories()
    return [r for r in repos if r.tool == 'Mercurial']

class ReviewFetcher(object):
    ui = None
    reviewboard = None
    rbrepo = None

    repo = None

    def __init__(self, ui, reviewboard, rbrepo, opts):
        self.ui = ui
        self.reviewboard = reviewboard
        self.rbrepo = rbrepo

        self.dryrun = opts.get('dry_run', False)

    def fetch_reviewed(self):
        """Fetch changes into repository"""
        shipable = self.reviewboard.shipable_requests(self.rbrepo.id)
        if not shipable:
            self.ui.debug(_("Nothing shipable found for repository %s\n") % self.rbrepo.name)
            return

        self.ui.status(_("Processing shipped review requests for repo %s\n") % self.rbrepo.name)
        self.repo = self.get_local_repo()

        for request in shipable:
            self.ui.status(_("Processing review request %s\n") % request.id)
            try:
                self.clean_working_copy()
                fetched = self.fetch_review_request(request)
                if fetched and not self.dryrun:
                    self.report_success(request)

            except util.Abort, e:
                self.ui.status(_("Processing of request %s failed (%s)\n") % (request.id, e.message))
                if not self.dryrun:
                    self.report_failure(request, e)


    def get_local_repo(self):
        rname = self.rbrepo.name
        if not os.path.exists(rname):
            commands.clone(self.ui, str(self.rbrepo.path), str(rname))

        repo = hg.repository(self.ui, rname)
        commands.pull(self.ui, repo, self.rbrepo.path)
        return repo

    def fetch_review_request(self, request):
        bundles = self.reviewboard.download_attachement_with_given_caption(request.id, 'changeset bundle')
        if not bundles:
            self.ui.warn(_("Warning: no mercurial bundles were found in review request %s\n") % request.id)
            return False

        self.ui.pushbuffer()
        try:
            try:
                commands.unbundle(self.ui, self.repo, *bundles)
            except LookupError, e:
                raise util.Abort("Cannot unbundle: %s" % e.message)
        finally:
            self.ui.popbuffer()

        # find and merge any heads, introduced by importing bundle
        heads = self.repo.heads()
        branchheads = {}
        for head in heads:
            ctx = self.repo[head]
            branch = ctx.branch()
            if branch not in branchheads:
                branchheads[branch] = []
            branchheads[branch].append(ctx)

        for branch, heads in branchheads.items():
            self.merge_heads(branch, heads, request.id)

        return True

    def merge_heads(self, branch, heads, requestid):
        if len(heads) == 1:
            return  # nothing to merge

        if len(heads) > 2:
            raise util.Abort(_("Review request bundle import resulted in more than two heads on branch %s") % branch)

        self.ui.status(_("Merging heads for branch %s\n") % branch)
        self.ui.pushbuffer()
        try:
            commands.update(self.ui, self.repo, heads[0].rev())
            commands.merge(self.ui, self.repo, tool="internal:merge")

            message = _("Automatic merge after review request %s fetch") % requestid
            commands.commit(self.ui, self.repo, message=message)
        finally:
            self.ui.popbuffer()

    def report_success(self, request):
        from . import BUNDLE_ATTACHMENT_CAPTION
        self.push_reviewed()
        self.reviewboard.rename_attachments_with_caption(request.id,
                                                         BUNDLE_ATTACHMENT_CAPTION,
                                                         _("%s (submitted)") % BUNDLE_ATTACHMENT_CAPTION)
        self.reviewboard.publish(request.id)
        self.reviewboard.submit(request.id)

    def push_reviewed(self):
        commands.push(self.ui, self.repo, self.rbrepo.path)

    def report_failure(self, request, exception):
        self.ui.status(_("Reporting failure to review request %s\n") % request.id)
        from . import BUNDLE_ATTACHMENT_CAPTION
        reviewmsg = _("Automatic process was unable to add reviewed changesets into "
                      "the mercurial repository: \n\n    %s.\n\nResolve the problem "
                      "and resubmit review.") % exception.message
        self.reviewboard.rename_attachments_with_caption(request.id,
                                                         BUNDLE_ATTACHMENT_CAPTION,
                                                         _("%s (failed)") % BUNDLE_ATTACHMENT_CAPTION)
        self.reviewboard.publish(request.id)
        self.reviewboard.review(request.id, reviewmsg)

    def clean_working_copy(self):
        self.strip_outgoing()

        self.ui.pushbuffer()
        try:
            commands.update(self.ui, self.repo, clean=True)
        finally:
            self.ui.popbuffer()

    def strip_outgoing(self):
        from . import findoutgoing
        remoterepo = hg.repository(self.ui, self.rbrepo.path)
        out = findoutgoing(self.repo, remoterepo)
        if not out:
            return

        cl = self.repo.changelog
        revs = set([cl.rev(r) for r in out])
        descendants = set(cl.descendants(*revs))
        roots = revs.difference(descendants)

        roots = list(roots)
        roots.sort()
        roots.reverse()
        self.ui.status("Stripping local revisions %s\n" % roots)

        for node in roots:
            self.ui.note("Stripping revision %s...\n" % node)
            self.ui.pushbuffer()
            try:
                repair.strip(self.ui, self.repo, cl.node(node), backup='none')
            finally:
                self.ui.popbuffer()
