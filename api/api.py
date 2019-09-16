import requests

from xmppserverui import settings
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

    def _wrapped_call(self, method, url, status_code, data):
        try:
            self.raw_response = method(url, json=data)
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
            self._wrapped_call(method, url, success_code, data)
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
        self._call_method('post', '/xabber_oauth_issue_token', 200, data=data,
                          login_method=True, auth_required=False, **kwargs)
        self.session.auth = None
        return self.success

    def logout(self, host, **kwargs):
        data = {
            "token": self.token,
            "host": host
        }
        self._call_method('post', '/xabber_revoke_token', 200, data=data,
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
        return self._call_method('post', '/xabber_oauth_issue_token', 200, data=data,
                          login_method=True, auth_required=False, **kwargs)

    def registered_vhosts(self, data, **kwargs):
        return self._call_method('post', '/registered_vhosts', 200, data=data,
                                 **kwargs)

    def get_registered_users(self, data, **kwargs):
        return self._call_method('post', '/registered_users', 200, data=data,
                                 **kwargs)

    def xabber_registered_users(self, data, **kwargs):
        return self._call_method('post', '/xabber_registered_users', 200,
                                 data=data, **kwargs)

    def xabber_registered_users_count(self, data, **kwargs):
        return self._call_method('post', '/xabber_registered_users_count', 200,
                                 data=data, **kwargs)

    def xabber_registered_chats(self, data, **kwargs):
        return self._call_method('post', '/xabber_registered_chats', 200,
                                 data=data, **kwargs)

    def xabber_registered_chats_count(self, data, **kwargs):
        return self._call_method('post', '/xabber_registered_chats_count', 200,
                                 data=data, **kwargs)

    def register_user(self, data, **kwargs):
        return self._call_method('post', '/register', 200, data=data,
                                 **kwargs)

    def unregister_user(self, data, **kwargs):
        data_copy = data.copy()
        data_copy['user'] = data_copy.pop('username')
        return self._call_method('post', '/unregister', 200, data=data_copy,
                                 **kwargs)

    def set_vcard(self, data, **kwargs):
        data['name'] = data.get('name', '').upper()
        return self._call_method('post', '/set_vcard', 200, data=data,
                                 **kwargs)

    def set_vcard2(self, data, **kwargs):
        data['name'] = data.get('name', '').upper()
        data['subname'] = data.get('subname', '').upper()
        return self._call_method('post', '/set_vcard2', 200, data=data,
                                 **kwargs)

    def get_vcard(self, data, **kwargs):
        data['name'] = data.get('name', '').upper()
        return self._call_method('post', '/get_vcard', 200, data=data,
                                 **kwargs)

    def get_vcard2(self, data, **kwargs):
        data['name'] = data.get('name', '').upper()
        data['subname'] = data.get('subname', '').upper()
        return self._call_method('post', '/get_vcard2', 200, data=data,
                                 **kwargs)

    def create_user(self, data, **kwargs):
        new_user_data = {"user": data.get("username"),
                         "host": data.get("host"),
                         "password": data.get("password")} #TODO fix it
        self.register_user(new_user_data)
        if not self.success:
            return self.success

        self.edit_user_vcard(data)
        return self.success

    def edit_user_vcard(self, data, **kwargs):
        username, host = data.get("username"), data.get("host")
        vcard = data.get('vcard', dict())
        for key, value in vcard.iteritems():
            if isinstance(value, dict):
                for nested_key, nested_value in value.iteritems():
                    vcard2_data = {"user": username,
                                   "host": host,
                                   "name": key,
                                   "subname": nested_key,
                                   "content": nested_value.strip()}
                    self.set_vcard2(vcard2_data)
                if not self.success:
                    self.unregister_user({"username": username, "host": host})
                    self.success = False
                    self.response = {'error': 'Error with creating user.'}
                    break
            else:
                vcard_data = {"user": username,
                              "host": host,
                              "name": key,
                              "content": value.strip()}
                self.set_vcard(vcard_data)
            if not self.success:
                self.unregister_user({"username": username, "host": host})
                self.success = False
                self.response = {'error': 'Error with creating user.'}
                break

        return self.success

    def change_password_api(self, data, **kwargs):
        return self._call_method('post', '/change_password', 200, data=data, **kwargs)

    def check_user_password(self, data, **kwargs):
        return self._call_method('post', '/check_password', 200, data=data, **kwargs)

    def get_groups(self, data, **kwargs):
        return self._call_method('post', '/srg_list', 200, data=data, **kwargs)

    def get_group_info(self, data, **kwargs):
        return self._call_method('post', '/srg_get_info', 200, data=data, **kwargs)

    def srg_create_api(self, data, **kwargs):
        return self._call_method('post', '/srg_create', 200, data=data, **kwargs)

    def delete_group(self, data, **kwargs):
        return self._call_method('post', '/srg_delete', 200, data=data, **kwargs)

    def srg_user_add_api(self, data, **kwargs):
        return self._call_method('post', '/srg_user_add', 200, data=data, **kwargs)

    def srg_user_del_api(self, data, **kwargs):
        return self._call_method('post', '/srg_user_del', 200, data=data, **kwargs)

    def create_group(self, data, **kwargs):
        group_data = {
            "group": data["group"],
            "host": data["host"],
            "name": data["name"],
            "description": data["description"],
            "display": data["displayed_groups"]
        }
        self.srg_create_api(group_data)
        return self.success

    def stats(self, data, **kwargs):
        return self._call_method('post', '/stats', 200, data=data, **kwargs)

    def stats_host(self, data, **kwargs):
        return self._call_method('post', '/xabber_num_online_users', 200, data=data, **kwargs)

