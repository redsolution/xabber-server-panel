import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xmppserverui.settings")
# sys.path[0:0] = [os.path.expanduser("~/django")]
application = get_wsgi_application()
