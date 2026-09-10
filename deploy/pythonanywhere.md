# Deploying to PythonAnywhere

This app runs as a single PythonAnywhere web app: Django serves both the REST
API (`/api/...`) and the built Svelte frontend (everything else) via
WhiteNoise, so you don't need a separate static file host.

> **Note on PostgreSQL:** PythonAnywhere's Postgres support is only available
> on paid ("Hacker" tier and above) accounts — free accounts only get MySQL.
> If you're on a free account, either upgrade, or swap `DATABASE_URL` to a
> `mysql://` URL and add `mysqlclient` to `requirements.txt` instead of
> `psycopg2-binary`. Everything else in this guide is unaffected.

## 0. Removing a previous web app first (if you're replacing an existing site)

I don't have access to your PythonAnywhere account, so this part has to be
done by you in the dashboard — here's exactly how.

If you already have a different app running on your PythonAnywhere account
(e.g. the legacy CRM/complaint-management system) and want this DSL Tracker
to take over the same domain (`yourusername.pythonanywhere.com`), do this
**before** step 7 below (the old app has to be deleted so the domain slot is
free for the new one — a free/basic PythonAnywhere account can generally
only have one web app per domain):

1. **Back up first.** On a Bash console:
   ```bash
   # Back up the old app's code
   tar -czf ~/old_site_backup_$(date +%Y%m%d).tar.gz /path/to/old/project

   # Back up its database (adjust for MySQL/Postgres/SQLite as appropriate)
   mysqldump -u yourusername -h yourusername.mysql.pythonanywhere-services.com \
     'yourusername$olddbname' > ~/old_db_backup_$(date +%Y%m%d).sql
   ```
   Download these backups (Files tab → right-click → Download) somewhere
   off PythonAnywhere before deleting anything. This step is optional but
   strongly recommended — deletion in the next steps is not reversible.

2. **Delete the old web app.** Go to the **Web** tab, find the old app under
   your domain, and click **Delete** (usually at the bottom of that app's
   configuration page). Confirm when prompted. This removes the web app
   configuration and its WSGI file, but does **not** delete your code or
   database — those are separate.

3. **Remove the old code (optional).** Once you've confirmed the backup is
   good:
   ```bash
   rm -rf /home/yourusername/old_project_directory
   ```

4. **Drop the old database (optional).** On the **Databases** tab, or via a
   console:
   ```bash
   mysql -u yourusername -h yourusername.mysql.pythonanywhere-services.com -p
   # then: DROP DATABASE `yourusername$olddbname`;
   ```
   (For Postgres, drop it from the Postgres console on the Databases tab
   instead.)

5. **Deactivate any scheduled tasks** the old app relied on (**Tasks** tab),
   if it had any — they'll otherwise keep running and erroring out against
   code that no longer exists.

Once the old web app is deleted, continue with step 1 below to set up the
new one under the same domain.

## 1. Get the code onto PythonAnywhere

Open a **Bash console** on PythonAnywhere and clone or upload your repo:

```bash
git clone <your-repo-url> dsl_tracker
cd dsl_tracker
```

(If you're not using git, use the **Files** tab to upload the zip and unzip it
in a Bash console with `unzip dsl_tracker.zip`.)

## 2. Create the PostgreSQL database

On the **Databases** tab:
1. Set a Postgres password if you haven't already.
2. Create a database, e.g. named `dsltracker` (PythonAnywhere will actually
   name it `yourusername$dsltracker`).
3. Note the **host** shown on that tab (something like
   `yourusername-1234.postgres.pythonanywhere-services.com`) and the port
   (usually `12345` — shown on the same page).

Your `DATABASE_URL` will look like:

```
postgres://yourusername:YOUR_DB_PASSWORD@yourusername-1234.postgres.pythonanywhere-services.com:12345/yourusername$dsltracker
```

## 3. Create a virtualenv and install dependencies

```bash
cd ~/dsl_tracker/backend
python3.11 -m venv ~/.virtualenvs/dsltracker
source ~/.virtualenvs/dsltracker/bin/activate
pip install -r requirements.txt
```

## 4. Configure environment variables

Create `~/dsl_tracker/backend/.env` (this file is git-ignored — never commit
it):

```bash
DEBUG=False
DJANGO_SECRET_KEY=<generate one — see below>
DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com
DATABASE_URL=postgres://yourusername:YOUR_DB_PASSWORD@yourusername-1234.postgres.pythonanywhere-services.com:12345/yourusername$dsltracker
DJANGO_TIME_ZONE=Asia/Karachi
CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Build the Svelte frontend and wire it into Django

Django serves the built frontend from `backend/frontend_dist/`. PythonAnywhere
consoles have Node available, but the free tier's outbound internet access
to npm is restricted for some accounts — if `npm install` fails, build the
frontend on your own machine and upload the `frontend/dist/` folder instead.

```bash
cd ~/dsl_tracker/frontend
npm install
npm run build
cp -r dist/* ../backend/frontend_dist/ 2>/dev/null || mkdir -p ../backend/frontend_dist && cp -r dist/* ../backend/frontend_dist/
```

## 6. Run migrations, seed data (optional), and collect static files

```bash
cd ~/dsl_tracker/backend
source ~/.virtualenvs/dsltracker/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data          # optional: sample records for a demo
python manage.py collectstatic --noinput
```

## 7. Create the web app

On the **Web** tab:
1. **Add a new web app** → choose **Manual configuration** (not the
   Django wizard, since we want our own settings module) → pick the Python
   version matching your virtualenv (3.11).
2. Set **Source code** to `/home/yourusername/dsl_tracker/backend`.
3. Set **Virtualenv** to `/home/yourusername/.virtualenvs/dsltracker`.
4. Edit the **WSGI configuration file** (linked on the Web tab) and replace
   its contents with:

```python
import os
import sys

path = "/home/yourusername/dsl_tracker/backend"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dsltracker.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

   `.env` is loaded automatically by `django-environ` from the `backend/`
   directory, so no extra `os.environ[...]` lines are needed here.

5. Under **Static files**, you can leave this blank — WhiteNoise handles
   static serving from within the Django app itself. (Optionally add a
   `/static/` → `/home/yourusername/dsl_tracker/backend/staticfiles` mapping
   for a small performance boost, but it isn't required.)
6. Click the big green **Reload** button.

Your app should now be live at `https://yourusername.pythonanywhere.com`,
with the API under `https://yourusername.pythonanywhere.com/api/`.

## 8. Redeploying after changes

```bash
cd ~/dsl_tracker
git pull   # or re-upload changed files
cd backend
source ~/.virtualenvs/dsltracker/bin/activate
pip install -r requirements.txt      # if requirements changed
python manage.py migrate             # if models changed
python manage.py collectstatic --noinput
```

If the frontend changed, rebuild it (step 5) too. Then go to the **Web** tab
and click **Reload** again — PythonAnywhere doesn't pick up code changes
automatically.

## Troubleshooting

- **500 error after deploy**: check the **Error log** on the Web tab first —
  it almost always shows the real Python traceback.
- **"DisallowedHost" errors**: your `DJANGO_ALLOWED_HOSTS` in `.env` doesn't
  match the domain you're visiting.
- **Static files 404 / unstyled site**: re-run `collectstatic` and make sure
  `frontend_dist/` actually has files in it (step 5) before that.
- **Database connection refused**: double check the host/port from the
  Databases tab — they're specific to your account and change if you're on
  a different PythonAnywhere region.
