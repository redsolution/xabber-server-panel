from django.shortcuts import reverse, loader
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import management
from django.contrib import messages

from xabber_server_panel.base_modules.config.models import RootPage
from xabber_server_panel.base_modules.users.models import User
from xabber_server_panel.base_modules.users.decorators import permission_admin
from xabber_server_panel.base_modules.circles.models import Circle
from xabber_server_panel.base_modules.circles.utils import check_circles
from xabber_server_panel.base_modules.users.utils import check_users, check_permissions
from xabber_server_panel.base_modules.config.utils import get_modules
from xabber_server_panel.utils import check_versions, reload_server, get_error_messages
from xabber_server_panel.api.utils import get_api
from xabber_server_panel.mixins import ServerStartedMixin
from xabber_server_panel import version as current_version

import importlib
import os
import re
import shutil
import zipfile
from django.conf import settings


class Root(TemplateView):

    def get(self, request, *args, **kwargs):

        # redirect to module root
        rp = RootPage.objects.first()
        modules = get_modules()

        if rp and rp.module:
            if rp.module != 'home' and rp.module in modules:
                module = 'modules.%s' % rp.module

                # return current root module view
                try:
                    module_view = importlib.import_module(module).views.RootView.as_view()
                    return module_view(request)
                except(AttributeError, ModuleNotFoundError):
                    pass

        return HttpResponseRedirect(
            reverse('home')
        )


class HomePage(LoginRequiredMixin, TemplateView):

    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        context = {}
        return self.render_to_response(context, **kwargs)


class Search(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'search.html'

    def get(self, request, *args, **kwargs):
        try:
            text = request.GET.get('search', '').strip()
        except:
            text = ''

        host = request.current_host
        api = get_api(request)

        context = {}

        if host:

            if check_permissions(request.user, 'circles'):
                # check circles from server
                check_circles(api, host.name)

                circles = Circle.objects.filter(
                    Q(circle__contains=text, host=host.name)
                    | Q(name__contains=text, host=host.name)
                ).exclude(circle=host.name).order_by('circle')
                context['circles'] = circles

            if check_permissions(request.user, 'users'):
                # check users from server
                check_users(api, host.name)

                users = User.objects.filter(
                    Q(username__contains=text, host=host.name)
                    | Q(first_name__contains=text, host=host.name)
                    | Q(last_name__contains=text, host=host.name)
                ).order_by('username')
                context['users'] = users

            if check_permissions(request.user, 'groups'):
                # get group list
                groups = api.get_groups(
                    {
                        "host": host.name
                    }
                ).get('groups')

                if groups:
                    group_list = [group for group in groups if text in group.get('name', '')]
                    context['groups'] = group_list

        if request.is_ajax():
            if object == 'users':
                template = 'users/parts/user_list.html'
            elif object == 'circles':
                template = 'circles/parts/circle_list.html'
            elif object == 'groups':
                template = 'groups/parts/groups_list.html'
            else:
                template = 'parts/search_list.html'
            html = loader.render_to_string(template, context, request)
            response_data = {
                'html': html,
            }
            return JsonResponse(response_data)

        return self.render_to_response(context, **kwargs)


class Suggestions(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'parts/dropdown_field.html'

    def get(self, request, *args, **kwargs):

        try:
            self.text = request.GET.get('text', '').strip()
        except:
            self.text = ''

        if self.text.count('@') == 1:
            # Split the search string into local part and host
            self.localpart, self.host_part = self.text.split('@')
        else:
            self.localpart = self.host_part = None

        try:
            self.objects = request.GET.get('objects').split(',')
        except:
            self.objects = []

        type = request.GET.get('type')

        if type == 'search':
            self.template_name = 'parts/dropdown_search.html'

        self.hosts = request.hosts.values_list('name', flat=True)

        self.api = get_api(request)

        self.context = {}

        response_data = {}
        if self.hosts and self.text:
            if 'circles' in self.objects and check_permissions(request.user, 'circles'):
                self.search_circles()

            if 'users' in self.objects and check_permissions(request.user, 'users'):
                self.search_users()

            if 'groups' in self.objects and check_permissions(request.user, 'groups'):
                self.search_groups()

            html = loader.render_to_string(self.template_name, self.context)

            response_data['html'] = html

        return JsonResponse(response_data)

    def search_circles(self):
        # create circles query
        q = Q()
        if self.localpart or self.host_part:
            q |= Q(
                circle__contains=self.localpart,
                host__startswith=self.host_part,
                host=self.request.current_host.name
            )
        else:
            q |= Q(
                circle__contains=self.text,
                host=self.request.current_host.name
            )
            q |= Q(
                host__contains=self.text,
                host=self.request.current_host.name
            )
            q |= Q(
                name__contains=self.text,
                host=self.request.current_host.name
            )

        circles = Circle.objects.only('id', 'circle', 'host').filter(q).order_by('circle', 'host')
        circles = circles.exclude(circle__in=self.hosts)
        self.context['circles'] = circles[:10]

    def search_users(self):
        q = Q()
        if self.localpart or self.host_part:
            q |= Q(
                username__contains=self.localpart,
                host__startswith=self.host_part,
                host=self.request.current_host.name
            )
        else:
            q |= Q(username__contains=self.text, host=self.request.current_host.name)
            q |= Q(host__contains=self.text, host=self.request.current_host.name)

        users = User.objects.only('id', 'username', 'host').filter(q).order_by('username', 'host')
        self.context['users'] = users[:10]

    def search_groups(self):
        group_list = []

        # get group list
        groups = self.api.get_groups(
            {
                "host": self.request.current_host.name
            }
        ).get('groups')

        if groups:
            for group in groups:
                if self.text in group.get('name', ''):
                    group_list += [group]

            self.context['groups'] = group_list[:10]


class UpdatePanel(LoginRequiredMixin, TemplateView):

    @permission_admin
    def get(self, request, *args, **kwargs):
        self.archive_path = 'panel.zip'  # Path to your zip archive
        if os.path.exists(self.archive_path):
            self.extract_files()
        else:
            messages.error(request, 'Panel archive does not exists.')

        error_messages = get_error_messages(request)
        if not error_messages:
            messages.success(request, 'Xabber Server Panel updated successfully.')

        return HttpResponseRedirect(
            reverse('home')
        )

    def extract_files(self):
        # Define paths
        base_dir = settings.BASE_DIR  # Base directory of the project
        project_path = settings.PROJECT_ROOT
        unzipped_path = os.path.join(settings.BASE_DIR, 'unzipped_project')
        version_file = 'xabber_server_panel/__init__.py'

        try:
            # Unzip the archive and check version
            new_version = None
            with zipfile.ZipFile(self.archive_path, 'r') as zip_ref:
                zip_ref.extractall(unzipped_path)  # Extract to a temporary directory
                if version_file in zip_ref.namelist():
                    with zip_ref.open(version_file) as f:
                        file_content = f.read().decode('utf-8')
                        new_version = self.extract_version(file_content)

            check_v_result = check_versions(current_version, new_version)
            if not check_v_result.get('success'):
                raise Exception(check_v_result.get('error'))

            # Backup current project files (optional but recommended)
            backup_path = os.path.join(base_dir, 'backup')
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.copytree(project_path, os.path.join(backup_path, 'xabber_server_panel'))

            # Replace the project files
            for item in os.listdir(unzipped_path):
                s = os.path.join(unzipped_path, item)
                d = os.path.join(base_dir, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            management.call_command('collectstatic', '--noinput', interactive=False)

            reload_server()
        except Exception as e:
            messages.error(self.request, e)

        # Clean up
        shutil.rmtree(unzipped_path)

    def extract_version(self, file_content):
        for line in file_content.splitlines():
            match = re.match(r"^version\s*=\s*['\"]([^'\"]*)['\"]", line)
            if match:
                return match.group(1)
        return None