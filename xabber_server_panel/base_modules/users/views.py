from django.shortcuts import reverse, loader
from django.views.generic import TemplateView
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from datetime import datetime

from xabber_server_panel.base_modules.circles.models import Circle
from xabber_server_panel.base_modules.circles.utils import check_circles
from xabber_server_panel.utils import get_error_messages
from xabber_server_panel.base_modules.users.utils import get_user_data_for_api, get_user_sessions
from xabber_server_panel.base_modules.users.decorators import permission_read, permission_write, permission_admin
from xabber_server_panel.api.utils import get_api
from xabber_server_panel.mixins import ServerStartedMixin

from .models import User, CustomPermission, get_apps_choices
from .forms import UserForm
from .utils import check_users, block_user, ban_user, unblock_user, set_expires


class CreateUser(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'users/create.html'

    @permission_write
    def get(self, request, *args, **kwargs):

        context = {
            'form': UserForm()
        }

        return self.render_to_response(context)

    @permission_write
    def post(self, request, *args, **kwargs):

        form = UserForm(request.POST)
        self.api = get_api(request)

        if form.is_valid():
            # create user instance without save in db
            user = form.save(commit=False)

            self.create_user_api(user, form.cleaned_data)

            # check api errors
            error_messages = get_error_messages(request)
            if not error_messages:
                # save user in db success
                user.save()
                messages.success(request, 'User "%s" created successfully.' % user.full_jid)

                return HttpResponseRedirect(
                    reverse(
                        'users:detail',
                        kwargs={
                            'id': user.id
                        }
                    )
                )
        else:
            # add common errors
            common_error = form.errors.get('__all__')
            if common_error:
                messages.error(request, common_error)


        context = {
            'form': form
        }
        return self.render_to_response(context)

    def create_user_api(self, user, cleaned_data):
        self.api.create_user(
            get_user_data_for_api(user, cleaned_data.get('password'))
        )
        if user.is_admin and self.request.user.is_admin:
            self.api.set_admin(
                {
                    "username": cleaned_data['username'],
                    "host": cleaned_data['host']
                }
            )


class UserDetail(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'users/detail.html'

    @permission_read
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        context = {
            'user': user,
        }
        return self.render_to_response(context)

    @permission_write
    def post(self, request, id, *args, **kwargs):
        try:
            self.user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if self.user.host not in request.user.get_allowed_hosts():
            raise Http404

        self.api = get_api(request)

        self.errors = []

        # update user params
        self.update_user()

        if self.errors:
            for error in self.errors:
                messages.error(request, error)
        else:
            # check api errors
            error_messages = get_error_messages(request)
            if not error_messages:
                messages.success(request, 'User "%s" changed successfully.' % self.user.full_jid)

        context = {
            'user': self.user,
        }
        return self.render_to_response(context)

    def update_user(self):

        password = self.request.POST.get('password')
        confirm_password = self.request.POST.get('confirm_password')

        # change password can only admin
        if (password or confirm_password) and (self.request.user.is_admin or self.request.user == self.user):

            # Check user auth backend
            if self.user.auth_backend_is_ldap:
                self.errors += ['User auth backend is "ldap". Password cant be changed.']

            elif password == confirm_password:

                self.api.change_password_api(
                    {
                        'password': password,
                        'username': self.user.username,
                        'host': self.user.host
                    }
                )

                # Change the user's password
                self.user.set_password(password)

            else:
                self.errors += ['Password is incorrect.']

        user_status = self.user.status

        # set expires if it's provided
        # BEFORE CHANGE STATUS!!!
        expires_date = self.request.POST.get('expires_date')
        expires_time = self.request.POST.get('expires_time')
        delete_expires = self.request.POST.get('delete_expires')

        if expires_date or delete_expires:
            if self.user == self.request.user:
                self.errors += ['You cant change self expires.']
            elif self.user.is_admin and not self.request.user.is_admin:
                self.errors += ['You cant change expires of admin.']
            else:
                if delete_expires:
                    set_expires(self.api, self.user, None)
                elif expires_date:

                    # set default time if it's not provided
                    if not expires_time:
                        expires_time = '12:00'

                    expires_date = datetime.strptime(expires_date, '%Y-%m-%d')
                    expires_time = datetime.strptime(expires_time, '%H:%M').time()
                    expires = datetime.combine(expires_date, expires_time)
                    set_expires(self.api, self.user, expires)

        status = self.request.POST.get('status')
        if status and user_status != status:
            self.change_status(status)

        self.user.save()

    def change_status(self, status):

        """ Change status and send data to server """

        if status == 'BLOCKED':
            reason = self.request.POST.get('reason')
            if self.request.user == self.user:
                self.errors += ['You can not block yourself.']
            elif self.user.is_admin and not self.request.user.is_admin:
                self.errors += ['You can not block admin.']
            else:
                block_user(self.api, self.user, reason)

        elif status == 'BANNED' and not self.user.auth_backend_is_ldap:
            if self.request.user == self.user:
                self.errors += ['You can not ban yourself.']
            elif self.user.is_admin and not self.request.user.is_admin:
                self.errors += ['You can not ban admin.']
            else:
                ban_user(self.api, self.user)

        elif status == 'ACTIVE':
            unblock_user(self.api, self.user)


class UserBlock(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    @permission_write
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        api = get_api(request)

        reason = self.request.GET.get('reason')

        if request.user == user:
            messages.error(request, 'You can not block yourself.')
        elif user.is_admin and not request.user.is_admin:
            messages.error(request, 'You can not block admin.')
        else:
            block_user(api, user, reason)

        # redirect to previous url or users list
        referer = request.META.get('HTTP_REFERER')
        if referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('users:list'))


class UserUnBlock(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    @permission_write
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        api = get_api(request)

        unblock_user(api, user)

        # redirect to previous url or users list
        referer = request.META.get('HTTP_REFERER')
        if referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('users:list'))


class UserDelete(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    @permission_write
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        api = get_api(request)

        if user.auth_backend_is_ldap:
            messages.error(request, 'User auth backend is "ldap". User cant be deleted.')
        elif user.is_admin and not request.user.is_admin:
            messages.error(request, 'You can not delete admin.')
        elif user.full_jid != request.user.full_jid:
            user.delete()
            response = api.unregister_user(
                {
                    'username': user.username,
                    'host': user.host
                }
            )

            # check api errors
            if not response.get('errors'):
                messages.success(request, 'User "%s" deleted successfully.' % user.full_jid)
        else:
            messages.error(request, 'You can not delete yourself.')

        # redirect to previous url or users list
        user_detail_url = reverse('users:detail', kwargs={'id': id})
        referer = request.META.get('HTTP_REFERER')
        if referer and user_detail_url not in referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('users:list'))


class UserVcard(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'users/vcard.html'

    @permission_read
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        context = {
            'user': user,
        }
        return self.render_to_response(context)

    @permission_write
    def post(self, request, id, *args, **kwargs):
        try:
            self.user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if self.user.host not in request.user.get_allowed_hosts():
            raise Http404

        self.api = get_api(request)

        # update user params
        self.update_user()

        context = {
            'user': self.user,
        }
        return self.render_to_response(context)

    def update_user(self):
        self.user.nickname = self.request.POST.get('nickname')

        self.user.first_name = self.request.POST.get('first_name')

        self.user.last_name = self.request.POST.get('last_name')

        response = self.api.set_vcard(
            get_user_data_for_api(self.user)
        )

        self.user.save()

        # check api errors
        if not response.get('errors'):
            messages.success(self.request, 'User "%s" changed successfully.' % self.user.full_jid)


class UserCircles(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'users/circles.html'

    @permission_read
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        api = get_api(request)

        check_circles(api, user.host)

        self.circles = Circle.objects.filter(host=user.host).exclude(circle=user.host)

        context = {
            'user': user,
            'circles': self.circles
        }
        return self.render_to_response(context)

    @permission_write
    def post(self, request, id, *args, **kwargs):
        try:
            self.user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if self.user.host not in request.user.get_allowed_hosts():
            raise Http404

        self.circles = Circle.objects.filter(host=self.user.host).exclude(circle=self.user.host)
        self.api = get_api(request)

        # update user params
        self.update_user()

        # check api errors
        error_messages = get_error_messages(request)
        if not error_messages:
            messages.success(self.request, 'User "%s" changed successfully.' % self.user.full_jid)

        context = {
            'user': self.user,
            'circles': self.circles
        }
        return self.render_to_response(context)

    def update_user(self):
        # change circles in db and send data to server
        circles = self.request.POST.getlist('circles', [])

        new_circles = set(map(int, circles))
        existing_circles = set(self.user.circles.values_list('id', flat=True))

        # Added circles id list
        ids_to_add = new_circles - existing_circles

        # Removed circles id list
        ids_to_delete = existing_circles - new_circles

        # add circles
        circles_to_add = self.circles.filter(id__in=ids_to_add)
        for circle in circles_to_add:
            self.api.add_circle_members(
                {
                    'circle': circle.circle,
                    'host': circle.host,
                    'members': [self.user.full_jid]
                }
            )

        # delete circles
        circles_to_delete = self.circles.filter(id__in=ids_to_delete)
        for circle in circles_to_delete:
            self.api.del_circle_members(
                {
                    'circle': circle.circle,
                    'host': circle.host,
                    'members': [self.user.full_jid]
                }
            )
        self.user.circles.set(circles)

        self.user.save()


class UserList(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'users/list.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        host = request.current_host
        self.users = User.objects.none()
        api = get_api(request)

        context = {}

        if host:
            check_users(api, host.name)

            self.users = User.objects.filter(host=host.name)

            context['users'] = self.users.order_by('username')

        if request.is_ajax():
            html = loader.render_to_string('users/parts/user_list.html', context, request)
            response_data = {
                'html': html,
            }
            return JsonResponse(response_data)

        return self.render_to_response(context)


class UserPermissions(ServerStartedMixin, LoginRequiredMixin, TemplateView):
    template_name = 'users/permissions.html'

    @permission_admin
    def get(self, request, id, *args, **kwargs):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if user.host not in request.user.get_allowed_hosts():
            raise Http404

        # check if user change himself
        if user == request.user:
            messages.error(request, 'You cant change self permissions.')
            return HttpResponseRedirect(reverse('home'))

        permissions = {
            app[0]: {
                'app_name': app[1],
                'permissions': CustomPermission.objects.filter(app=app[0])
            }
            for app in get_apps_choices()
        }

        context = {
            'user': user,
            'permissions': permissions
        }
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, id, *args, **kwargs):
        try:
            self.user = User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

        if self.user.host not in request.user.get_allowed_hosts():
            raise Http404

        # check if user change himself
        if self.user == request.user:
            messages.error(request, 'You cant change self permissions.',)
            return HttpResponseRedirect(reverse('home'))

        self.api = get_api(request)

        self.update_permissions()

        # check api errors
        error_messages = get_error_messages(request)
        if not error_messages:
            self.user.save()
            messages.success(self.request, 'Permissions changed successfully.')

        permissions = {
            app[0]: {
                'app_name': app[1],
                'permissions': CustomPermission.objects.filter(app=app[0])
            }
            for app in get_apps_choices()
        }

        context = {
            'user': self.user,
            'permissions': permissions
        }
        return self.render_to_response(context)

    def update_permissions(self):

        is_admin = self.request.POST.get('is_admin', False)

        permission_id_list = []

        for app in get_apps_choices():
            app_permission_id_list = self.request.POST.getlist('permissions_%s' % app[0], [])
            permission_id_list += app_permission_id_list

        permission_list = CustomPermission.objects.filter(id__in=permission_id_list)

        self.user.is_admin = True if is_admin else False

        self.user.permissions.set(permission_list)

        if is_admin:
            self.api.set_admin(
                {
                    "username": self.user.username,
                    "host": self.user.host
                }
            )
        else:
            self.api.del_admin(
                {
                    "username": self.user.username,
                    "host": self.user.host,
                }
            )

            permissions = self.get_permissions_dict()

            self.api.set_permissions(
                {
                    "username": self.user.username,
                    "host": self.user.host,
                    "permissions": permissions,
                }
            )

        # delete user sessions if it's has no permissions
        if not self.user.is_admin and not self.user.permissions.exists():
            user_sessions = get_user_sessions(self.user)
            if user_sessions:
                for session in user_sessions:
                    session.delete()

    def get_permissions_dict(self):

        """
            Create permissions dict depending on selected user permissions
        """

        permissions = {}

        circles_read = self.user.permissions.filter(app='circles', permission='read').exists()
        circles_write = self.user.permissions.filter(app='circles', permission='write').exists()
        if circles_write:
            permissions['circles'] = 'write'
        elif circles_read:
            permissions['circles'] = 'read'
        else:
            permissions['circles'] = 'forbidden'

        dashboard_read = self.user.permissions.filter(app='dashboard', permission='read').exists()
        dashboard_write = self.user.permissions.filter(app='dashboard', permission='write').exists()
        if dashboard_write:
            permissions['server'] = 'write'
        elif dashboard_read:
            permissions['server'] = 'read'
        else:
            permissions['server'] = 'forbidden'

        groups_read = self.user.permissions.filter(app='groups', permission='read').exists()
        groups_write = self.user.permissions.filter(app='groups', permission='write').exists()
        if groups_write:
            permissions['groups'] = 'write'
        elif groups_read:
            permissions['groups'] = 'read'
        else:
            permissions['groups'] = 'forbidden'

        users_read = self.user.permissions.filter(app='users', permission='read').exists()
        users_write = self.user.permissions.filter(app='users', permission='write').exists()
        if users_write:
            permissions['users'] = 'write'
            permissions['vcard'] = 'write'
        elif users_read:
            permissions['users'] = 'read'
            permissions['vcard'] = 'read'
        else:
            permissions['users'] = 'forbidden'
            permissions['vcard'] = 'forbidden'

        return permissions