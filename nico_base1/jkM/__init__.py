# -*- coding: cp932 -*-
"""
Get JiKkyo Comment.

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
	base= _prevAM4(dt_)
	return int( (dt_- base).total_seconds()* 100 )

def _prevAM4(dt_):
	base= dt(*dt_.timetuple()[:3], 4)
	if dt_< base:
		base-= td(1)
	return base

def _vposSerializer(startDT):
	VPOSDAY= (60* 60* 24)* 100
	VPOS2HOUR= (60* 60* 2)* 100
	# vposbase= int(startDT.timestamp())* 100
	baseAM4= _prevAM4(startDT)
	def go(elem):
		dt_= dt.fromtimestamp( int(elem.get("date")) )
		it= {}
		try:
			vpos= int( elem.get("vpos") )
		except TypeError:
			# vpos なければ自分で生成
			import random
			randv= -random.randint(150, 250)
			vpos= vposdiffAt( dt_ )+ randv
			it["add_randvpos"]= str(randv)

		diffdays= (_prevAM4(dt_)- baseAM4).days
		# 4時をすぎているが vpos が更新されていないものに注意
		if dt_.hour== 4 and VPOS2HOUR< vpos:
			# log_f(elem.get("no"), dt_, f"vpos[sec]: { vpos// 100 }")
			diffdays-= 1
		it["vpos"]= str( VPOSDAY* diffdays+ vpos )
		return it
	return go


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

class GetFlvError(RuntimeError): pass
class JKCommentError(RuntimeError): pass


class CmtsIter:
	"""
	response が no の順番に従っていることに依存
	date は date_usec を無視すれば順番に従っている
	vpos は順番どおりではない。コメント送信時間のずれが加味されている？

	vpos は date よりも早まっている

	以上古いメモ
	以下重要

	.生データは4時をまたぐと vpos が 0 にリセットされるが
		このクラスは4時をまたぐごとに日付分 vpos に加算し
		あたかも開始時刻から vpos が連続しているように要素を返す

	.4時をまたいだ後もまれにそのまま古いスレッドから投稿されるコメが存在する
		経験的に4時から数分間存在すると考えられる
		この4時から余裕をもってコメントを探す期間 (秒数)は
		変数 'EXTRA_LOOKUP_SEC_FROM_AM4' で調節する

	.このクラスは 1回でも 4時をまたぐと
		もっとも新しい時間に投稿されたコメントから順に
		変数 'DEFAULT_COUNTDOWN' からカウントダウンしながら属性 'no' を書き換える
		もとの 'no' は 'original_no' 属性として保持する
		-> この挙動を無効にするには 変数 'DEFAULT_COUNTDOWN' に None を代入する
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

	DEFAULT_COUNTDOWN= 1000000000
	EXTRA_LOOKUP_SEC_FROM_AM4= 60* 30

	@staticmethod
	def _enumeratorOf(countdown_from, overAM4):
		if overAM4 and isinstance(countdown_from, int):
			import itertools as itls
			return lambda e, _g= itls.count(countdown_from, -1): (
				e.set("original_no", e.get("no")) or str(next(_g))
			)
		else:
			return lambda e: e.get("no")

	def getAM4FlvInfo(self, am4_ts, end_ts):
		"""
		必ずAM4 からの新しいスレッドを取得
		あてずっぽうメンテ対策:
			4時から 24h 以内の様々な時間から getflv を試みる

		より確実に 例外を出さずにスレッド情報を取得したければ
		このメソッドをオーバーライドして工夫してください

		わかりにくい提案:
			長い期間のコメントを取得する際
			CmtsIter を普通にイテレートするだけでは
			1回どこかで例外が発生しただけでコメの取得が止まってしまいますが
			_getAM4Chunks を使って 1日分のchunk ごとのイテレートを例外処理すれば
			発生した 1日のみで 被害を抑え、コメの取得を続行できます

			もしくは取得期間を小分けして保存しましょう
		"""
		jk= self.self; start_ts= am4_ts; jkCh= self.jkCh
		log_f("[main] flvInfo: 4:30")
		flvInfo= jk.getflv2(jkCh, start_ts+ 60* 30, end_ts)
		if flvInfo.get("error"):
			import time; time.sleep(1)
			log_f("[main] try again: flvInfo: 12:00")
			flvInfo= jk.getflv2(jkCh, start_ts+ 8* 60* 60, end_ts)
		if flvInfo.get("error"):
			import time; time.sleep(1)
			log_f("[main] try again: flvInfo: 26:00")
			flvInfo= jk.getflv2(jkCh, start_ts+ 22* 60* 60, end_ts)
		return flvInfo


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
			raise GetFlvError(
				"[main] LoggedOut or Expired or OutsideServicePeriod: bad flv2 info 'user_id'"
			)

		def _getAM4Chunks():
			now= int( _prevAM4(dt.fromtimestamp(end_ts)).timestamp() )
			end= end_ts
			ORG_STDT= dt.fromtimestamp(start_ts)
			# 4時を超えているのに昨日のスレッドを取得してしまうのを防ぐ
			IS_NEAR_AM4= ORG_STDT.hour== 4 and ORG_STDT.minute== 0
			enumerator= this._enumeratorOf(
				this.DEFAULT_COUNTDOWN
				, IS_NEAR_AM4 or start_ts<= now
			)
			def go(e):
				e.set("no", enumerator(e))
				date= int(e.get("date"))
				return start_ts<= date and date<= end_ts
			flvInfo= {}
			if IS_NEAR_AM4 or start_ts<= now:
				while 1:
					log_f(f"[main] near AM4")
					log_f(f"[main] { dt.fromtimestamp(now) } -- { dt.fromtimestamp(end) }")
					flvInfo= this.getAM4FlvInfo(now, end)
					yield filter(go, _get1Day(now, end, flvInfo))
					end= now+ this.EXTRA_LOOKUP_SEC_FROM_AM4
					now= int( (dt.fromtimestamp(now)- td(1)).timestamp() )
					if not start_ts<= now:
						break
			now= start_ts
			lastFlvInfo= self.getflv2(jkCh, now, end)
			# 最後に先ほどと同じスレッドを取得しなかったならば
			if lastFlvInfo.get("start_time")!= flvInfo.get("start_time"):
				log_f(f"[main] { dt.fromtimestamp(now) } -- { dt.fromtimestamp(end) }")
				yield filter( go, _get1Day(now, end, lastFlvInfo) )

		def get():
			log_f(f"[main] start {jkCh}")
			for chunk in _getAM4Chunks():
				yield from chunk
			log_f(f"[main] end   {jkCh}, st: { dt.fromtimestamp(start_ts)}")

		_serialize= _vposSerializer(dt.fromtimestamp(start_ts))

		def _get1Day(start_ts, end_ts, flvInfo):
			if flvInfo.get('error'):
				raise GetFlvError(
					"[main] LoggedOut or Expired or OutsideServicePeriod: bad flv2 info"
				)
			wbkey= self.getwaybackkey(flvInfo["thread_id"])
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
					log_f(f"[main] try again: {type(exc).__name__, exc}")
				else:
					raise exc
				elems= tuple(
					e.attrib.update( _serialize(e) ) or e
					for e in reversed(packet.findall("chat"))
					if int(e.attrib["no"])< min_no
				)
				try:
					nomaxE= elems[0]; nominE= elems[-1]
				except IndexError:
					log_f(f"[main] break: Not found element")
					break
				if nomaxE is nominE:
					log_f(f"[main] final: chat len({len(elems)})")
					yield nominE
					break
				crntMaxNo= int( nomaxE.attrib["no"] )
				if (
					min_no!= float("inf")
					and crntMaxNo+ 1!= min_no
				):
					raise JKCommentError(f'[main] TruncatedComments: getmax={crntMaxNo}, crntmin={min_no}')
				min_no= int(nominE.attrib["no"])
				min_ts= (
					# min( int(e.attrib["date"]) for e in elems )
					int( nominE.attrib["date"] )
				)
				yield from elems

			log_f(f"[main] last min_no: {min_no}")

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

# alias
chName2JKMap= jkTable

