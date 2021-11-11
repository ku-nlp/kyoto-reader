.. kyoto-reader documentation master file, created by
   sphinx-quickstart on Thu Feb 13 17:17:28 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=========================================================================
kyoto-reader: A processor for KWDLC, KyotoCorpus, and AnnotatedFKCCorpus
=========================================================================


About
========================

京都大学が公開している述語項構造や共参照関係が付与されたコーパスをパースし、Python から扱うためのインターフェースを提供します。
このツールは pyknp のラッパーであるため、形態素情報や係り受け関係なども扱うことが可能です。

.. list-table:: 利用可能なコーパス一覧
    :widths: 30 20 10
    :header-rows: 1

    * - Name
      - Domain
      - Size
    * - 京都大学ウェブ文書リードコーパス_ (KWDLC)
      - ウェブテキスト
      - 16,038 文
    * - 京都大学テキストコーパス_ (KyotoCorpus)
      - 新聞記事・社説
      - 15,872 文
    * - 不満調査データセットタグ付きコーパス_ (AnnotatedFKCCorpus)
      - 不満に関する投稿
      - 1,282 文

.. _京都大学ウェブ文書リードコーパス: https://github.com/ku-nlp/KWDLC
.. _京都大学テキストコーパス: https://github.com/ku-nlp/KyotoCorpus
.. _不満調査データセットタグ付きコーパス: https://github.com/ku-nlp/AnnotatedFKCCorpus

Requirements
========================

- Python
    -  Verified Versions: 3.7, 3.8, 3.9, 3.10
- `pyknp 0.4.6+`_
- KNP_ (optional)
- JumanDIC_ (optional)

.. _`pyknp 0.4.6+`: https://github.com/ku-nlp/pyknp
.. _KNP: https://github.com/ku-nlp/knp
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


A Brief Explanation of KWDLC and other corpora
================================================

| KWDLC, KyotoCorpus, AnnotatedFKCCorpus はいずれも日本語の文書に対して形態素や構文情報の他、述語項構造や共参照関係が人手で付与されたコーパス。
| KWDLC はウェブから抽出した 3 文を 1 文書として約 5,000 文書に対してアノテーションされている。
| KyotoCorpus は毎日新聞の記事を対象に、形態素・構文情報については 40,000 文に、述語項構造・共参照関係についてはそのうちの約 10,000 文にアノテーションされている。
| AnnotatedFKCCorpus は一般の人々から集められた不満テキスト約 1,300 文に対してアノテーションを行ったコーパスである。
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

   from kyoto_reader import KyotoReader, Document

   # 文書集合を扱うオブジェクト
   reader = KyotoReader('w201106-0000060050.knp',  # ファイルまたはディレクトリのパスを指定する
                        target_cases=['ガ', 'ヲ', 'ニ'],  # ガ,ヲ,ニ格のみを対象とする
                        target_corefs=['=', '=構', '=≒', '=構≒'],  # 共参照として扱う関係を列挙
                        extract_nes=True  # 固有表現もコーパスから抽出する
                        )
   print('読み込んだ文書:')
   for doc_id in reader.doc_ids:
       print(f'  文書 ID: {doc_id}')

   print('\n--- 述語項構造 ---')
   document: Document = reader.process_document('w201106-0000060050')
   for predicate in document.get_predicates():
       print(f'述語: {predicate.core}')
       for case, arguments in document.get_arguments(predicate).items():
           print(f'  {case}格: ', end='')
           print(', '.join(str(argument) for argument in arguments))

   print('\n--- ツリー形式 ---')
   document.draw_tree(sid='w201106-0000060050-1', coreference=False)

プログラムの出力結果

.. code-block:: none

   読み込んだ文書:
     文書 ID: w201106-0000060050

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
   コイン┐
     トスを─┐  ガ:不特定:人 ヲ:コイン
         ３回┤
         行う。  ガ:読者,不特定:人,著者 ヲ:トス


CLI Interfaces
========================

``kyoto`` コマンドを使用することで、コーパスの内容を表示したりコーパスを加工したりできる。

Browsing files
------------------------

- ``kyoto show``: KNP ファイルの内容をツリー形式で表示 (ディレクトリを指定した場合、含まれる全てのファイルを表示)

.. code-block:: bash

   $ kyoto show /path/to/knp/file.knp

- ``kyoto list``: 指定されたディレクトリに含まれる文書 ID を列挙

.. code-block:: bash

   $ kyoto list /path/to/knp/directory

Processing Corpus
------------------------

コーパスを解析し、追加の素性を付与 (KNP と JumanDIC が必要)

- ``kyoto configure``: コーパスのディレクトリに素性付与のための Makefile を生成

  - ``make`` を実行することで、コーパスが 1 文書 1 ファイルに分割され、 ``knp/`` ディレクトリに素性の付与されたファイルが出力される。

.. code-block:: bash

   $ kyoto configure --corpus-dir /path/to/downloaded/knp/directory --data-dir /path/to/output/directory --juman-dic-dir /path/to/JumanDIC/directory
   created Makefile at /path/to/output/directory
   $ cd /path/to/output/directory
   $ make -j <num-parallel>

- ``kyoto idsplit``: コーパスを train/dev/test ファイルに分割

.. code-block:: bash

   $ kyoto idsplit --corpus-dir /path/to/knp/dir --output-dir /path/to/output/dir --train /path/to/train/id/file --dev /path/to/dev/id/file --test /path/to/test/id/file

Zsh Completions
------------------------

``<virtualenv-path>/share/zsh/site-functions`` を ``FPATH`` に追加することで ``kyoto`` コマンドの補完が可能 (zsh 限定)

.. code-block:: bash

   $ echo 'export FPATH=<virtualenv-path>/share/zsh/site-functions:$FPATH' >> ~/.zshrc

Documents
============
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   kyoto_reader
   kyoto_reader.reader
   kyoto_reader.document
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
