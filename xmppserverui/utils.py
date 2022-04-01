import os
import time
import subprocess
import string
import random

from django.core.paginator import Paginator, EmptyPage
from django.urls import reverse
from django.contrib.auth import logout

from django.conf import settings


def get_xabber_web_suffix():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(5))


def is_xmpp_server_installed():
    return os.path.isfile(settings.INSTALLATION_LOCK)


def is_xmpp_server_should_start():
    if not os.path.isfile(settings.EJABBERD_STATE):
        return False
    server_state = int(open(settings.EJABBERD_STATE, "r").read(1))
    return server_state == settings.EJABBERD_STATE_ON


def get_default_url(user, django_user=None):
    if user.is_anonymous:
        return reverse('auth:login')
    if django_user:
        if django_user.is_admin or django_user.get_all_permissions():
            return reverse('server:home')
    return reverse('root-page')


def logout_full(request):
    if request.user.is_authenticated:
        request.user.api.logout(host=request.session['_auth_user_host'])
        logout(request)


def get_pagination_data(data, page):
    limit = settings.PAGINATION_PAGE_SIZE
    total_count = len(data)
    try:
        page = int(page)
    except ValueError:
        page = 1

    paginator = Paginator(data, limit)
    try:
        data = paginator.page(page)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)

    if paginator.num_pages <= 7:
        page_range = paginator.page_range
    elif page <= 3:
        page_range = [1, 2, 3, '...', paginator.num_pages]
    elif page >= paginator.num_pages - 2:
        page_range = [1, '...', paginator.num_pages - 2,
                      paginator.num_pages - 1, paginator.num_pages]
    else:
        page_range = [1, '...', page - 1, page, page + 1, '...',
                      paginator.num_pages]

    title = '{all} of {all}'.format(all=total_count) \
            if len(paginator.page_range) < 2 \
            else '{first} - {last} of {all}'.format(
            first=(page - 1) * limit + 1,
            last=(page - 1) * limit + len(data),
            all=total_count)

    return {"data": data, "curr_page": page, "title": title,
            "page_range": page_range}


def execute_ejabberd_cmd(cmd):
    cmd_ejabberd = [settings.EJABBERDCTL, ] + cmd
    return subprocess.call(cmd_ejabberd,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0


def start_ejabberd():
    if not is_xmpp_server_installed():
        return None
    if not is_xmpp_server_should_start():
        return None
    if is_ejabberd_running()['success']:
        return None
    cmd = ['start']
    response = {"success": execute_ejabberd_cmd(cmd)}

    while not is_ejabberd_running()['success']:
        time.sleep(1)
    started_ejabberd()
    return response


def started_ejabberd():
    if not is_xmpp_server_installed():
        return None
    if not is_xmpp_server_should_start():
        return None
    if is_ejabberd_running()['success']:
        return None
    cmd = ['started']
    response = {"success": execute_ejabberd_cmd(cmd)}
    return response


def is_ejabberd_running():
    cmd = ['status']
    return {"success": execute_ejabberd_cmd(cmd)}


def get_chats_pagination_data(data, curr_page, total_pages, total_objects, obj_per_page):

    if total_pages <= 7:
        page_range = range(1, total_pages + 1)
    elif curr_page <= 3:
        page_range = [1, 2, 3, '...', total_pages]
    elif curr_page >= total_pages - 2:
        page_range = [1, '...', total_pages - 2,
                      total_pages - 1, total_pages]
    else:
        page_range = [1, '...', curr_page - 1, curr_page, curr_page + 1, '...',
                      total_pages]

    title = '{all} of {all}'.format(all=total_objects) if len(page_range) < 2 \
        else '{first} - {last} of {all}'.format(
        first=(curr_page - 1) * obj_per_page + 1,
        last=(curr_page - 1) * obj_per_page + len(data),
        all=total_objects)

    context = {
        "data": data,
        "curr_page": curr_page,
        "title": title if title else "0 of 0",
        "page_range": page_range,
        "total_pages": total_pages,
        "previous_page_number": curr_page - 1,
        "next_page_number": curr_page + 1
    }
    return context
