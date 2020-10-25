# nico_base1

* �ȒP�ŃC���^���N�e�B�u�ɂ��g����j�R�j�R�֘A�i�\��j�̃R�����g�擾API


# Features

* ���̂Ƃ��� �j�R�j�R�����̃R�����g�̂�
_�v�ǉ�_

# Requirement

* Python 3. �Ȃ񂿂�� ���炢 (���s��. �v�C���X�g�[��)
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

# jk: nico_base1.jk.main._JKAPI
jk= main.loginJK("your-address@example.com", "your-password")

# save comments as XML file
jk.syoboi(program).save(directory= ".")
```

���̂ق��ɂ����낢��A�v���[�`�L��
�h�L�������e�[�V�����E�V�O�l�`�����C�����������̂��޿�

_�v�ǉ�_


# Author

* shutate342

