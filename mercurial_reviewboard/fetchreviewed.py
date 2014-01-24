"""
Command to fetch approved changes from reviewboard and apply to relevant
repository.
"""
import os

import re

from distutils.version import LooseVersion
from pprint import pprint

from mercurial.i18n import _

from mercurial import hg
from mercurial import repair
from mercurial import discovery
from mercurial import scmutil
from mercurial import commands
from mercurial import util
import datetime

import urllib
import urllib2
import base64
import cookielib
import json
from pprint import pprint

import reviewboard
from SingleRun import SingleRun

@SingleRun("fetchreviewed")
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
    
    ui.status("\n\nStarting fetchreview...\n")
    ui.status(_("%s\n") % str(datetime.datetime.now()))

    find_server(ui, opts)
    reviewboard = getreviewboard(ui, opts)

    rbrepos = get_repositories(reviewboard)

    for r in rbrepos:
        rf = ReviewFetcher(ui, reviewboard, r, opts)
        rf.fetch_reviewed()
        rf.fetch_pending()
    
    ui.status(_("%s\n") % str(datetime.datetime.now()))
    ui.status("Finished fetchreview.\n")

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
        self.opts = opts

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
                    self.update_jira(request, "Shipped")
                else:
                    self.ui.status(_("Review request %s was not submitted \n") % request.id)

				
            except util.Abort, e:
                self.ui.status(_("Processing of request %s failed (%s)\n") % (request.id, e.message))
                if not self.dryrun:
                    self.report_failure(request, e)
					
    def fetch_pending(self):
        pending = self.reviewboard.pending_requests()
        if not pending:
            self.ui.status(_("Nothing pending found for repository %s\n") % self.rbrepo.name)
            return
        self.ui.status(_("Processing pending review requests for repo %s\n") % self.rbrepo.name)
        if os.path.exists("reviews.json"):
            infile = file("reviews.json", "r+")
            data = json.load(infile)
            reviews = data['reviews']
            request_id_exists = False
            new_reviews = []
            for request in pending: 
                for review in reviews:
                    if request.id == review['id']:
                        request_id_exists = True
                        review = {'id' : request.id, 'summary' : request.summary}
                        new_reviews.append(review)
                        break
                if request_id_exists is False:
                    review = {'id' : request.id, 'summary' : request.summary}
                    new_reviews.append(review)
                    self.update_jira(request, "Pending")
            
            outfile = file("reviews.json", "w+")
            data = json.dumps({'reviews' : new_reviews}) 
            outfile.write(data)
            outfile.close()
        else:
            outfile = file("reviews.json", "w+")
            reviews = []
            for request in pending:
                self.ui.status(_("Processing review request %s\n") % request.id)       
                review = {'id' : request.id, 'summary' : request.summary}
                reviews.append(review)
                self.update_jira(request, "Pending")
            data = json.dumps({'reviews' : reviews}) 
            outfile.write(data)
            outfile.close()

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
            self.ui.status(_("Warning: no mercurial bundles were found in review request %s\n") % request.id)
            return False
        
        self.ui.status(_("Bundles found: %s\n") % str(bundles))
        self.ui.pushbuffer()
        try:
            try:
                self.ui.status("Apply bundle to local repository\n")
                commands.unbundle(self.ui, self.repo, *bundles)
            except LookupError, e:
                self.ui.status(_("Cannot unbundle: %s\n") % e.message)
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


        for bundle in bundles:
            self.ui.status(_("Deleting local bundle: %s\n") % str(bundle))
            os.unlink(bundle)        

        return True

    def jira_section_available(self):
        if self.ui.config('jira', 'server', None) is None:
            self.ui.status(_("You don't have a server specified in [jira] section in your  ~/.hgrc.\n"))
            return False
        if self.ui.config('jira', 'user', None) is None:
            self.ui.status(_("You don't have a user specified in [jira] section in your  ~/.hgrc.\n"))
            return False
        if self.ui.config('jira', 'password', None) is None:
            self.ui.status(_("You don't have a password specified in [jira] section in your  ~/.hgrc.\n"))
            return False
        return True
        
    def update_jira(self, request, message=None): 
        if self.jira_section_available() is False:
            return
        review_board_message = "Review request submitted."
        jira_tickets = re.findall( r'([A-Z]+-[0-9]+)', request.summary)
        jira_server = self.ui.config('jira', 'server')
        jira_user = self.ui.config('jira', 'user')
        jira_password = self.ui.config('jira', 'password')
	
        #Get Submitter info from review
        review = self.reviewboard._get_request(request.id)
        submitter_name = review['links']['submitter']['title']
        submitter_href = review['links']['submitter']['href']
	
        reviewboard_server = self.ui.config('reviewboard', 'server')
        review_url = reviewboard_server + "/r/" + str(request.id)
        jira_comment = "Review Board: " + message + "!\n" + "User: " + submitter_name + "\n" + "Link: " + review_url
	
        for jira_ticket in jira_tickets:
            self.ui.status(_("Jira ticket: %s\n") % str(jira_ticket))
            self.ui.status(_("Adding comment for ticket...\n"))
            url = jira_server + '/rest/api/latest/issue/%s/comment' % jira_ticket
            auth = base64.encodestring('%s:%s' % (jira_user, jira_password)).replace('\n', '')

            data = json.dumps({'body': jira_comment})

            request = urllib2.Request(url, data, {
                'Authorization': 'Basic %s' % auth,
                'X-Atlassian-Token': 'no-check',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
                })
		
            try:
                response = urllib2.urlopen(request).read()
            except IOError, e: 
                if hasattr(e, 'code') and e.code == 404:
                    self.ui.status(_("Jira ticket: %s") % str(jira_ticket) + (" does not exist!\n"))
            else:                               
                self.ui.status(_("Comment added.\n"))

    def merge_heads(self, branch, heads, requestid):
        if len(heads) == 1:
            return  # nothing to merge

        if len(heads) > 2:
            self.ui.status(_("Review request bundle import resulted in more than two heads on branch %s") % branch)
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
        self.ui.status(_("Submitting review request %s\n") % request.id)
        self.reviewboard.submit(request.id)

    def push_reviewed(self):
        push_result = commands.push(self.ui, self.repo, self.rbrepo.path, new_branch=True)
        self.ui.status(_("Push result %d\n") % push_result)
        if (push_result != 0):
            if (push_result == 1):
                self.ui.status(_("Nothing to push. Push command returned: %d\n") % push_result)
            else:
                self.ui.status(_("Cannot push. Please resubmit review request. Push command returned: %d\n") % push_result)
                raise util.Abort("Cannot push. Please resubmit review request. Push command returned: %d" % push_result)
            

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
            commands.revert(self.ui, self.repo, all=True, no_backup=True)
        finally:
            self.ui.popbuffer()

    def strip_outgoing(self):
        from . import findoutgoing
        
        if LooseVersion(util.version()) >= LooseVersion('2.3'):
            remoterepo = hg.peer(self.repo, self.opts, self.rbrepo.path)
        else:
            remoterepo = hg.repository(self.ui, self.rbrepo.path)
        
        out = findoutgoing(self.repo, remoterepo)
        if not out:
            return

        cl = self.repo.changelog
        revs = set([cl.rev(r) for r in out])
        if LooseVersion(util.version()) >= LooseVersion('2.3'):
            descendants = set(cl.descendants(revs))
        else:
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
