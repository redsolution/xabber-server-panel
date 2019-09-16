import django.dispatch

success_installation = django.dispatch.Signal(
    providing_args=["xmpp_host", "admin"])
