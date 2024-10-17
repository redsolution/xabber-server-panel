import hashlib
import hmac
import base64
import json
import time
import ast

from django.conf import settings

from xabber_server_panel.base_modules.config.models import ModuleSettings


def get_webhook_secret():
    webhook_settings = ModuleSettings.objects.filter(
        host='global',
        module='mod_webhooks'
    ).first()

    if webhook_settings is None:
        return None
    secret_raw = webhook_settings.get_options().get('secret')
    return ast.literal_eval(secret_raw)


def check_signature(request):
    signature = request.headers.get(settings.WEBHOOKS_SIGNATURE_HEADER)
    if not signature:
        return check_jwt(request)

    key = get_webhook_secret()

    if key is None:
        return False

    key = key.encode()
    body = request.body
    body_hash = hmac.new(key, body, hashlib.sha256).hexdigest()
    return body_hash == signature


def _extract_jwt(auth_header):
    try:
        auth_header_list = auth_header.split()
        if auth_header_list[0] != 'Bearer':
            return None
        token = auth_header_list[1].split('.')
        return dict(header=token[0], payload=token[1], signature=token[2])
    except:
        return None


def _to_json(b64str):
    s = b64str + '=' * (-len(b64str) % 4)
    decoded = base64.urlsafe_b64decode(s).decode()
    try:
        return json.loads(decoded)
    except:
        return None


def check_jwt(request):

    key = get_webhook_secret()

    if key is None:
        return False

    token = _extract_jwt(request.headers.get('Authorization'))
    if token is None:
        return False
    header = _to_json(token['header'])
    if header['alg'] != 'HS256':
        return False
    payload = _to_json(token['payload'])
    iat = payload.get('iat', False)
    if not iat or (int(time.time()) - iat) > 60:
        return False
    digest = hmac.new(key.encode(), (token['header'] + '.' + token['payload']).encode(), hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(digest).decode().replace('=', '')
    return signature == token['signature']


class WebHookResponse(Exception):
    """Exception for returning the result of processing a web hook.

    Attributes:
        response -- HttpResponse object that contains the generated response

    """

    def __init__(self, response):
        self.response = response
        super().__init__()
