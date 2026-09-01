# It Was Always DNS

I spent four hours in a packet trace with tcpdump running hot,
and every single byte was fine. The name was what was not.

The service had gone quiet at a little after nine.
The pods were up, the disks were clear, the metrics all read fine.

I read the load balancer logs. I read the app logs twice.
I restarted half the cluster, which is never good advice.

The record had a five-minute time to live, or so I had believed.
The resolver in the base image had a cache that it conceived

entirely on its own, with a default of an hour,
and nothing in my careful plan had any kind of power.

The old address had moved along. The new one was correct.
The client held the stale one like a keepsake in its pocket.

Now I will grant the counterpoint, and grant it in good faith:
"it is always DNS" has become a lazy sort of wraith.

People say it when they mean "I have not looked at this yet,"
and blaming the resolver is the cheapest thing to bet.

The saying is not wisdom. It is only where to start,
because names are the one layer almost nobody owns in part.

And what will get you next is not the record or the cache.
It is that nobody on the team can say who holds the zone,

so when the record needs a change at half past one at night,
you will find the only person with the login has moved on.
