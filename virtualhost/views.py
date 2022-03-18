import math
import time
from datetime import datetime, timedelta
from importlib import import_module
from django.contrib.auth.models import Permission
from django.db.models import Count
from django.views.generic import TemplateView
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, Http404, HttpResponse, QueryDict

from django.conf import settings
from xmppserverui.utils import get_pagination_data
from xmppserverui.mixins import PageContextMixin, ServerStartedMixin
from .forms import RegisterUserForm, UnregisterUserForm, EditUserVcardForm, \
    CreateGroupForm, EditGroupForm, DeleteGroupForm, AddGroupMemberForm, \
    DeleteGroupMemberForm, ChangeUserPasswordForm, AddGroupAllMemberForm, DeleteGroupAllMemberForm, RegistrationKeysForm
from .models import User, Group, GroupMember, GroupChat, VirtualHost

USER_TAB_DETAILS = 'user-details'
USER_TAB_VCARD = 'user-vcard'
USER_TAB_SECURITY = 'user-security'
USER_TAB_GROUPS = 'user-groups'
USER_TAB_PERMISSIONS = 'user-permissions'

GROUP_TAB_DETAILS = 'group-details'
GROUP_TAB_MEMBERS = 'group-members'
GROUP_TAB_SUBSCRIPTIONS = 'group-subscriptions'
TAB_REGISTRATION_KEYS = 'registration-keys'
EXCLUDED_PERMISSIONS_APPS = ['admin', 'auth', 'sessions', 'contenttypes']
EXCLUDED_PERMISSIONS_MODELS = [
    'authbackend', 'configdata', 'configuration', 'ldapsettings', 'ldapsettingsserver', 'serverconfig',
    'serverconfiguration', 'groupmember', "virtualhost", 'basemoduleconfig'
]
EXCLUDED_PERMISSIONS_CODENAMES = [
    'add_dashboard', 'change_dashboard', 'delete_dashboard', 'add_groupchat', 'change_groupchat', 'delete_groupchat',
    'add_userpassword', 'delete_userpassword', "view_userpassword"
]

PERMISSIONS_DICT = {
    'virtualhost.view_user': {'users': 'read'},
    'virtualhost.view_group': {'circles': 'read'},
    'virtualhost.view_groupchat': {'groups': 'read'},
    'server.view_dashboard': {'server': 'read'},
    'virtualhost.add_user': {'users': 'write'},
    'virtualhost.delete_user': {'users': 'write'},
    'virtualhost.change_user': {'users': 'write'},
    'virtualhost.change_userpassword': {'users': 'write'},
    'virtualhost.add_group': {'circles': 'write'},
    'virtualhost.delete_group': {'circles': 'write'},
    'virtualhost.change_group': {'circles': 'write'},
}


def update_module_permissions():
    for module_name in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
        try:
            module = import_module(module_name + ".apps")
            config = getattr(module, 'ModuleConfig')
            EXCLUDED_PERMISSIONS_MODELS.extend(getattr(config, 'EXCLUDED_PERMISSIONS_MODELS'))
            EXCLUDED_PERMISSIONS_CODENAMES.extend(getattr(config, 'EXCLUDED_PERMISSIONS_CODENAMES'))
        except ImportError:
            print('Module', module_name, 'does not exist')
        except AttributeError:
            print('Module', module_name, 'app config is improperly configured')


update_module_permissions()


def set_api_permissions(user, curr_user, perms_list):
    django_perms_list = ['{0}.{1}'.format(p.content_type.app_label, p.codename) for p in perms_list]
    commands = []
    if not curr_user.is_admin:
        for perm in django_perms_list:
            try:
                if isinstance(PERMISSIONS_DICT[perm], list):
                    for command in PERMISSIONS_DICT[perm]:
                        commands += [command]
                else:
                    commands += [PERMISSIONS_DICT[perm]]
            except KeyError:
                pass
        perms_dict = {key: 'forbidden' for key in ['circles', 'groups', 'users', 'server', 'vcard']}
        sorted_perms = sorted(commands, key=lambda i: list(i.values()))
        for perm in sorted_perms:
            key, value = list(perm.items())[0]
            perms_dict[key] = value
        perms_dict['vcard'] = perms_dict['users']
        user.api.xabber_del_admin(
            {
                "username": curr_user.username,
                "host": curr_user.host,
            }
        )
        user.api.xabber_set_permissions(
            {
                "username": curr_user.username,
                "host": curr_user.host,
                "permissions": perms_dict,
            }
        )

    else:
        user.api.xabber_set_admin(
            {
                "username": curr_user.username,
                "host": curr_user.host,
            }
        )


# def get_page_title(paginator, data, hosts_count):
#     return str(paginator.count + hosts_count)


class VhostContextView(ServerStartedMixin):
    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get_vhost_obj(self, request, *args, **kwargs):
        host_name = self.get_vhost(request)
        try:
            host = VirtualHost.objects.get(name=host_name)
        except Exception as e:
            host = None
        return host

    def get_response(self, request, *args, **kwargs):
        response = self.render_to_response(kwargs['context'])
        if 'vhost' not in request.COOKIES:
            expires = datetime.utcnow() + timedelta(days=30)
            expires = datetime.strftime(expires, "%a, %d-%b-%Y %H:%M:%S GMT")
            response.set_cookie('vhost', kwargs['vhost'], expires=expires)
        return response


class SearchView(VhostContextView, TemplateView):
    template_name = 'virtualhost/search.html'

    def get(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        if request.GET.get('search'):
            search_name = request.GET.get('search').rstrip().lstrip()
            user = request.user
            users = user.api.xabber_registered_users({"host": vhost})
            groups = user.api.get_groups({"host": vhost})
            chats = user.api.xabber_registered_chats({"host": vhost, "limit": 200, "page": 1})
            data_users = []
            data_groups = []
            data_chats = []
            if "error" not in users:
                django_users = User.objects.filter(username__contains=search_name, host=vhost)
                for user in users:
                    django_user = filter(lambda o: o.username == user['name'], django_users)
                    django_user = next(django_user, None)
                    if django_user:
                        data_users.append({"username": user['name'], "user": django_user})
            if "error" not in groups:
                all_groups = Group.objects.filter(group__contains=search_name, host=vhost)
                groups_members_count = GroupMember.objects.values('group__group').annotate(dcount=Count('group'))
                for g in groups:
                    group = filter(lambda o: o.group == g, all_groups)
                    group = next(group, None)
                    if group:
                        count = next(filter(lambda o: o['group__group'] == group.group, groups_members_count),
                                     {'group__group': 'null', 'dcount': 0})['dcount']
                        if GroupMember.objects.filter(group=group, username="@all@").exists():
                            # TODO get rid of list()
                            count += User.objects.filter(host=group.host).count() - 1

                        data_groups.append({
                            "group": g,
                            "members": count,
                            "name": group.name if group.name else '',
                            "id": group.id
                        })
                data_groups.sort(key=lambda k: k['group'])
                data_groups.sort(key=lambda k: k['members'], reverse=True)
            if "error" not in chats:
                django_users = list(User.objects.all().values())
                for chat in chats:
                    if search_name in chat['name']:
                        if len(chat["owner"].split('@')) == 2:
                            owner_username, owner_host = chat["owner"].split('@')
                        elif len(chat["owner"].split('@')) == 1:
                            owner_username = chat["owner"]
                            owner_host = ".".join(owner_username.split('.')[1:])
                        else:
                            pass
                        user = next(filter(lambda o: o['username'] == owner_username
                                                     and o['host'] == owner_host, django_users), None)

                        data_chats.append({"chat": chat, "owner_id": user['id'] if user else None})
            context = {'data_users': data_users, 'data_groups': data_groups, 'data_chats': data_chats}
            context = {**context, **self.context}
            return self.get_response(request, vhost=vhost, context=context)
        else:
            return HttpResponseRedirect(reverse('server:home'))


class UserListView(VhostContextView, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/users.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        users = user.api.xabber_registered_users({"host": vhost}).get('users')

        if "error" in users:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": users.get("error")})

        django_users = User.objects.filter(host=vhost).values('username')
        django_users = [o['username'] for o in django_users]
        unknown_users = []
        for user in users:
            if user['username'] not in django_users:
                unknown_users.append(User(username=user['username'], host=vhost, auth_backend=user['backend']))
        User.objects.bulk_create(unknown_users)

        # vhost_obj = self.get_vhost_obj(request)
        # allowed_user_change = True
        # allowed_user_delete = False \
        #     if (hasattr(vhost_obj, 'ldapsettings') and
        #         vhost_obj.ldapsettings.is_enabled) \
        #     else True

        django_users = User.objects.filter(host=vhost)
        data = []
        for user in users:
            django_user = filter(lambda o: o.username == user['username'], django_users)
            django_user = next(django_user, None)
            if django_user:
                data.append({"username": user['username'],
                             "user": django_user})

        page = request.GET.get('page', 1)
        context = get_pagination_data(data, page)
        context = {**context, **self.context}
        return self.get_response(request, vhost=vhost, context=context)


class UserCreateView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_create.html'

    def get(self, request, *args, **kwargs):
        if not self.context['vhosts_cr']:
            return HttpResponseRedirect(reverse('error:403'))

        user = request.user
        if self.context['auth_user'].is_admin:
            form = RegisterUserForm(user, vhosts=self.context['vhosts_cr'])
        else:
            try:
                host = VirtualHost.objects.get(name=self.context['auth_user'].host)
                form = RegisterUserForm(user, vhosts=[host])
            except VirtualHost.DoesNotExist:
                raise Http404

        return self.render_to_response({
            "form": form,
            "gen_pass_len": settings.GENERATED_PASSWORD_MAX_LEN
        })

    def post(self, request, *args, **kwargs):
        if not self.context['vhosts_cr']:
            return HttpResponseRedirect(reverse('error:403'))

        user = request.user
        if self.context['auth_user'].is_admin:
            form = RegisterUserForm(user, request.POST, request.FILES, vhosts=self.context['vhosts_cr'])
        else:
            try:
                data = QueryDict.copy(request.POST)
                if 'is_admin' in data:
                    del data['is_admin']
                host = VirtualHost.objects.get(name=self.context['auth_user'].host)
                form = RegisterUserForm(user, data, request.FILES, vhosts=[host])
            except VirtualHost.DoesNotExist:
                raise Http404
        if form.is_valid():
            if form.cleaned_data['is_admin'] is True and self.context['auth_user'].is_admin:
                user.api.xabber_set_admin(
                    {
                        "username": form.cleaned_data['username'],
                        "host": form.cleaned_data['host']
                    }
                )
            return HttpResponseRedirect(
                reverse('virtualhost:user-created',
                        kwargs={'user_id': form.new_user.id}))
        return self.render_to_response({
            "form": form,
            "gen_pass_len": settings.GENERATED_PASSWORD_MAX_LEN
        })


class UserCreatedView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_created.html'

    def get(self, request, *args, **kwargs):
        if not self.context['vhosts_cr']:
            return HttpResponseRedirect(reverse('error:403'))

        try:
            new_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        user_pass = new_user.password
        new_user.password = None
        new_user.save()

        return self.render_to_response({
            "new_user": new_user,
            'user_pass': user_pass
        })


class UserInstructionView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_instruction.html'

    def get(self, request, *args, **kwargs):
        try:
            user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404

        return self.render_to_response({
            'host': user.host,
            'username': user.full_jid,
        })

    def post(self, request, *args, **kwargs):
        try:
            user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        password = request.POST.get('password')

        return self.render_to_response({
            'host': user.host,
            'username': user.full_jid,
            'password': password
        })


class UserDetailsView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_details.html'

    def _get_vcard(self, request, curr_user):
        user = request.user
        nickname, first_name, last_name = None, None, None
        vcard = user.api.get_vcard({"username": curr_user.username,
                                    "host": curr_user.host})
        if user.api.success:
            if vcard.get('vcard'):
                nickname = vcard.get('vcard').get('nickname')
            try:
                first_name = vcard['vcard']['n']['given']
            except KeyError:
                pass
            try:
                last_name = vcard['vcard']['n']['family']
            except KeyError:
                pass
        return nickname, first_name, last_name

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        self.check_host(curr_user.host)
        nickname, first_name, last_name = self._get_vcard(request, curr_user)
        curr_user.nickname = nickname
        curr_user.first_name = first_name
        curr_user.last_name = last_name
        curr_user.save()

        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_DETAILS})


class UserSecurityView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_security.html'

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        else:
            if not curr_user.allowed_change_password or curr_user.is_admin and not self.context['auth_user'].is_admin:
                return HttpResponseRedirect(reverse('error:403'))
        self.check_host(curr_user.host)
        user = request.user
        form = ChangeUserPasswordForm(user)
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_SECURITY,
                                        "form": form})

    def post(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        else:
            if not curr_user.allowed_change_password:
                return HttpResponseRedirect(reverse('error:403'))
        self.check_host(curr_user.host)
        user = request.user
        form = ChangeUserPasswordForm(user, request.POST, user_to_change=curr_user)
        if form.is_valid():
            curr_user.set_password(request.POST['password'])
            curr_user.save()
            return HttpResponseRedirect(reverse('virtualhost:user-details', kwargs={"user_id": curr_user.id}))
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_SECURITY,
                                        "form": form})


class UserGroupsView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_groups.html'

    def get_user_groups_list(self, user):
        user_groups = list(map(lambda x: x.group.group, GroupMember
                               .objects
                               .filter(username=user.username, host=user.host)))
        groups_on_host = Group.objects.filter(host=user.host)
        for group in groups_on_host:
            if GroupMember.objects.filter(group=group, username='@all@'):
                user_groups.append(group.group)
        return user_groups

    def get_groups_list(self, user):
        groups_on_host = Group.objects.filter(host=user.host)
        user_groups = list(map(lambda x: x.group, GroupMember
                               .objects
                               .filter(username=user.username, host=user.host)))
        data = []
        for group in groups_on_host:
            checked = GroupMember.objects.filter(group=group, username='@all@').exists()
            data.append({
                'group': group.group,
                'is_system': group.is_system,
                'checked': checked if checked else group in user_groups,
                'active': not checked,
                'group_verbose': 'All' if group.is_system else None,
                'secondary_verbose': '({})'.format(group.host) if group.is_system else None,
            })
        data.sort(key=lambda g: (g["checked"], g["active"]), reverse=True)
        return data

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        self.check_host(curr_user.host)

        groups = self.get_groups_list(curr_user)
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_GROUPS,
                                        "displayed_groups": groups})

    def post(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        self.check_host(curr_user.host)

        user = request.user
        post_data = request.POST.copy()
        post_data.pop('displayed_groups')
        form_group_list = request.POST.get('displayed_groups').split(';')
        groups = self.get_user_groups_list(curr_user)
        groups_to_add = list(set(form_group_list) - set(groups))
        groups_to_del = list(set(groups) - set(form_group_list))

        error = False

        for item in groups_to_add:
            data = {
                'member': curr_user.full_jid,
            }
            group = Group.objects.filter(group=item, host=curr_user.host)
            if not group.exists():
                error = True
                continue
            group = group.first()
            form = AddGroupMemberForm(user=user, data=data, group=group)
            if not form.is_valid():
                error = True

        for item in groups_to_del:
            data = {
                'member': curr_user.full_jid,
            }
            group = Group.objects.filter(group=item, host=curr_user.host)
            if not group.exists():
                error = True
                continue
            group = group.first()
            form = DeleteGroupMemberForm(user=user, data=data, group=group)
            if not form.is_valid():
                error = True

        if error:
            return self.render_to_response({"curr_user": curr_user,
                                            "active_tab": USER_TAB_GROUPS,
                                            "select_groups_error": "An unexpected error has occurred. Please, "
                                                                   "try again later.",
                                            "displayed_groups": self.get_groups_list(curr_user)})

        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_GROUPS,
                                        "displayed_groups": self.get_groups_list(curr_user)})


class DeleteUserView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_delete.html'

    def get(self, request, *args, **kwargs):
        try:
            user_to_del = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        else:
            if not user_to_del.allowed_delete:
                return HttpResponseRedirect(reverse('error:403'))
        self.check_host(user_to_del.host)

        user = request.user
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        form = UnregisterUserForm(user, username=username, host=host)
        return self.render_to_response({"user_to_del": user_to_del,
                                        "form": form})

    def post(self, request, *args, **kwargs):
        try:
            user_to_del = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        else:
            if not user_to_del.allowed_delete:
                return HttpResponseRedirect(reverse('error:403'))
        self.check_host(user_to_del.host)

        user = request.user
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        post_data = request.POST.copy()
        post_data.update({"username": user_to_del.username,
                          "host": user_to_del.host})
        form = UnregisterUserForm(user, post_data, username=username, host=host)
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:users'))
        return self.render_to_response({"user_to_del": user_to_del,
                                        "form": form})


class UserVcardView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_vcard.html'

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        self.check_host(curr_user.host)
        user = request.user
        data = {"nickname": curr_user.nickname,
                "first_name": curr_user.first_name,
                "last_name": curr_user.last_name}
        if curr_user.photo:
            data["photo"] = curr_user.photo
        form = EditUserVcardForm(user, initial=data,
                                 vhosts=self.context['vhosts'])
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_VCARD,
                                        "form": form})

    def post(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        self.check_host(curr_user.host)
        user = request.user
        post_data = request.POST.copy()
        post_data.update({"username": curr_user.username,
                          "host": curr_user.host})
        form = EditUserVcardForm(user, post_data, request.FILES,
                                 vhosts=self.context['vhosts'])
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:user-details', kwargs={"user_id": curr_user.id}))
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_VCARD,
                                        "form": form})


class GroupListView(VhostContextView, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/groups.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        groups = user.api.get_groups({"host": vhost}).get('circles')

        if "error" in groups:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": groups.get("error")})
        all_groups = Group.objects.filter(host=vhost)
        groups_members_count = GroupMember.objects.values('group__group').annotate(dcount=Count('group'))
        data = []
        for g in groups:
            # group = filter(lambda o: o['group'] == g, all_groups)
            group = all_groups.filter(group=g)
            if not group:
                data.append({"group": g, "members": 0})
            else:
                group = group[0]
                count = next(filter(lambda o: o['group__group'] == group.group, groups_members_count),
                             {'group__group': 'null', 'dcount': 0})['dcount']
                if GroupMember.objects.filter(group=group, username="@all@").exists():
                    # TODO get rid of list()
                    count += User.objects.filter(host=group.host).count() - 1

                data.append({
                    "group": g,
                    "members": count,
                    "name": group.name if group.name else '',
                    "id": group.id
                })
        data.sort(key=lambda k: k['group'])
        data.sort(key=lambda k: k['members'], reverse=True)

        page = request.GET.get('page', 1)
        context = get_pagination_data(data, page)
        context = {**context, **self.context}
        return self.get_response(request, vhost=vhost, context=context)


class GroupCreateView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_create.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        if self.context['auth_user'].is_admin:
            form = CreateGroupForm(user, vhosts=self.context['vhosts_cr'])
        else:
            try:
                host = VirtualHost.objects.get(name=self.context['auth_user'].host)
                form = CreateGroupForm(user, vhosts=[host])
            except VirtualHost.DoesNotExist:
                raise Http404
        return self.render_to_response({"form": form})

    def post(self, request, *args, **kwargs):
        user = request.user
        if self.context['auth_user'].is_admin:
            form = CreateGroupForm(user, request.POST, vhosts=self.context['vhosts_cr'])
        else:
            try:
                host = VirtualHost.objects.get(name=self.context['auth_user'].host)
                form = CreateGroupForm(user, request.POST, vhosts=[host])
            except VirtualHost.DoesNotExist:
                raise Http404
        if form.is_valid():
            return HttpResponseRedirect(
                reverse('virtualhost:group-details',
                        kwargs={"group_id": form.new_group.id}))
        return self.render_to_response({"form": form})


class GroupCreatedView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_created.html'


class DeleteGroupView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_delete.html'

    def get_group(self, id):
        try:
            return Group.objects.get(id=id)
        except Group.DoesNotExist:
            raise Http404

    def get(self, request, *args, **kwargs):
        group = self.get_group(kwargs['group_id'])
        self.check_host(group.host)
        user = request.user
        form = DeleteGroupForm(user)
        return self.render_to_response({"circle": group, "form": form})

    def post(self, request, *args, **kwargs):
        group = self.get_group(kwargs['group_id'])
        self.check_host(group.host)
        user = request.user
        post_data = request.POST.copy()
        post_data.update({"circle": group.group, "host": group.host})
        form = DeleteGroupForm(user, post_data)
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:groups'))
        return self.render_to_response({"circle": group, "form": form})


class GroupMembersView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_members.html'

    def get_group(self, id):
        try:
            return Group.objects.get(id=id)
        except Group.DoesNotExist:
            raise Http404

    def get_group_members(self, group):
        data = []
        users = list(User.objects.all())
        group_members = group.groupmember_set.exclude(username='@all@')
        for member in group_members:
            member_data = {"member": member.full_jid, "checked": True}
            try:
                member_data["user"] = [user for user in users
                                       if user.username == member.username
                                       and user.host == member.host][0]
            except IndexError:
                member_data["user"] = None
            data.append(member_data)
        data = sorted(data, key=lambda k: (k['member'].split('@')[1],
                                           k['member'].split('@')[0]))

        if group.groupmember_set.filter(username='@all@').exists():
            all_count = len(User.objects.filter(host=group.host))
            all = 'all@{}'.format(group.host)
            data.insert(0, {'member': all,
                            'member_verbose': 'All',
                            'secondary_verbose': '(%s on %s )' % (str(all_count), group.host),
                            'user': None})
        return data

    def get_adv_users_count(self, group):
        if group.groupmember_set.filter(username='@all@').exists():
            return len(User.objects.filter(host=group.host)) - len(group.groupmember_set.filter(host=group.host))
        else:
            return 0

    def get_page_context(self, request, *args, **kwargs):
        group = self.get_group(kwargs['group_id'])
        self.check_host(group.host)
        member_list = self.get_group_members(group)

        page = request.GET.get('page', 1)
        context = get_pagination_data(member_list, page)
        context['group'] = group
        context['active_tab'] = GROUP_TAB_MEMBERS
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        context['add_member_form'] = AddGroupMemberForm(user)
        context['delete_member_form'] = DeleteGroupMemberForm(user)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        form = AddGroupMemberForm(user, request.POST, group=context["group"])
        if form.is_valid():
            context = self.get_page_context(request, *args, **kwargs)
            context['added_new_member'] = True
            form = AddGroupMemberForm(user)
        else:
            context['has_form_errors'] = True
        context['add_member_form'] = form
        return self.render_to_response(context)


class GroupMembersSelectView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_members_select.html'

    def get_group(self, id):
        try:
            return Group.objects.get(id=id)
        except Group.DoesNotExist:
            raise Http404

    def get_group_members(self, group):
        return [gm.full_jid for gm in group.groupmember_set.all()]

    def get_member_list(self, group):
        all_users = [user.full_jid for user in User.objects.all()]
        all_chats = [chat.full_jid for chat in GroupChat.objects.all()]
        group_members = [gm.full_jid
                         for gm in group.groupmember_set.exclude(username='@all@')]
        members = list(set(all_users) | set(group_members) | set(all_chats))
        members = [{"member": member,
                    "checked": member in group_members,
                    "chat_marker": member in all_chats}
                   for member in members]
        members = sorted(members, key=lambda k: (k['member'].split('@')[1],
                                                 k['member'].split('@')[0]))
        all = 'all@{}'.format(group.host)
        members.insert(0, {'member': all,
                           'member_verbose': 'All',
                           'secondary_verbose': '({})'.format(group.host),
                           'checked': all in self.get_group_members(group),
                           'chat_marker': False})
        return members

    def get_page_context(self, request, *args, **kwargs):
        group = self.get_group(kwargs['group_id'])
        self.check_host(group.host)
        return {
            "active_tab": GROUP_TAB_MEMBERS,
            "group": group,
            "members": self.get_member_list(group)}

    def get(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        post_data = request.POST.copy()
        post_data.pop('member_list')
        form_member_list = request.POST.get('member_list').split(' ')
        group_members = self.get_group_members(context['group'])
        members_to_add = list(set(form_member_list) - set(group_members))
        members_to_del = list(set(group_members) - set(form_member_list))

        errors = False
        is_all_del = False
        is_all_added = False

        for member in members_to_del:
            if member.split('@')[0] == 'all':
                post_data['host'] = context["group"].host
                form = DeleteGroupAllMemberForm(user,
                                                post_data,
                                                group=context["group"])
                if not form.is_valid():
                    errors = True
                    break
                else:
                    is_all_del = True
                    break
        if not is_all_del:
            for member in members_to_del:
                if not member:
                    continue
                if member.split('@')[0] != 'all':
                    post_data['member'] = member
                    form = DeleteGroupMemberForm(user,
                                                 post_data,
                                                 group=context["group"])
                    if not form.is_valid():
                        errors = True
                        break
        for member in members_to_add:
            if member.split('@')[0] == 'all':
                post_data['host'] = context["group"].host
                form = AddGroupAllMemberForm(user,
                                             post_data,
                                             group=context["group"])
                if not form.is_valid():
                    errors = True
                    break
                else:
                    is_all_added = True
                    break
        if not is_all_added:
            for member in members_to_add:
                if not member:
                    continue
                if member.split('@')[0] != 'all':
                    post_data.update({'member': member})
                    form = AddGroupMemberForm(user,
                                              post_data,
                                              group=context["group"])
                    if not form.is_valid():
                        errors = True
                        break
        if errors:
            context["select_members_error"] = \
                "An unexpected error has occurred. Please, try again later."
            return self.render_to_response(context)
        return HttpResponseRedirect(
            reverse('virtualhost:group-members',
                    kwargs={"group_id": context["group"].id}))


class GroupDetailsView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_details.html'

    def get_group(self, id):
        try:
            return Group.objects.get(id=id)
        except Group.DoesNotExist:
            raise Http404

    def get_page_context(self, request, *args, **kwargs):
        group = self.get_group(kwargs["group_id"])
        self.check_host(group.host)
        return {"active_tab": GROUP_TAB_DETAILS,
                "group": group}

    def get(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        data = {"name": context["group"].name,
                "description": context["group"].description}
        # TODO vhosts ????
        context["form"] = EditGroupForm(user,
                                        initial=data,
                                        vhosts=self.context['vhosts'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        post_data = request.POST.copy()
        post_data.update({"group": context["group"].group,
                          "host": context["group"].host,
                          "displayed_groups": context["group"].displayed_groups})
        form = EditGroupForm(user, post_data, vhosts=self.context['vhosts'])
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:groups'))
        context["form"] = form
        return self.render_to_response(context)


class GroupSubscribersView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_subscribers.html'

    def get_group(self, id):
        try:
            return Group.objects.get(id=id)
        except Group.DoesNotExist:
            raise Http404

    def count_group_members(self, groups_members, group):
        members = list(filter(lambda o: o['group'] == group, groups_members))
        additional = 0
        for member in members:
            if member['username'] == '@all@':
                additional = User.objects.filter(host=member['host']).count() - 1
        return len(members) + additional

    def get_displayed_groups(self, group):
        all_groups = Group.objects.filter(host=group.host)
        all_groups_members = list(GroupMember.objects.all().values('group', 'username', 'host'))
        displayed_groups = group.displayed_groups if group.displayed_groups else []
        result = []
        for g in all_groups:
            if g.is_system:
                result.append({'group': g.group,
                               'group_verbose': 'All',
                               'secondary_verbose': '({})'.format(g.host),
                               'checked': g.group in displayed_groups,
                               'system': True,
                               'members_ext': '@all@ %s' % g.host,
                               'members': self.count_group_members(all_groups_members, g.pk)})
            else:
                result.append({'group': g.group,
                               'checked': g.group in displayed_groups,
                               'system': True,
                               'members': self.count_group_members(all_groups_members, g.pk)})
        result = sorted(result, key=lambda k: k["group"] and k['system'])
        return result

    def get_page_context(self, request, *args, **kwargs):
        group = self.get_group(kwargs["group_id"])
        self.check_host(group.host)
        return {"active_tab": GROUP_TAB_SUBSCRIPTIONS,
                "group": group,
                "displayed_groups": self.get_displayed_groups(group)}

    def get(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        context["form"] = EditGroupForm(user, vhosts=self.context['vhosts'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        post_data = request.POST.copy()
        post_data.update({"group": context["group"].group,
                          "host": context["group"].host,
                          "name": context["group"].name,
                          "description": context["group"].description})
        form = EditGroupForm(user, post_data, vhosts=self.context['vhosts'])
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:group-subscriptions',
                                                kwargs={"group_id": context["group"].id}))
        context["form"] = form
        return self.render_to_response(context)


class ChatListView(VhostContextView, TemplateView):
    page_section = 'vhosts-chats'
    template_name = 'virtualhost/chats.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)

        pagination_limit = settings.PAGINATION_PAGE_SIZE
        pagination_page = int(request.GET.get('page', 1))

        chats = user.api.xabber_registered_chats(
            {"host": vhost,
             "limit": pagination_limit,
             "page": pagination_page}).get('groups')
        if "error" in chats:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": chats.get("error")})

        django_users = list(User.objects.all().values())
        data = []
        for chat in chats:
            if len(chat["owner"].split('@')) == 2:
                owner_username, owner_host = chat["owner"].split('@')
            elif len(chat["owner"].split('@')) == 1:
                owner_username = chat["owner"]
                owner_host = ".".join(owner_username.split('.')[1:])
            else:
                return self.get_response(request,
                                         vhost=vhost,
                                         context={"error": chats.get("error")})
            user = next(filter(lambda o: o['username'] == owner_username
                                         and o['host'] == owner_host, django_users), None)

            data.append({"chat": chat,
                         "owner_id": user['id'] if user else None})

        page = request.GET.get('page', 1)
        context = get_pagination_data(data, page)
        return self.get_response(request, vhost=vhost, context=context)


class UserPermissionsView(PageContextMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_permissions.html'

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        return self.render_to_response({
            "curr_user": curr_user,
            "active_tab": USER_TAB_PERMISSIONS,
            "perms": Permission.objects.all().exclude(
                content_type__model__in=EXCLUDED_PERMISSIONS_MODELS).exclude(
                content_type__app_label__in=EXCLUDED_PERMISSIONS_APPS).exclude(
                codename__in=EXCLUDED_PERMISSIONS_CODENAMES),
            "user_perms": curr_user.user_permissions.all(),
            })

    def post(self, request, *args, **kwargs):
        user = self.context['auth_user']
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        post_data = request.POST.copy()
        post_data.pop('displayed_perms')
        if request.POST.get('admin_setting'):
            curr_user.is_admin = True
            curr_user.save()
        else:
            curr_user.is_admin = False
            curr_user.save()
        if request.POST.get('displayed_perms'):
            form_perm_list = request.POST.get('displayed_perms').split(';')
        else:
            form_perm_list = []
        if user.has_perms(form_perm_list) or user.is_admin or user.is_superuser:
            perms = Permission.objects.filter(id__in=form_perm_list)
            view_perms = []
            for perm in perms:
                try:
                    view_perm = Permission.objects.get(codename='view_' + perm.content_type.model,
                                                       content_type=perm.content_type)
                    if view_perm:
                        view_perms += [str(view_perm.id)]
                except Permission.DoesNotExist:
                    pass
            curr_user.user_permissions.set(form_perm_list + view_perms)
            set_api_permissions(request.user, curr_user, curr_user.user_permissions.all())

        return self.render_to_response({
            "curr_user": curr_user,
            "active_tab": USER_TAB_PERMISSIONS,
            "perms": Permission.objects.exclude(
                content_type__model__in=EXCLUDED_PERMISSIONS_MODELS).exclude(
                content_type__app_label__in=EXCLUDED_PERMISSIONS_APPS).exclude(
                codename__in=EXCLUDED_PERMISSIONS_CODENAMES),
            "user_perms": curr_user.user_permissions.all(),
        })


class KeysView(PageContextMixin, TemplateView):
    page_section = 'server-keys'
    template_name = 'virtualhost/registration_keys.html'

    def get_page_context(self, vhost=None):
        return {
            'active_tab': TAB_REGISTRATION_KEYS
        }

    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        context = self.get_page_context()
        keys_list = user.api.get_keys({"host": vhost}).get('keys')
        for key in keys_list:
            key['expire'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(key.get('expire')))
        context['keys'] = keys_list
        context['vhosts'] = self.context['vhosts']
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        user.api.delete_key({"host": vhost}, key=request.POST.get('key'))
        return HttpResponseRedirect(reverse('virtualhost:registration-keys'))


class ChangeKeyView(PageContextMixin, TemplateView):
    page_section = 'server-keys'
    template_name = 'virtualhost/change_key.html'

    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get(self, request, *args, **kwargs):
        context = {'current_key': kwargs.get('key')}
        user = request.user
        vhost = self.get_vhost(request)
        vhost = VirtualHost.objects.filter(name=vhost).first()
        keys_list = user.api.get_keys({"host": vhost}).get('keys')
        initial_attrs = next(x for x in keys_list if x["key"] == context['current_key'])
        expire = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(initial_attrs.get('expire')))
        description = initial_attrs.get('description')
        context['form'] = RegistrationKeysForm(
            vhosts=self.context['vhosts'], vhost=vhost, description=description, expire=expire)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = RegistrationKeysForm(request.POST, vhosts=self.context['vhosts'])
        if form.is_valid():
            current_key = kwargs.get('key')
            user = request.user
            user.api.change_key({"host": form.cleaned_data['host'],
                                 "expire": form.cleaned_data['expire'],
                                 "description": form.cleaned_data['description']},
                                current_key)
            return HttpResponseRedirect(reverse('virtualhost:registration-keys'))
        context = {'form': form}
        return self.render_to_response(context)


class AddKeyView(PageContextMixin, TemplateView):
    page_section = 'server-keys'
    template_name = 'virtualhost/add_key.html'

    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get(self, request, *args, **kwargs):
        context = {}
        vhost = self.get_vhost(request)
        vhost = VirtualHost.objects.filter(name=vhost).first()
        vhost = VirtualHost.objects.filter(name=vhost).first()
        if vhost:
            context['form'] = RegistrationKeysForm(
                vhosts=self.context['vhosts'], vhost=vhost)
        else:
            context['form'] = RegistrationKeysForm(vhosts=self.context['vhosts'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = RegistrationKeysForm(request.POST, vhosts=self.context['vhosts'])
        if form.is_valid():
            user = request.user
            user.api.create_key({"host": form.cleaned_data['host'],
                                 "expire": form.cleaned_data['expire'],
                                 "description": form.cleaned_data['description']})
            return HttpResponseRedirect(reverse('virtualhost:registration-keys'))
        context = {'form': form}
        return self.render_to_response(context)
