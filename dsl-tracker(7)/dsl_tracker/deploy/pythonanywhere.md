# Deploying to PythonAnywhere (Free Tier / MySQL)

This app runs as a single PythonAnywhere web app: Django serves both the REST
API (`/api/...`) and the built Svelte frontend (everything else) via
WhiteNoise, so you don't need a separate static file host.

**Database:** this guide uses MySQL, since that's what PythonAnywhere's free
tier provides (PostgreSQL is a paid-tier-only feature there). The project
uses `PyMySQL` as the driver — a pure-Python MySQL client with no system
libraries or compilation required, so `pip install` stays fast and simple
even on the free tier's limited console. `dsltracker/__init__.py` registers
it as Django's `MySQLdb` automatically; you don't need to configure anything
for this part.

> Have a paid tier with PostgreSQL instead? Swap `DATABASE_URL` to a
> `postgres://` URL and uncomment `psycopg2-binary` in `requirements.txt` —
> everything else in this guide is identical.

## 0. Removing a previous web app first (if you're replacing an existing site)

I don't have access to your PythonAnywhere account, so this part has to be
done by you in the dashboard — here's exactly how.

If you already have a different app running on your PythonAnywhere account
(e.g. the legacy CRM/complaint-management system) and want this DSL Tracker
to take over the same domain (`yourusername.pythonanywhere.com`), do this
**before** step 7 below (the old app has to be deleted so the domain slot is
free for the new one — a free account can only have one web app per domain):

1. **Back up first.** On a Bash console:
   ```bash
   # Back up the old app's code
   tar -czf ~/old_site_backup_$(date +%Y%m%d).tar.gz /path/to/old/project

   # Back up its database (free tier = MySQL)
   mysqldump -u yourusername -h yourusername.mysql.pythonanywhere-services.com -p \
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

5. **Deactivate any scheduled tasks** the old app relied on (**Tasks** tab),
   if it had any — they'll otherwise keep running and erroring out against
   code that no longer exists.

Once the old web app is deleted, continue with step 1 below to set up the
new one under the same domain.

## 1. Get the code onto PythonAnywhere

Open a **Bash console** and upload/extract your project:

```bash
cd ~
unzip dsl-tracker.zip   # uploaded via the Files tab
mkdir -p ~/projects
mv dsl_tracker ~/projects/dsl_tracker
cd ~/projects/dsl_tracker
```

(Using git instead? `git clone <your-repo-url> ~/projects/dsl_tracker` works too.)

## 2. Set up the MySQL database

Free-tier PythonAnywhere accounts come with **one MySQL database already
created** for you, named `yourusername$default`. You can use that one, or
create an additional database specifically for this app:

1. Go to the **Databases** tab.
2. If you haven't already, set a MySQL password (top of the page).
3. Under "Create a database", enter `dsltracker` (PythonAnywhere will name
   it `yourusername$dsltracker`) and click **Create**.
4. Note the **host** shown on that page — for MySQL on PythonAnywhere it's
   always `yourusername.mysql.pythonanywhere-services.com`, port `3306`.

Your `DATABASE_URL` will look like:

```
mysql://yourusername:YOUR_DB_PASSWORD@yourusername.mysql.pythonanywhere-services.com:3306/yourusername$dsltracker
```

(If you're reusing the pre-created `yourusername$default` database instead
of making a new one, just swap the database name at the end of that URL.)

## 3. Create a virtualenv and install dependencies

```bash
cd ~/projects/dsl_tracker/backend
python3.11 -m venv ~/.virtualenvs/dsltracker
source ~/.virtualenvs/dsltracker/bin/activate
pip install -r requirements.txt
```

This installs `PyMySQL` along with Django and everything else — no native
compilation, so this should complete quickly with no build errors.

## 4. Configure environment variables

Create `~/projects/dsl_tracker/backend/.env` (this file is git-ignored —
never commit it):

```bash
nano .env
```

Paste in (filling in your actual username and DB password):

```
DEBUG=False
DJANGO_SECRET_KEY=<generate one — see below>
DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com
DATABASE_URL=mysql://yourusername:YOUR_DB_PASSWORD@yourusername.mysql.pythonanywhere-services.com:3306/yourusername$dsltracker
DJANGO_TIME_ZONE=Asia/Karachi
CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com
```

Save with `Ctrl+O`, `Enter`, then `Ctrl+X`.

Generate a secret key to paste into `DJANGO_SECRET_KEY` above:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Build the Svelte frontend and wire it into Django

Django serves the built frontend from `backend/frontend_dist/`. PythonAnywhere
consoles have Node available, but free-tier outbound internet access to npm
is restricted on some accounts — if `npm install` fails, build the frontend
on your own machine instead and upload the resulting `frontend/dist/` folder
via the Files tab, then skip straight to the `cp -r` line below.

```bash
cd ~/projects/dsl_tracker/frontend
npm install
npm run build
mkdir -p ../backend/frontend_dist
cp -r dist/* ../backend/frontend_dist/
```

## 6. Run migrations, seed data (optional), and collect static files

```bash
cd ~/projects/dsl_tracker/backend
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
2. Set **Source code** to `/home/yourusername/projects/dsl_tracker/backend`.
3. Set **Virtualenv** to `/home/yourusername/.virtualenvs/dsltracker`.
4. Edit the **WSGI configuration file** (linked on the Web tab) and replace
   its contents with:

```python
import os
import sys

path = "/home/yourusername/projects/dsl_tracker/backend"
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
   `/static/` → `/home/yourusername/projects/dsl_tracker/backend/staticfiles`
   mapping for a small performance boost, but it isn't required.)
6. Click the big green **Reload** button.

Your app should now be live at `https://yourusername.pythonanywhere.com`,
with the API under `https://yourusername.pythonanywhere.com/api/`.

## 8. Redeploying after changes

```bash
cd ~/projects/dsl_tracker
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
- **`django.db.utils.OperationalError` / access denied**: double-check the
  username, password, and database name in `DATABASE_URL` against exactly
  what's shown on the Databases tab — MySQL database/username strings on
  PythonAnywhere always include the `yourusername$` prefix.
- **`ModuleNotFoundError: No module named 'MySQLdb'`**: this means
  `dsltracker/__init__.py`'s `pymysql.install_as_MySQLdb()` didn't run —
  confirm `PyMySQL` is actually installed in the active virtualenv
  (`pip show pymysql`) and that you didn't accidentally remove that file's
  contents.
- **Free-tier MySQL only allows connections from PythonAnywhere itself**:
  this is expected and not a bug — you can't connect to it from your local
  machine or another host, only from consoles/web apps within your
  PythonAnywhere account.
