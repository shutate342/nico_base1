# -* coding: cp932 *-

"""
# Get Comments From Site 'www.nicovideo.jp'

# Main Usage:

import nico_base1.nico_www as m

session= m.login("your-address@example.com", "your-password")

# want to get comments 'YagaKimi' episode 1
#     session.cmtsOf("https://www.nicovideo.jp/watch/1539138303")
cmts= session.cmtsOf("https://www.nicovideo.jp/watch/so33993109")

# cmts.getCrnt() -> bytes
# cmts.getCrnt(m.json.load) -> (JSON document to a Python object)
# cmts.getCrnt(cmts.CHATS) -> [xml.etree.ElementTree.Element]
elems= cmts.getAt(m.dt(2018,10,15,14,35), cmts.CHATS)

# example: use elems
# len([e for e in elems if e.get("deleted")])
# -> count current deleted comments
# elems= [e for e in elems if not ("TDN" in e.text or "ＴＤＮ" in e.text)]
# -> filter comments

# save to file
# cmts.getVideoID("No ID") -> "sm***" or "so***" or ...
dst= cmts.getFileNameTitle("Default title if not found")+ ".xml"

from nico_base1.local_cmts import elems2PacketETree
# force overwrite
elems2PacketETree(elems).write( dst, "utf_8")

# or
from nico_base1.local_cmts import newDefaultSink
# default: raise FileExistsError
newDefaultSink(b"\x0d\x0a").bindPath(dst)(elems)
"""

import json
from   datetime import datetime as dt

log_f= print

def json2ChatElems(loadsArg):
	"""
	create Element generator

	loadsArg: response from www.nicovideo.jp comments API
	"""
	from xml.etree.ElementTree import Element
	for d in json.loads(loadsArg):
		d= d.get("chat")
		if not d: continue
		t= d.pop("content", "")
		it= Element("chat", { k: str(v) for k, v in d.items() })
		it.text= t
		yield it


from   .. import nico_base1 as _base
def login(mail_tel, password, timeout= (9, 40)):
	"""
	timeout: object
		= (connectTimeout, readTimeout): tuple
		= timeout: float
		= None (set blocking True)
	"""
	# d= dict(timeout= timeout) if not isinstance(timeout, object) else {}
	return _NicoWWW(_base.Login(mail_tel, password), timeout)


class _NicoWWW(_base._TimeoutMgr):

	def cmtsOf(self, url):
		with self.openTO(url) as resp:
			import bs4
			_dbs= bs4.BeautifulSoup(resp, "html.parser")
			_apid= _RequestBuilder._parseStream(str(_dbs))
			return _Comments(
				timeout= (self.connectTimeout, self.readTimeout)
				, **self.__dict__, **(lambda d: d.pop("self") and d)(locals())
				, **{ k: getattr(_apid, k) for k
					in set(dir(_apid))- set(dir(dict)) if k[:1]!= "_"
				}
			)

	def _newThreadkey(self, apid):
		from urllib.parse import parse_qs
		with self.openTO( _threadkeyURLOf(apid._threadForThreadkey) ) as resp:
			b= resp.read()
			try:
				it= parse_qs(b.decode("ascii"))["threadkey"][0]
				return it
			except KeyError:
				log_f(f"[threadkey] { b }")
				return ""

	def _newWaybackkey(self, apid):
		URL= (
			"https://flapi.nicovideo.jp/api/getwaybackkey"
			f"?thread={ apid._threadForThreadkey }"
		)
		from urllib.parse import parse_qs
		with self.openTO( URL ) as resp:
			try:
				b= resp.read()
				return parse_qs(b.decode("ascii"))["waybackkey"][0]
			except KeyError:
				log_f(f"[waybackkey] { b }")
				return ""


def getContent(io):
	"-> io.read()"
	return io.read()


class _Comments(_NicoWWW):
	_debug= None

	@staticmethod
	def CHATS(bytesIO_):
		return list(json2ChatElems(bytesIO_.read()))

	def _reqGo(self, req, parseBIO):
		with self.openTO(req) as resp:
			type(self)._debug= locals()
			return parseBIO(resp)

	def getCrnt(self, parseBIO= getContent):
		"""
		parseBIO: function(bytesIO: http.client.HTTPResponse) -> object
			# OK:
			def getContent(io):
				return io.read()
			# NG:
			def getContent(io):
				yield io.read()
			# HTTResponse is already closed
			generator= cmts.getCrnt(getContent)
			assert next(generator)== b""
		"""
		tkey= self._newThreadkey(self._apid)
		req= self._apid._crnt(tkey)
		return self._reqGo(req, parseBIO)

	def getWhen(self, timestamp_sec, parseBIO= getContent):
		tkey= self._newThreadkey(self._apid)
		wkey= self._newWaybackkey(self._apid)
		req= self._apid._when(
			threadkey= tkey
			, waybackkey= wkey
			, when= timestamp_sec
		)
		return self._reqGo(req, parseBIO)

	def getAt(self, dt:dt, parseBIO= getContent):
		return self.getWhen( int(dt.timestamp()), parseBIO)

# def _getCrntJSONCmts(urlopen, apid, then= lambda _:_):



def _idAttrValue(bs, tagAttrName):
	try:
		it= bs.select(f"[{ tagAttrName }]")[0]
	except IndexError:
		raise RuntimeError(f"[nico_www] {tagAttrName}")
	return it[tagAttrName]


def _raise(t, *args):
	raise t(*args)

_ESSENTIAL_ATTRS= "data-environment", "data-api-data"


class _DataApiData(dict):

	_defaultThread= property(
		lambda apid: apid['thread']["ids"]["default"]
	)
	_threadForThreadkey= property(
		lambda apid: apid['thread']["ids"]["community"] or apid._defaultThread
	)

	def getVideoID(self, default):
		try: return self["video"]['id']
		except: return default

	def getFileNameTitle(self, default, esc= r'[\n\r\t\\/:*?"<>|]', replaced= "_"):
		# r'[\n\r\\/:*?"<>|]' r'[^\w\-_\.\u3000 ]'
		import re
		go= lambda s: re.sub(esc, replaced, s)
		try: return go( self["video"]["title"] )
		except: return go( default )

	@classmethod
	def _parseStream(cls, byteslike_or_io):
		import bs4
		bs= bs4.BeautifulSoup(byteslike_or_io, "html.parser")
		s= ( _idAttrValue(bs, "data-api-data") )
		return json.loads(s, object_hook= cls)

	@property
	def _user_id(self):
		try:
			return (
				self.get("viewer") and self['viewer']['id']
				or self['video']['dmcInfo']['user']['user_id']
			)
		except:
			log_f("[_user_id] NotFound"); return ""

	@property
	def _userkey(self):
		try:    return self['context']['userkey']
		except: log_f("[_userkey] NotFound"); return

	@staticmethod
	def _getWaybackD(waybackkey, when):
		if {waybackkey, when}== {None}:
			return {}
		if not all([isinstance(waybackkey, str), isinstance(when, int)]):
			raise ValueError(waybackkey, when)
		return locals()

	def _mkPings(apid, threadkey= None, index= 0, waybackkey= None, when= None):
		b= _PingsBuilder(index)
		dur= apid["video"]["duration"]
		id= apid._user_id; ukey= apid._userkey
		waybackD= apid._getWaybackD(waybackkey, when)
		for d in apid['commentComposite']['threads']:
			if (not d["isActive"]):# or (waybackD and d['label']== "default"):
				continue
			content= (
				_content100(dur)
				if   d["fork"]== 0
				else _content25(dur)
			)
			b= b.addPingOf(
				thread= d["id"]
				, fork= d["fork"]
				, content= content
				, user_id= id
				, isLeafRequired= d['isLeafRequired']
				, threadkey= (
					threadkey is None and _raise(RuntimeError, "isThreadkeyRequired")
					or threadkey
					if d['isThreadkeyRequired'] else None
				)
				, userkey= ukey if (d["label"]== "default") and (not waybackD) else None
				, **waybackD
			)
		return b


class _RequestBuilder(_DataApiData):

	def _crnt(apid, threadkey):
		from urllib.request import Request
		return Request(
			"https://nmsg.nicovideo.jp/api.json/"
			, data= json.dumps( apid._mkPings(threadkey).build(0) ).encode("utf_8")
			, headers= { 'Content-Type': 'text/plain;charset=UTF-8' }
			, method= "POST"
		)

	def _when(apid, threadkey, waybackkey, when):
		from urllib.request import Request
		d= apid._mkPings(
			threadkey, waybackkey= waybackkey, when= when
		).build(0)
		return Request(
			"https://nmsg.nicovideo.jp/api.json/"
			, data= json.dumps( d ).encode("utf_8")
			, headers= { 'Content-Type': 'text/plain;charset=UTF-8' }
			, method= "POST"
		)


_content100= lambda dur_sec: f"0-{ int(dur_sec)//60+ 1 }:100,1000,nicoru:100"
_content25= lambda dur_sec: f"0-{ int(dur_sec)//60+ 1 }:25,nicoru:100"

_threadkeyURLOf= lambda n_thread: (
	f"https://flapi.nicovideo.jp/api/getthreadkey?thread={n_thread}"
)


class _PingsBuilder:
	def __init__(self, index= 0, acc= []):
		self._index= index
		self._acc= acc

	def build(self, outerIndex):
		return [
			{'ping': {'content': f'rs:{ outerIndex }'}}
			, *self._acc
			, {'ping': {'content': f'rf:{ outerIndex }'}}
		]

	def addPingOf(
		self
		, *
		, thread
		, fork
		, content
		, isLeafRequired
		, user_id
		, userkey= None
		, threadkey= None
		, **others
	):
		unk= set(others)- {"waybackkey", "when"}
		if unk:
			raise KeyError(unk)
		dThread= {'thread': {
			'fork': fork,
			'language': 0,
			'nicoru': 3,
			'scores': 1,
			'thread': str(thread),
			'user_id': str(user_id),
			'version': '20090904',
			'with_global': 1}}
		dThread["thread"].update(others)
		dThreadL= {'thread_leaves': {
			'content': content,
			'fork': fork,
			'language': 0,
			'nicoru': 3,
			'scores': 1,
			'thread': str(thread),
			'user_id': str(user_id)}}
		dThreadL["thread_leaves"].update(others)
		set_= dThread["thread"].__setitem__
		setl= dThreadL["thread_leaves"].__setitem__
		if threadkey:
			set_("threadkey", threadkey); setl("threadkey", threadkey)
			set_("force_184", "1"); setl("force_184", "1")
		if userkey:
			set_("userkey", userkey); setl("userkey", userkey)
		i= self._index
		acc= [
			*self._acc,
			{'ping': {'content': f'ps:{ i }'}},
			dThread,
			{'ping': {'content': f'pf:{ i }'}}
		]
		if isLeafRequired:
			i+= 1
			acc.extend([
				{'ping': {'content': f'ps:{ i }'}},
				dThreadL,
				{'ping': {'content': f'pf:{ i }'}}
			])
		return _PingsBuilder(i+ 1, acc)

