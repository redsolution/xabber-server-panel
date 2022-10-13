import hashlib
import hmac
from django.conf import settings


def check_signature(request):
    signature = request.headers.get(settings.WEBHOOKS_SIGNATURE_HEADER)
    key = settings.WEBHOOKS_SECRET
    if key is None or not signature:
        return False
    key = key.encode()
    body = request.body
    body_hash = hmac.new(key, body, hashlib.sha256).hexdigest()
    return body_hash == signature


class WebHookResponse(Exception):
    """Exception for returning the result of processing a web hook.

    Attributes:
        response -- HttpResponse object that contains the generated response

    """

    def __init__(self, response):
        self.response = response
        super().__init__()
