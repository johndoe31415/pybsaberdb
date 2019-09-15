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

import json

class Song():
	def __init__(self, song_key, level_author, title, song_hash, difficulties, recommended, thumbs_up, thumbs_down, categories):
		self._song_key = song_key
		self._level_author = level_author
		self._title = title
		self._song_hash = song_hash
		self._difficulties = difficulties
		self._recommended = recommended
		self._thumbs_up = thumbs_up
		self._thumbs_down = thumbs_down
		self._categories = categories

	@property
	def song_key(self):
		return self._song_key

	@property
	def level_author(self):
		return self._level_author

	@property
	def title(self):
		return self._title

	@property
	def song_hash(self):
		return self._song_hash

	@property
	def difficulties(self):
		return self._difficulties

	@property
	def recommended(self):
		return self._recommended

	@property
	def thumbs_up(self):
		return self._thumbs_up

	@property
	def thumbs_down(self):
		return self._thumbs_down

	@property
	def categories(self):
		return self._categories

	@property
	def total_votes(self):
		return self.thumbs_up + self.thumbs_down

	@property
	def percentage(self):
		if self.total_votes == 0:
			return 0
		else:
			return self.thumbs_up / self.total_votes * 100

	@classmethod
	def from_rowdict(cls, rowdict):
		difficulties = set()
		if rowdict["difficulty_easy"]:
			difficulties.add("easy")
		if rowdict["difficulty_normal"]:
			difficulties.add("normal")
		if rowdict["difficulty_hard"]:
			difficulties.add("hard")
		if rowdict["difficulty_expert"]:
			difficulties.add("expert")
		if rowdict["difficulty_expertplus"]:
			difficulties.add("expert+")
		categories = set(json.loads(rowdict["categories_json"]))
		return cls(song_key = rowdict["song_key"], level_author = rowdict["level_author"], title = rowdict["title"], song_hash = rowdict["hash"], difficulties = difficulties, recommended = bool(rowdict["recommended"]), thumbs_up = rowdict["thumbs_up"], thumbs_down = rowdict["thumbs_down"], categories = categories)

	def includes_all_categories(self, categories):
		return all(category in self.categories for category in categories)

	def includes_any_category(self, categories):
		return any(category in self.categories for category in categories)

	@property
	def download_url(self):
		return "https://beatsaver.com/cdn/%s/%s.zip" % (self.song_key, self.song_hash)

	def __str__(self):
		if len(self.categories) == 0:
			category_str = "/"
		else:
			category_str = ", ".join(sorted(self.categories))
		return "%s: %s (by %s) -- %.1f%% (%d votes, %d up, %d down), categories: %s" % (self.song_key, self.title, self.level_author, self.percentage, self.total_votes, self.thumbs_up, self.thumbs_down, category_str)
