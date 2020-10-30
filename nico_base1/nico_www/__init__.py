"""
Get Comments From Site 'www.nicovideo.jp'
"""

import json

log_f= print

def _json2ChatElems(loadsArg):
	from xml.etree.ElementTree import Element
	for d in json.loads(loadsArg):
		d= d.get("chat")
		if not d: continue
		t= d.pop("content", "")
		it= Element("chat", d)
		it.text= t
		yield it


# class _Page:
# 	def __init__(self, urlopen, url):
# 		import bs4
# 		with urlopen(url) as resp:
# 			bs= bs4.BeautifulSoup(resp.read(), "html.parser")
# 			apid= _DataApiData.fromBS(bs)
# 
# 			# del bs
# 		self.__dict__.update(**locals())
# 		del self.self


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

	# defaultThread= property(
	# 	lambda apid: apid['thread']["ids"]["default"]
	# )
	threadForThreadkey= property(
		lambda apid: apid['thread']["ids"]["community"]
	)

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

	def _mkPings(apid, threadkey= None, index= 0):
		b= _PingsBuilder(index)
		dur= apid["video"]["duration"]
		id= apid._user_id; ukey= apid._userkey
		for d in apid['commentComposite']['threads']:
			if not d["isActive"]:
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
				, userkey= ukey if d["label"]== "default" else None
			)
		return b


class _CmtsRequest(_DataApiData):

	def crnt(apid, threadkey):
		from urllib.request import Request
		return Request(
			"https://nmsg.nicovideo.jp/api.json/"
			, data= json.dumps( apid._mkPings(threadkey).build(0) ).encode("utf_8")
			, headers= { 'Content-Type': 'text/plain;charset=UTF-8' }
			, method= "POST"
		)

	def _newThreadkey(apid, urlopen):
		from urllib.parse import parse_qs
		with urlopen( _threadkeyURLOf(apid.threadForThreadkey) ) as resp:
			return parse_qs(resp.read().decode("ascii"))["threadkey"][0]


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
	):
		dThread= {'thread': {
			'fork': fork,
			'language': 0,
			'nicoru': 3,
			'scores': 1,
			'thread': str(thread),
			'user_id': str(user_id),
			'version': '20090904',
			'with_global': 1}}
		dThreadL= {'thread_leaves': {
			'content': content,
			'fork': fork,
			'language': 0,
			'nicoru': 3,
			'scores': 1,
			'thread': str(thread),
			'user_id': str(user_id)}}
		set= dThread["thread"].__setitem__
		setl= dThreadL["thread_leaves"].__setitem__
		if threadkey:
			set("threadkey", threadkey); setl("threadkey", threadkey)
			set("force_184", "1"); setl("force_184", "1")
		if userkey:
			set("userkey", userkey); setl("userkey", userkey)
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

