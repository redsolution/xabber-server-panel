from django.views.generic import TemplateView
from django.shortcuts import loader, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from xabber_server_panel.base_modules.users.decorators import permission_read, permission_write
from xabber_server_panel.api.utils import get_api
from xabber_server_panel.base_modules.groups.forms import GroupForm
from xabber_server_panel.mixins import ServerStartedMixin


class GroupList(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'groups/list.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        api = get_api(request)
        host = request.current_host
        groups = []

        if host:
            groups = api.get_groups(
                {
                    "host": host.name
                }
            ).get('groups')

            # sort groups by localpart
            if groups:
                groups = sorted(groups, key=lambda d: d['localpart'])

        context = {
            'groups': groups
        }

        if request.is_ajax():
            html = loader.render_to_string('groups/parts/groups_list.html', context, request)
            response_data = {
                'html': html
            }
            return JsonResponse(response_data)
        return self.render_to_response(context)


class GroupCreate(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'groups/create.html'

    @permission_write
    def get(self, request, *args, **kwargs):
        form = GroupForm()

        context = {
            'form': form
        }
        return self.render_to_response(context)

    @permission_write
    def post(self, request, *args, **kwargs):
        api = get_api(request)

        form = GroupForm(request.POST)

        if form.is_valid():

            response = api.create_group({
                "localpart": form.cleaned_data.get('localpart'),
                "host": form.cleaned_data.get('host'),
                "owner": form.cleaned_data.get('owner'),
                "name": form.cleaned_data.get('name'),
                "privacy": form.cleaned_data.get('privacy'),
                "index": form.cleaned_data.get('index'),
                "membership": form.cleaned_data.get('membership')
            })

            # Check api errors
            if not response.get('errors'):
                messages.success(request, 'Group "%s" created successfully' % form.cleaned_data.get("localpart"))

                return HttpResponseRedirect(reverse('groups:list'))

        context = {
            'form': form
        }
        return self.render_to_response(context)


class GroupDelete(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    @permission_write
    def get(self, request, localpart, *args, **kwargs):
        api = get_api(request)
        host = request.current_host

        if localpart and host:
            response = api.delete_group(
                {
                    'localpart': localpart,
                    'host': host.name
                }
            )

            if not response.get('errors'):
                messages.success(request, 'Group "%s" deleted successfully' % localpart)

        # redirect to previous url or groups list
        referer = request.META.get('HTTP_REFERER')
        if referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('groups:list'))