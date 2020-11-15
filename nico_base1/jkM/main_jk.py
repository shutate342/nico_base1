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
	���[�U�[�̂��߂� sy._Program �쐬���\�b�h

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
	��� save ���\�b�h�ŃR�����g��ۑ�����N���X�ł��B
	server ������ �R�����g�C�e���[�^�ɃA�N�Z�X�ł��܂��B

	* ���̃N���X�ł̓R�����g�������^�C�~���O (vpos) ��
		�J�n������ 0 �ɂȂ�悤�f�t�H���g�Œ�������Ă��܂�
		���f�[�^�͖����S������ɂȂ��Ă��܂�
		�R�����g�C�e���[�^���璼�ڗv�f���擾����ۂ͒��ӂ��Ă�������
		�𗧂֐�: jkM.vposdiffAt
			shiftFWer(
				jkM.vposdiffAt( jkM.dt.fromtimestamp(timestamp: int) )
			) ��
			element �� �}�b�v����֐����ł��܂�

	�R�����g�C�e���[�^����ۑ�:
		.�R�����g�������܂�ɂ������Ȃ����
			jkM.elems2ETree �֐����g�p��A
			write ���\�b�h�����p�ł��܂�
		.��L�̕��@�̓���������������̂�
			_Sink �I�u�W�F�N�g�Ȃ���S�ł�
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
	�e�탁�\�b�h���g���ăR�����g���擾���܂�
	"""

	syoboi= SyoboiCmts.of

	def stat(jk, prog: sy._Program) -> SyoboiCmts:
		"""
		�t�@�C���̍Ō��
		�v���C���A�R�����g�ő啪���Ȃǂ̏���t������
		SyoboiCmts ��Ԃ��܂��B
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
			datetime �� timedelta �ɂ����Ԃ��w��ł��܂�
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
	# e�e���̃}���`�Ґ��H�����ɂ��Ă��܂���
	, "64": "jk2", "65": "jk2"
# kbs
	, "36": "jk1143"
# NHK���W�I��1
	, "49": "jk594"
	# NHK���W�I��2
	, "195": "jk693"
	# ���W�Inikkei
	, "218": "jk3925"
# inter fm
	, "180": "jk761"
# tokyo fm
	, "162": "jk800"
# tbs
	, "53": "jk954"
	# ��������
	, "41": "jk1134"
# �j�b�|��
	, "30": "jk1242"
# bayfm
	, "166": "jk780"
# nack5
	, "188": "jk795"
# ���R�n�}
	, "190": "jk847"
# ���W�I���{
	, "191": "jk1422"
# zip-fm
	, "184": "jk778"
# fm aichi
	, "186": "jk807"
# �������{�����Ń��W�I�������J�n -> cbc���W�I
	, "183": "jk1053"
# ���C
	, "139": "jk1332"
# radio cube fm�O�d
	, "185": "jk789"
# �������� == ABC���W�I
	, "38": "jk1008"
# �������� == MBS���W�I
	, "134": "jk1179"
# ���
	, "35": "jk1314"
# ���W�I�֐�
	, "133": "jk558"
	# NHKBS-1
	, "9": "jk101"
	# OK: , "71": "jk141"
	# BS�W���p��
	, "15": "jk171"
	# �X�^�[
	, "217": "jk200", "219": "jk201", "214": "jk202"
	# twellv
	, "129": "jk222"
	# ������w bs or cs?: ������wCS�e���r
	, "158": "jk231"
	# BS�X�J�p�[!
	, "196": "jk241"
	# ���{�f����`�����l��
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
