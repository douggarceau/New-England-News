# Boston calendar integration

The daily GitHub Actions job collects the 25 configured venues at 09:17 UTC
(05:17 Boston daylight time / 04:17 standard time). It uses Python's standard
library, bounded public requests spaced at least two seconds apart, and no AI
API. Manual runs use Actions > Refresh Boston calendar > Run workflow.

`data/cal.json` is the persisted event state, including each observed source and
retrieval time. Failed sources retain their previously observed future events.
If every source fails, the job fails without modifying the published file.
Past dates and explicit cancellations are filtered. Passim's calendar-level
venue inference is labeled in the website. An absent event in a bounded feed
is not treated as proof of cancellation. Other venues and sports data are
preserved. Source response caps mean this is not an exhaustive city calendar.

The job commits only `data/cal.json`, then requests the repository's existing
GitHub Pages build. A concurrent conflicting push fails safely instead of
replacing other work. Check Actions for collection or deployment failures.

The collector reads City Winery's advertised Boston iCalendar feed directly.
Brighton Music Hall, Paradise, MGM and Big Night Live use the public
Ticketmaster Discovery feeds embedded by their official promoter, Crossroads
Presents. The public widget key and venue IDs were verified on October 23,
2026; every returned event still passes the exact venue/room policy. The
Wilbur uses its official Ticketmaster venue feed. A checked-in mapping of
91 existing performance identities preserves separate show times and prevents
duplicates when changing providers. New performances use their ticket ID.
These routes avoid making collection depend on the presentation page shell.

Regattabar's official TicketWeb events are also available through the
Ticketmaster Discovery venue feed (KovZ917AYuX). This route includes partner
events and preserves their original TicketWeb URLs and existing identities.
All 12 published Regattabar event URLs matched the verified feed on October 23.
