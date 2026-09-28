# CI/CD

This project ships with a real, working CI/CD pipeline — designed around
what PythonAnywhere's free tier can *actually* do, rather than something
that looks impressive but quietly doesn't work. Read the "Why not fully
automatic?" section below before assuming this pushes code to production
on every commit — it doesn't, by design, and that's the right call for a
tool holding live customer data.

## What runs automatically (GitHub Actions)

On every push and pull request against `main`, `.github/workflows/ci-cd.yml`
runs:

1. **`test`** — the full Django test suite (59 tests). Everything else is
   gated on this passing.
2. **`build-frontend`** — `npm install && npm run build`, plus a check that
   the built `index.html` actually references `/static/assets/...` (this
   exact regression caused a blank-page bug once already — the pipeline now
   catches it before it ever reaches production instead of after).

Only on a push to `main` that passes both of the above:

3. **`publish-deploy`** — bakes the compiled frontend into
   `backend/frontend_dist/` and pushes the whole result (backend code +
   pre-built frontend) to a `deploy` branch.

This gives you real CI (nothing broken merges silently) and the first half
of CD (a `deploy` branch is always a tested, ready-to-run snapshot of the
latest good `main`) with zero PythonAnywhere credentials or secrets
involved — it's pure GitHub Actions, using its own built-in token to push
to your own repo.

## Getting code from the `deploy` branch onto PythonAnywhere

This is the part that has to happen on the PythonAnywhere side, because
GitHub Actions has no way to reach into your free-tier account (no SSH,
no arbitrary remote execution). `deploy.sh` at the repo root does this in
one command:

```bash
cd ~/dsl_tracker
git fetch origin deploy
git reset --hard origin/deploy
# ... installs deps, migrates, collects static, touches the WSGI file
```

**First-time setup:**

1. Edit `deploy.sh` — set `WSGI_FILE` to your actual path, shown on your
   Web tab (something like
   `/var/www/yourusername_pythonanywhere_com_wsgi.py`).
2. Push this repo to GitHub (if you haven't already) so the Actions
   workflow can run and create the `deploy` branch.
3. On PythonAnywhere, make sure your local clone has a remote pointing at
   GitHub:
   ```bash
   cd ~/dsl_tracker
   git remote -v   # should show your GitHub repo
   ```
   If it doesn't (e.g. you uploaded via zip originally instead of cloning),
   add it: `git init` (if needed), then
   `git remote add origin https://github.com/yourname/dsl-tracker.git`.

**Every time you want to deploy a change**, once it's merged to `main` and
GitHub Actions has finished (check the Actions tab — green check means the
`deploy` branch is updated):

```bash
bash ~/dsl_tracker/deploy.sh
```

That's the whole deploy. One command, run from a Bash console, takes a few
seconds.

## Going further: unattended deploys on a schedule

If you want PythonAnywhere to pick up new deploys without you running the
command yourself, use a **Scheduled Task** (Tasks tab):

```bash
bash ~/dsl_tracker/deploy.sh
```

Set it to run daily (free tier includes scheduled tasks — check your Tasks
tab for exactly how many and at what granularity your account allows).
`deploy.sh` is safe to run even when there's nothing new — `git reset
--hard` against an unchanged `deploy` branch is a no-op, and `migrate`/
`collectstatic` are both idempotent.

This gets you genuinely unattended CD: push to `main` → tests run → frontend
builds and is verified → `deploy` branch updates → within one scheduled-task
cycle, it's live — with no manual step at all.

## Why not fully automatic (push-to-production on every commit)?

Two deliberate reasons, not tier limitations:

1. **PythonAnywhere's free tier has no SSH access**, so GitHub Actions
   genuinely cannot reach in and run anything directly — the scheduled-task
   approach above is the honest ceiling on this tier. (If you move to a
   paid PythonAnywhere plan, SSH access unlocks a real push-based deploy:
   GitHub Actions can SSH in and run `deploy.sh` directly, right after the
   `publish-deploy` job, with no waiting on a schedule. Ask if you'd like
   that workflow addition when you're on a plan that supports it.)

2. **This holds live customer/fault data.** Even with SSH available,
   auto-deploying every merge straight to the only environment you have —
   no staging, no rollback window — means a bad migration or a subtle bug
   goes live the moment it's merged, with nobody looking at it first. The
   one-command manual trigger (or a once-daily scheduled pull) gives you a
   deliberate checkpoint: you decide when "tested and ready" becomes "live,"
   rather than that decision being made implicitly by whoever merged last.

## Rolling back

Since `deploy.sh` does a hard reset to `origin/deploy`, rolling back is:

```bash
cd ~/dsl_tracker
git log --oneline -10          # find the commit you want to roll back to
git push origin <commit-sha>:deploy --force   # from your own machine, not PythonAnywhere
```

Then re-run `bash ~/dsl_tracker/deploy.sh` on PythonAnywhere to pull that
older state. Database migrations don't automatically roll back with the
code — if the commit you're reverting to predates a migration that's
already been applied, you'll need `python manage.py migrate customers
<previous_migration_name>` as a separate, deliberate step.
