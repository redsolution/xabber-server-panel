import django.dispatch
from django.dispatch import receiver
from django.http import HttpResponse
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from xabber_server_panel.webhooks.utils import check_signature, WebHookResponse
from xabber_server_panel.base_modules.users.models import User

import json

webhook_received = django.dispatch.Signal()


@receiver(webhook_received)
def webhook_received_handler(sender, **kwargs):
    """
    Request path: "/xmppserver"
    Request body:
        { "target": "user",
          "action": "create/remove",
          "username": "bob",
          "host": "domain.com"
        }
    """
    path = kwargs.get('path', '')

    # Checking if the path matches the expected webhook path
    if path.rstrip('/') != 'xmppserver':
        return

    request = kwargs.get('request')

    # Checking the signature of the request
    if not check_signature(request):
        raise WebHookResponse(response=HttpResponse('Unauthorized', status=401))

    try:
        # Attempting to parse JSON from request body
        _json = json.loads(request.body)
    except json.JSONDecodeError:
        raise WebHookResponse(response=HttpResponse(status=400))

    # Extracting relevant data from the JSON payload
    target = _json.get('target')
    action = _json.get('action')
    username = _json.get('username')
    host = _json.get('host')

    if target == 'user':
        if action == 'create' and username and host:
            # Checking if the user already exists
            if User.objects.filter(username=username, host=host).exists():
                raise WebHookResponse(response=HttpResponse(status=201))

            # Creating a new user
            new_user = User(username=username, host=host)
            if settings.DEFAULT_ACCOUNT_LIFETIME > 0:
                # Setting expiration date if applicable
                expires = timezone.now() + timedelta(days=settings.DEFAULT_ACCOUNT_LIFETIME)
                new_user.expires = expires
            new_user.save()

            raise WebHookResponse(response=HttpResponse(status=201))

        elif action == 'remove' and username and host:
            # Removing the user
            User.objects.filter(username=username, host=host).delete()
            raise WebHookResponse(response=HttpResponse(status=201))