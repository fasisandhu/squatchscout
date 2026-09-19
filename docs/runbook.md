# Runbook

Everything here runs on the VM, as the `ubuntu` user, from `/opt/squatchscout/deploy`.

Compose needs both flags because the stack file and the project directory are the same
folder, so the whole repo is not the build context. To save typing:

```bash
cd /opt/squatchscout/deploy
alias dc='docker compose -f docker-compose.yml --project-directory .'
```

Every command below is written out in full so it can be copied without the alias.

## Is it up?

```bash
docker compose -f docker-compose.yml --project-directory . ps
curl -s https://$API_HOST/healthz
```

Healthy looks like three containers `running` and:

```json
{"status":"ok","db":"ok","llm_enabled":true,"version":"<the deployed git sha>"}
```

`db` anything but `ok` means Postgres is down or unreachable — check `ps` first.
`llm_enabled: false` means `GROQ_API_KEY` is missing or empty in `.env`; the app still
works, it just stops offering the natural-language box, AI refinement and call openers.
`version` is baked in at image build time, so it is the honest answer to "what is actually
running", not what is on `main`.

## Logs

```bash
docker compose -f docker-compose.yml --project-directory . logs -f api
```

They are JSON, one object per line. Useful filters:

```bash
# errors only
... logs api | grep '"level": "ERROR"'
# one search end to end
... logs api | grep '"search_id": "<id>"'
# what the AI layer is doing
... logs api | grep -E 'llm\.(rate_limited|model_rejected|error)'
# a crawl that failed on one site
... logs api | grep 'enrich.failed'
```

Alembic runs in its own process before uvicorn starts, so its migration lines are plain
text and appear before the JSON begins. That is expected, not a formatting bug.

## Restart just the API

```bash
docker compose -f docker-compose.yml --project-directory . restart api
```

Safe at any time. In-flight searches are lost, and the browser shows a stream error and
offers retry.

## Deploy, and roll back

Normal deploys are automatic: a push to `main` runs CI, and a green CI run triggers the
`deploy` workflow, which SSHes in and runs the script below with the new commit.

```bash
/opt/squatchscout/deploy/deploy.sh <sha-or-branch>   # deploy a specific commit
cat /opt/squatchscout/deploy/.deployed_sha           # what was last deployed successfully
```

The script fetches, resolves the ref against `origin` first, rebuilds, restarts, then polls
`/healthz` until `version` matches the requested sha. If it never matches, it redeploys the
previous sha from `.deployed_sha` on its own. So a bad deploy usually self-heals; to force
it by hand:

```bash
/opt/squatchscout/deploy/deploy.sh "$(cat /opt/squatchscout/deploy/.deployed_sha)"
```

If the deploy workflow is skipped with a notice saying `DEPLOY_HOST is not set`, the repo
secrets are missing — see the deployment section of the README.

## Migrations

```bash
# what the database is on right now
docker compose -f docker-compose.yml --project-directory . exec api alembic current
docker compose -f docker-compose.yml --project-directory . exec api alembic history
```

`deploy.sh` runs `alembic upgrade head` as part of the API container's start-up, so a
deploy that includes a migration applies it automatically. Writing a new one is a local
job:

```bash
cd api
.venv/Scripts/alembic revision --autogenerate -m "what changed"   # bin/ on POSIX
# read the generated file before committing it; autogenerate is a draft, not an answer
.venv/Scripts/alembic upgrade head
```

Alembic uses its own engine, which deliberately bypasses the SQLite foreign-key pragma,
because `batch_alter_table` rebuilds tables and enforcement would break those rebuilds.

## Backups

`deploy/backup.sh` dumps Postgres, gzips it, verifies the archive and keeps the last seven.
Install it once:

```bash
mkdir -p /opt/squatchscout/deploy/backups
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/squatchscout/deploy/backup.sh >> /opt/squatchscout/deploy/backups/cron.log 2>&1") | crontab -
crontab -l
/opt/squatchscout/deploy/backup.sh      # run once by hand and check the output
ls -lh /opt/squatchscout/deploy/backups/
```

It writes to a `.partial` name and renames only after `gzip -t` passes, so a dump that dies
halfway cannot leave a truncated file that looks like a good backup.

Restore one:

```bash
gunzip -c backups/2026-09-19.sql.gz \
  | docker compose -f docker-compose.yml --project-directory . exec -T postgres psql -U squatch squatchscout
```

## Rotate the Groq key

```bash
nano /opt/squatchscout/deploy/.env          # edit GROQ_API_KEY
docker compose -f docker-compose.yml --project-directory . up -d --force-recreate api
curl -s https://$API_HOST/healthz           # llm_enabled should be true
```

No rebuild needed; the key is read from the environment at start-up.

## Disk is full

`t3.micro` with a 16 GB root volume fills up from Docker build layers long before it fills
up from data.

```bash
df -h /
docker system df
docker image prune -f            # dangling layers from old builds, safe
docker image prune -a -f         # everything not currently used, forces a slower next build
du -sh /opt/squatchscout/deploy/backups/
```

Never `docker volume prune` — the `pgdata` volume is the database.

## Ubuntu updates

`setup-ubuntu.sh` enables unattended security upgrades. Once a month:

```bash
sudo unattended-upgrade -d
sudo reboot        # only if /var/run/reboot-required exists
```

Containers come back on their own after a reboot; every service is `restart: unless-stopped`.

## Certificates

Caddy obtains and renews the certificate itself. Nothing to do, but if HTTPS fails:

```bash
docker compose -f docker-compose.yml --project-directory . logs caddy | grep -i -E 'certificate|acme|error'
```

The usual causes, in order of likelihood:

1. Ports 80 and 443 are not open to `0.0.0.0/0` in the EC2 security group. Let's Encrypt
   validates over port 80; closing it breaks issuance even though the site serves on 443.
2. `API_HOST` in `.env` does not resolve to this machine's public IP.
3. The instance was stopped and started without an Elastic IP, so the address changed.

The first certificate is obtained on the first request, which can take 30 seconds. A TLS
error immediately after the first deploy is usually just impatience.

## CORS: the browser says the API is unreachable but curl works

`FRONTEND_ORIGINS` in `.env` must contain the exact Vercel origin, scheme included and no
trailing slash. After editing it:

```bash
docker compose -f docker-compose.yml --project-directory . up -d --force-recreate api
curl -s -X OPTIONS https://$API_HOST/api/searches \
  -H "Origin: https://<your-project>.vercel.app" \
  -H "Access-Control-Request-Method: POST" -i | grep -i access-control-allow-origin
```

A preview deployment on Vercel gets its own hostname, which will not be in the list. That
is a configuration fact, not a bug.

## Known limits, so they are not mistaken for faults

**Groq free tier.** 30 requests a minute, 1,000 a day, 8,000 tokens a minute, 200,000 a
day. The client throttles itself below that with a per-model token bucket, falls to the
next model on a 429, and stops for the day at `LLM_DAILY_SOFT_CAP`. When the budget is
gone, leads stay at `llm_status: skipped_budget` and the table is still complete and
correctly ranked — refinement is an enhancement, not a dependency.

**Overpass.** The public mirrors rate-limit and time out fairly often. Two are configured
and tried in order; when both fail the search returns an error and the right response is to
retry. In one round of sixteen queries while building the eval set, two failed outright.

**Nominatim.** One request per second, absolute. Results are cached, so a repeated location
costs nothing.

**t3.micro memory.** Two vCPU and 1 GB of RAM, with a swap file added by
`setup-ubuntu.sh` because Docker builds will otherwise be killed by the OOM reaper. If a
build dies without an error message, that is why. Check with `free -h` and `dmesg | tail`.

**Crawl coverage.** Some sites return 403 to a declared bot user agent. Those leads end up
`enrichment_status: unreachable` and score on OSM data alone. The tool does not disguise
its user agent to get around that.
