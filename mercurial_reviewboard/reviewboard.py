# api code for the reviewboard extension, inspired/copied from reviewboard
# post-review code.
import base64
import datetime
import getpass
import http.cookiejar
import json as simplejson
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from urllib.parse import urljoin, urlparse
import io


class APIError(Exception):
    pass


class ReviewBoardError(Exception):
    def __init__(self, json=None):
        self.msg = None
        self.code = None
        self.tags = {}

        if isinstance(json, str) or isinstance(json, str):
            try:
                json = simplejson.loads(json)
            except:
                self.msg = json
                return

        if json:
            if 'err' in json:
                self.msg = json['err']['msg']
                self.code = json['err']['code']
            for key, value in list(json.items()):
                if isinstance(value, str) or isinstance(value, str) or \
                        key == 'fields':
                    self.tags[key] = value

    def __str__(self):
        if self.msg:
            return ("%s (%s)" % (self.msg, self.code)) + \
                   ''.join([("\n%s: %s" % (k, v)) for k, v in list(self.tags.items())])
        else:
            return Exception.__str__(self)


class Repository:
    """
    Represents a ReviewBoard repository
    """

    def __init__(self, id, name, tool, path):
        self.id = id
        self.name = name
        self.tool = tool
        self.path = path


class Request:
    """
    Represents a ReviewBoard request
    """

    def __init__(self, id, summary):
        self.id = id
        self.summary = summary


class ReviewBoardHTTPPasswordMgr(urllib.request.HTTPPasswordMgr):
    """
    Adds HTTP authentication support for URLs.

    Python 2.4's password manager has a bug in http authentication when the
    target server uses a non-standard port.  This works around that bug on
    Python 2.4 installs. This also allows post-review to prompt for passwords
    in a consistent way.

    See: http://bugs.python.org/issue974757
    """

    def __init__(self, reviewboard_url):
        self.passwd = {}
        self.rb_url = reviewboard_url if type(reviewboard_url) != bytes else reviewboard_url.decode('utf-8')
        self.rb_user = None
        self.rb_pass = None

    def set_credentials(self, username, password):
        self.rb_user = username if type(username) != bytes else username.decode('utf-8')
        self.rb_pass = password if type(password) != bytes else password.decode('utf-8')

    def find_user_password(self, realm, uri):
        if uri.startswith(self.rb_url):
            if self.rb_user is None or self.rb_pass is None:
                print("==> HTTP Authentication Required")
                print('Enter username and password for "%s" at %s' % \
                      (realm, urlparse(uri)[1]))
                self.rb_user = input('Username: ')
                self.rb_pass = getpass.getpass('Password: ')
            return self.rb_user, self.rb_pass
        else:
            # If this is an auth request for some other domain (since HTTP
            # handlers are global), fall back to standard password management.
            return urllib.request.HTTPPasswordMgr.find_user_password(self, realm, uri)


class HttpErrorHandler(urllib.request.HTTPDefaultErrorHandler):
    """
    Error handler that doesn't throw an exception for any code below 400.
    This is necessary because RB returns 2xx codes other than 200 to indicate
    success.
    """

    def http_error_default(self, req, fp, code, msg, hdrs):
        if code >= 400:
            return urllib.request.HTTPDefaultErrorHandler.http_error_default(self,
                                                                             req, fp, code, msg, hdrs)
        else:
            result = urllib.error.HTTPError(req.get_full_url(), code, msg, hdrs, fp)
            result.status = code
            return result


class HttpClient:
    def __init__(self, url, proxy=None, api_token=None):
        if not url.endswith(b'/'):
            url = url + b'/'
        self.url = url
        if 'APPDATA' in os.environ:
            homepath = os.environ["APPDATA"]
        elif 'USERPROFILE' in os.environ:
            homepath = os.path.join(os.environ["USERPROFILE"], "Local Settings",
                                    "Application Data")
        elif 'HOME' in os.environ:
            homepath = os.environ["HOME"]
        else:
            homepath = ''
        self.api_token = api_token if type(api_token) != bytes else api_token.decode('utf-8')
        self.cookie_file = os.path.join(homepath, ".post-review-cookies.txt")
        self._cj = http.cookiejar.MozillaCookieJar(self.cookie_file)
        self._password_mgr = ReviewBoardHTTPPasswordMgr(self.url)
        self._opener = opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(proxy),
            urllib.request.UnknownHandler(),
            urllib.request.HTTPHandler(),
            HttpErrorHandler(),
            urllib.request.HTTPErrorProcessor(),
            urllib.request.HTTPCookieProcessor(self._cj),
            urllib.request.HTTPBasicAuthHandler(self._password_mgr),
            urllib.request.HTTPDigestAuthHandler(self._password_mgr)
        )
        urllib.request.install_opener(self._opener)

    def set_credentials(self, username, password):
        self._password_mgr.set_credentials(username, password)

    def api_request(self, method, url, fields=None, files=None):
        """
        Performs an API call using an HTTP request at the specified path.
        """
        try:
            rsp = self._http_request(method, url, fields, files)
            if rsp:
                return self._process_json(rsp)
            else:
                return None
        except APIError as e:
            rsp, = e.args
            raise ReviewBoardError(rsp)

    def has_valid_cookie(self):
        """
        Load the user's cookie file and see if they have a valid
        'rbsessionid' cookie for the current Review Board server.  Returns
        true if so and false otherwise.
        """
        try:
            parsed_url = urlparse(self.url)
            host = parsed_url[1]
            path = parsed_url[2] or '/'

            # Cookie files don't store port numbers, unfortunately, so
            # get rid of the port number if it's present.
            host = host.split(b":")[0]

            host = host.decode('utf-8')
            path = path.decode('utf-8')
            print("Looking for '%s %s' cookie in %s \n" % (host, path, self.cookie_file))

            self._cj.load(self.cookie_file, ignore_expires=True)
            try:
                cookie = self._cj._cookies[host][path]['rbsessionid']

                if not cookie.is_expired():
                    print("Loaded valid cookie -- no login required\n")
                    return True

                print("Cookie file loaded, but cookie has expired\n")
            except KeyError:
                print("Cookie file loaded, but no cookie for this server\n")
        except IOError as error:
            print("Couldn't load cookie file: %s" % error)
        return False

    def _http_request(self, method, path, fields, files):
        """
        Performs an HTTP request on the specified path.
        """
        if path.startswith('/'):
            path = path[1:]
        url = urljoin(self.url, str.encode(path))
        
        headers = {}

        self._provide_auth_header(headers)

        try:
            data = self._send_with_urllib(method, url.decode('utf-8').replace(" ", "%20"), fields, headers, files)

            try:
                self._cj.save(self.cookie_file)
            except:
                print("exception when cookie file saving")
                # this can be ignored safely
                pass
            return data
        except urllib.error.HTTPError as e:
            if not hasattr(e, 'code'):
                raise
            if e.code >= 400:
                e.msg = "HTTP Error: " + e.msg
                raise ReviewBoardError(e.msg)
            else:
                return ""
        except urllib.error.URLError as e:
            code = e.reason[0]
            msg = "URL Error: " + e.reason[1]
            raise ReviewBoardError({'err': {'msg': msg, 'code': code}})

    def _provide_auth_header(self, headers):
        if self.api_token:
            headers["Authorization"] = 'token %s' % self.api_token
        if self._password_mgr.rb_user and self._password_mgr.rb_pass:
            credentials = ('%s:%s' % (self._password_mgr.rb_user, self._password_mgr.rb_pass))
            encoded_credentials = base64.b64encode(credentials.encode('ascii'))
            headers["Authorization"] = 'Basic %s' % encoded_credentials.decode("ascii")

    def _process_json(self, data):
        """
        Loads in a JSON file and returns the data if successful. On failure,
        APIError is raised.
        """
        rsp = simplejson.loads(data)
        if rsp['stat'] == 'fail':
            raise APIError(rsp)
        return rsp

    def _send_with_urllib(self, method, url, fields, headers, files):
        form = MultiPartForm()
        if fields:
            for key in fields:
                form.add_field(key, fields[key])

        if files:
            for key in files:
                filename = files[key]['filename']
                content = files[key]['content']
                if type(content) != bytes:
                    content = content.encode('utf-8')
                form.add_file(key, filename,
                              fileHandle=io.BytesIO(content))

        # Build the request, including the byte-string
        # for the data to be posted.
        data = form.bytes()
        r = urllib.request.Request(url, data=data, method=method)

        r.add_header('Content-type', form.get_content_type())
        r.add_header('Content-length', len(data))
        if headers:
            for key in headers:
                r.add_header(key, headers[key])

        return urllib.request.urlopen(r).read().decode('utf-8')

class MultiPartForm:
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        # Use a large random byte string to separate
        # parts of the MIME data.
        self.boundary = uuid.uuid4().hex.encode('utf-8')
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary={}'.format(
            self.boundary.decode('utf-8'))

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))

    def add_file(self, fieldname, filename, fileHandle,
                 mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = (
                mimetypes.guess_type(filename)[0] or
                'application/octet-stream'
            )
        self.files.append((fieldname, filename, mimetype, body))
        return

    @staticmethod
    def _form_data(name):
        return ('Content-Disposition: form-data; '
                'name="{}"\r\n').format(name).encode('utf-8')

    @staticmethod
    def _attached_file(name, filename):
        return ('Content-Disposition: file; '
                'name="{}"; filename="{}"\r\n').format(
                    name, filename).encode('utf-8')

    @staticmethod
    def _content_type(ct):
        return 'Content-Type: {}\r\n'.format(ct).encode('utf-8')

    def bytes(self):
        """Return a byte-string representing the form data,
        including attached files.
        """
        buffer = io.BytesIO()
        boundary = b'--' + self.boundary + b'\r\n'

        # Add the form fields
        for name, value in self.form_fields:
            buffer.write(boundary)
            buffer.write(self._form_data(name))
            buffer.write(b'\r\n')
            if type(value) != bytes:
                buffer.write(value.encode('utf-8'))
            else:
                buffer.write(value)
            buffer.write(b'\r\n')

        # Add the files to upload
        for f_name, filename, f_content_type, body in self.files:
            buffer.write(boundary)
            buffer.write(self._attached_file(f_name, filename))
            buffer.write(self._content_type(f_content_type))
            buffer.write(b'\r\n')
            buffer.write(body)
            buffer.write(b'\r\n')

        buffer.write(b'--' + self.boundary + b'--\r\n')
        return buffer.getvalue()

class ApiClient:
    def __init__(self, httpclient, apiver):
        self._httpclient = httpclient
        self.apiver = apiver

    def _api_request(self, method, url, fields=None, files=None):
        return self._httpclient.api_request(method, url, fields, files)


class Api20Client(ApiClient):
    """
    Implements the 2.0 version of the API
    """

    def __init__(self, httpclient):
        ApiClient.__init__(self, httpclient, '2.0')
        self._repositories = None
        self._pending_user_requests = None
        self._pending_requests = None
        self._requestcache = {}

    def login(self, username=None, password=None):
        self._httpclient.set_credentials(username, password)
        return

    def repositories(self):
        if not self._repositories:
            rsp = self._api_request('GET', '/api/repositories/?max-results=500')
            self._repositories = [Repository(r['id'], r['name'], r['tool'],
                                             r['path'])
                                  for r in rsp['repositories']]
        return self._repositories

    def pending_user_requests(self):
        # Get all the pending request within the last week for a given user
        if not self._pending_user_requests:
            usr = str(self._httpclient._password_mgr.rb_user)
            delta = datetime.timedelta(days=7)
            today = datetime.datetime.today()
            sevenDaysAgo = today - delta
            rsp = self._api_request('GET', '/api/review-requests/' +
                                    '?from-user=%s' % usr +
                                    '&status=pending' +
                                    '&max-results=50' +
                                    '&last-updated-from=%s' % sevenDaysAgo)
            self._pending_user_requests = []
            for r in rsp['review_requests']:
                self._pending_user_requests += [Request(r['id'], r['summary'].strip())]

        return self._pending_user_requests

    def pending_requests(self):
        # Get all the pending request within the last week for a given user
        if not self._pending_requests:
            usr = str(self._httpclient._password_mgr.rb_user)
            delta = datetime.timedelta(days=7)
            today = datetime.datetime.today()
            sevenDaysAgo = today - delta
            rsp = self._api_request('GET', '/api/review-requests/' +
                                    '?status=pending' +
                                    '&max-results=50' +
                                    '&last-updated-from=%s' % sevenDaysAgo)
            self._pending_requests = []
            for r in rsp['review_requests']:
                self._pending_requests += [Request(r['id'], r['summary'].strip())]

        return self._pending_requests

    def shipable_requests(self, repo_id):
        # Get all the shipable request
        rsp = self._api_request('GET', '/api/review-requests/' +
                                '?status=pending&ship-it=1&repository=%s' % repo_id)
        return [Request(r['id'], r['summary'].strip()) for r in rsp['review_requests'] if r['approved']]

    def get_attachments_with_caption(self, id, caption):
        req = self._get_request(id)
        attachments = self._api_request('GET', req['links']['file_attachments']['href'])['file_attachments']
        return [a for a in attachments if a['caption'] == caption]

    def download_attachement_with_given_caption(self, id, caption):
        attachments_with_caption = [(a['url'], a['filename']) for a in self.get_attachments_with_caption(id, caption)]
        data_and_name = [(self._httpclient._http_request('GET', url, None, None), filename) for (url, filename) in attachments_with_caption]
        names = [name for data, name in data_and_name]
        for data, name in data_and_name:
            f = open(name, 'wb')
            f.write(data)
            f.close();
        return names;

    def delete_attachments_with_caption(self, id, caption):
        for a in self.get_attachments_with_caption(id, caption):
            self._api_request('DELETE', a['links']['delete']['href'])

    def rename_attachments_with_caption(self, id, oldcaption, newcaption):
        for a in self.get_attachments_with_caption(id, oldcaption):
            self._api_request('PUT', a['links']['update']['href'], {'caption': newcaption})

    def new_request(self, repo_id, fields={}, diff='', parentdiff='', files=None):
        req = self._create_request(repo_id)
        self._set_request_details(req, fields, diff, parentdiff, files)
        self._requestcache[req['id']] = req
        return req['id']

    def update_request(self, id, fields={}, diff='', parentdiff='', files=None):
        req = self._get_request(id)
        self._set_request_details(req, fields, diff, parentdiff, files)

    def publish(self, id):
        req = self._get_request(id)
        drafturl = req['links']['draft']['href']
        self._api_request('PUT', drafturl, {'public': '1'})

    def discard(self, id):
        req = self._get_request(id)
        drafturl = req['links']['update']['href']
        self._api_request('PUT', drafturl, {'status': 'discarded'})

    def submit(self, id):
        req = self._get_request(id)
        drafturl = req['links']['update']['href']
        self._api_request('PUT', drafturl, {'status': 'submitted'})

    def review(self, id, message):
        req = self._get_request(id)
        reviews = self._api_request('GET', req['links']['reviews']['href'])
        reviewurl = reviews['links']['create']['href']

        params = {'body_top': message,
                  'public': '1'}
        self._api_request('POST', reviewurl, params)

    def _create_request(self, repo_id):
        data = {'repository': repo_id}
        result = self._api_request('POST', '/api/review-requests/', data)
        return result['review_request']

    def _get_request(self, id):
        if id in self._requestcache:
            return self._requestcache[id]
        else:
            if isinstance(id,int):
                id=str(id)
            elif isinstance(id,bytes):
                id=id.decode()
            result = self._api_request('GET', '/api/review-requests/%s/' % id)
            self._requestcache[id] = result['review_request']
            return result['review_request']

    def _set_request_details(self, req, fields, diff, parentdiff, files):
        if fields:
            drafturl = req['links']['draft']['href']
            self._api_request('PUT', drafturl, fields)
        if diff:
            diffurl = req['links']['diffs']['href']
            data = {'path': {'filename': 'diff', 'content': diff}}
            if parentdiff:
                data['parent_diff_path'] = \
                    {'filename': 'parent_diff', 'content': parentdiff.decode('utf-8')}
            self._api_request('POST', diffurl, {}, data)
        if files:
            self._attach_files(req, files)

    def _attach_files(self, req, files):
        if files:
            furl = req['links']['file_attachments']['href']
            attachments = self._api_request('GET', furl)
            furl = attachments['links']['create']
            base_id = len(attachments['file_attachments']) + 1
            for k, f in list(files.items()):
                f_fields = {'caption': k}
                self._api_request(furl['method'], furl['href'], f_fields, {'path': f})


# this method must be compatible with THG implementation to make the plugin working in totroiseHg UI: https://foss.heptapod.net/mercurial/tortoisehg/thg/-/blob/branch/stable/tortoisehg/hgqt/postreview.py#L96 
def make_rbclient(url, username, password, proxy=None, api_token=None):

    httpclient = HttpClient(url, proxy, api_token=api_token)

    if not httpclient.has_valid_cookie() and not api_token:
        if not username:
            username = input('Username: ')
        if not password:
            password = getpass.getpass('Password: ')

    cli = Api20Client(httpclient)
    cli.login(username, password)
    return cli

