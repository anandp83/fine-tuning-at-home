# The Default I Never Changed

I stood a service up in March. The sample config shipped
with two lines marked REQUIRED, and those two are what I flipped.

The other forty settings stayed exactly as they came
from somebody who wrote them for a laptop, not my frame.

The one that mattered held a pool of ten connections wide,
which is plenty on a laptop and is nothing on my side.

For a year that was enough, because the traffic was polite.
It queued a little now and then, and cleared it overnight.

Then a neighboring team retired a cache I did not own,
and my request rate tripled in an afternoon alone.

The pool did what a pool does. It held ten, and made the rest
line up, and time out one by one, and fail the health check test.

I read the error backwards for two hours, maybe three,
because the message named the database and never mentioned me.

Now the case for the defaults, and I think it is quite strong:
a config where you must decide all forty is one you will get wrong.

Defaults are somebody's experience, compressed and handed down,
and overriding all of them discards it for a frown.

The move is not to change them all. It is to know which ones apply
to load, to limits, and to time, and read those with an eye.

What gets you is not the pool. You will size that in an hour.
It is the copy in staging, where a colleague raised the power

one night to make a red test green, and never wrote it down,
so the only box you trust to reproduce has disagreed all round.
