# nico_base1

* 簡単でインタラクティブにも使えるニコニコ関連（予定）のコメント取得API（非公式）
* 過剰にリクエストを送ってサーバーに負荷をかけることの無いようにしてください。


# Features

* ニコニコ実況
  * 基本的に [しょぼいカレンダー](https://cal.syoboi.jp/)(このサイトありきの実況 API です) の検索結果や  
    「放送時間」 のページURL から 要素をもらって従っていくと楽ですが  
	後で説明するように日付指定もできます。ちなみに過去ログのみ対応です。

* ニコニコ動画
  * URL などからコメントを取得、日付指定も可能です。下の Usage をご覧ください。
  * 割と取得に時間がかかる(動画時間に比例)、タイムアウトエラーが少し発生することに注意しましょう。
  * 気が向いたらチャンネルのリンク抽出とかも追加するかも。

_要追加_

# Requirement

* Python 3.7.0 で動作確認 (実行環境. 要インストール. あんまり古くなければ良い？)
* beautifulsoup4 (package. "pip install beautifulsoup4" のコマンドを実行. )

( 大抵ググると情報有 )
( 見落としあったらすみません )


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
# elems= [e for e in elems if not ("TDN" in e.text or "ＴＤＮ" in e.text)]
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

* 他のニコニコサービスAPIも追加する

# Author

* shutate342

