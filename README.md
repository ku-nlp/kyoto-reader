# kyoto-reader: A processor for KWDLC, KyotoCorpus, and AnnotatedFKCCorpus

![License](http://img.shields.io/badge/license-MIT-blue.svg)
[![Python 3.7,3.8,3.9,3.10](https://github.com/ku-nlp/kyoto-reader/actions/workflows/pythonpackage.yml/badge.svg)](https://github.com/ku-nlp/kyoto-reader/actions/workflows/pythonpackage.yml)
[![Python Versions](https://img.shields.io/pypi/pyversions/kyoto_reader.svg)](https://pypi.org/project/kyoto-reader/)

以下のコーパスから形態素・係り受け関係・述語項構造・共参照関係・固有表現情報を抽出し、Pythonから扱うためのインターフェースを提供します。 

- 京都大学ウェブ文書リードコーパス ([KWDLC](https://github.com/ku-nlp/KWDLC))
- 京都大学テキストコーパス ([KyotoCorpus](https://github.com/ku-nlp/KyotoCorpus))
- 不満調査データセットタグ付きコーパス ([AnnotatedFKCCorpus](https://github.com/ku-nlp/AnnotatedFKCCorpus))

## Requirements

- Python 3.7.2+
- [pyknp](https://github.com/ku-nlp/pyknp) 0.4.6+
- [KNP](http://nlp.ist.i.kyoto-u.ac.jp/index.php?KNP) 5.0+ (optional)
- [JumanDIC](https://github.com/ku-nlp/JumanDIC) (optional)

## Installation

```zsh
$ pip install kyoto-reader
```

## Documents

<https://kyoto-reader.readthedocs.io/en/latest/>

## Authors/Contact

京都大学 黒橋・褚・村脇研究室 (contact **at** nlp.ist.i.kyoto-u.ac.jp)
- Nobuhiro Ueda <ueda **at** nlp.ist.i.kyoto-u.ac.jp>
