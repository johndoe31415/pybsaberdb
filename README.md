# pybsaberdb
[BeastSaber](https://bsaber.com) is a fantastic site at which custom songs for
the brilliant VR-game [BeatSaber](https://beatsaber.com) 
([Steam link](https://store.steampowered.com/app/620980/Beat_Saber/)) can be
found. However, BeastSaber is a fairly slow site, so browsing all songs can
take a while. Additionally, the search options are fairly limited. For example,
let's say I want to search for all songs which has a minimum of 200 votes, at
least 80% of which should be upvotes, which includes either Electronic or
Synthwave as a genre and which has a "hard" level -- this is a query the
BeastSaber site simply doesn't allow. Furthermore, I wanted to bulk-download
songs so that I can quickly listen to them all in audacious instead of having
to click and wait 5 seconds for the preview every time. This script retrieves
all data from BeastSaber and then allows you to execute SQL-queries on the
resulting Sqlite3 database to find what you're looking for.

## License
GNU GPL-3.
