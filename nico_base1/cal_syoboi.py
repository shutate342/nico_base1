# -* coding: cp932 *-
"""
http://cal.syoboi.jp/mng?Action=ShowChList
-> ShowChList

例:
from nico_base1 import cal_syoboi as sy
from nico_base1.jkM import main_jk as main

# wanna view 'Hyouka'
title= sy.search("氷菓")[0]

# getCount(default) -> episode count
programs= sy.groupby(lambda e: e.getCount(None), title.programs)

# select episode 12 broadcasted on 'TOKYO MX'
program= sy.groupby(lambda e: e.chName, programs[12])["TOKYO MX"][0]

# jk: nico_base1.jk.main._JKAPI
jk= main.loginJK("your-address@example.com", "your-password")

# save comments as XML file
jk.syoboi(program).save(directory= ".")
"""

import bs4
import re
from   datetime import timedelta as td, datetime as dt
import urllib.request as _req
import functools as _ftls

from   . import nico_base1 as _base
_OPENER= _base._TimeoutMgr(_base.CookieLogin(_base.cookiejar.CookieJar()))


def _class(v):
	return {"class": v}

_REG_START= re.compile(r"(\d{4})-(\d+)-(\d+)[^\d]+(\d+):(\d+)")
_REG_URL_TID= re.compile(r"/tid/(\d+)")


class _ErrProgramValue: pass
ERR= _ErrProgramValue()

class _ErrProgram:
	def __init__(self, debug):
		self.debug= debug
		self.error= debug.pop("e")
		self.bs= debug.pop("bs")

	@staticmethod
	def ofErr(e, bs, msg):
		return _ErrProgram(locals())

	def __repr__(self):
		return f'<_ErrProgram({ self.error }) { list(self.debug.values()) }>'


	def __getattr__(self, name):
		return ERR

	__str__= __repr__


_ifNone= lambda it: lambda default: default if it is None else it


class _Program:

	def getDumpable(prog):
		d= prog.__dict__.copy()
		d["count"]= d.pop("getCount")(None); d["subtitle"]= d.pop("getSubtitle")(None)
		d["startTT"]= d.pop("startDT").timetuple()[:6]
		return d

	def _ProgramCtor(
		self, chName, startDT, min, count= None, subtitle= None
		, _syChID= None, _HTMLID= None
		, **kwargs
	):
		del kwargs
		getCount= _ifNone(count)
		getSubtitle= _ifNone(subtitle)
		del count, subtitle
		self.__dict__.update(locals())
		self.__dict__.pop("self")
	__init__= _ProgramCtor

	def __repr__(self):
		return f"<_Program({ str(self.startDT) }, { self.chName })>"

	__str__= __repr__

	@staticmethod
	def of(bs):
		try:
			chName= bs.find("td", _class("ch")).text.strip()
			args= list(map(
				int
				, _REG_START.search(bs.find("td", _class("start")).text).groups()
			))
			if args[-2]>= 24:
				args[-2]-= 24
				startDT= dt(*args)+ td(1)
			else:
				startDT= dt(*args)
			del args
			min= int(bs.find("td", _class("min")).text)
			try:
				count= bs.find("td", _class("count")).text
				if "." in count:
					raise RuntimeError(f"[_Program] count: {count}")
				count= int(count)
			except ValueError:
				count= None
				pass
			subtitle= "".join(
				e for e in bs.find("td", _class("subtitle")).children
				if isinstance(e, str)
			)
			_syChID= bs.select("a.pidlink")[0]["href"].split("=", 1)[-1].split("#", 1)[0]
			_HTMLID= bs.get("id")
			return _Program(**locals())
		except Exception as e:
			return _ErrProgram(locals())

def fromDumpArgs(startTT, **kwargs) -> _Program:
	"""
	Construct _Program from '_Program.getDumpable' dict
	"""
	return _Program(startDT= dt(*startTT), **kwargs)


def bs2EitherProgs(parsed: bs4.BeautifulSoup, pastonly= True) -> dict:
	"""
	ret["rights"] -> [_Program]
	ret["lefts"] -> [_ErrProgram]
	"""
	try:
		# tbody= parsed.select("table.progs > tbody")[0]
		# programs= tbody.find_all(recursive= False)
		programs= parsed.select("table.progs")[0].select("tr.past" if pastonly else "table > tr")
		it= groupby(type, map(_Program.of, programs))
		it["rights"]= it.pop(_Program, [])
		it["lefts"]= it.pop(_ErrProgram, [])
		return it
	except Exception as e:
		raise RuntimeError("ParseError or APIChanged", e)


def _formatProgramsURL(request):
	it= request
	if it.host!= 'cal.syoboi.jp':
		raise ValueError(f"InvalidHost: '{it.host}', expected 'cal.syoboi.jp'")
	try:
		tid= _REG_URL_TID.search(it.selector).group(1)
	except Exception as e:
		raise ValueError(f"InvalidURLPath: '{ it.selector }', expected like '/tid/0001'")

	return f"https://cal.syoboi.jp/tid/{ tid }/time"


@_ftls.lru_cache(1)
def parse( url_or_titleObj, assertNotEmpty= True, pastonly= True) -> [_Program]:
	"""
	cal.syoboi.jp のサイトから見たいタイトルを検索します。
	すると タイトルの候補画面 or タイトル画面そのものに移動します。
	url_or_titleObj
		それぞれ 候補から URL をコピー or ブラウザのページ URL をコピーしたもの

	放送された番組の一覧を返します。

	また url_or_titleObj に
		.ローカル な Path Like Object やファイルパス文字列
			この場合、各タイトルの項目のうち
			「放送時間」のページデータを指定してください
			このようにローカルファイルを利用すれば
			サーバーの負荷を減らせます
		.search 関数で取得した Title Object
		.Request Object
	も指定できます
	"""
	def go():
		it= url_or_titleObj
		try:
			if not isinstance(it, _req.Request):
				it= _req.Request(it)
		except Exception as parseErr:
			try:
				import os
				with open(it, "rb") as f: return bs2EitherProgs(toBS(f), pastonly)
			except Exception as e:
				raise RuntimeError(
					"Failed to parse URL or local file"
					f"\nFormer: {parseErr}\nLatter: {e}"
					"\nif Latter: Please reconfirm your local file content."
				)
		it= (
			it if hasattr(it, "_syoboi_title")
			else _formatProgramsURL(it)
		)
		with _OPENER.simpleop(it) as resp:
			return bs2EitherProgs(toBS(resp), pastonly)

	it= go()
	if it["lefts"]:
		_base.log_f('[cal_syoboi] ParseError num: {len(it["lefts"])}')
	it= it["rights"]
	if assertNotEmpty and not it:
		raise AssertionError(
			"NotFoundPrograms [sy.parse]: APIChanged or InvalidContentPath"
		)
	return it

toBS= lambda o: bs4.BeautifulSoup(o, "html.parser")


_chID2NameMap= dict()
def chID2Name(chid):
	if not _chID2NameMap:
		with _OPENER.openTO(f"{ DBURL }?Command=ChLookup") as resp:
			_chID2NameMap.update({
				e.find("chid").text: e.find("chname").text
				for e in bs4.BeautifulSoup(resp, "html.parser").findAll("chitem")
			})
	return _chID2NameMap[chid]


class TitleID(str):
	"""
	title id in cal.syoboi.jp like "2288"
	This class uses 'cal.syoboi.jp' database URL (cal_syoboi.DBURL).
	"""

	def __new__(cls, cal_syoboi_title_identifier: object):
		"""
		cal_syoboi_title_identifier
			2288 or "2288" or "http://cal.syoboi.jp/tid/2288"
		"""
		id= src= cal_syoboi_title_identifier
		if isinstance(id, TitleID):
			return id
		try:
			id= str(int(id))
		except:
			if isinstance(id, _req.Request):
				try:
					id= _REG_URL_TID.search(_formatProgramsURL(id)).group(1)
				except Exception as e:
					raise ValueError(f"[TitleID] ParseError: '{id.full_url}'", e)
			else:
				try:
					id= _REG_URL_TID.search(id).group(1)
				except AttributeError:
					raise ValueError(f"[TitleID] NotFoundTID: '{id}'")
				except Exception as e:
					raise ValueError(f"[TitleID] ParseError: '{id}'", e)
		it= str.__new__(TitleID, id)
		# setattr(it, "src", src)
		return it

	def __repr__(self):
		return f"TitleID('{ self }')"


	@_ftls.lru_cache()
	def lookupT(tid):
		"Function 'fetchTID2NameMap' can get many title names efficiently."
		it= TitleID.fetchTID2NameMap([tid])[tid]
		import time; time.sleep(1)
		return it


	@staticmethod
	def fetchTID2NameMap(cal_syoboi_title_identifiers: [object]) -> dict:
		"""
		cal_syoboi_title_identifiers
			list of title IDs in cal.syoboi.jp like
			2288 or "2288" or "http://cal.syoboi.jp/tid/2288"
		return dictobj
			dictobj[TITLE_ID]== TITLE_NAME

		***Please check***
			https://sites.google.com/site/syobocal/spec/db-php
		"""
		TIDs= {e: e for e in map(TitleID, cal_syoboi_title_identifiers) }
		import urllib.parse as p
		with _OPENER.openTO(
			f'{ DBURL }?Command=TitleLookup'
			f'&TID={ p.quote( ",".join(TIDs) ) }&Fields=Title'
		) as resp:
			return {
				TIDs.get(e["id"]): e.find("title").text
				for e in toBS(resp)("titleitem")
			}


	def lookupP(
		tid, dtrange: (dt, dt)= None, lastUpdateDT: dt= None
		, *, counts= [], chIDs= [], pastonly= True
		, chID2Name= chID2Name
	) -> dict:
		"""
		tid
			title id in cal.syoboi.jp like "2288"
		return
			programs of this tid

		ret["rights"] -> [_Program]
		ret["lefts"] -> [_ErrProgram]

		***Please check***
			https://sites.google.com/site/syobocal/spec/db-php
		"""
		DTFMT= "%Y%m%d_%H%M%S"
		fields= []
		qs= {
			"Command": "ProgLookup"
			, "Range": (
				dtrange and f'{ dtrange[0].strftime(DTFMT) }-{ dtrange[1].strftime(DTFMT) }'
			)
			, "LastUpdate": lastUpdateDT and f'{ lastUpdateDT.strftime(DTFMT) }-'
			, "Count": ",".join(map(str, counts))
			, "Fields":  ",".join(fields) 
			,  "ChID": ",".join(map(str, chIDs)) 
			, "JOIN": "SubTitles"
			, "TID": tid
		}
		import urllib.parse as p
		URL= f'{ DBURL }?{ p.urlencode([t for t in qs.items() if t[1]]) }'
		with _OPENER.openTO(URL) as resp:
			bs= toBS(resp)
			code= int(getattr(bs.find("code"), "text", "-1"))
			msg= getattr(bs.find('message'), "text", "(No MSG)")
			if code in (400, ):
				raise ValueError(dict(code= code, msg= msg, tid= tid, URL= URL))
			items= map(_progitemConverter(chID2Name), bs("progitem"))
			it= groupby(type, items)
			now= dt.now()
			it["rights"]= [
				e for e in it.pop(_Program, [])
				if not pastonly or e.startDT+ td(minutes= e.min)< now
			]
			it["lefts"]= it.pop(_ErrProgram, [])
			it["respcode"]= code
			it["respmsg"]= msg
			return it


class Title(_req.Request):

	def __str__(self):
		return f'Title({ getattr(self, "_syoboi_title", self.full_url) })'

	__repr__= __str__

	programs= property(parse)
	titleID= property(TitleID)

	@staticmethod
	def _of(url, title= None):
		it= Title(url)
		if title: it._syoboi_title= title
		return it

	@staticmethod
	def sOfSeason(quarter: str) -> tuple:
		"example 2019: { '2019q1', '2019q2', '2019q3', '2019q4' }"
		args= (r"\d+q[1-4]", quarter)
		if not re.fullmatch(*args):
			raise ValueError(*args)
		with _OPENER.simpleop(
			'https://cal.syoboi.jp/quarter/'+ quarter
		) as resp:
			return tuple(
				Title._of('https://cal.syoboi.jp'+e['href'], e.text)
				for e in toBS(resp).select('td>a.title')
			)

def search(title_query: str) -> [Title]:
	"""
	title: str
		あなたの探したい作品のタイトルの検索クエリ

	タイトルの候補を返します。
	"""
	from urllib.parse import quote
	go= lambda s: (
		f'https://cal.syoboi.jp/find?type=quick&sd=1&kw={ quote(s) }'
		.replace("%20", "+")
	)
	getTitles= lambda bs: (
		next(e.parents).find("a")
		for e in bs.select("div.findComment")
	)
	joinSlash= lambda a, b: (
		f'{ a[:-1] if a[-1:]== "/" else a }/{ b[1:] if b[:1]== "/" else b }'
	)

	url= go(title_query)
	try:
		with _OPENER.simpleop(url) as resp:
			bs= toBS(resp.read())
	except Exception as e:
		raise RuntimeError("通信エラーが発生しました", e)
	if not "find?" in resp.url:
		return [
			Title._of(
				joinSlash(resp.url, "time")
				, [*[next(e.children) for e in bs.select("h1[title]")], ""][0].strip()
			)
		]
	from functools import reduce
	return [
		Title._of(
			reduce(joinSlash, ["https://cal.syoboi.jp", e["href"], "time"])
			, e.text
		)
		for e in getTitles(bs)
	]


# programsIter, progsIterB

def groupby(f, ite):
	ps= {}
	for e in ite:
		ps.setdefault(f(e), []).append(e)
	return ps

# class TVBroadcastTable:


DBURL= "http://cal.syoboi.jp/db.php"


def searchChID(chNamePattern: str, methodName: str= "search") -> list:
	"""
	Search channel ID in 'cal.syoboi.jp'.
	methodName
		fullmatch or match or search
	return
		matching dict results (pair of 'chName', 'syChID')
	"""
	try: chID2Name("1")
	except: pass
	go= getattr(re.compile(chNamePattern), methodName)
	return [
		{"chName": name, "syChID": id}
		for id, name in _chID2NameMap.items() if go(name)
	]


def _progitemConverter(chID2Name= chID2Name):
	def progitem2EitherProg(parsed: bs4.element.Tag):
		try:
			e= bs= parsed
			try:
				count= int(e.find("count").text)
			except:
				count= None
			_syChID= e.find("chid").text
			chName= chID2Name(_syChID)
			if not isinstance(chName, str):
				raise TypeError("[progitem2EitherProg] chName:", type(chName))
			startDT= dt.strptime(e.find("sttime").text.strip(), "%Y-%m-%d %H:%M:%S")
			min= int((
				dt.strptime(e.find("edtime").text.strip(), "%Y-%m-%d %H:%M:%S")
				- startDT
			).total_seconds())// 60
			subtitle= e.find("stsubtitle").text.strip() or e.find("subtitle").text.strip()
			return _Program(**locals())
		except Exception as e:
			return _ErrProgram.ofErr(e, bs, f"[progitem2EitherProg] {type(e).__name__}")
	return progitem2EitherProg

