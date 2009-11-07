# api code for the reviewboard extension, inspired/copied from reviewboard
# post-review code.

import cookielib
import mimetools
import urllib2
import simplejson
from urlparse import urljoin

class APIError(Exception):
    pass

class ReviewBoardError(Exception):
    pass

class ReviewBoard:
    def __init__(self, url):
        if not url.endswith('/'):
            url = url + '/'
        self.url       = url
        self._cj = cookielib.MozillaCookieJar()
        self._opener = opener = urllib2.build_opener(
                        urllib2.ProxyHandler(),
                        urllib2.UnknownHandler(),
                        urllib2.HTTPHandler(),
                        urllib2.HTTPDefaultErrorHandler(),
                        urllib2.HTTPErrorProcessor(),
                        urllib2.HTTPCookieProcessor(self._cj),
                        )
        urllib2.install_opener(self._opener)
        self._repositories = None
        self._requests = None

    def login(self, username, password):
        self._api_post('/api/json/accounts/login/', {
            'username': username,
            'password': password,
        })

    def repositories(self):
        if not self._repositories:
            rsp = self._api_post('/api/json/repositories/')
            self._repositories = rsp['repositories']
        return self._repositories

    def requests(self):
        if not self._requests:
            rsp = self._api_post('/api/json/reviewrequests/all/')
            self._requests = rsp['review_requests']
        return self._requests

    def users(self):
        rsp = self._api_post('/api/json/users/')
        self.users = rsp['users']
        return self.users

    def new_request(self, repo_id, fields={}, diff='', parentdiff=''):
        repository_path = None
        for r in self.repositories():
            if r['id'] == int(repo_id):
                repository_path = r['path']
                break
        if not repository_path:
            raise ReviewBoardError, ("can't find repository with id: %s" % \
                                        repo_id)

        id = self._create_request(repository_path)

        self._set_request_details(id, fields, diff, parentdiff)

        return id

    def update_request(self, id, fields={}, diff='', parentdiff=''):
        request_id = None
        for r in self.requests():
            if r['id'] == int(id):
                request_id = int(id)
                break
        if not request_id:
            raise ReviewBoardError, ("can't find request with id: %s" % id)

        self._set_request_details(request_id, fields, diff, parentdiff)

        return request_id

    def publish(self, id):
        self._api_post('api/json/reviewrequests/%s/publish/' % id)

    def _save_draft(self, id):
        rsp = self._api_post("/api/json/reviewrequests/%s/draft/save/" % id )

    def _api_post(self, url, fields=None, files=None):
        """
        Performs an API call using HTTP POST at the specified path.
        """
        try:
            return self._process_json( self._http_post(url, fields, files) )
        except APIError, e:
            rsp, = e.args

            raise ReviewBoardError, ("%s (%s)" % \
                                    (rsp["err"]["msg"], rsp["err"]["code"]) )

    def _http_post(self, path, fields, files=None):
        """
        Performs an HTTP POST on the specified path.
        """
        if path.startswith('/'):
            path = path[1:]
        url = urljoin(self.url, path)
        content_type, body = self._encode_multipart_formdata(fields, files)
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(body))
        }

        try:
            r = urllib2.Request(url, body, headers)
            data = urllib2.urlopen(r).read()
            return data
        except urllib2.URLError, e:
            raise ReviewBoardError, ("Unable to access %s.\n%s" % \
                    (url, e))
        except urllib2.HTTPError, e:
            raise ReviewBoardError, ("Unable to access %s (%s).\n%s" % \
                    (url, e.code, e.read()))

    def _process_json(self, data):
        """
        Loads in a JSON file and returns the data if successful. On failure,
        APIError is raised.
        """
        rsp = simplejson.loads(data)

        if rsp['stat'] == 'fail':
            raise APIError, rsp

        return rsp

    def _encode_multipart_formdata(self, fields, files):
        """
        Encodes data for use in an HTTP POST.
        """
        BOUNDARY = mimetools.choose_boundary()
        content = ""

        fields = fields or {}
        files = files or {}

        for key in fields:
            content += "--" + BOUNDARY + "\r\n"
            content += "Content-Disposition: form-data; name=\"%s\"\r\n" % key
            content += "\r\n"
            content += fields[key] + "\r\n"

        for key in files:
            filename = files[key]['filename']
            value = files[key]['content']
            content += "--" + BOUNDARY + "\r\n"
            content += "Content-Disposition: form-data; name=\"%s\"; " % key
            content += "filename=\"%s\"\r\n" % filename
            content += "\r\n"
            content += value + "\r\n"

        content += "--" + BOUNDARY + "--\r\n"
        content += "\r\n"

        content_type = "multipart/form-data; boundary=%s" % BOUNDARY

        return content_type, content

    def _create_request(self, repository_path):
        data = { 'repository_path': repository_path }
        rsp = self._api_post('/api/json/reviewrequests/new/', data)

        return rsp['review_request']['id']

    def _set_request_field(self, id, field, value):
        self._api_post('/api/json/reviewrequests/%s/draft/set/' %
                                id, { field: value })

    def _upload_diff(self, id, diff, parentdiff=""):
        data = {'path': {'filename': 'diff', 'content': diff}}
        if parentdiff:
            data['parent_diff_path'] = \
                {'filename': 'parent_diff', 'content': parentdiff}
        rsp = self._api_post('/api/json/reviewrequests/%s/diff/new/' % \
                                id, {}, data)

    def _set_fields(self, id, fields={}):
        for field in fields:
            self._set_request_field(id, field, fields[field])

    def _set_request_details(self, id, fields, diff, parentdiff):
        self._set_fields(id, fields)
        if diff:
            self._upload_diff(id, diff, parentdiff)
        if fields or diff:
            self._save_draft(id)
