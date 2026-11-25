# AI Prompt: Build a Module for Xabber Server Panel

You are implementing an installable module for Xabber Server Panel. Follow this specification exactly. This prompt is self-contained: do not assume that reference module archives or a running panel instance are available.

The target panel uses Python, Django 3.2, server-rendered Django templates, Bootstrap 5.3, SQLite for panel state, PostgreSQL for the XMPP server, and ejabberd. A module may extend only the panel UI, only the XMPP server, or both.

If a requested feature conflicts with this specification, identify the conflict before changing the panel core. Prefer a minimal module and do not invent extension hooks.

## 1. What the panel installer does

The installer expects a gzip-compressed tar archive. It:

1. extracts the archive into a temporary directory with path-traversal and unsafe-link checks;
2. reads NAME and VERSION from module.spec;
3. validates the version against an installed module;
4. copies panel/<NAME>/ to modules/<NAME>/;
5. adds modules.<NAME> to Django INSTALLED_APPS at runtime;
6. runs migrate <NAME> if migrations/__init__.py exists;
7. runs collectstatic --noinput;
8. copies server files to the external XMPP modules directory;
9. copies compiled ebin/*.beam files to ejabberd's common ebin directory;
10. imports the module's ModuleConfig metadata;
11. stores module metadata and server file paths in the panel database;
12. imports YAML server configuration variants;
13. creates read/write permissions for the module;
14. regenerates the ejabberd modules configuration;
15. reloads the WSGI application.

Installation has rollback support for Django migrations, the previous panel module directory, copied server files, module metadata, and the runtime app registry. Rollback cannot undo arbitrary external API calls, subprocess effects, third-party database writes, or side effects performed during import or AppConfig.ready().

The installer does not install Python, npm, Erlang, or operating-system dependencies.

## 2. Required archive layout

Use this exact top-level layout:

```text
module.spec
panel/                         # optional only for a server-only module
  my_module/
    __init__.py
    apps.py
    urls.py
    views.py
    forms.py                   # optional
    models.py                  # optional
    config.py                  # optional ejabberd config provider
    migrations/               # required when models exist
      __init__.py
      0001_initial.py
    templates/
      my_module/
        info.html
        base.html              # optional
    static/                    # optional
      my_module/
        css/
        js/
        img/
server/                        # optional
  my_module/
    ebin/                      # optional compiled Erlang files
      mod_my_module.beam
    conf/                      # optional selectable YAML variants
      default.yml
```

module.spec, panel/, and server/ must be directly in the archive root. Do not wrap them in a release or repository directory.

If panel/ exists, panel/<NAME>/ must exist. A server-only archive may omit panel/. At least one useful panel or server component must be present.

Never package:

- __pycache__, *.pyc, test caches, coverage output;
- .git, CI metadata, editor settings, or a virtual environment;
- local settings, credentials, API tokens, private keys, or certificates;
- database files, dumps, logs, uploaded user data, or temporary files;
- source maps or frontend build inputs unless explicitly required.

Build the archive from a clean staging directory.

## 3. module.spec contract

Create module.spec in the archive root:

```ini
NAME = my_module
SUMMARY = Human-readable module summary
VERSION = 26.11.1
AUTHOR = Developer Name
EMAIL = developer@example.com
HOME = https://example.com/my-module
```

When a server configuration replaces built-in ejabberd modules, add:

```ini
REPLACE = mod_example, mod_other
```

Rules enforced or implied by the current panel:

- NAME is required.
- VERSION is required.
- REPLACE is optional and accepts comma-separated module names.
- SUMMARY, AUTHOR, EMAIL, and HOME are useful metadata but are not consumed by the current installer.
- NAME and VERSION are converted to lowercase.
- NAME must equal the Python package directory, Django app label, and URL namespace.
- The database field for NAME is limited to 30 characters.
- Use only lowercase ASCII letters, digits, and underscores.
- NAME must be a valid Python package and should not collide with a panel app.
- VERSION must consist only of integer components separated by dots, for example 26.11 or 26.11.1.
- Numeric tuple comparison is used. A lower version is rejected.
- An equal version is normally rejected. The panel has one special equal-version free-to-paid upgrade case.
- Do not use v1.2, 1.2-beta, 2026-11-25, spaces, or other suffixes.

## 4. Minimal panel application

Replace my_module consistently in every example.

### panel/my_module/__init__.py

Django 3.2 must discover the custom AppConfig:

```python
default_app_config = 'modules.my_module.apps.ModuleConfig'
```

### panel/my_module/apps.py

```python
from django.apps import AppConfig


class ModuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.my_module'
    verbose_name = 'My Module'

    # True only when the module supplies a URL named "root".
    root_page = False

    # True for an administrator-only global module.
    global_module = False

    # Optional names of URL patterns shown in the global Create menu.
    create_views_names = []
```

Panel-specific AppConfig attributes:

- verbose_name is stored as the module display name and shown in navigation.
- root_page=True makes the module eligible as the panel root page. The module must expose <NAME>:root.
- global_module=True means only administrators receive its sidebar link. Otherwise the sidebar checks the user's module read permission.
- create_views_names must be a list of URL names. Each resolved view must define create_title and create_subtitle class attributes.

Example create view metadata:

```python
class CreateThingView(ServerStartedMixin, LoginRequiredMixin, TemplateView):
    template_name = 'my_module/create.html'
    create_title = 'Thing'
    create_subtitle = 'Create a new thing.'
```

### panel/my_module/urls.py

Every panel module should expose an info view because the sidebar reverses <NAME>:info.

```python
from django.urls import path

from .views import CreateThingView, InfoView, RootView


app_name = 'my_module'

urlpatterns = [
    path('info/', InfoView.as_view(), name='info'),
    path('create/', CreateThingView.as_view(), name='create'),
    # Include this route only when root_page=True.
    path('', RootView.as_view(), name='root'),
]
```

The panel automatically mounts these URLs under /modules/my_module/. Do not add that prefix inside the module.

### panel/my_module/views.py

```python
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from xabber_server_panel.base_modules.users.decorators import (
    permission_admin,
    permission_read,
    permission_write,
)
from xabber_server_panel.mixins import ServerStartedMixin

from .forms import MySettingsForm


class InfoView(ServerStartedMixin, LoginRequiredMixin, TemplateView):
    template_name = 'my_module/info.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        form = MySettingsForm(initial={})
        return self.render_to_response({'form': form})

    @permission_write
    def post(self, request, *args, **kwargs):
        form = MySettingsForm(request.POST)
        if not form.is_valid():
            return self.render_to_response({'form': form})

        # Save validated data atomically here.
        messages.success(request, 'Settings saved successfully.')
        return HttpResponseRedirect(reverse('my_module:info'))


class RootView(TemplateView):
    # Add LoginRequiredMixin if the root page is not intentionally public.
    template_name = 'my_module/root.html'


class CreateThingView(ServerStartedMixin, LoginRequiredMixin, TemplateView):
    template_name = 'my_module/create.html'
    create_title = 'Thing'
    create_subtitle = 'Create a new thing.'

    @permission_write
    def post(self, request, *args, **kwargs):
        # Validate and create.
        return HttpResponseRedirect(reverse('my_module:info'))
```

Rules:

- Use LoginRequiredMixin for authenticated pages.
- Use permission_read on read endpoints.
- Use permission_write on every mutation available to delegated administrators.
- Use permission_admin for actions restricted to full panel administrators.
- Permission decorators derive the app from the URL namespace, so app_name must be correct.
- Use ServerStartedMixin only when the operation needs a running ejabberd.
- Put ServerStartedMixin before LoginRequiredMixin in the inheritance list.
- ServerStartedMixin returns HTTP 503 and server_not_started.html while ejabberd is stopped.
- GET and HEAD must never change state.
- After a successful POST, redirect using the Post/Redirect/Get pattern.
- Do not catch every exception. Catch expected exceptions and log unexpected failures safely.
- Never use print() in production module code.

## 5. Forms and settings

Use Django forms for all untrusted input.

```python
from django import forms
from django.core.validators import URLValidator


class MySettingsForm(forms.Form):
    endpoint = forms.URLField(
        validators=[URLValidator()],
        required=True,
    )
    token = forms.CharField(
        max_length=512,
        widget=forms.PasswordInput(render_value=True),
    )
    enabled = forms.BooleanField(required=False)
```

Validate JIDs, hostnames, UUIDs, ports, URLs, file types, sizes, and enumerated values explicitly.

The panel provides two useful generic settings models:

- AddSettings stores arbitrary key/value settings associated with module_name.
- ModuleSettings stores JSON options for an ejabberd module and host, unique by (host, module).

VirtualHost contains configured XMPP hosts. RootPage contains the selected root module.

Do not store secrets in source code, templates, static files, module.spec, logs, or Django messages. If a secret is stored in the database, never send it to client-side JavaScript and mask it in forms where practical.

Use transaction.atomic() when several database writes must succeed together. Generate the ejabberd configuration only after validation and successful persistence.

## 6. Permissions

The panel creates CustomPermission rows for installed modules with read and write levels. Non-global module navigation is visible only when the current user has module read permission. Administrators bypass ordinary permission restrictions through the panel permission logic.

Apply permissions at the view boundary. Hiding a button in a template is not authorization.

For templates, the panel exposes check_user_permissions through users template tags. Use it only for presentation; repeat enforcement in the view.

## 7. Templates and frontend

A normal module page should extend the panel layout:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}My Module{% endblock %}
{% block content_title %}My Module settings{% endblock %}

{% block css %}
  <link rel="stylesheet" href="{% static 'my_module/css/module.css' %}">
{% endblock %}

{% block content %}
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button class="btn btn-primary" type="submit">Save</button>
  </form>
{% endblock %}

{% block js %}
  {{ block.super }}
  <script src="{% static 'my_module/js/module.js' %}"></script>
{% endblock %}
```

Rules:

- Use Bootstrap 5.3 and existing panel visual patterns.
- Namespace every template and static asset with the module name.
- Preserve block.super in inherited JavaScript blocks.
- Include csrf_token in every POST form.
- Escape output by default.
- Never apply safe to user-controlled or external data.
- Use json_script or another safe JSON mechanism for JavaScript configuration.
- Do not inline secrets into HTML.
- Test light and dark themes, mobile widths, empty states, errors, and long values.
- Prebuild frontend bundles. The installer does not run npm.

## 8. Models and migrations

Models are normal Django 3.2 models.

```python
from django.db import models


class Thing(models.Model):
    name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name
```

Migration rules:

- Include migrations/__init__.py whenever models exist.
- Add a new numbered migration for every released schema change.
- Never rewrite an already published migration.
- Depend on the previous module migration.
- In data migrations, use the historical apps registry and apps.get_model().
- Do not perform network requests or call ejabberd from a migration.
- Provide reverse operations for data migrations where feasible.
- Test clean installation and direct upgrade from the previous released version.
- Test rollback on a copy of the panel database.
- Avoid import-time queries because the app may load before migrations are applied.

## 9. Dynamic ejabberd configuration

A module can add entries to modules_config.yml through panel/my_module/config.py.

```python
from xabber_server_panel.base_modules.config.models import (
    BaseXmppModule,
    BaseXmppOption,
    VirtualHost,
)


def get_xmpp_server_config():
    result = []

    for host in VirtualHost.objects.all():
        result.append(
            BaseXmppModule(
                vhost=host.name,
                name='mod_my_module',
                module_options={
                    'enabled': 'true',
                    'endpoint': '"https://service.example/api"',
                },
            )
        )
        result.append(
            BaseXmppOption(
                vhost=host.name,
                name='my_global_option',
                value='"value"',
            )
        )

    return result
```

Contract:

- The function is discovered by importing each installed app's config module.
- It is called while the panel builds modules_config.yml.
- Return an iterable of BaseXmppModule and BaseXmppOption instances.
- Other returned object types are ignored.
- vhost must refer to an existing VirtualHost or the special global host.
- BaseXmppOption does not accept a dictionary value.
- module_options is a dictionary.
- The panel uses a custom YAML renderer. Follow existing value conventions; strings that must remain quoted in YAML may require quote characters in the stored value.
- Keep the function deterministic and fast.
- Do not mutate the database, call a network service, start a process, or write files.
- Validate persisted settings before they can reach this function.
- An exception can prevent generation of the shared ejabberd configuration.

Call make_xmpp_config() after a settings change only when regeneration is actually required and all writes have succeeded.

## 10. Server component

The complete server/ directory is copied into the panel's external XMPP module directory. Namespace files beneath server/<NAME>/ to avoid collisions.

Every regular file directly under server/<any_directory>/ebin/ whose name ends in .beam is additionally copied into ejabberd's common ebin directory.

Rules:

- Compile Erlang code before packaging.
- Build against a compatible Erlang/OTP and target ejabberd version.
- Do not expect the installer to compile source code.
- Avoid generic beam filenames that may overwrite another module.
- Matching destination files are replaced during installation.
- The panel records server file paths for later removal.
- Do not include installation scripts that mutate the operating system.

### Selectable server configuration variants

Files under this exact directory are imported:

```text
server/<NAME>/conf/*.yml
server/<NAME>/conf/*.yaml
```

The filename without extension becomes the variant name. The file contents are stored as a ModuleServerConfig. After installation, an administrator assigns a variant to selected virtual hosts.

If a variant replaces built-in modules, list them in module.spec REPLACE. The panel removes replaced modules from generated configuration for assigned hosts and rejects overlapping replacement conflicts on the same hosts.

Each configuration file must be a self-contained YAML fragment in the structure expected by the panel. Parse it with yaml.safe_load() before packaging. Do not use unsafe YAML constructors.

## 11. External HTTP services

For modules that call an external service:

- use requests.Session when connection reuse is useful;
- use settings.HTTP_REQUEST_TIMEOUT on every call;
- construct URLs with urllib.parse.urljoin or controlled URL concatenation, not os.path.join;
- validate configured base URLs;
- send authentication in headers, never query strings;
- handle connect timeout, read timeout, connection failure, invalid JSON, and non-2xx status;
- map failures to safe user-facing messages;
- never display raw response bodies, tokens, tracebacks, or internal URLs;
- do not disable TLS verification;
- do not retry non-idempotent operations unless idempotency is guaranteed;
- avoid network calls during import, app startup, migrations, and configuration rendering.

## 12. Dependency rules

The installer does not process requirements.txt inside a module.

Therefore:

- Prefer Python packages already used by the panel: Django 3.2, requests, PyYAML, ldap3, and the existing project dependencies.
- Do not execute pip, npm, apt, or another package manager from module code.
- Do not download executable code at startup.
- If a new dependency is unavoidable, specify its exact compatible version and treat it as a separate panel deployment change.
- Vendor code only when licensing, security review, and update ownership are clear.
- Prebuild frontend assets.
- Document required ejabberd, Erlang/OTP, PostgreSQL, and external-service versions.

## 13. Security requirements

Before delivery, verify:

- authorization is enforced in views, not only templates;
- mutations never use GET;
- CSRF protection remains enabled;
- all input is validated and length-limited;
- database access uses the ORM or parameterized SQL;
- subprocess receives an argument list and never shell=True;
- paths are resolved under an allowed base directory;
- uploads have type and size limits and cannot traverse directories;
- external content is not treated as trusted HTML;
- secrets do not enter source control, logs, errors, HTML, or JavaScript;
- network requests have timeouts and TLS verification;
- no broad exception handler hides programming errors;
- logs contain enough context for diagnosis but no credentials or personal message content;
- object access is scoped to the current host and user permissions;
- destructive operations require an explicit POST and clear confirmation;
- public root views expose no panel administration data.

## 14. Packaging

From a clean staging directory:

```bash
tar -czf module_my_module_26.11.1.tar.gz module.spec panel server
```

When no server component exists:

```bash
tar -czf module_my_module_26.11.1.tar.gz module.spec panel
```

Inspect the result:

```bash
tar -tzf module_my_module_26.11.1.tar.gz
```

Confirm that all paths are relative, no link escapes the archive root, and the only top-level entries are module.spec, panel/, and optional server/.

## 15. Verification checklist

Perform as many checks as the available environment permits:

1. Confirm NAME, package directory, AppConfig.name, app_name, templates, and static namespaces match.
2. Confirm VERSION is numeric and greater than the installed version.
3. Compile Python files with compileall or py_compile.
4. Enable the app in a disposable panel environment.
5. Run python manage.py check.
6. Run python manage.py makemigrations --check --dry-run <NAME>.
7. Apply migrations to a database copy.
8. Test migration rollback where supported.
9. Run collectstatic --noinput.
10. Reverse <NAME>:info, optional <NAME>:root, and all create view names.
11. Test anonymous, authenticated without permission, read-only, write, and administrator access.
12. Test with ejabberd running and stopped.
13. Validate all YAML with yaml.safe_load().
14. Test light theme, dark theme, mobile layout, empty data, invalid data, and service failures.
15. Test clean installation.
16. Test upgrade directly from the previous published version.
17. Force a mid-install failure in a disposable environment and inspect rollback.
18. Inspect the archive for secrets, caches, absolute paths, symlinks, and unexpected files.
19. Verify that uninstalling the module does not delete unrelated files.
20. Verify external side effects and document how to reverse them manually.

Never use production as the first installation test.

## 16. Required AI output

Deliver all of the following:

1. the final .tar.gz archive;
2. its complete file tree;
3. NAME and VERSION;
4. a summary of behavior;
5. all routes and required permission levels;
6. all models and migrations;
7. all settings and whether any are secrets;
8. ejabberd configuration produced by config.py;
9. packaged beam files and compatibility assumptions;
10. configuration variants and REPLACE declarations;
11. external and deployment dependencies;
12. verification commands and their actual results;
13. untested scenarios;
14. known limitations;
15. upgrade and rollback instructions.

Do not claim that an integration test passed when only static analysis was performed. When information or infrastructure is missing, state the limitation explicitly and still complete all safe static checks.
