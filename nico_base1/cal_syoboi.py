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

def _class(v):
	return {"class": v}

_REG_START= re.compile(r"(\d{4})-(\d+)-(\d+)[^\d]+(\d+):(\d+)")

_DEFAULT_TIMEOUT= 20

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

	@staticmethod
	def _fromDumpD(startTT, **kwargs):
		return _Program(startDT= dt(*startTT), **kwargs)

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
			# import sys; print(f"[_Program] { e }", file= sys.stderr)
			return _ErrProgram(locals())

def bs2EitherProgs(parsed: bs4.BeautifulSoup) -> dict:
	"""
	ret["rights"] -> [_Program]
	ret["lefts"] -> [_ErrProgram]
	"""
	try:
		# tbody= parsed.select("table.progs > tbody")[0]
		# programs= tbody.find_all(recursive= False)
		programs= parsed.select("table.progs")[0].select("tr.past")
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
		tid= re.match(r"/tid/(\d+)", it.selector).group(1)
	except Exception as e:
		raise ValueError(f"InvalidURLPath: '{ it.selector }', expected like '/tid/0001'")

	return f"https://cal.syoboi.jp/tid/{ tid }/time"


def parse(url_or_titleObj, assertNotEmpty= True) -> [_Program]:
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
				with open(it, "rb") as f: return _b2Progs(f.read())
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
		with _req.urlopen(it, timeout= _DEFAULT_TIMEOUT) as resp:
			return _b2Progs(resp.read())

	it= go()
	if assertNotEmpty and not it:
		raise AssertionError(
			"NotFoundPrograms [sy.parse]: APIChanged or InvalidContentPath"
		)
	return it


def _b2Progs(bytes_):
	return bs2EitherProgs(bs4.BeautifulSoup(bytes_, "html.parser"))["rights"]


class Title(_req.Request):

	def __str__(self):
		return f'Title({ getattr(self, "_syoboi_title", self.full_url) })'

	__repr__= __str__

	programs= property(parse)

	@staticmethod
	def _of(url, title= None):
		it= Title(url)
		if title: it._syoboi_title= title
		return it

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
	b2bs4= lambda b: bs4.BeautifulSoup(b, "html.parser")
	getTitles= lambda bs: (
		next(e.parents).find("a")
		for e in bs.select("div.findComment")
	)
	joinSlash= lambda a, b: (
		f'{ a[:-1] if a[-1:]== "/" else a }/{ b[1:] if b[:1]== "/" else b }'
	)

	url= go(title_query)
	try:
		with _req.urlopen(url, timeout= _DEFAULT_TIMEOUT) as resp:
			bs= b2bs4(resp.read())
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


def lookupT(tid) -> str:
	"""
	tid: title id in cal.syoboi.jp
	return (url of tid's title)
	"""
	return (
		f'{ DBURL }?Command=TitleLookup'
		f'&TID={ tid }&Fields=Title'
	)

def lookupP(tid, startDT= dt(2009,11,20), endDT= None, lastUpdateDT= None) -> str:
	"""
	tid: title id in cal.syoboi.jp like "2288"
	endDT: default: datetime.now()
	return (url of programs)
	"""
	return (
		f'{ DBURL }?Command=ProgLookup'
		f'&Range={ startDT.strftime("%Y%m%d_%H%M%S") }'
		f'-{ (endDT or dt.now()).strftime("%Y%m%d_%H%M%S") }'
		f'{ lastUpdateDT and "&LastUpdate="+ lastUpdateDT.strftime("%Y%m%d_%H%M%S")+ "-" or "" }'
		f'&JOIN=SubTitles&TID={ tid }'
	)

