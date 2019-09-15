#!/usr/bin/python3
#
#	CachedRequests - Use python-requests and cache into a sqlite3 database
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of pycommon.
#
#	pycommon is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pycommon is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pycommon; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>
#
#	File UUID 7561ab48-416b-476d-baaa-937c111104b5

import sqlite3
import requests
import time
import collections
import contextlib
import urllib.parse
import hashlib
import json

class CachedRequests():
	_GenericRequest = collections.namedtuple("GenericRequest", [ "verb", "url", "postdata", "headers", "return_json", "max_age_secs" ])
	_Response = collections.namedtuple("Response", [ "status_code", "headers", "content", "cached", "age" ])

	def __init__(self, cache_filename = ".requests_cache.sqlite3", cache_duration_secs = 3600, cache_post = False, fixed_headers = None, minimum_gracetime_secs = None, cache_failed_requests = True):
		self._session = requests.Session()
		self._db = sqlite3.connect(cache_filename)
		self._cursor = self._db.cursor()
		self._cache_duration_secs = cache_duration_secs
		self._cache_post = cache_post
		self._fixed_headers = fixed_headers
		self._minimum_gracetime_secs = minimum_gracetime_secs
		self._cache_failed_requests = cache_failed_requests
		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""
			CREATE TABLE cached_requests (
				id integer PRIMARY KEY,
				request_key varchar UNIQUE,
				stored_timestamp float NOT NULL,
				verb varchar NOT NULL,
				uri varchar NOT NULL,
				request_headers_json varchar NOT NULL,
				response_headers_json varchar NOT NULL,
				status_code integer NOT NULL,
				content blob NOT NULL
			);
			""")
		self._db.commit()

	@staticmethod
	def _hash_request(request):
		request_data = [ request.verb, request.url ]
		if request.postdata is None:
			request_data.append("")
		else:
			request_data.append(request.postdata.hex())
		if (request.headers is None) or (len(request.headers) == 0):
			request_data.append("")
		else:
			request_data.append(json.dumps(request.headers, sort_keys = True))
		hashvalue = hashlib.sha256(("\n".join(request_data)).encode("utf-8"))
		return hashvalue.hexdigest()

	@staticmethod
	def _build_url(base_url, query_params):
		if query_params is None:
			query_params = { }
		if isinstance(query_params, dict):
			query_params = query_params.items()
		query_params = list(query_params)
		query_params.sort()
		if len(query_params) == 0:
			return base_url
		else:
			return base_url + "?" + urllib.parse.urlencode(query_params)

	def _determine_headers(self, request_headers):
		if self._fixed_headers is None:
			headers = { }
		else:
			headers = dict(self._fixed_headers)
		if request_headers is not None:
			headers.update(request_headers)
		return headers

	def _cache_lookup(self, max_age_secs, request_hash):
		now = time.time()
		max_age = now - max_age_secs
		result = self._cursor.execute("SELECT stored_timestamp, response_headers_json, status_code, content FROM cached_requests WHERE (stored_timestamp > ?) AND (request_key = ?);", (max_age, request_hash)).fetchone()
		if result is None:
			return None
		else:
			(stored_timestamp, response_headers_json, status_code, content) = result
			return self._Response(status_code = status_code, headers = json.loads(response_headers_json), content = content, cached = True, age = now - stored_timestamp)

	def _cache_store(self, request, request_hash, response):
		try:
			self._cursor.execute("INSERT INTO cached_requests (request_key, stored_timestamp, verb, uri, request_headers_json, response_headers_json, status_code, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
				(request_hash, time.time(), request.verb, request.url, json.dumps(request.headers), json.dumps(response.headers), response.status_code, response.content))
		except sqlite3.IntegrityError:
			self._cursor.execute("UPDATE cached_requests SET stored_timestamp = ?, response_headers_json = ?, status_code = ?, content = ? WHERE request_key = ?;",
				(time.time(), json.dumps(response.headers), response.status_code, response.content, request_hash))
		self._db.commit()

	def _execute_uncached(self, request):
		if self._minimum_gracetime_secs is not None:
			time.sleep(self._minimum_gracetime_secs)
		response = requests.request(method = request.verb, url = request.url, data = request.postdata, headers = request.headers)
		return self._Response(status_code = response.status_code, headers = dict(response.headers), content = response.content, cached = False, age = 0)

	def _execute(self, request):
		if (request.verb == "POST") and (not self._cache_post):
			# Never cache POST requests
			response = self._execute_uncached(request)
		else:
			request_hash = self._hash_request(request)
			cached_response = self._cache_lookup(max_age_secs = request.max_age_secs, request_hash = request_hash)
			if cached_response is None:
				response = self._execute_uncached(request)
				if (self._cache_failed_requests) or (response.status_code == 200):
					self._cache_store(request, request_hash, response)
			else:
				response = cached_response
		if request.return_json:
			response = json.loads(response.content)
		return response

	def get(self, url, query_params = None, headers = None, max_age_secs = None, return_json = False):
		request = self._GenericRequest(verb = "GET", url = self._build_url(url, query_params), postdata = None, headers = self._determine_headers(headers), max_age_secs = max_age_secs if (max_age_secs is not None) else self._cache_duration_secs, return_json = return_json)
		return self._execute(request)

	def post(self, url, query_params = None, postdata = None, headers = None, max_age_secs = None, return_json = False):
		request = self._GenericRequest(verb = "POST", url = self._build_url(url, query_params), postdata = postdata, headers = self._determine_headers(headers), max_age_secs = max_age_secs if (max_age_secs is not None) else self._cache_duration_secs, return_json = return_json)
		return self._execute(request)


if __name__ == "__main__":
	cr = CachedRequests(cache_duration_secs = 10)
	cr.get("https://google.de", query_params = [ ("foo", "bar"), ("a", "b") ])
	cr.get("https://google.de", query_params = { "foo": "bar", "a": "b" })
	rsp = cr.get("https://beatsaver.com/api/maps/downloads", return_json = True)
	print(rsp)
