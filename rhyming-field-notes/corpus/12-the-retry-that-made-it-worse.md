# The Retry That Made It Worse

I added a retry because the call would sometimes fail:
three attempts, a second apart, the standard sort of rail.

It worked. For eighteen months it worked, and quietly it hid
a dependency that got slower every quarter, and it did

that job so well that nobody downstream had cause to ask
why the timing charts had drifted, or to take on such a task.

Then the thing it called got slow. Not broken. Merely slow,
from twenty milliseconds to two seconds in a row.

My timeout was one second. So the call would fail, and then
the retry fired, and failed again, and fired once again.

Three times the load on something that was struggling to begin,
from every caller, all at once, which is how you pile in.

It had been merely limping when the afternoon began.
What we sent it was a wall, and every caller ran

the same three attempts, on the same one second, all in phase,
because we had all copied it from the same example page.

Now the case for the retry, because there certainly is one:
most failures are a single packet lost, and then it is done.

Removing them entirely trades a rare and ugly day
for a hundred small annoyances that never go away.

The fix is not no retries. It is retries that back off,
that add a little randomness, and that know when to stop.

What gets you is not the retry. You will find that in a day.
It is the client in another team that copied it away

in twenty sixteen, kept the loop, and never got the fix,
and calls you every morning with a pattern you cannot unpick.
