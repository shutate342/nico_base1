# -* coding: cp932 *-
"""
http://cal.syoboi.jp/mng?Action=ShowChList
-> ShowChList

��:
# sy: This module.
titles= sy.search("�X��")
title= titles[0]
programs= sy.groupby(lambda e: e.getCount(None), title.programs)

# jk: nico_base1.jk.main._JKAPI
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

	def __repr__(self):
		return f'<_ErrProgram({ self.error }) { list(self.debug.values()) }>'


	def __getattr__(self, name):
		return ERR

	__str__= __repr__


_ifNone= lambda it: lambda default: default if it is None else it

class _Program:

	def __init__(self, chName, startDT, min, count= None, subtitle= None, **kwargs):
		del kwargs
		getCount= _ifNone(count)
		getSubtitle= _ifNone(subtitle)
		del count, subtitle
		self.__dict__.update(locals())
		self.__dict__.pop("self")

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
			return _Program(**locals())
		except Exception as e:
			return _ErrProgram(locals())

def bs2EitherProgs(parsed: bs4.BeautifulSoup) -> dict:
	"""
	ret["rights"] -> [_Program]
	ret["lefts"] -> [_ErrProgram]
	"""
	# tbody= parsed.select("table.progs > tbody")[0]
	# programs= tbody.find_all(recursive= False)
	programs= parsed.select("table.progs")[0].select("tr.past")
	it= groupby(type, map(_Program.of, programs))
	it["rights"]= it.pop(_Program, [])
	it["lefts"]= it.pop(_ErrProgram, [])
	return it


def parse(url_or_titleObj) -> [_Program]:
	"""
	cal.syoboi.jp �̃T�C�g���猩�����^�C�g�����������܂��B
	����� �^�C�g���̌���� or �^�C�g����ʂ��̂��̂Ɉړ����܂��B
	url_or_titleObj
		���ꂼ�� ��₩�� URL ���R�s�[ or �u���E�U�̃y�[�W URL ���R�s�[��������

	�������ꂽ�ԑg�̈ꗗ��Ԃ��܂��B
	"""
	it= url_or_titleObj
	it= (
		isinstance(it, _req.Request) and it
		or isinstance(it, str) and _req.Request(it)
		or exec(f'raise TypeError(type(it))')
	)
	with _req.urlopen(it, timeout= _DEFAULT_TIMEOUT) as resp:
		return _b2Progs(resp.read())

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
		���Ȃ��̒T��������i�̃^�C�g���̌����N�G��

	�^�C�g���̌���Ԃ��܂��B
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
		raise RuntimeError("�ʐM�G���[���������܂���", e)
	if not "find?" in resp.url:
		return [
			Title._of(
				joinSlash(resp.url, "time")
				, getattr([*bs.select("h1[title]"), None][0], "text", "").strip()
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

