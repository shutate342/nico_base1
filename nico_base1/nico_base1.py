# -* coding: cp932 *-

# from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
# http.client.IncompleteRead

import urllib.request as _req

log_f= print

def _MAGIC(o):
	log_f(f"[MagicNumber] {o}")
	return o

class _UserAgentForger(_req.BaseHandler):

	def http_request(self, request):
		request.add_header(
			"User-Agent", (
				"Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
				" Chrome/80.0.3987.132 Safari/537.36"
			)
		)
		return request

	https_request= http_request

class _RedirectCanceller(_req.HTTPRedirectHandler):

	def redirect_request(self, req, fp, code, msg, headers, newurl):
		fp.close()
		self.val20201001= dict(resp= fp, newurl= newurl)
		# r: _req.Request= None
		# return r


def _mapReadTimeout(resp, floa):
	"""
	ブロックする処理 (コネクション接続など) のタイムアウト時間(秒数)として利用されます
	.setblocking(True) == .settimeout(None)
	.setblocking(False)== .settimeout(0.0)
	"""
	resp.fp.raw._sock.settimeout(floa)
	return resp


class Login:

	def __init__(self, mail_tel, password):
		try:
			referer= "https://account.nicovideo.jp/login?site=niconico"
			timeout= _MAGIC(9)
			cookieMgr= _req.HTTPCookieProcessor()
			observer= _RedirectCanceller()
			opener= _req.build_opener(cookieMgr, _UserAgentForger(), observer)
			opener.open(referer, timeout= timeout).close()

			URL= "https://account.nicovideo.jp/login/redirector?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url="

			import urllib.parse as _p
			POST_DATA= (
				f"mail_tel={ _p.quote(mail_tel) }"
				f"&password={ _p.quote(password) }"
				"&auth_id=2844463106"
			).encode("ascii")

			from urllib.error import HTTPError
		except Exception as e:
			raise RuntimeError(e)
		try:
			opener.open(_req.Request(
				URL
				, data= POST_DATA
				, headers= {
					"Accept": "text/html, application/xhtml+xml, */*"
					, "Content-Type": "application/x-www-form-urlencoded"
					, "Content-Length": len(POST_DATA)
					, "Connection": "Keep-Alive"
					, "Cache-Control": "no-cache"
					, "Referer": referer
				}
			), timeout= timeout).close()
		except HTTPError as e:
			self.director= opener
			self.cookieMgr= cookieMgr
			if not "user_session" in set(e.name for e in cookieMgr.cookiejar):
				raise ValueError("Failed to login", mail_tel, self)
			return
		raise RuntimeError("UnreachableCode")


class _TimeoutMgr:

	def __init__(self, login, timeout= (9, 20), **kwargs):
		"timeout: (connect, read)"
		try:
			connectTimeout, readTimeout= timeout
		except TypeError:
			connectTimeout= readTimeout= timeout
		del timeout
		open= login.director.open

		kwargs.update(locals())
		self.__dict__= kwargs
		del self.self, self.kwargs

	def openTO(self, openarg):
		"Time Out"
		it= _mapReadTimeout(
			self.open(openarg, timeout= self.connectTimeout)
			, self.readTimeout
		)
		return it

	simpleop= openTO

	def logout(self) -> type(None):
		URL= "https://account.nicovideo.jp/logout"
		try:
			self.open(URL).close()
		except Exception as e:
			if getattr(e, "code", -1)== 303:
				return
			raise e
		raise RuntimeError("APIChanged")


