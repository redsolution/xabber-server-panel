import math
from datetime import datetime, timedelta

from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, Http404, HttpResponse

from xmppserverui import settings
from xmppserverui.mixins import PageContextMixin, ServerStartedMixin, SQLAuthMixin
from .forms import RegisterUserForm, UnregisterUserForm, EditUserVcardForm, \
    CreateGroupForm, EditGroupForm, DeleteGroupForm, AddGroupMemberForm, \
    DeleteGroupMemberForm, ChangeUserPasswordForm, AddGroupAllMemberForm, DeleteGroupAllMemberForm
from .models import User, Group, GroupMember, GroupChat


USER_TAB_DETAILS = 'user-details'
USER_TAB_VCARD = 'user-vcard'
USER_TAB_SECURITY = 'user-security'
USER_TAB_GROUPS = 'user-groups'

GROUP_TAB_DETAILS = 'group-details'
GROUP_TAB_MEMBERS = 'group-members'
GROUP_TAB_SUBSCRIPTIONS = 'group-subscriptions'


def get_page_title_old(paginator, data, hosts_count):
    return "{}-{} of {}".format(data.start_index(),
                                data.end_index(),
                                paginator.count + hosts_count) \
        if data.start_index() != data.end_index() \
        else "{} of {}".format(data.end_index(), paginator.count + hosts_count)


def get_page_title(paginator, data, hosts_count):
    return str(paginator.count + hosts_count)


class VhostContextView(ServerStartedMixin):
    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES \
            else self.context['vhosts'].first().name

    def get_response(self, request, *args, **kwargs):
        response = self.render_to_response(kwargs['context'])
        if 'vhost' not in request.COOKIES:
            expires = datetime.utcnow() + timedelta(days=30)
            expires = datetime.strftime(expires, "%a, %d-%b-%Y %H:%M:%S GMT")
            response.set_cookie('vhost', kwargs['vhost'], expires=expires)
        return response


class UserListView(VhostContextView, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/users.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        users = user.api.get_registered_users({"host": vhost})
        user_count = len(users)

        if "error" in users:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": users.get("error")})

        django_users = list(User.objects.filter(host=vhost).values())
        data = []
        for user in users:
            django_user = filter(lambda o: o['username'] == user, django_users)
            data.append({
                "username": user,
                "user": django_user[0] if django_user else None,
                "photo_url": settings.MEDIA_URL + django_user[0]["photo"] if django_user else None
             })

        pagination_limit = settings.PAGINATION_PAGE_SIZE
        paginator = Paginator(data, pagination_limit)
        paginator_page = int(request.GET.get('page', 1))
        data = paginator.page(paginator_page)
        page_title = '{all} of {all}'.format(all=user_count) \
            if len(paginator.page_range) < 2 \
            else '{first} - {last} of {all}'.format(
            first=(paginator_page - 1) * pagination_limit + 1,
            last=(paginator_page - 1) * pagination_limit + len(data),
            all=user_count)

        return self.get_response(request,
                                 vhost=vhost,
                                 context={"data": data,
                                          "pages": paginator.page_range,
                                          "curr_page": paginator_page,
                                          "curr_page_title": page_title})


class UserCreateView(SQLAuthMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_create.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        form = RegisterUserForm(user, vhosts=self.context['vhosts'])
        return self.render_to_response({
            "form": form,
            "gen_pass_len": settings.GENERATED_PASSWORD_MAX_LEN
        })

    def post(self, request, *args, **kwargs):
        user = request.user
        form = RegisterUserForm(user, request.POST, request.FILES,
                                vhosts=self.context['vhosts'])
        if form.is_valid():
            return HttpResponseRedirect(
                reverse('virtualhost:user-created',
                        kwargs={'user_id': form.new_user.id}))
        return self.render_to_response({
            "form": form,
            "gen_pass_len": settings.GENERATED_PASSWORD_MAX_LEN
        })


class UserCreatedView(SQLAuthMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_created.html'

    def get(self, request, *args, **kwargs):
        try:
            new_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
        user_pass = new_user.password
        new_user.password=None
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

        user.api.get_vcard({"user": curr_user.username,
                            "host": curr_user.host,
                            "name": "nickname"})
        if user.api.success:
            nickname = user.api.response["content"]

        user.api.get_vcard2({"user": curr_user.username,
                             "host": curr_user.host,
                             "name": "n",
                             "subname": "given"})
        if user.api.success:
            first_name = user.api.response["content"]

        user.api.get_vcard2({"user": curr_user.username,
                             "host": curr_user.host,
                             "name": "n",
                             "subname": "family"})
        if user.api.success:
            last_name = user.api.response["content"]

        return nickname, first_name, last_name

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404

        nickname, first_name, last_name = self._get_vcard(request, curr_user)
        curr_user.nickname = nickname
        curr_user.first_name = first_name
        curr_user.last_name = last_name
        curr_user.save()

        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_DETAILS})


class UserSecurityView(SQLAuthMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_security.html'

    def get(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404

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

        user = request.user
        form = ChangeUserPasswordForm(user, request.POST, user_to_change=curr_user)
        if form.is_valid():
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
            checked = GroupMember.objects.filter(group=group, username='@all@')
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

        groups = self.get_groups_list(curr_user)
        return self.render_to_response({"curr_user": curr_user,
                                        "active_tab": USER_TAB_GROUPS,
                                        "displayed_groups": groups})

    def post(self, request, *args, **kwargs):
        try:
            curr_user = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404

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


class DeleteUserView(SQLAuthMixin, TemplateView):
    page_section = 'vhosts-users'
    template_name = 'virtualhost/user_delete.html'

    def get(self, request, *args, **kwargs):
        try:
            user_to_del = User.objects.get(id=kwargs["user_id"])
        except User.DoesNotExist:
            raise Http404
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
        user = request.user
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        post_data = request.POST.copy()
        post_data.update({"username": user_to_del.username,
                          "host": user_to_del.host})
        form = UnregisterUserForm(user, post_data,  username=username, host=host)
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
        groups = user.api.get_groups({"host": vhost})
        if "error" in groups:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": groups.get("error")})
        all_groups = Group.objects.filter(host=vhost)
        all_groups_members = list(GroupMember.objects.all().values('group', 'host'))
        data = []
        for g in groups:
            # group = filter(lambda o: o['group'] == g, all_groups)
            group = all_groups.filter(group=g)[0]
            if not group:
                data.append({"group": g, "members": None})
            else:
                if GroupMember.objects.filter(group=group, username="@all@").exists():
                    count = len(filter(lambda o: o['group'] == group.id and o['host'] != group.host,
                                          all_groups_members)) + User.objects.filter(host=group.host).count()
                else:
                    count = len(filter(lambda o: o['group'] == group.id,
                                          all_groups_members))
                data.append({
                    "group": g,
                    "members": count,
                    "name": group.name if group.name else '',
                    "id": group.id
                })
        data.sort(key=lambda k:  k['group'])
        data.sort(key=lambda k: k['members'], reverse=True)

        paginator = Paginator(data, settings.PAGINATION_PAGE_SIZE)
        page = int(request.GET.get('page', 1))
        groups = paginator.page(page)
        page_title = get_page_title(paginator, groups, hosts_count=0)

        return self.get_response(request,
                                 vhost=vhost,
                                 context={"group_list": groups,
                                          "pages": paginator.page_range,
                                          "curr_page": page,
                                          "curr_page_title": page_title})


class GroupCreateView(PageContextMixin, TemplateView):
    page_section = 'vhosts-groups'
    template_name = 'virtualhost/group_create.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        form = CreateGroupForm(user, vhosts=self.context['vhosts'])
        return self.render_to_response({"form": form})

    def post(self, request, *args, **kwargs):
        user = request.user
        form = CreateGroupForm(user, request.POST, vhosts=self.context['vhosts'])
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
        user = request.user
        form = DeleteGroupForm(user)
        return self.render_to_response({"group": group, "form": form})

    def post(self, request, *args, **kwargs):
        group = self.get_group(kwargs['group_id'])
        user = request.user
        post_data = request.POST.copy()
        post_data.update({"group": group.group, "host": group.host})
        form = DeleteGroupForm(user, post_data)
        if form.is_valid():
            return HttpResponseRedirect(reverse('virtualhost:groups'))
        return self.render_to_response({"group": group, "form": form})


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
        member_list = self.get_group_members(group)

        paginator = Paginator(member_list, settings.PAGINATION_PAGE_SIZE)
        page = int(request.GET.get('page', 1))
        members = paginator.page(page)
        page_title = get_page_title(paginator, members, hosts_count=self.get_adv_users_count(group))

        return {"active_tab": GROUP_TAB_MEMBERS,
                "group": group,
                "members": members,
                "pages": paginator.page_range,
                "curr_page": page,
                "curr_page_title": page_title}

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
        members = filter(lambda o: o['group'] == group, groups_members)
        additional = 0
        for member in members:
            if member['username'] == '@all@':
                additional = User.objects.filter(host=member['host']).count() - 1
        return len(members) + additional

    def get_displayed_groups(self, group):
        all_groups = Group.objects.filter(host=group.host)
        all_groups_members = list(GroupMember.objects.all().values('group', 'username', 'host'))
        displayed_groups = [g for g in group.displayed_groups.split('\\n')] \
            if group.displayed_groups else []
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

        chat_count = user.api.xabber_registered_chats_count(
            {"host": vhost}).get('number')
        chats = user.api.xabber_registered_chats(
            {"host": vhost,
             "limit": pagination_limit,
             "page": pagination_page})
        if "error" in chats:
            return self.get_response(request,
                                     vhost=vhost,
                                     context={"error": chats.get("error")})

        django_users = list(User.objects.all().values())
        data = []
        for chat in chats:
            owner_username, owner_host = chat["owner"].split('@')
            user = filter(lambda o: o['username'] == owner_username
                                    and o['host'] == owner_host, django_users)
            data.append({"chat": chat,
                         "owner_id": user[0]['id'] if user else None})

        page_count = int(math.ceil(float(chat_count) / pagination_limit))
        pagination_range = xrange(1, page_count + 1)
        page_title = '{all} of {all}'.format(all=chat_count) \
            if len(pagination_range) < 2 \
            else '{first} - {last} of {all}'.format(
            first=(pagination_page - 1) * pagination_limit + 1,
            last=(pagination_page - 1) * pagination_limit + len(data),
            all=chat_count)

        return self.get_response(request,
                                 vhost=vhost,
                                 context={"data": data,
                                          "pages": pagination_range,
                                          "curr_page": pagination_page,
                                          "curr_page_title": page_title})
