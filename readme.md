# nico_base1

* �ȒP�ŃC���^���N�e�B�u�ɂ��g����j�R�j�R�֘A�i�\��j�̃R�����g�擾API


# Features

* ���̂Ƃ��� �j�R�j�R�����̃R�����g�̂�
  * ��{�I�� [����ڂ��J�����_�[](https://cal.syoboi.jp/)(���̃T�C�g���肫�̎��� API �ł�) �̌������ʂ�  
    �u�������ԁv �̃y�[�WURL ���� �v�f��������ď]���Ă����Ɗy�ł���  
	��Ő�������悤�ɓ��t�w����ł��܂��B���Ȃ݂ɉߋ����O�̂ݑΉ��ł��B

_�v�ǉ�_

# Requirement

* Python 3.7.0 �œ���m�F (���s��. �v�C���X�g�[��. ����܂�Â��Ȃ���Ηǂ��H)
* beautifulsoup4 (package. "pip install beautifulsoup4" �̃R�}���h�����s. )

( ���O�O��Ə��L )
( �����Ƃ��������炷�݂܂��� )


# Usage


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

* ���O�C�����s�킩�肸�炢 (�擾���� RuntimeError �ł킩�銴��)
* jkM.jkTable �S�����낦��
* ���̃j�R�j�R�T�[�r�XAPI���ǉ�����

# Author

* shutate342

