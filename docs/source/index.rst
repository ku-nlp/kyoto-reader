.. kyoto-reader documentation master file, created by
   sphinx-quickstart on Thu Feb 13 17:17:28 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===================================================
kyoto-reader: A processor for KWDLC and KyotoCorpus
===================================================


About
========================

京都大学ウェブ文書リードコーパス (KWDLC_) や京都大学テキストコーパス (KyotoCorpus_) をパースし、
述語項構造や共参照関係を扱うためのインターフェースを提供します。
このツールは pyknp のラッパーであるため、形態素情報や係り受け関係なども扱うことが可能です。

.. _KWDLC: https://github.com/ku-nlp/KWDLC
.. _KyotoCorpus: https://github.com/ku-nlp/KyotoCorpus


Requirements
========================

- Python
    -  Verified Versions: 3.7, 3.8, 3.9
- `pyknp 0.4.5`_
- KNP (optional)
- JumanDIC_ (optional)

.. _`pyknp 0.4.5`: https://github.com/ku-nlp/pyknp
.. _JumanDIC: https://github.com/ku-nlp/JumanDIC


Install kyoto-reader
========================

.. code-block:: bash

    $ pip install kyoto-reader

or

.. code-block:: bash

    $ git clone https://github.com/ku-nlp/kyoto-reader
    $ cd kyoto-reader
    $ python setup.py install [--prefix=path]


A Brief Explanation of KWDLC/KyotoCorpus
================================================

| KWDLC と KyotoCorpus はどちらも日本語の文書に対して形態素や構文情報の他、述語項構造や共参照関係が人手で付与されたコーパス。
| KWDLC はウェブから抽出した3文を1文書として約5,000文書に対してアノテーションされている。
| KyotoCorpus は毎日新聞の記事を対象に、形態素・構文情報については 40,000 文に、述語項構造・共参照関係についてはそのうちの 10,000 文にアノテーションされている。
| なお、述語項構造・共参照関係のアノテーションは ``<rel>`` タグによって行われている。

KWDLC の例:

.. code-block:: none

   # S-ID:w201106-0000060050-1 JUMAN:6.1-20101108 KNP:3.1-20101107 DATE:2011/06/21 SCORE:-44.94406 MOD:2017/10/15 MEMO:
   * 2D
   + 1D
   コイン こいん コイン 名詞 6 普通名詞 1 * 0 * 0
   + 3D <rel type="ガ" target="不特定:人"/><rel type="ヲ" target="コイン" sid="w201106-0000060050-1" id="0"/>
   トス とす トス 名詞 6 サ変名詞 2 * 0 * 0
   を を を 助詞 9 格助詞 1 * 0 * 0
   * 2D
   + 3D
   ３ さん ３ 名詞 6 数詞 7 * 0 * 0
   回 かい 回 接尾辞 14 名詞性名詞助数辞 3 * 0 * 0
   * -1D
   + -1D <rel type="ガ" target="不特定:人"/><rel type="ガ" mode="？" target="読者"/><rel type="ガ" mode="？" target="著者"/><rel type="ヲ" target="トス" sid="w201106-0000060050-1" id="1"/>
   行う おこなう 行う 動詞 2 * 0 子音動詞ワ行 12 基本形 2
   。 。 。 特殊 1 句点 1 * 0 * 0
   EOS


Usage
========================

上記の例のデータが入ったファイル ``w201106-0000060050.knp`` を読み込む場合

.. code-block:: python

   from pathlib import Path
   from typing import List
   from kyoto_reader import KyotoReader, Document, Predicate

   # 文書集合を扱うオブジェクト
   reader = KyotoReader(Path('w201106-0000060050.knp'),  # ファイルまたはディレクトリを Path オブジェクトで指定する
                        target_cases=['ガ', 'ヲ', 'ニ'],  # ガ,ヲ,ニ格のみを対象とする
                        target_corefs=['=', '=構', '=≒', '=構≒'],  # 共参照として扱う関係を列挙
                        extract_nes=True  # 固有表現もコーパスから抽出する
                        )
   print('読み込んだ文書:')
   for doc_id in reader.doc_ids:
       print(f'  文書ID: {doc_id}')

   print('\n--- 述語項構造 ---')
   document: Document = reader.process_document('w201106-0000060050')
   for predicate in document.get_predicates():
       print(f'述語: {predicate.midasi}')
       for case, arguments in document.get_arguments(predicate).items():
           print(f'  {case}格: ', end='')
           print(', '.join(argument.midasi for argument in arguments))

   print('\n--- ツリー形式 ---')
   document.draw_tree(sid='w201106-0000060050-1', coreference=False)

プログラムの出力結果

.. code-block:: none

   読み込んだ文書:
     文書ID: w201106-0000060050

   --- 述語項構造 ---
   述語: トス
     ガ格: 不特定:人
     ヲ格: コイン
     ニ格:
   述語: 行う
     ガ格: 不特定:人, 読者, 著者
     ヲ格: トス
     ニ格:

   --- ツリー形式 ---
   コインn┐
    トスnをp─┐  不特定:人:ガ コイン:ヲ :ニ
        ３n回s┤
        行うv。*  不特定:人,著者,読者:ガ トス:ヲ :ニ


CLI Interfaces
========================

``kyoto`` コマンドを使用することで、CLI から一部機能を使用することができる。

- KNP ファイルの内容をツリー形式で表示 (ディレクトリを指定した場合、含まれる全てのファイルを表示)

.. code-block:: bash

   $ kyoto show /path/to/knp/file.knp

- 指定されたディレクトリに含まれる文書ID を列挙

.. code-block:: bash

   $ kyoto list /path/to/knp/directory


Corpus Preprocessor
========================

Makefile を使用してコーパスに追加の素性を付与することができる (KNP と JumanDIC が必要)。

- 以下のコマンドを実行することでコーパスのディレクトリに Makefile が生成される。

.. code-block:: bash

   $ kyoto configure --corpus-dir /path/to/downloaded/knp/directory --data-dir /path/to/output/directory --juman-dic-dir /path/to/JumanDIC/directory
   created Makefile at /path/to/output/directory

- 生成された Makefile を実行することで、コーパスが1文書1ファイルに分割され、 ``knp/`` ディレクトリに素性の付与されたファイルが出力される。

.. code-block:: bash

   $ cd /path/to/output/directory
   $ make -i

``idsplit`` コマンドを使用してコーパスを train/dev/test ファイルに分割することができる。

.. code-block:: bash

   $ kyoto idsplit --corpus-dir /path/to/knp/dir --output-dir /path/to/output/dir --train /path/to/train/id/file --dev /path/to/dev/id/file --test /path/to/test/id/file

Documents
============
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   kyoto_reader
   kyoto_reader.reader
   kyoto_reader.sentence
   kyoto_reader.base_phrase
   kyoto_reader.pas
   kyoto_reader.coreference
   kyoto_reader.ne


Author/Contact
========================
京都大学 黒橋・河原研究室 (contact **at** nlp.ist.i.kyoto-u.ac.jp)

- Nobuhiro Ueda


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
