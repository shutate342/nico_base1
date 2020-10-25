# nico_base1

* 簡単でインタラクティブにも使えるニコニコ関連（予定）のコメント取得API


# Features

* 今のところ ニコニコ実況のコメントのみ
_要追加_

# Requirement

* Python 3. なんちゃら ぐらい (実行環境. 要インストール)
* beautifulsoup4 (package. "pip install beautifulsoup4" のコマンドを実行. )
( 大抵ググると情報有 )
( 見落としあったらすみません )


# Usage


```python
from nico_base1 import cal_syoboi as sy
from nico_base1.jkM import main_jk as main

# wanna view 'Hyouka'
title= sy.search("氷菓")[0]

# getCount(default) -> episode count
programs= sy.groupby(lambda e: e.getCount(None), title.programs)

# select episode 12 broadcasted on 'TOKYO MX'
program= sy.groupby(lambda e: e.chName, programs[12])["TOKYO MX"][0]

# jk: nico_base1.jk.main._JKAPI
jk= main.loginJK("your-address@example.com", "your-password")

# save comments as XML file
jk.syoboi(program).save(directory= ".")
```

このほかにもいろいろアプローチ有り
ドキュメンテーション・シグネチャも気持ち書いたのでﾄﾞｿﾞ

_要追加_


# Author

* shutate342

