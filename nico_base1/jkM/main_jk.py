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

class _Sink:
	"""
	consume XML elements

	__call__ メソッドの引数にある要素たちを
	レンダリングし、ファイルに書き込みます。
	"""

	@staticmethod
	def of(sep= b"", encoding= "utf_8"):
		enc= encoding
		def go(bytesFp, elems, epilogues):
			writer= bytesFp.write
			writer((
				f"<?xml version='1.0' encoding='{enc}'?>"
				"<packet>"
			).encode(enc))
			renderBytes= jkM.ET.tostring
			try:
				for e in elems:
					writer(sep); writer(renderBytes(e, enc, "html"))
				for e in epilogues:
					writer(sep); writer(renderBytes(e, enc, "html"))
			except (Exception, KeyboardInterrupt) as exc:
				raise exc
			finally:
				writer(b"</packet>")
		return _Sink(**locals())

	def __init__(self, **kwargs):
		self.__dict__= kwargs

	def __call__(self, bytesFp, elems: jkM.ET.Element, epilogues= []):
		return self.go(bytesFp, elems, epilogues)

newDefaultSink= _Sink.of

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
				, jkM.jkTable[prog.chName]
				, ts
				, ts+ (60* prog.min)
			)
			, prog
		)

	def __init__(self, cmtsIter: jkM.CmtsIter, prog):
		server= cmtsIter
		self.__dict__.update(locals())

	def save(self, directory, sink: _Sink= None, elemMapper= None) -> None:
		"""
		elemMapper: function(e: jkM.ET.Element) -> jkM.ET.Element
		"""
		dst= os.path.join(directory, self.filename)
		if os.path.exists(dst):
			raise OSError(dst)
		with open(dst, "wb") as f:
			(sink or _Sink.of(b"\r\n"))(
				f
				, map(elemMapper or shiftFWer( jkM.vposdiffAt(self.prog.startDT) ), self.server)
				, self.server.epilogues
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
				jk, jkM.jkTable[prog.chName]
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

