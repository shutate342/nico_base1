# nico_base1

* 簡単でインタラクティブにも使えるニコニコ関連（予定）のコメント取得API


# Features

* 今のところ ニコニコ実況のコメントのみ
  * 基本的に [しょぼいカレンダー](https://cal.syoboi.jp/)(このサイトありきの実況 API です) の検索結果や  
    「放送時間」 のページURL から 要素をもらって従っていくと楽ですが  
	後で説明するように日付指定もできます。ちなみに過去ログのみ対応です。

_要追加_

# Requirement

* Python 3.7.0 で動作確認 (実行環境. 要インストール. あんまり古くなければ良い？)
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

# jk: main._JKAPI
jk= main.loginJK("your-address@example.com", "your-password")

# save comments as XML file
jk.syoboi(program).save(directory= ".")
```

このほかにもいろいろアプローチ有り
```python
jk.syoboi( main.programOf("NHK 総合", sy.dt(2020,1,1), 30) ).server
jk.syoboi( main.programOf("jk1"     , sy.dt(2020,1,1), 30) ).server
jk.syoboi( main.programOf(1         , sy.dt(2020,1,1), 30) ).server
# option
jk.dt2Log(            "jk1", sy.dt(2020,1,1), sy.td(minutes= 30))
jk.getLog(            "jk1", 1577804400, 1577804400+ 60*30)
main.jkM.CmtsIter(jk, "jk1", 1577804400, 1577804400+ 60*30)
```
これらは いずれも同じコメント内容の CmtsIter を返す、はず (NHK, 2020/1/1 0時から 30分間)


ドキュメンテーション・シグネチャも気持ち書いたのでﾄﾞｿﾞ

_要追加_

# ToDo

* ログイン失敗わかりずらい (取得時の RuntimeError でわかる感じ)
* jkM.jkTable 全部そろえる
* 他のニコニコサービスAPIも追加する

# Author

* shutate342

