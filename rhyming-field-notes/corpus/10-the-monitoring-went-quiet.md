# The Monitoring Went Quiet

I woke up to no alerts and thought the week had gone quite well,
and the truth was that the watcher had been dead since Sunday's bell.

The dashboards were still loading. Every panel drew a line.
The lines were flat and green and old, and flat and green looks fine.

The collector had stopped writing after filling up its queue.
The graphs kept showing the last value that they ever knew.

A missing signal renders as a steady one on most,
and a steady one is exactly what we hope for at our post.

That is the failure I most want you to take from what I write.
Monitoring fails silent. It fails looking right.

An outage announces itself. A blind spot does not call.
You find it when you go to look and find nothing there at all.

The fix is not more panels and it is not more thresholds set.
It is one alert that fires when the data does not get

collected on its schedule, the dead man's switch, the heartbeat,
which is the only check that treats its own absence as defeat.

Now here is the honest cost, and I do not want to hide it:
a heartbeat alert is noisy and your team will come to chide it.

It fires on a deploy, it fires when a network hiccups twice,
and an alert that cries too often gets a filter, which is the price.

I have no clean answer. I have only the observation
that the silent failures are the ones with no notification,

and if you must choose which to tune, tune the one that shouts,
because the quiet one will never give you anything to sort out.

What gets you after all of this is not the collector at all.
It is that the heartbeat alert routes to the channel on the wall

that the team stopped reading in the spring when they moved to a new one,
and nobody remembered that the routing rule was still there, undone.
