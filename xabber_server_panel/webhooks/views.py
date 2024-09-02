import traceback

from django.http import HttpResponse
from django.views.generic import View

from .signals import webhook_received
from .utils import WebHookResponse


class Hook(View):

    def post(self, request, hook_path, *args, **kwargs):
        try:
            webhook_received.send(sender=None, path=hook_path, request=request)
        except WebHookResponse as result:
            return result.response
        except:
            traceback.print_exc()
            return HttpResponse(status=500)

        return HttpResponse(status=404)
