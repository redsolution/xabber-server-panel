import requests

from django.conf import settings
from .exceptions import ResponseException


class EjabberdAPI(object):
    def __init__(self):
        self.authorized = False
        self.token = None
        self.session = requests.Session()
        self.base_url = settings.EJABBERD_API_URL
        self._cleanup_for_request()

    def _cleanup_for_request(self):
        self.raw_response = None
        self.response = None
        self.status_code = None
        self.success = None

    def fetch_token(self, token):
        self.token = token
        self.session.headers.update({'Authorization': 'Bearer {}'.format(token)})

    def _wrapped_call(self, method, url, status_code, data, http_method):
        try:
            if http_method in ("post", "delete", "put"):
                self.raw_response = method(url,
                                           json=data,
                                           timeout=settings.HTTP_REQUEST_TIMEOUT)
            elif http_method == "get":
                self.raw_response = method(url,
                                           params=data,
                                           timeout=settings.HTTP_REQUEST_TIMEOUT)
        except requests.exceptions.ConnectionError:
            self.status_code = 503
            raise ResponseException({'type': 'connection_error'})
        except requests.exceptions.RequestException as e:
            self.status_code = 500
            raise ResponseException({'type': 'request_error', 'detail': e})
        except Exception as e:
            self.status_code = 500
            raise ResponseException({'type': 'client_error', 'detail': e})
        try:
            self.response = self.raw_response.json() if self.raw_response.text else {}
        except Exception:
            raise ResponseException({'type': 'invalid_json'})
        self.status_code = self.raw_response.status_code
        if self.status_code != status_code:
            raise ResponseException({'type': 'bad_status_code',
                                     'detail': self.status_code})

    def _call_method(self, http_method, relative_url, success_code, data,
                     login_method=False, auth_required=True, return_bool=False):
        self._cleanup_for_request()
        method = getattr(self.session, http_method)
        url = self.base_url + relative_url
        try:
            self._wrapped_call(method, url, success_code, data, http_method)
        except ResponseException as e:
            self.success = False
            if self.response is None:
                error = e.get_error_message()
            else:
                try:
                    error = self.response.get('message')
                except Exception as e:
                    error = ''
            # error = self.response.get('message') if self.response \
            #     else e.get_error_message()
            self.response = {'error': error}
        else:
            self.success = True
            if auth_required:
                self.authorized = True
            elif login_method:
                self.fetch_token(self.response.get('token'))
                self.authorized = True
        return self.success if return_bool else self.response

    def login(self, credentials, **kwargs):
        username = credentials.get('username')
        password = credentials.get('password')
        data = {
            "jid": username,
            "ip": credentials.get("source_ip", ""),
            "browser": credentials.get("source_browser", ""),
            "scopes": settings.EJABBERD_API_SCOPES,
            "ttl": settings.EJABBERD_API_TOKEN_TTL
        }
        self.session.auth = requests.auth.HTTPBasicAuth(username, password)
        self._call_method('post', '/issue_token', 201, data=data,
                          login_method=True, auth_required=False, **kwargs)
        self.session.auth = None
        return self.success

    def logout(self, host, **kwargs):
        data = {
            "token": self.token,
            "host": host
        }
        self._call_method('post', '/revoke_token', 200, data=data,
                          **kwargs)
        if self.success:
            self.authorized = False
        return self.success

    def request_token(self, username, ip, browser, **kwargs):
        data = {
            "jid": username,
            "ip": ip,
            "browser": browser,
            "scopes": settings.EJABBERD_API_SCOPES,
            "ttl": settings.EJABBERD_API_TOKEN_TTL
        }
        return self._call_method('post', '/issue_token', 201, data=data,
                                 login_method=True, auth_required=False, **kwargs)

    def registered_vhosts(self, data, **kwargs):
        return self._call_method('get', '/vhosts', 200, data=data,
                                 **kwargs)

    def xabber_set_admin(self, data, **kwargs):
        return self._call_method('post', '/admins', 201,
                                 data=data, **kwargs)

    def xabber_del_admin(self, data, **kwargs):
        return self._call_method('delete', '/admins', 201,
                                 data=data, **kwargs)

    def xabber_set_permissions(self, data, **kwargs):
        return self._call_method('post', '/permissions', 201,
                                 data=data, **kwargs)

    def xabber_registered_users(self, data, **kwargs):
        return self._call_method('get', '/users', 200,
                                 data=data, **kwargs)

    def xabber_registered_users_count(self, data, **kwargs):
        return self._call_method('get', '/users/count', 200,
                                 data=data, **kwargs)

    def xabber_registered_chats(self, data, **kwargs):
        return self._call_method('get', '/groups', 200, data=data, **kwargs)

    def xabber_registered_chats_count(self, data, **kwargs):
        return self._call_method('post', '/groups/count', 200,
                                 data=data, **kwargs)

    def register_user(self, data, **kwargs):
        self._call_method('post', '/users', 201, data=data, **kwargs)
        if self.status_code == 409:
            self.response = {'error': "This user already exists."}
        return self.response

    def unregister_user(self, data, **kwargs):
        data_copy = data.copy()
        data_copy['username'] = data_copy.pop('username')
        self._call_method('delete', '/users', 200, data=data_copy, **kwargs)
        if not self.success:
            self.response = {'error': 'This user has not been deleted.'}
        return self.response

    def set_vcard(self, data, **kwargs):
        return self._call_method('post', '/vcard', 200, data=data,
                                 **kwargs)

    def get_vcard(self, data, **kwargs):
        return self._call_method('get', '/vcard', 200, data=data, **kwargs)

    def create_user(self, data, **kwargs):
        new_user_data = {"username": data.get("username"),
                         "host": data.get("host"),
                         "password": data.get("password")}
        self.register_user(new_user_data)
        if not self.success:
            return self.success

        self.edit_user_vcard(data)
        return self.success

    def edit_user_vcard(self, data, **kwargs):
        username, host = data.get("username"), data.get("host")
        vcard = data.get('vcard', dict())
        vcard_data = {"username": username,
                      "host": host,
                      "vcard": vcard}
        self.set_vcard(vcard_data)
        if not self.success:
            self.unregister_user({"username": username, "host": host})
            self.success = False
            self.response = {'error': 'Error with creating user.'}
        return self.success

    def change_password_api(self, data, **kwargs):
        return self._call_method('put', '/users/set_password', 200, data=data, **kwargs)

    def get_groups(self, data, **kwargs):
        return self._call_method('get', '/circles', 200, data=data, **kwargs)

    def srg_create_api(self, data, **kwargs):
        return self._call_method('post', '/circles', 200, data=data, **kwargs)

    def delete_group(self, data, **kwargs):
        return self._call_method('delete', '/circles', 200, data=data, **kwargs)

    def srg_user_add_api(self, data, **kwargs):
        return self._call_method('post', '/circles/members', 200, data=data, **kwargs)

    def srg_user_del_api(self, data, **kwargs):
        return self._call_method('delete', '/circles/members', 200, data=data, **kwargs)

    def create_group(self, data, **kwargs):
        group_data = {
            "circle": data["group"],
            "host": data["host"],
            "name": data["name"],
            "description": data["description"],
            "display": data["displayed_groups"]
        }
        self.srg_create_api(group_data)
        return self.success

    def stats_host(self, data, **kwargs):
        return self._call_method('get', '/users/online', 200, data=data, **kwargs)
