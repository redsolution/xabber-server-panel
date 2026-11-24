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

### Interactive question protocol

Do not ask for every value in one large message. Before the first question,
and in **every** later reply that asks for more information, print this compact
numbered progress list. Its labels are intentionally no longer than five words;
they are an annotation of the remaining deployment decisions, not the full
question text.

```text
❌ 1. XMPP path and API
❌ 2. Panel listener and hosts
❌ 3. Panel database plan
❌ 4. XMPP database state
❌ 5. External integrations
❌ 6. TLS prerequisites
❌ 7. Certificate automation
```

Ask only the first unresolved item after the list. Once the user's answer has
been checked for completeness and accepted, replace that item's `❌` with `✅`.
Keep unresolved items marked `❌`. Reprint the whole list after every user
answer, then ask only the next unresolved question. If an answer is incomplete,
keep its `❌`, explain what is missing, and ask only for the missing part.

For question 3, present the panel database recovery/reinitialization choices as
numbered sub-items. Do not mark an explicitly destructive option complete until
the user has given the required confirmation. The detailed question following
the compact list must still name the relevant setting, explain its purpose,
state whether it is optional, and give an expected-value example.

Question 6 must offer an explicit choice: configure or verify TLS now, or
postpone TLS and run the panel over HTTP for now. If the user postpones TLS,
mark question 6 as `✅ postponed` and question 7 as `✅ not required`; do not
ask certificate-automation questions. Do not remove or modify any existing
ejabberd certificates or TLS configuration when TLS is postponed. If the user
chooses TLS, question 7 asks separately whether certificates will be managed
automatically or supplied and renewed manually.

`SECRET_KEY` is not a user question. The AI must generate a fresh high-entropy
Django secret locally, write it directly to the local `settings.py`, and never
print or commit the value. It must preserve an already configured local secret
unless the user explicitly asks to rotate it.

`DEBUG` is also not a user question: set `DEBUG = True` in the local
`settings.py`, overriding the generic default. Do not ask about
`MOD_WEBHOOKS_URL`, XMPP listener ports, `DNS_SERVICE`, `CRON_JOB_TOKEN`,
installation markers, module paths, or log paths. Leave optional settings at
their defaults unless current local settings already override them. Derive
server-specific paths, `.installation_lock`, `XMPP_SERVER_STATE`, listener
ports, and the ejabberd Panel API from `XMPP_DIR` and the existing ejabberd
configuration. If the API URL cannot be determined from that inspection, ask
only for the missing URL as part of question 1.

| Required input | Purpose |
| --- | --- |
| `PANEL_DIR` | The absolute panel checkout path. Ask for it only when the current working directory is not already the intended panel checkout, or when the user explicitly wants the panel placed in another directory. |
| `XMPP_DIR` | Absolute directory of the existing XMPP Server distribution. |
| Panel IP, port, and public hostnames | The **panel IP** is the IP address on which the panel process listens. The **port** is its local listening port. **Public hostnames** are the DNS names users enter in a browser; they are required for `ALLOWED_HOSTS`, reverse-proxy configuration, and HTTPS certificates. |
| `XMPP_SERVER_API_URL` | Derive the ejabberd panel API endpoint, including its scheme, host, port, and `/panel` path, from the existing ejabberd configuration. Ask only if that inspection is inconclusive. |
| `XABBER_SERVICES_API_URL`, `XABBER_SERVICES_UI_URL`, `PLUGINS_API_URL` | Dependent Xabber/Plugins API endpoints; an explicit empty value is valid only when that integration is intentionally disabled. |
| PostgreSQL connection information | Required by the installation wizard and for database checks: host, database name, database user, and a secure way to provide the password. Never request a password in a public prompt or log it. |
| Certificate settings | Confirm whether TLS is required and whether the certificates already exist before configuring their paths. Leave `MOD_WEBHOOKS_URL` unset so its built-in fallback applies. |
| Panel and ejabberd runtime users | Do not ask initially. Use the current operating-system user as the panel user by default, determine the ejabberd user from its process or installation ownership, and test the required access. Ask for an explicit permissions decision only if those checks reveal a conflict. |
| Existing panel and XMPP state | `panel.sqlite3` is the panel's own SQLite database: panel accounts, permissions, virtual-host records, module metadata, and panel settings. `.installation_lock` is a marker that tells the panel the XMPP installation was already completed and prevents redirecting to the new-server wizard. XMPP PostgreSQL contains the actual XMPP service data, such as accounts, rosters, and server/module data. Ask whether to restore existing state, reset the existing XMPP database, or use a different empty database. |

Ask one concise clarification if any required value is unknown. Do not proceed
past read-only discovery until the user supplies it or explicitly authorizes a
chosen default.

### Certificate prerequisite

Before enabling TLS endpoints, the user must provision the required
certificates or explicitly choose to run without TLS during local development.
Ask which of the following are already available:

1. A panel HTTPS certificate for every public panel hostname, if the panel is
   served over HTTPS by Apache, Nginx, or another reverse proxy.
2. An XMPP TLS certificate for every XMPP virtual host. A single certificate
   with the required Subject Alternative Names, or an appropriate wildcard
   certificate, is acceptable.
3. A PEM deployment bundle in the format expected by the existing ejabberd
   configuration. Commonly this consists of the private key and full certificate
   chain in a PEM file; the AI must inspect the existing `certfile`/`certfiles`
   settings rather than assume one layout.
4. A CA bundle path when the deployment uses a private CA or requires explicit
   trust configuration.

The AI must not generate private keys, request private-key contents, or invent
certificate paths. It should verify that the user-provided certificate files
exist, are readable by `XMPP_USER`, and cover the configured hostnames.

### Settings reference: values to request or confirm

The AI must name the relevant setting when asking for a value. It must first
use the current checkout and ejabberd configuration to determine values that
can be read safely; it asks the user only for the remaining deployment choices.
Examples below show the expected **format only**; replace every angle-bracket
placeholder with the user's deployment value.

| Setting(s) from `generic_settings.py` | What to ask for | Expected format/example |
| --- | --- | --- |
| `DEBUG`, `ALLOWED_HOSTS` | Set `DEBUG` to `True` without asking. Ask only for browser-facing DNS names for `ALLOWED_HOSTS`. | `DEBUG = True`; `ALLOWED_HOSTS = ['<panel.example.net>']` |
| `DATABASES['default']` | Whether to reuse the default panel SQLite DB or use an explicitly provided Django DB configuration. | SQLite: `NAME = '<PANEL_DIR>/panel.sqlite3'` |
| `XMPP_SERVER_DIR` | Existing XMPP Server installation directory. | `'<ABSOLUTE_XMPP_DIR>'` |
| `XMPP_SERVER_DB_DUMP` | SQL schema dump bundled with the selected XMPP Server version; needed only for a fresh XMPP DB. | `'<XMPP_DIR>/.../pg-install.new.sql'` |
| `XMPP_SERVER_CONFIG_PATH`, `XMPP_SERVER_EBIN_DIR`, `XMPP_SERVER_CTL` | ejabberd config directory, Erlang `.beam` directory, and executable path. | `'<XMPP_DIR>/etc/ejabberd'`, `'<XMPP_DIR>/lib/.../ebin'`, `'<XMPP_DIR>/bin/ejabberdctl'` |
| `XMPP_SERVER_STATE`, `INSTALLATION_LOCK`, `XMPP_SERVER_LOG_DIR`, `XMPP_SERVER_LOG_FILE` | Runtime state marker, installation-complete marker, and ejabberd log location. | `'<XMPP_DIR>/server_state'`, `'<XMPP_DIR>/.installation_lock'`, `'<XMPP_DIR>/var/log/ejabberd/ejabberd.log'` |
| `XMPP_SERVER_VHOSTS_CONFIG_FILE`, `XMPP_SERVER_MODULES_CONFIG_FILE`, `XMPP_SERVER_ADD_CONFIG_FILE` | Names of included ejabberd YAML files; normally retain the current names. | `'virtual_hosts.yml'`, `'modules_config.yml'`, `'additional_config.yml'` |
| `XMPP_SERVER_EXTERNAL_MODULES_DIR`, `USER_FILES`, `MOD_NICK_AVATAR_FILES` | Panel-owned directories for installed modules and uploaded/generated files. | `'<PANEL_DIR>/xmppserver_modules'`, `'<PANEL_DIR>/user_files'` |
| `XMPP_SERVER_API_URL` | Derive the ejabberd Panel API endpoint used by Django from the existing listener configuration; ask only if it cannot be read. | `'http://<ejabberd-api-host>:<port>/panel'` |
| `XMPP_CLIENT_PORT`, `XMPP_SERVER_PORT`, `XMPP_HTTP_PORT`, `XMPP_HTTPS_PORT`, `XMPPS_CLIENT_PORT` | Read existing listener ports from ejabberd configuration and preserve them. | Strings such as `'5222'`, `'5269'`, `'5443'`, `'5280'`, `'5223'` |
| `XABBER_SERVICES_API_URL`, `XABBER_SERVICES_UI_URL`, `PLUGINS_API_URL` | Optional Xabber Services and plugin-catalogue integrations. | `'https://<services-api-host>'`, `'https://<services-ui-host>/'`, `'https://<plugins-api-host>/api/v1'`, or `''` to disable each integration |
| `MOD_WEBHOOKS_URL` | Optional URL where ejabberd module webhooks reach this panel. Do not ask for it; leave it unset to use the built-in fallback. | When explicitly overridden: `'https://<panel-host>/webhooks/xmppserver/'`; otherwise omit it. |
| `CERT_CONF_DIR`, `CERTS_DIR`, `CERT_CONF_FILENAME`, `CERT_DOMAIN_FILENAME` | Certificate-manager configuration and output directories. | `'<ABSOLUTE_CERT_CONFIG_DIR>'`, `'<ABSOLUTE_CERT_OUTPUT_DIR>'`, `'acertmgr.conf'`, `'domains.conf'` |
| `XMPP_SERVER_ADD_CERTS_DIRS` | Additional certificate directories ejabberd should load, if any. | `['<ABSOLUTE_CERT_DIR>']` or `[]` |
| `CERT_AUTHORITY`, `CERT_API`, `CERT_VALIDATE_OCSP`, `CERT_ACTION`, `CHALLENGE_URL`, `CHALLENGE_RECORD` | ACME/validation details, only when the panel manages certificate issuance. | A user-approved ACME URL, API version string, OCSP mode, deploy command, challenge URL, and DNS record. Keep the existing values when this integration is already configured. |
| `CRON_JOB_TOKEN`, `DNS_SERVICE` | Optional scheduled-job token and DNS resolver endpoint. Do not ask for them; retain defaults or existing local overrides. | `''`; `'https://<dns-resolver>/resolve'` |

### Required question format and per-setting purpose

For every value the AI requests, its question must state: **setting name**,
**what the panel uses it for**, **whether it is optional**, and **the expected
format**. It must not ask only for an unnamed category such as “certificate
paths” or “API URLs”. Use this reference when forming the questions.

| Setting | What it is used for | Required when | Expected value format |
| --- | --- | --- | --- |
| `PANEL_IP` *(runtime value, not a Django setting)* | IP address passed to the development server or used by the chosen WSGI/reverse-proxy service as the panel listener address. | Always confirm before starting the panel. | A user-selected IP address, for example `'<panel-ip>'`. |
| `PANEL_PORT` *(runtime value, not a Django setting)* | TCP port on which that panel listener accepts requests. | Always confirm before starting the panel. | Port number, for example `'<panel-port>'`. |
| `SECRET_KEY` | Django cryptographic secret used to sign sessions, CSRF data, and other security-sensitive values. | Always set for a new local `settings.py`. | Generate a high-entropy quoted string directly in local `settings.py`; never print it in chat or commit it. |
| `DEBUG` | Enables Django development diagnostics. | Set automatically; do not ask. | `True`. |
| `ALLOWED_HOSTS` | Restricts which HTTP Host headers Django accepts. | Ask as part of question 2. | Python list: `['<panel-hostname>']`. |
| `DATABASES['default']['NAME']` | Path to the panel's SQLite DB, which stores panel-side accounts, permissions, module metadata, and settings. | Always confirm when reusing or creating panel state. | `'<PANEL_DIR>/panel.sqlite3'` or an approved Django database configuration. |
| `XMPP_SERVER_DIR` | Root of the XMPP Server distribution. All derived runtime paths depend on it. | Ask as question 1. | Absolute directory: `'<XMPP_DIR>'`. |
| `XMPP_SERVER_DB_DUMP` | SQL schema file applied only during fresh XMPP database initialization. | Derive from the selected XMPP distribution; do not ask. | Absolute `.sql` file inside the selected XMPP distribution. |
| `XMPP_SERVER_CONFIG_PATH` | Directory containing `ejabberd.yml` and its included YAML files. | Derive from `XMPP_SERVER_DIR`; do not ask. | Absolute directory: `'<XMPP_DIR>/etc/ejabberd'`. |
| `XMPP_SERVER_EBIN_DIR` | Destination for `.beam` files copied by the panel module installer. | Derive from `XMPP_SERVER_DIR`; do not ask. | Absolute `ebin` directory inside the XMPP release. |
| `XMPP_SERVER_CTL` | Executable used by the panel to start, stop, reload, register users, and manage ejabberd. | Derive from `XMPP_SERVER_DIR`; do not ask. | Absolute executable path: `'<XMPP_DIR>/bin/ejabberdctl'`. |
| `XMPP_SERVER_STATE` | File where the panel records whether it requested ejabberd to be on or off. | Derive from `XMPP_SERVER_DIR`; do not ask. | Writable file path, normally under `XMPP_DIR`. |
| `INSTALLATION_LOCK` | File that marks the XMPP installation complete; it suppresses the new-server wizard. | Derive and inspect from `XMPP_SERVER_DIR`; do not ask. | Existing or intended writable marker file, normally `'<XMPP_DIR>/.installation_lock'`. |
| `XMPP_SERVER_LOG_DIR`, `XMPP_SERVER_LOG_FILE` | ejabberd log directory and the main log file displayed by the panel. | Derive from `XMPP_SERVER_DIR`; do not ask. | Absolute directory and file path. |
| `XMPP_SERVER_EXTERNAL_MODULES_DIR` | Panel-owned destination for non-`.beam` server files from installed modules. | Use current-project default; do not ask. | Writable absolute directory, normally under `PANEL_DIR`. |
| `USER_FILES`, `MOD_NICK_AVATAR_FILES` | Panel directories for user-uploaded files and generated nickname avatars. | Use current-project defaults; do not ask. | Writable absolute directories. |
| `XMPP_SERVER_API_URL` | Base URL used by the panel's authenticated API client to call ejabberd's `/panel` endpoint. | Derive during question 1; ask only when config inspection is inconclusive. | URL including scheme, host, port, and `/panel`: `'http://<host>:<port>/panel'`. |
| `XMPP_CLIENT_PORT` | Port written into generated ejabberd config for XMPP client connections. | Read from ejabberd config; do not ask. | Numeric string, for example `'5222'`. |
| `XMPP_SERVER_PORT` | Port written into generated ejabberd config for server-to-server connections. | Read from ejabberd config; do not ask. | Numeric string, for example `'5269'`. |
| `XMPP_HTTP_PORT` | Port of the ejabberd HTTP listener that the bundled template marks `tls: true` and uses for `/api`, `/panel`, `/upload`, `/ws`, and `/iq`. | Read from ejabberd config; do not ask. | Numeric string. Preserve the existing deployment value. |
| `XMPP_HTTPS_PORT` | Port of the second ejabberd HTTP listener and the port embedded in the bundled upload/IQ HTTPS URLs. Its name alone is not proof of TLS: inspect the generated `ejabberd.yml` before changing it. | Read from ejabberd config; do not ask. | Numeric string. Preserve the existing deployment value. |
| `XMPPS_CLIENT_PORT` | Port for direct TLS XMPP client connections. | Read from ejabberd config; do not ask. | Numeric string, for example `'5223'`. |
| `XABBER_SERVICES_API_URL` | Base URL for the Xabber Services API client. | Xabber Services integration is enabled. | URL without a secret, or `''` to disable. |
| `XABBER_SERVICES_UI_URL` | Base URL used to build Xabber Services browser links. | Xabber Services integration is enabled. | URL ending in `/`, or `''` to disable. |
| `PLUGINS_API_URL` | Base URL for the plugin catalogue and plugin token client. | Remote plugin catalogue is enabled. | URL such as `'https://<host>/api/v1'`, or `''` to disable. |
| `MOD_WEBHOOKS_URL` | Callback URL written into the `mod_webhooks` configuration. | Do not ask; leave unset to use the panel's fallback: configured `panel_address`, then `https://xabber.<XMPP_HOST>/webhooks/xmppserver/`. | Full panel webhook URL only when an existing local override must be retained. |
| `CERT_CONF_DIR` | Directory where the panel creates certificate-manager configuration files. | Panel-managed certificate issuance is enabled. | Writable absolute directory. |
| `CERTS_DIR` | Directory from which the panel reads generated PEM files and certificate status. | TLS/certificate management is enabled. | Readable absolute directory containing PEM files. |
| `CERT_CONF_FILENAME` | Filename of the certificate-manager global configuration inside `CERT_CONF_DIR`. | Panel-managed certificate issuance is enabled. | Filename such as `'acertmgr.conf'`. |
| `CERT_DOMAIN_FILENAME` | Filename of the generated per-domain certificate configuration inside `CERT_CONF_DIR`. | Panel-managed certificate issuance is enabled. | Filename such as `'domains.conf'`. |
| `XMPP_SERVER_ADD_CERTS_DIRS` | Extra certificate directories made available to ejabberd. | Certificates are stored outside the default directory. | Python list of absolute directories, or `[]`. |
| `CERT_AUTHORITY` | ACME certificate authority URL used by the certificate manager. | Panel-managed certificate issuance is enabled. | User-approved HTTPS URL. |
| `CERT_API` | ACME API version used by the certificate manager. | Panel-managed certificate issuance is enabled. | Version string such as `'v2'`. |
| `CERT_VALIDATE_OCSP` | OCSP validation mode used when checking issued certificates. | Panel-managed certificate issuance is enabled. | The deployment's approved validation setting. |
| `CERT_ACTION` | Command run after a certificate changes, normally to deploy/reload it. | Automatic certificate deployment is enabled. | Approved executable command string, or `None`. |
| `CHALLENGE_URL` | Endpoint used by the custom Xabber DNS challenge mode to create/delete ACME challenge records. | Custom Xabber DNS challenge mode is enabled. | User-provided HTTPS URL. |
| `CHALLENGE_RECORD` | Expected DNS target used to verify the ACME challenge setup. | Custom Xabber DNS challenge mode is enabled. | DNS record string ending with `.` when required. |
| `DNS_SERVICE` | DNS-over-HTTP resolver queried when the panel validates host and certificate DNS records. | Use the generic default or an existing local override; do not ask. | Resolver URL ending in `/resolve`. |
| `CRON_JOB_TOKEN` | Token expected by scheduled account-expiry maintenance command. | Keep the default disabled value or an existing local override; do not ask. | `''` or an existing protected local value. |

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

### When `panel.sqlite3` is absent

The AI must offer the user these explicit choices rather than treating the
situation as a blocker:

1. **Restore the previous panel state (recommended):** restore the matching
   `panel.sqlite3` backup. This preserves panel administrators, permissions,
   virtual-host records, module metadata, and settings.
2. **Create a new XMPP installation in a different empty PostgreSQL database:**
   create/select a new empty database, set its connection parameters, remove no
   data from the existing database, and complete the panel installation wizard
   using the new database.
3. **Reinitialize the existing XMPP database (destructive):** only after the
   user explicitly confirms that all data in the named database may be deleted,
   back it up and run:

   ```bash
   cd "$PANEL_DIR"
   ./venv/bin/python manage.py prepare_installation --server_db "<DATABASE_NAME>"
   ```

   This management command stops ejabberd if it is running, drops the named
   PostgreSQL database, creates it again, resets relevant panel migrations, and
   removes `.installation_lock`. It does **not** ask for confirmation itself and
   relies on the local `dropdb`/`createdb` environment, so the AI must verify the
   target database and show the destructive command before execution.

After option 2 or 3, start the panel and complete `/installation/steps/`. The
wizard asks for these exact values:

| Wizard field | Meaning | Example format |
| --- | --- | --- |
| `host` | Primary XMPP virtual-host domain. | `'<xmpp.example.net>'` |
| `db_host` | PostgreSQL host or IP address. | `'<postgres-host>'` |
| `db_name` | The selected new or reinitialized XMPP PostgreSQL database. | `'<xmpp_database_name>'` |
| `db_user` | PostgreSQL role allowed to use that database. | `'<xmpp_database_user>'` |
| `db_user_pass` | Password for `db_user`; enter it directly in the form or protected secret store, never in chat. | `'<secret>'` |
| `username` | Localpart of the first XMPP/panel administrator account. | `'<admin>'` |
| `password` | Password for that administrator account; enter it only through a protected channel. | `'<secret>'` |
| `base_cronjobs` | Whether the panel should create its built-in scheduled jobs. | `true` or `false` |

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

DEBUG = True
ALLOWED_HOSTS = ['<PANEL_PUBLIC_HOSTNAME>', '<PANEL_IP>']
# Generate a fresh high-entropy value locally. Keep this file out of Git.
SECRET_KEY = '<LOCALLY_GENERATED_SECRET>'
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

Use the user running the setup as the default panel user; do not ask the user
to choose one. Determine the ejabberd user read-only before considering any
permissions change:

```bash
PANEL_USER="$(id -un)"
PANEL_GROUP="$(id -gn)"
ps -eo user,group,cmd | grep -E '[e]jabberd|[b]eam.smp'
ps -eo user,group,cmd | grep -E '[g]unicorn|[u]wsgi|[a]pache2|[m]od_wsgi'
stat -c '%U:%G %n' "$XMPP_DIR" "$XMPP_DIR/etc/ejabberd" \
  "$XMPP_DIR/lib/ejabberd-0.0/ebin"
```

If the current user can access every required path, retain that arrangement.
The panel may be run by that user for the local setup. If a production process
manager later uses a different account, its service configuration must use an
account with the same verified access. Do not change users, groups, ownership,
or modes merely because the names differ.

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

If the read-only checks show an actual access failure, report the exact path and
operation that fail. Only after the user explicitly approves a shared-group
change, use this reviewed pattern for the directories the panel writes:

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
./venv/bin/python manage.py runserver "$PANEL_IP:$PANEL_PORT"
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
curl -I "http://$PANEL_IP:$PANEL_PORT/"
```

## Prompt for an AI agent

```text
Read AI_DEPLOY_EXISTING_XMPP.md and safely attach Xabber Server Panel to an
existing XMPP Server. Start by inspecting and reporting the current checkout.
Then resolve the deployment values listed in the runbook. Read values from the
current checkout and ejabberd configuration whenever possible, and ask me only
for decisions or values that cannot be safely determined that way. Name the
relevant `generic_settings.py` setting for each value requested from me and
state its expected format with a placeholder example. Explain what the panel IP,
panel SQLite database, installation lock, and XMPP PostgreSQL database mean
when asking for them. Use the current operating-system user as the default
panel user; determine ejabberd ownership and access read-only, and ask about a
shared group only if an actual permission check fails. If the current directory
is already the panel checkout, do not require a separate PANEL_DIR value. Follow
the Interactive question protocol: always show its compact, numbered status
list before asking for information; ask only one unresolved item at a time; and
reprint the full list with ✅/❌ statuses after every answer.
Generate a new `SECRET_KEY` locally in `settings.py` yourself, without asking
me for it or printing it; preserve an existing local secret unless I request a
rotation. First confirm the certificate prerequisite: panel HTTPS certificates,
XMPP virtual-host certificates, PEM layout, and any CA bundle. Do not invent or
hardcode deployment values; derive them only from the inspected local files.
First inspect panel.sqlite3, .installation_lock, PostgreSQL
state, users, groups, and file permissions. If panel.sqlite3 is absent, offer
the documented choices to restore it, use a different empty XMPP database, or
explicitly reinitialize the named database with prepare_installation; never take
the destructive path without confirmation. Do not run the installation wizard
or overwrite ejabberd.yml when the XMPP database is populated. Put local paths
and API endpoints only in settings.py. Before enabling module installation,
verify that the current user and ejabberd user have the documented access; use
an explicitly approved shared group only if the checks require it. Show proposed
configuration changes and final validation results, but never disclose secrets.
```
