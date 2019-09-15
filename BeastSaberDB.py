#	pybsaberdb - Python interface to BeastSaber database
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of pybsaberdb.
#
#	pybsaberdb is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pybsaberdb is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pybsaberdb; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import sqlite3
import contextlib
import json
import time
from lxml import etree
from CachedRequests import CachedRequests

class BeastSaberDB():
	_URIS = {
		"api_desc":			"https://bsaber.com/wp-json/bsaber-api",
		"rating":			"https://bsaber.com/wp-json/bsaber-api/songs/%(song_key)s/ratings",
		"songs":			"https://bsaber.com/wp-json/bsaber-api/songs",
		"details_html":		"https://bsaber.com/songs/%(song_key)s/",
	}

	def __init__(self):
		self._session = CachedRequests(fixed_headers = { "Accept": "application/json" }, minimum_gracetime_secs = 1.0, cache_failed_requests = False)
		self._db = sqlite3.connect("beastsaber.sqlite3")
		self._cursor = self._db.cursor()

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""
				CREATE TABLE songs (
					id integer NOT NULL PRIMARY KEY,
					song_key varchar NOT NULL UNIQUE,
					level_author varchar NOT NULL,
					title varchar NOT NULL,
					hash varchar NOT NULL,
					rating_update_timet float NULL,
					rating_fun float NULL,
					rating_rhythm float NULL,
					rating_flow float NULL,
					rating_pattern_quality float NULL,
					rating_readability float NULL,
					rating_level_quality float NULL,
					metadata_update_timet float NULL,
					difficulty_easy boolean NULL,
					difficulty_normal boolean NULL,
					difficulty_hard boolean NULL,
					difficulty_expert boolean NULL,
					difficulty_expertplus boolean NULL,
					recommended boolean NULL,
					thumbs_up integer NULL,
					thumbs_down integer NULL,
					categories_json varchar NULL
				);
			""")
		self._db.commit()

	def get_rating(self, song_key, max_age_secs = 86400):
		assert(isinstance(song_key, str))
		return self._session.get(self._URIS["rating"] % { "song_key": song_key }, max_age_secs = max_age_secs, return_json = True)

	def get_api_desc(self, max_age_secs = 86400 * 7):
		return self._session.get(self._URIS["api_desc"], max_age_secs = max_age_secs, return_json = True)

	def get_songs(self, page = 1, max_age_secs = 86400 * 7):
		return self._session.get(self._URIS["songs"], query_params = { "page": str(page) }, max_age_secs = max_age_secs, return_json = True)

	def fill_songs_db(self, page = 1):
		result = self.get_songs(page = page)
		for song in result["songs"]:
			if len(song["song_key"]) == 0:
				continue
			with contextlib.suppress(sqlite3.IntegrityError):
				self._cursor.execute("INSERT INTO songs (song_key, level_author, title, hash) VALUES (?, ?, ?, ?);", (song["song_key"], song["level_author_name"], song["title"], song["hash"]))
		self._db.commit()
		return result["next_page"]

	def fill_songs_complete_db(self, verbose = False):
		page = 1
		while page is not None:
			if verbose:
				print("Retrieving page %d" % (page))
			page = self.fill_songs_db(page)

	def retrieve_rating(self, song_key):
		assert(isinstance(song_key, str))
		rating = self.get_rating(song_key)
		self._cursor.execute("UPDATE songs SET rating_update_timet = ?, rating_fun = ?, rating_rhythm = ?, rating_flow = ?, rating_pattern_quality = ?, rating_readability = ?, rating_level_quality = ? WHERE song_key = ?;",
				(time.time(), rating["average_ratings"]["fun_factor"], rating["average_ratings"]["rhythm"], rating["average_ratings"]["flow"], rating["average_ratings"]["pattern_quality"], rating["average_ratings"]["readability"], rating["average_ratings"]["level_quality"], song_key))

	def retrieve_missing_ratings(self):
		for row in self._cursor.execute("SELECT song_key FROM songs WHERE rating_update_timet is NULL;").fetchall():
			song_key = row[0]
			self.retrieve_rating(song_key)
		self._db.commit()

	def retrieve_song_details(self, song_key):
		assert(isinstance(song_key, str))
		result = self._session.get(self._URIS["details_html"] % { "song_key": song_key })
		html = etree.HTML(result.content)

		difficulties = html.xpath("//a[@class='post-difficulty']/text()")
		categories = html.xpath("//span[@class='bsaber-categories']/a/text()")
		thumbs_up_down = html.xpath("//span[@class='post-stat']")
		assert(thumbs_up_down[0].xpath("i")[0].get("class") == "fa fa-thumbs-up fa-fw")
		assert(thumbs_up_down[1].xpath("i")[0].get("class") == "fa fa-thumbs-down fa-fw")
		thumbs_up = int("".join(thumbs_up_down[0].xpath("text()")).strip())
		thumbs_down = int("".join(thumbs_up_down[1].xpath("text()")).strip())
		recommended = len(html.xpath("//div[@class='post-recommended bsaber-tooltip -recommended']")) > 0

		return {
			"difficulties": set(difficulty.lower() for difficulty in difficulties),
			"categories":	set(category.lower() for category in categories),
			"thumbs_up":	thumbs_up,
			"thumbs_down":	thumbs_down,
			"recommended":	recommended,
		}

	def fill_song_details(self, song_key):
		details = self.retrieve_song_details(song_key)
		print(song_key, details)
		categories_json = json.dumps(sorted(list(details["categories"])))
		self._cursor.execute("UPDATE songs SET metadata_update_timet = ?, difficulty_easy = ?, difficulty_normal = ?, difficulty_hard = ?, difficulty_expert = ?, difficulty_expertplus = ?, thumbs_up = ?, thumbs_down = ?, categories_json = ? WHERE song_key = ?;",
				(time.time(), "easy" in details["difficulties"], "normal" in details["difficulties"], "hard" in details["difficulties"], "expert" in details["difficulties"], "expert+" in details["difficulties"], details["thumbs_up"], details["thumbs_down"], categories_json, song_key))
		self._db.commit()

	def fill_missing_song_details(self):
		for row in self._cursor.execute("SELECT song_key FROM songs WHERE metadata_update_timet is NULL;").fetchall():
			song_key = row[0]
			self.fill_song_details(song_key)
