# Configure a Checked-Out Xabber Server Panel with an Existing XMPP Server

This runbook is for an AI agent that must configure the current Xabber Server
Panel checkout to work with an **existing** XMPP Server distribution. It focuses
on runtime configuration and does not prescribe a Git acquisition workflow. The
panel can write ejabberd configuration, install Erlang modules, and modify the
XMPP PostgreSQL database.

This document deliberately contains no deployment-specific paths, hostnames, or
API endpoints. Treat every value shown as `<PLACEHOLDER>` as required input,
not as a default.

## Safety rules for the AI agent

1. Never delete `XMPP_DIR`, its Mnesia data, the XMPP PostgreSQL database,
   certificates, `panel.sqlite3`, or `.installation_lock` without explicit user approval.
2. Do not open `/installation/` or run the panel installation flow against a
   non-empty XMPP PostgreSQL database. That flow creates the schema and rewrites
   `ejabberd.yml`; it is for a new server only.
3. Keep deployment-specific paths in `PANEL_DIR/settings.py`. Do not edit
   `xabber_server_panel/generic_settings.py` for a local deployment.
4. Before changing an existing `ejabberd.yml`, show the proposed diff, create a
   timestamped backup, and stop ejabberd first.
5. Do not print database passwords, component passwords, API tokens, or
   private-key contents in chat, logs, or documentation.

## 1. Collect required deployment inputs

Before creating files, changing permissions, or starting services, the AI must
ask the user for the following values. It must not infer them from this
document or silently reuse paths from another host.

| Required input | Purpose |
| --- | --- |
| `PANEL_DIR` | Absolute directory where the panel source and its local state will live. |
| `XMPP_DIR` | Absolute directory of the existing XMPP Server distribution. |
| Panel bind address, port, and public hostnames | Development-server binding, `ALLOWED_HOSTS`, and reverse-proxy configuration. |
| `XMPP_SERVER_API_URL` | ejabberd panel API endpoint, including its scheme, host, port, and `/panel` path. |
| `XABBER_SERVICES_API_URL`, `XABBER_SERVICES_UI_URL`, `PLUGINS_API_URL` | Dependent Xabber/Plugins API endpoints; an explicit empty value is valid only when that integration is intentionally disabled. |
| PostgreSQL connection information | Required only when creating or migrating the XMPP database; never request a password in a public prompt or log it. |
| Certificate and webhook settings | `CERT_CONF_DIR`, `CERTS_DIR`, `MOD_WEBHOOKS_URL`, and any required CA-file location. |
| Panel and ejabberd runtime users | Needed to configure ownership and module-installation permissions. |
| Existing panel state | Whether `panel.sqlite3`, `.installation_lock`, and the XMPP PostgreSQL database must be reused. |

Ask one concise clarification if any required value is unknown. Do not proceed
past read-only discovery until the user supplies it or explicitly authorizes a
chosen default.

## 2. Inspect the current checkout and existing installation

The AI should first confirm that `PANEL_DIR` is the panel checkout and report
its branch, revision, and working-tree status.

```bash
cd "$PANEL_DIR"
test -f manage.py
test -f requirements.txt
git status --short --branch
git rev-parse --short HEAD
```

Run read-only checks first:

```bash
test -x "$XMPP_DIR/bin/ejabberdctl"
test -d "$XMPP_DIR/etc/ejabberd"
test -f "$XMPP_DIR/etc/ejabberd/ejabberd.yml"
test -d "$XMPP_DIR/var/lib/ejabberd"
"$XMPP_DIR/bin/ejabberdctl" status || true

test -f "$PANEL_DIR/panel.sqlite3" && echo 'panel database exists'
test -f "$XMPP_DIR/.installation_lock" && echo 'XMPP installation is locked'
```

Choose the deployment path from the result:

| Existing state | Safe action |
| --- | --- |
| `panel.sqlite3` and `.installation_lock` exist | Attach the panel to the existing server. Reuse both files and do not use the installation wizard. |
| XMPP PostgreSQL contains data but `panel.sqlite3` is missing | Stop and ask the user for a panel database backup or an approved migration plan. Do not run the new-server wizard. |
| XMPP PostgreSQL is empty and `.installation_lock` is absent | This is a new server. The normal `/installation/steps/` flow may be used. |

## 3. Prepare the current checkout and install Python dependencies

Create or reuse a virtual environment in the current checkout and install the
dependencies required by its current revision.

```bash
cd "$PANEL_DIR"

python3 -m venv venv
./venv/bin/pip install --upgrade pip setuptools
./venv/bin/pip install -r requirements.txt
```

## 4. Configure local paths and API endpoints in `settings.py`

Create or update `PANEL_DIR/settings.py`. It must import defaults and override
every path that depends on the XMPP Server location. Use absolute paths.

```python
from xabber_server_panel.generic_settings import *
import os

DEBUG = <TRUE_FOR_LOCAL_DEVELOPMENT_OR_FALSE_FOR_PRODUCTION>
ALLOWED_HOSTS = ['<PANEL_PUBLIC_HOSTNAME>', '<PANEL_BIND_HOST>']
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

XMPP_SERVER_DIR = '<ABSOLUTE_XMPP_DIR>'
XMPP_SERVER_DB_DUMP = os.path.join(
    XMPP_SERVER_DIR, 'xabberserver_tools', 'utils', 'psql', 'pg-install.new.sql'
)
XMPP_SERVER_CONFIG_PATH = os.path.join(XMPP_SERVER_DIR, 'etc', 'ejabberd')
XMPP_SERVER_EBIN_DIR = os.path.join(XMPP_SERVER_DIR, 'lib', 'ejabberd-0.0', 'ebin')
XMPP_SERVER_CTL = os.path.join(XMPP_SERVER_DIR, 'bin', 'ejabberdctl')
XMPP_SERVER_STATE = os.path.join(XMPP_SERVER_DIR, 'server_state')
INSTALLATION_LOCK = os.path.join(XMPP_SERVER_DIR, '.installation_lock')
MODULE_SERVER_FILES_DIR = os.path.join(XMPP_SERVER_DIR, 'add_files')
XMPP_SERVER_LOG_DIR = os.path.join(XMPP_SERVER_DIR, 'var', 'log', 'ejabberd')
XMPP_SERVER_LOG_FILE = os.path.join(XMPP_SERVER_LOG_DIR, 'ejabberd.log')

# This is panel-owned storage, not the ejabberd runtime distribution.
XMPP_SERVER_EXTERNAL_MODULES_DIR = os.path.join(BASE_DIR, 'xmppserver_modules')

# Values must be supplied by the user for this deployment.
XMPP_SERVER_API_URL = '<EJABBERD_PANEL_API_URL>'
XABBER_SERVICES_API_URL = '<XABBER_SERVICES_API_URL_OR_EMPTY>'
XABBER_SERVICES_UI_URL = '<XABBER_SERVICES_UI_URL_OR_EMPTY>'
PLUGINS_API_URL = '<PLUGINS_API_URL_OR_EMPTY>'
MOD_WEBHOOKS_URL = '<PANEL_WEBHOOK_URL_OR_EMPTY>'
# Set CERT_CONF_DIR and CERTS_DIR only when certificate files are managed locally.
```

Preserve deployment-specific values for certificates, database access,
components, and webhooks in this local file when required (`CERT_CONF_DIR`,
`CERTS_DIR`, `MOD_WEBHOOKS_URL`, database overrides, and so on). Keep local
settings and secrets out of Git.

Validate the resulting paths:

```bash
cd "$PANEL_DIR"
./venv/bin/python - <<'PY'
import os
import settings
for name in ('XMPP_SERVER_DIR', 'XMPP_SERVER_CONFIG_PATH', 'XMPP_SERVER_CTL',
             'XMPP_SERVER_STATE', 'INSTALLATION_LOCK', 'XMPP_SERVER_LOG_DIR'):
    value = getattr(settings, name)
    print(f'{name}={value} exists={os.path.exists(value)}')
PY
```

Every path must exist except `XMPP_SERVER_STATE` when ejabberd has never been
started.

## 5. File ownership and permissions

Module installation is a write operation. The panel installer copies Python
apps into `PANEL_DIR/modules`, server files into
`PANEL_DIR/xmppserver_modules`, compiled `.beam` files into
`XMPP_SERVER_EBIN_DIR`, updates `modules_config.yml`, and runs Django migrations
and `collectstatic`. Rollback needs the same permissions.

Identify the runtime users before changing ownership:

```bash
ps -eo user,group,cmd | grep -E '[e]jabberd|[b]eam.smp'
ps -eo user,group,cmd | grep -E '[g]unicorn|[u]wsgi|[a]pache2|[m]od_wsgi'
```

The preferred local-development arrangement is to run ejabberd and the panel
under one non-root service account. In production, if they use different
accounts, create a shared service group and add both accounts to it. Do not
recursively change ownership of a production server until the user confirms the
account names and exact scope.

The panel runtime user needs read/write access to:

```text
PANEL_DIR/panel.sqlite3
PANEL_DIR/modules/
PANEL_DIR/xmppserver_modules/
PANEL_DIR/user_files/
PANEL_DIR/static/                  # when collectstatic is run by the panel
PANEL_DIR/logs/
XMPP_DIR/etc/ejabberd/              # ejabberd.yml and included YAML files
XMPP_DIR/lib/ejabberd-0.0/ebin/     # .beam files installed by modules
```

The ejabberd runtime user needs read access to the config, installed modules,
and certificates, plus its normal write access to `XMPP_DIR/var/`.

After the user confirms `PANEL_USER`, `XMPP_USER`, and a shared group such as
`xabber-panel`, use this reviewed pattern for the directories the panel writes:

```bash
PANEL_USER=<panel-runtime-user>
XMPP_USER=<ejabberd-runtime-user>
SHARED_GROUP=xabber-panel

sudo groupadd --system "$SHARED_GROUP" 2>/dev/null || true
sudo usermod -aG "$SHARED_GROUP" "$PANEL_USER"
sudo usermod -aG "$SHARED_GROUP" "$XMPP_USER"

sudo install -d -o "$PANEL_USER" -g "$SHARED_GROUP" -m 2775 \
  "$PANEL_DIR/modules" "$PANEL_DIR/xmppserver_modules" \
  "$PANEL_DIR/user_files" "$PANEL_DIR/static" "$PANEL_DIR/logs"

sudo chgrp -R "$SHARED_GROUP" \
  "$PANEL_DIR/modules" "$PANEL_DIR/xmppserver_modules" \
  "$XMPP_DIR/etc/ejabberd" "$XMPP_DIR/lib/ejabberd-0.0/ebin"
sudo chmod -R g+rwX \
  "$PANEL_DIR/modules" "$PANEL_DIR/xmppserver_modules" \
  "$XMPP_DIR/etc/ejabberd" "$XMPP_DIR/lib/ejabberd-0.0/ebin"
sudo find "$PANEL_DIR/modules" "$PANEL_DIR/xmppserver_modules" \
  "$XMPP_DIR/etc/ejabberd" "$XMPP_DIR/lib/ejabberd-0.0/ebin" \
  -type d -exec chmod g+s {} +

sudo chown "$PANEL_USER:$SHARED_GROUP" "$PANEL_DIR/panel.sqlite3"
sudo chmod 660 "$PANEL_DIR/panel.sqlite3"
```

The setgid bit on directories makes new module files inherit the shared group.
Restart the panel and ejabberd services after changing group membership.

## 6. Check absolute paths in `ejabberd.yml`

Moving `XMPP_DIR` does not update absolute paths already stored in
`ejabberd.yml`. Find stale references first:

```bash
rg -n -F "$PANEL_DIR/xmppserver" "$XMPP_DIR/etc/ejabberd"
rg -n 'include_config_file|certfiles|certfile|ca_file' \
  "$XMPP_DIR/etc/ejabberd/ejabberd.yml"
```

The include paths must point to the configured `XMPP_DIR`:

```text
<XMPP_DIR>/etc/ejabberd/virtual_hosts.yml
<XMPP_DIR>/etc/ejabberd/modules_config.yml
<XMPP_DIR>/etc/ejabberd/additional_config.yml
```

If stale paths are found, show them, back up the configuration, stop ejabberd,
replace only confirmed paths, then start ejabberd and inspect the fresh log.
Certificate paths are independent of `XMPP_DIR`; only change them if the
certificate directory moved. Verify that every `certfile`, `certfiles` glob, and
`ca_file` is readable by ejabberd.

## 7. Initialize and run the panel

For an existing initialized XMPP Server and panel database:

```bash
cd "$PANEL_DIR"
./venv/bin/python manage.py migrate
./venv/bin/python manage.py collectstatic --noinput
./venv/bin/python manage.py check
./venv/bin/python manage.py runserver "$PANEL_BIND_HOST:$PANEL_BIND_PORT"
```

Open the user-supplied panel URL. With an existing `.installation_lock`, the
panel must not redirect to `/installation/steps/`.

For production, run the WSGI app with `DJANGO_SETTINGS_MODULE=settings` under
a service account that has the documented permissions. Do not use Django's
development server in production.

## 8. Final verification

```bash
"$XMPP_DIR/bin/ejabberdctl" status
cd "$PANEL_DIR"
./venv/bin/python manage.py check
rg -n -F "$PANEL_DIR/xmppserver" "$XMPP_DIR/etc/ejabberd" && exit 1 || true
curl -I "http://$PANEL_BIND_HOST:$PANEL_BIND_PORT/"
```

## Prompt for an AI agent

```text
Read AI_DEPLOY_EXISTING_XMPP.md and safely attach Xabber Server Panel to an
existing XMPP Server. Start by inspecting and reporting the current checkout.
Then ask me for every required deployment-specific path, hostname, API endpoint,
certificate location, runtime user, and existing-state decision listed in the
runbook. Do not infer or hardcode values. First inspect panel.sqlite3,
.installation_lock, PostgreSQL state, users, groups, and file permissions. Do
not run the installation wizard or overwrite ejabberd.yml when the XMPP
database is populated. Put local paths and API endpoints only in settings.py.
Before enabling module installation, make the panel and ejabberd runtime users
able to write the documented module/config paths through an explicitly confirmed
shared group. Show proposed configuration changes and final validation results,
but never disclose secrets.
```
