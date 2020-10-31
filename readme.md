# nico_base1

* �ȒP�ŃC���^���N�e�B�u�ɂ��g����j�R�j�R�֘A�i�\��j�̃R�����g�擾API�i������j
* �ߏ�Ƀ��N�G�X�g�𑗂��ăT�[�o�[�ɕ��ׂ������邱�Ƃ̖����悤�ɂ��Ă��������B


# Features

* �j�R�j�R����
  * ��{�I�� [����ڂ��J�����_�[](https://cal.syoboi.jp/)(���̃T�C�g���肫�̎��� API �ł�) �̌������ʂ�  
    �u�������ԁv �̃y�[�WURL ���� �v�f��������ď]���Ă����Ɗy�ł���  
	��Ő�������悤�ɓ��t�w����ł��܂��B���Ȃ݂ɉߋ����O�̂ݑΉ��ł��B

* �j�R�j�R����
  * URL �Ȃǂ���R�����g���擾�A���t�w����\�ł��B���� Usage ���������������B
  * ���Ǝ擾�Ɏ��Ԃ�������(���掞�Ԃɔ��)�A�^�C���A�E�g�G���[�������������邱�Ƃɒ��ӂ��܂��傤�B
  * �C����������`�����l���̃����N���o�Ƃ����ǉ����邩���B

_�v�ǉ�_

# Requirement

* Python 3.7.0 �œ���m�F (���s��. �v�C���X�g�[��. ����܂�Â��Ȃ���Ηǂ��H)
* beautifulsoup4 (package. "pip install beautifulsoup4" �̃R�}���h�����s. )

( ���O�O��Ə��L )
( �����Ƃ��������炷�݂܂��� )


# Usage

## www.nicovideo.jp

```python
import nico_base1.nico_www as m

session= m.login("your-address@example.com", "your-password")

# want to get comments 'YagaKimi' episode 1
#     session.cmtsOf("https://www.nicovideo.jp/watch/1539138303")
#     session.cmtsOf(                        m.watch(1539138303))
cmts= session.cmtsOf("https://www.nicovideo.jp/watch/so33993109")

# cmts.getCrnt() -> bytes
# cmts.getCrnt(m.json.load) -> (JSON document to a Python object)
# cmts.getCrnt(cmts.CHATS) -> [xml.etree.ElementTree.Element]
elems= cmts.getAt(m.dt(2018,10,15,14,35), cmts.CHATS)

# example: use elems
# len([e for e in elems if e.get("deleted")])
# -> count current deleted comments
# elems= [e for e in elems if not ("TDN" in e.text or "�s�c�m" in e.text)]
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
```


## jk.nicovideo.jp

```python
from nico_base1 import cal_syoboi as sy
from nico_base1.jkM import main_jk as main

# wanna view 'Hyouka'
title= sy.search("�X��")[0]

# getCount(default) -> episode count
programs= sy.groupby(lambda e: e.getCount(None), title.programs)

# select episode 12 broadcasted on 'TOKYO MX'
program= sy.groupby(lambda e: e.chName, programs[12])["TOKYO MX"][0]

# jk: main._JKAPI
jk= main.loginJK("your-address@example.com", "your-password")

# save comments as XML file
jk.syoboi(program).save(directory= ".")
```

���̂ق��ɂ����낢��A�v���[�`�L��
```python
jk.syoboi( main.programOf("NHK ����", sy.dt(2020,1,1), 30) ).server
jk.syoboi( main.programOf("jk1"     , sy.dt(2020,1,1), 30) ).server
jk.syoboi( main.programOf(1         , sy.dt(2020,1,1), 30) ).server
# option
jk.dt2Log(            "jk1", sy.dt(2020,1,1), sy.td(minutes= 30))
jk.getLog(            "jk1", 1577804400, 1577804400+ 60*30)
main.jkM.CmtsIter(jk, "jk1", 1577804400, 1577804400+ 60*30)
```
������ ������������R�����g���e�� CmtsIter ��Ԃ��A�͂� (NHK, 2020/1/1 0������ 30����)


�h�L�������e�[�V�����E�V�O�l�`�����C�����������̂��޿�

_�v�ǉ�_


# ToDo

* ���̃j�R�j�R�T�[�r�XAPI���ǉ�����

# Author

* shutate342

