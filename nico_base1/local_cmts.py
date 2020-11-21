# -*- coding: cp932 -*-

import xml.etree.ElementTree as ET

def elems2PacketETree(elems):
	"例外が発生した時メッセージが分かりにくいので注意"
	packet= ET.Element("packet")
	# 例外の投げ方が凶悪
	packet.extend(elems)
	return ET.ElementTree(packet)

elems2ETree= elems2PacketETree


class _Sink:
	"""
	consume XML elements

	__call__ メソッドの引数にある要素たちを
	レンダリングし、ファイルに書き込みます。
	"""

	@staticmethod
	def of(sep= b"", encoding= "utf_8"):
		import os
		enc= encoding
		def go(bytesFp, elems, epilogues):
			writer= bytesFp.write
			writer((
				f"<?xml version='1.0' encoding='{enc}'?>"
				f"{ os.linesep }<packet>"
			).encode(enc))
			renderBytes= ET.tostring
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
		"Override with your parameters"
		self.__dict__= kwargs

	def __call__(self, bytesFp, elems: [ET.Element], epilogues= []):
		"Override me"
		return self.go(bytesFp, elems, epilogues)

	def bindPath(self, fullpath):
		"-> function(elems, epilogues= [])"
		from pathlib import Path
		it= Path(fullpath)
		if it.exists():
			return self.bindPath(self.renameStrategy(it))
		def call(elems: [ET.Element], epilogues= []):
			with it.open("wb") as f:
				return self(f, elems, epilogues)
		return call

	def renameStrategy(self, pathobj):
		"Override me"
		raise FileExistsError(pathobj)


newDefaultSink= _Sink.of

