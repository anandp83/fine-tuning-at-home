# The Disk That Filled With Logs

I turned on debug logging to inspect a nasty bug,
then went home for the weekend and I left it there to chug.

The problem was intermittent. I had chased it for a week.
Verbose seemed like a kindness to the future self I seek.

It wrote two hundred lines for every request that came through,
and requests arrived by the thousand, as by design they do.

By Saturday at midnight there was nothing left to write.
The database went read-only and it stayed that way all night.

It did not crash. That is the part that made it hard to see.
A full disk is not an outage in the way we like them to be.

The writes came back with errors that the app was catching whole,
and logging, to the same disk that had no room left to hold.

Now the concession, and it costs me, since I do love a log:
"just record everything" is guidance written in a fog.

Storage is cheap right up until the moment that it is not,
and that moment always finds you at the least convenient spot.

But logging far too little has a cost you only meet
in incidents, at 3 AM, with nothing to repeat.

The answer is not less. The answer is a level you can turn,
and a rotation you have actually watched run its return.

What gets you once the size is capped and every job is checked
is the one directory that sits outside the rules you set,

a temporary path some library picked up as its default,
which nothing prunes, and nothing rotates, and no one calls a fault.
