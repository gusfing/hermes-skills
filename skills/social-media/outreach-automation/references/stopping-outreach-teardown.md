# Stopping outreach cleanly

The user said *"stop all linkedin and x work for now"*. Disabling the timers was
necessary and **not sufficient**. Three live emitters survived, one of them with
`--send` already loaded.

## What was still running after `systemctl --user disable --now`

```
x-daily.timer      inactive / disabled
li-engage.timer    inactive / disabled
li-connect.timer   inactive / disabled
```

and yet:

```
1218467  python -u li_engage.py --likes 3 --comments 2 --send
1218469  python /home/opc/kawaki-outreach/li_connect.py --limit 5 --send --no-note
```

Both were mid-run. `disable --now` stops the *unit*; it does not signal a
`oneshot` already executing, and these carry `--send`, so they were actively
liking, commenting and firing connection requests at the moment the user asked
for silence.

Then a third survivor:

```
.jhawkg@gmail.com's daily report cron  0 4 * * *   -> still scheduled
```

It would have messaged the user a 09:30 summary of work that no longer ran.

## The full teardown

```bash
# 1. timers
systemctl --user stop    x-daily.timer li-engage.timer li-connect.timer
systemctl --user disable x-daily.timer li-engage.timer li-connect.timer

# 2. in-flight jobs the timers did NOT reach
pgrep -af "li_engage\.py|li_connect\.py|x_loop\.py|x_post\.py|x_engage\.py"
kill <pids>; sleep 4; kill -9 <pids>

# 3. the lock they dropped mid-run
rm -f /home/opc/kawaki-outreach/.cdp.lock

# 4. reporting crons that describe the stopped work
#    pause the job, do not delete it - the user may want it back
```

Verify, do not assume:

```bash
for u in x-daily li-engage li-connect; do
  printf "%-12s %s / %s\n" "$u" \
    "$(systemctl --user is-active  $u.timer)" \
    "$(systemctl --user is-enabled $u.timer)"
done
pgrep -af "li_engage\.py|x_loop\.py" || echo "NONE RUNNING"
```

## The stale lock

Killing a process mid-`cdp_lock` leaves `.cdp.lock` on disk. The next run blocks
on it — or, worse, a stale pid inside it makes the lock look *held* by a
process that no longer exists, so every future tick halts for no visible reason.

Delete it as part of any forced teardown, and say so in the report. A lock file
whose owner you killed is an artifact of your kill, not a pre-existing fault.

## What to leave running, and how to decide

The dashboard (`dash-server.service`) was left up deliberately: it only reads
logs and posts nothing, and the user still wanted to see history. Decide by
asking **does this unit write to a third party?**

- writes (posts, comments, DMs, invites) -> stop it
- reads (dashboards, reports, ledgers) -> ask, then default to leaving it

## Reporting a stop honestly

`li-engage.service` came back `failed`, not clean `inactive` — the SIGTERM landed
mid-run. Do not round that up to "stopped cleanly"; report the state the unit
actually shows and note that `failed` here means killed-in-flight, not broken.

The user reads the output. A stop report that says "all off" when two senders
were mid-run is exactly the class of overclaim that `evidence-before-claiming`
exists to prevent — the inverse claim is just as false as the original one.
