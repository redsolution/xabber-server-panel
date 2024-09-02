from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.contrib import messages
from django.urls import resolve

from .utils import check_permissions


def permission_read(func):

    @wraps(func)
    def wrapper(view, request, *args, **kwargs):

        # resolve app name by url
        resolver_match = resolve(request.path)
        app_name = resolver_match.app_name

        if check_permissions(request.user, app_name):
            return func(view, request, *args, **kwargs)
        else:
            messages.error(request, 'You have no permissions for this request.')
            return HttpResponseRedirect(reverse('home'))

    return wrapper


def permission_write(func):

    @wraps(func)
    def wrapper(view, request, *args, **kwargs):

        # resolve app name by url
        resolver_match = resolve(request.path)
        app_name = resolver_match.app_name

        if check_permissions(request.user, app_name, permission='write'):
            return func(view, request, *args, **kwargs)
        else:
            messages.error(request, 'You have no permissions for this request.')

            # redirect logic if user has no permissions
            referer = request.META.get('HTTP_REFERER')
            if request.method == 'POST':
                return HttpResponseRedirect(request.path)
            elif referer:
                # If there is a referer, redirect to it
                return HttpResponseRedirect(referer)
            else:
                return HttpResponseRedirect(reverse('home'))

    return wrapper


def permission_admin(func):

    @wraps(func)
    def wrapper(view, request, *args, **kwargs):

        if request.user.is_admin:
            return func(view, request, *args, **kwargs)
        else:
            messages.error(request, 'You have no permissions for this request.')

            # redirect logic if user has no permissions
            referer = request.META.get('HTTP_REFERER')
            if request.method == 'POST':
                return HttpResponseRedirect(request.path)
            elif referer:
                # If there is a referer, redirect to it
                return HttpResponseRedirect(referer)
            else:
                return HttpResponseRedirect(reverse('home'))

    return wrapper