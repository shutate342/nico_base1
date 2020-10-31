# -* coding: cp932 *-
"""
{'thread': '1496775611', 'no': '8', 'vpos': '5873500', 'date': '1496834336', 'deleted': '2', 'anonymity': '1'}
"""

from   ..nico_base1 import *
from   ..nico_base1 import _TimeoutMgr, _MAGIC
from   ..local_cmts import elems2ETree
from   datetime import datetime as dt, timedelta as td
import xml.etree.ElementTree as ET


def dtPair(dt, duration= 60* 30) -> (dt, dt):
	"duration [second]: int"
	return dt, dt+ td(seconds= duration)


def vposdiffAt(dt_):
	"""
	vpos は毎朝 4 時を基準に更新されます。
	return i [second] * 100: int
		| 0 <= i < 24[hour]
	"""
	base= dt(*dt_.timetuple()[:3], 4)
	if dt_< base:
		base-= td(1)
	return int( (dt_- base).total_seconds()* 100 )


class _JK(_TimeoutMgr):
	"""
	res_from=-1000&version=20061206
	"""
	from urllib.parse import parse_qs
	parse_qs= staticmethod(parse_qs)

	def getflv2(self, jkCh, start_ts, end_ts):
		URL= (
			f"http://jk.nicovideo.jp/api/v2/getflv?v={ jkCh }"
			f"&start_time={ start_ts }&end_time={ end_ts }"
		)
		with self.openTO(URL) as resp:
			it= self.parse_qs(resp.read().decode(_MAGIC("utf_8")))
		return {
			k: v[0] for k, v in it.items()
			if (len(v)!= 1) and log_f(f"[v2/getflv] '{k}': not 1 value") or True
		}

	def getwaybackkey(self, thread_id):
		URL= f"http://jk.nicovideo.jp/api/v2/getwaybackkey?thread={thread_id}"
		with self.openTO(URL) as resp:
			return resp.read().decode(_MAGIC("utf_8"))[len("waybackkey="):]

	def getXMLCmts(self, host, thread_id, res_from, when, user_id, waybackkey):
		"res_from は -1000 より小さくても意味なし？"
		URL= (
			f"http://{host}/api/thread?thread={ thread_id }"
			f"&res_from={ res_from }&version=20061206&when={when}&user_id={user_id}"
			f"&waybackkey={ waybackkey }&scores=1"
		)
		with self.openTO(URL) as resp:
			return resp.read().decode(_MAGIC("utf_8"))


class CmtsIter:
	"""
	response が no の順番に従っていることに依存
	date は date_usec を無視すれば順番に従っている
	vpos は順番どおりではない。コメント送信時間のずれが加味されている？
	"""

	def __iter__(self):
		return self.get()

	@property
	def name(self):
		d= self.flvInfo
		dt_= dt.fromtimestamp(self.start_ts)
		return (
			f'jk{ d["channel_no"] }_{ d["channel_name"] }'
			"_"
			f'{ dt_.strftime("%Y%m%d") }_{ dt_.strftime("%H%M%S") }'
		)

	@property
	def epilogues(self):
		return []

	def __init__(this, self: _JK, jkCh: str, start_ts: int, end_ts: int):
		"""
		jkCh: channel like 'jk1'
		start_ts[sec]: start timestamp
		end_ts[sec]: end timestamp
		"""
		flvInfo= self.getflv2(jkCh, start_ts, end_ts)
		try:
			user_id= flvInfo["user_id"]
		except KeyError:
			raise RuntimeError(
				"[main] LoggedOut or Expired or OutsideServicePeriod: bad flv2 info 'user_id'"
			)
		wbkey= self.getwaybackkey(flvInfo["thread_id"])
		
		def get():
			min_ts= end_ts
			min_no= float("inf")
			while start_ts<= min_ts:
				args= (
					f'{ flvInfo["ms"] }:{ flvInfo["http_port"] }'
					, flvInfo["thread_id"]
					, _MAGIC(-1000)
					# ここ大事
					, min_ts+ 1
					, user_id
					, wbkey
				)
				for _ in range(5):
					try:
						packet= ET.fromstring(self.getXMLCmts(*args))
						break
					except Exception as e:
						exc= e
						log_f(f"[main] try again: {type(exc), exc}")
				else:
					raise exc
				elems= tuple(
					e for e in packet.findall("chat")
					if int(e.attrib["no"])< min_no
				)
				try:
					crntMaxNo= int( elems[-1].attrib["no"] )
				except IndexError:
					log_f(f"[main] break: Not found element")
					break
				if (
					min_no!= float("inf")
					and crntMaxNo+ 1!= min_no
				):
					raise RuntimeError(f'[main] TruncatedComments: getmax={crntMaxNo}, crntmin={min_no}')
				min_no= int(elems[0].attrib["no"])
				min_ts= (
					# min( int(e.attrib["date"]) for e in elems )
					int( elems[0].attrib["date"] )
				)
				yield from reversed(elems)

			log_f(f"[main] end {jkCh} {start_ts}")

		this.__dict__.update(locals())

class CmtsIterStat(CmtsIter):
	"１秒間に 256 コメ以上あるとオーバーフローします"

	@staticmethod
	def movingcnts(cntsPerSec, rangeSec= 60, stepSec= 1):
		import itertools as itls
		# keys= itls.starmap(
		keys= map(
			slice
			, itls.count(0, stepSec)
			, range(rangeSec, len(cntsPerSec)+ 1, stepSec)
		)
		return tuple(
			map(sum, map(cntsPerSec.__getitem__, keys))
		)

	def __iter__(self):
		nomas= set()
		miums= set()
		start_ts= self.start_ts
		base_vpos= vposdiffAt(dt.fromtimestamp(self.start_ts))
		cnts= bytearray(self.end_ts- start_ts+ 1)
		excl= 0
		deleted= 0
		for e in self.get():
			d= e.attrib
			try:
				i= ( int(d["vpos"])- base_vpos )// 100
			except KeyError:
				log_f(f"[stat] This is ambiguous error msg: attrs({d})")
			if i< 0 or len(cnts)<= i:
				excl+= 1
				continue
			cnts[i]+= 1
			try:
				(miums if d.get("premium") else nomas).add(d["user_id"])
			except KeyError:
				d["deleted"]
				deleted+= 1

			yield e

		movcnts= self.movingcnts(cnts)
		# Unknown format code '\x20' for object of type 'float' -> { .25:.2 }
		self._stats= [
			ET.Comment(
				f'cmts="{ sum(cnts) }" excluded="{ excl }" mave="{ sum(cnts)* 60/ len(cnts):.2f}"'
			)
			, ET.Comment(
				f' mmax="{ max(movcnts) }" mmin="{ min(movcnts) }"'
				f' total_users="{ len(nomas)+ len(miums) }" premiums="{ len(miums) }"'
			)
		]

	@property
	def epilogues(self):
		it= getattr(self, "_stats", None)
		if it is None:
			raise RuntimeError("Please call this after '*iter(this)'")
		yield from it


jkTable= dict(
	(lambda no, key: [key.strip(), f"jk{ no.strip() }"])
	(*s.strip().split("=", 1))
	for s in """

	1   =NHK 総合 
	2   =Eテレ
	4   =日本テレビ
	5   =テレビ朝日
	6   =TBS テレビ
	6   =TBS
	7   =テレビ東京
	8   =フジテレビ
	9   =TOKYO MX
	10  =テレ玉
	11  =tvk
	12  =チバテレビ


	594 =NHKラジオ第1
	693 =NHKラジオ第2
	825 =NHK-FM
	792 =AIR-G'
	1287=HBCラジオ
	1440=STVラジオ
	3925=ラジオNIKKEI第1放送
	761 =Inter FM
	800 =TOKYO FM
	813 =J-WAVE
	954 =TBSラジオ
	1134=文化放送
	1197=茨城放送
	1242=ニッポン放送
	764 =RADIO BERRY
	863 =FMぐんま
	780 =bayfm
	795 =NACK5
	847 =FMヨコハマ
	1422=ラジオ日本
	778 =ZIP-FM
	807 =FM AICHI
	1053=CBCラジオ
	1332=東海ラジオ
	1431=ぎふチャン
	789 =radio CUBE FM三重
	765 =FM COCOLO
	802 =FM802
	851 =FM OSAKA
	899 =Kiss FM KOBE
	1008=朝日放送
	1179=毎日放送
	1314=ラジオ大阪
	1143=KBS京都
	558 =ラジオ関西
	1557=和歌山放送
	808 =FM FUKUOKA
	827 =Love FM
	1278=RKBラジオ
	1413=九州朝日放送


	101 =NHKBS-1
	103 =NHK BSプレミアム
	141 =BS 日テレ
	141 =BS日テレ
	151 =BS 朝日
	151 =BS朝日
	161 =BS-TBS
	171 =BSジャパン
	181 =BSフジ
	191 =WOWOWプライム 
	192 =WOWOWライブ 
	193 =WOWOWシネマ

	200 =スターチャンネル1
	201 =スターチャンネル2
	202 =スターチャンネル3

	211 =BSイレブン
	211 =BS11イレブン

	222 =TwellV
	231 =放送大学
	234 =BSグリーンチャンネル
	236 =BSアニマックス
	238 =FOX bs 238
	241 =BSスカパー!
	242 =J Sports 1
	243 =J Sports 2
	244 =J Sports 3
	245 =J Sports 4
	251 =BS釣りビジョン
	252 =IMAGICA BS
	255 =BS日本映画専門チャンネル 
	256 =ディズニー・チャンネル
	258 =Dlife
	910 =SOLiVE24
 
""".split("\n") if s and not s.isspace() )

