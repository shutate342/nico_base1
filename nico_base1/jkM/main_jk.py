# -* coding: cp932 *-

"""
first:
	Use loginJK -> _JKAPI

from timestamp:
	Use jkM.CmtsIter(jkapi: _JKAPI, "jk11", 1346688000, 1346689800)
		-> iterator of 'chat' elements
from datetime:
	Use _JKAPI.dt2Log(~)
		-> jkM.CmtsIter
	Use _JKAPI.syoboi(~) or _JKAPI.stat(~) with sy._Program
		-> SyoboiCmts
			.save(~) -> XML file
			.server -> jkM.CmtsIter
"""

from   .. import jkM
from   .. import nico_base1 as base
from   .. import cal_syoboi as sy
from   ..local_cmts import _Sink, newDefaultSink
import os

elementsTest= lambda jk: [*jkM.CmtsIter(jk, "jk11", 1346688000, 1346689800)]

E= dict(encoding= "utf_8")

def shiftFWer(vpos):
	"shift 'vpos' forward"
	vpos= int(vpos)
	def mapper(elem):
		d= elem.attrib
		d["vpos"]= str(int(d["vpos"])- vpos)
		return elem
	return mapper


def programOf(chIdentifier: object, startDT: jkM.dt, min: int, **kwargs):
	"""
	ユーザーのための sy._Program 作成メソッド

	chIdentifier: object
		'TOKYO MX' or 'jk9' or 9
	min[minutes]: int
	"""
	d= jkM.jkTable
	it= chIdentifier
	jkCh= f"jk{it}" if isinstance(it, int) else it
	import re
	if re.fullmatch(r"jk\d+", jkCh):
		for t in d.items():
			if t[1]!= jkCh: continue
			it= t[0]; break
	if not it in d:
		raise ValueError(
			f"'{chIdentifier}', and jkM.jkTable is incomplete."
		)
	return sy._Program(it , startDT, min, **kwargs)


class SyoboiCmts:
	"""
	主に save メソッドでコメントを保存するクラスです。
	server 属性で コメントイテレータにアクセスできます。

	* このクラスではコメントが流れるタイミング (vpos) は
		開始時刻に 0 になるようデフォルトで調整されています
		生データは毎朝４時が基準になっています
		コメントイテレータから直接要素を取得する際は注意してください
		役立つ関数: jkM.vposdiffAt
			shiftFWer(
				jkM.vposdiffAt( jkM.dt.fromtimestamp(timestamp: int) )
			) で
			element を マップする関数ができます

	コメントイテレータから保存:
		.コメント数があまりにも多くなければ
			jkM.elems2ETree 関数を使用後、
			write メソッドが利用できます
		.上記の方法はメモリを圧迫するので
			_Sink オブジェクトなら安心です
			newDefaultSink()(open("hoge.xml", "wb"), server: jkM.CmtsIter)
	"""

	@staticmethod
	def of(jk, prog: sy._Program):
		ts= int(prog.startDT.timestamp())
		# (this, self: _JK, jkCh, start_ts, end_ts)
		return SyoboiCmts(
			jkM.CmtsIter(
				jk
				, tryJKChID(prog)
				, ts
				, ts+ (60* prog.min)
			)
			, prog
		)

	def __init__(self, cmtsIter: jkM.CmtsIter, prog):
		server= cmtsIter
		self.__dict__.update(locals())

	def saveAs(self, fullpath, sink: _Sink= None, elemMapper= None) -> type(None):
		"""
		save file as 'fullpath'

		elemMapper: function(e: jkM.ET.Element) -> jkM.ET.Element
		"""
		dst= fullpath
		if os.path.exists(dst):
			raise FileExistsError(dst)
		with open(dst, "wb") as f:
			(sink or _Sink.of(os.linesep.encode("utf_8"), "utf_8"))(
				f
				, map(elemMapper or shiftFWer( jkM.vposdiffAt(self.prog.startDT) ), self.server)
				, self.server.epilogues
			)

	def save(self, directory, *args, **kwargs) -> type(None):
		"""
		elemMapper: function(e: jkM.ET.Element) -> jkM.ET.Element
		"""
		return self.saveAs(
			os.path.join(directory, self.filename)
			, *args, **kwargs
		)
		
	@property
	def filename(self):
		c= self.prog.getCount("")
		if isinstance(c, int):
			c= f"{c:02}."
		return f"{ c }{ self.server.name }.xml"


class _JKAPI(jkM._JK):
	"""
	各種メソッドを使ってコメントを取得します
	"""

	syoboi= SyoboiCmts.of

	def stat(jk, prog: sy._Program) -> SyoboiCmts:
		"""
		ファイルの最後に
		プレ垢数、コメント最大分速などの情報を付加する
		SyoboiCmts を返します。
		"""
		ts= int(prog.startDT.timestamp())
		return SyoboiCmts(
			jkM.CmtsIterStat(
				jk, tryJKChID(prog)
				, ts, ts+ (60* prog.min)
			)
			, prog
		)

	import functools as ftls
	getLog= ftls.partialmethod(jkM.CmtsIter)
	del ftls

	def dt2Log(self, jkCh, startDT: jkM.dt, endDTorTD) -> jkM.CmtsIter:
		"""
		endDTorTD: jkM.dt or jkM.td
			datetime か timedelta により期間を指定できます
		"""
		n1= int(startDT.timestamp())
		n2= int((
			startDT+ endDTorTD
			if   isinstance(endDTorTD, jkM.td)
			else endDTorTD
		).timestamp())
		return self.getLog(jkCh, n1, n2)


def loginJK(mail_tel, password, timeout= object()) -> _JKAPI:
	d= dict(timeout= timeout) if not type(timeout) is object else {}
	return _JKAPI(base.Login(mail_tel, password), **d)


def tryJKChID(prog: sy._Program) -> str:
	"""
	Get JKChID more strictly than jkM.jkTable.
	return 'jk****'
	"""
	return (
		syChIDTable.get(getattr(prog, "_syChID", None))
		or jkM.jkTable[prog.chName]
	)


# Test:
# itemd= {e.find("chid").text: e.find("chname").text for e in LOOKUPS("chitem")}
# g= (print(f"myi: {e}") or (itemd[e[0]], MAIN.programOf(e[1], None, 0).chName) for e in syChIDTable.items())
# next(g), ...
syChIDTable= {
	"1": "jk1"
	, "2": "jk2"
	# eテレのマルチ編成？同じにしてしまった
	, "64": "jk2", "65": "jk2"
# kbs
	, "36": "jk1143"
# NHKラジオ第1
	, "49": "jk594"
	# NHKラジオ第2
	, "195": "jk693"
	# ラジオnikkei
	, "218": "jk3925"
# inter fm
	, "180": "jk761"
# tokyo fm
	, "162": "jk800"
# tbs
	, "53": "jk954"
	# 文化放送
	, "41": "jk1134"
# ニッポン
	, "30": "jk1242"
# bayfm
	, "166": "jk780"
# nack5
	, "188": "jk795"
# ヨコハマ
	, "190": "jk847"
# ラジオ日本
	, "191": "jk1422"
# zip-fm
	, "184": "jk778"
# fm aichi
	, "186": "jk807"
# 中部日本放送でラジオ放送を開始 -> cbcラジオ
	, "183": "jk1053"
# 東海
	, "139": "jk1332"
# radio cube fm三重
	, "185": "jk789"
# 朝日放送 == ABCラジオ
	, "38": "jk1008"
# 毎日放送 == MBSラジオ
	, "134": "jk1179"
# 大阪
	, "35": "jk1314"
# ラジオ関西
	, "133": "jk558"
	# NHKBS-1
	, "9": "jk101"
	# OK: , "71": "jk141"
	# BSジャパン
	, "15": "jk171"
	# スター
	, "217": "jk200", "219": "jk201", "214": "jk202"
	# twellv
	, "129": "jk222"
	# 放送大学 bs or cs?: 放送大学CSテレビ
	, "158": "jk231"
	# BSスカパー!
	, "196": "jk241"
	# 日本映画専門チャンネル
	, "40": "jk255"

	,
'3': 'jk8',
'4': 'jk4',
'5': 'jk6',
'6': 'jk5',
'7': 'jk7',
'8': 'jk11',
'13': 'jk12',
'14': 'jk10',
'16': 'jk161',
'17': 'jk181',
'18': 'jk151',
'19': 'jk9',
'66': 'jk1143',
'71': 'jk141',
'76': 'jk193',
'83': 'jk1431',
'97': 'jk192',
'106': 'jk825',
'128': 'jk211',
'138': 'jk1413',
'163': 'jk256',
'197': 'jk236',
'179': 'jk103',
'204': 'jk191',
'212': 'jk258',
}
