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
	vpos �͖��� 4 ������ɍX�V����܂��B
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
		"res_from �� -1000 ��菬�����Ă��Ӗ��Ȃ��H"
		URL= (
			f"http://{host}/api/thread?thread={ thread_id }"
			f"&res_from={ res_from }&version=20061206&when={when}&user_id={user_id}"
			f"&waybackkey={ waybackkey }&scores=1"
		)
		with self.openTO(URL) as resp:
			return resp.read().decode(_MAGIC("utf_8"))


class CmtsIter:
	"""
	response �� no �̏��Ԃɏ]���Ă��邱�ƂɈˑ�
	date �� date_usec �𖳎�����Ώ��Ԃɏ]���Ă���
	vpos �͏��Ԃǂ���ł͂Ȃ��B�R�����g���M���Ԃ̂��ꂪ��������Ă���H
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
					# �����厖
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
	"�P�b�Ԃ� 256 �R���ȏ゠��ƃI�[�o�[�t���[���܂�"

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

	1   =NHK ���� 
	2   =E�e��
	4   =���{�e���r
	5   =�e���r����
	6   =TBS �e���r
	6   =TBS
	7   =�e���r����
	8   =�t�W�e���r
	9   =TOKYO MX
	10  =�e����
	11  =tvk
	12  =�`�o�e���r


	594 =NHK���W�I��1
	693 =NHK���W�I��2
	825 =NHK-FM
	792 =AIR-G'
	1287=HBC���W�I
	1440=STV���W�I
	3925=���W�INIKKEI��1����
	761 =Inter FM
	800 =TOKYO FM
	813 =J-WAVE
	954 =TBS���W�I
	1134=��������
	1197=������
	1242=�j�b�|������
	764 =RADIO BERRY
	863 =FM�����
	780 =bayfm
	795 =NACK5
	847 =FM���R�n�}
	1422=���W�I���{
	778 =ZIP-FM
	807 =FM AICHI
	1053=CBC���W�I
	1332=���C���W�I
	1431=���Ӄ`����
	789 =radio CUBE FM�O�d
	765 =FM COCOLO
	802 =FM802
	851 =FM OSAKA
	899 =Kiss FM KOBE
	1008=��������
	1179=��������
	1314=���W�I���
	1143=KBS���s
	558 =���W�I�֐�
	1557=�a�̎R����
	808 =FM FUKUOKA
	827 =Love FM
	1278=RKB���W�I
	1413=��B��������


	101 =NHKBS-1
	103 =NHK BS�v���~�A��
	141 =BS ���e��
	141 =BS���e��
	151 =BS ����
	151 =BS����
	161 =BS-TBS
	171 =BS�W���p��
	181 =BS�t�W
	191 =WOWOW�v���C�� 
	192 =WOWOW���C�u 
	193 =WOWOW�V�l�}

	200 =�X�^�[�`�����l��1
	201 =�X�^�[�`�����l��2
	202 =�X�^�[�`�����l��3

	211 =BS�C���u��
	211 =BS11�C���u��

	222 =TwellV
	231 =������w
	234 =BS�O���[���`�����l��
	236 =BS�A�j�}�b�N�X
	238 =FOX bs 238
	241 =BS�X�J�p�[!
	242 =J Sports 1
	243 =J Sports 2
	244 =J Sports 3
	245 =J Sports 4
	251 =BS�ނ�r�W����
	252 =IMAGICA BS
	255 =BS���{�f����`�����l�� 
	256 =�f�B�Y�j�[�E�`�����l��
	258 =Dlife
	910 =SOLiVE24
 
""".split("\n") if s and not s.isspace() )

