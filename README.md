# kyoto-reader: Parser for KWDLC and KyotoCorpus

京都大学ウェブ文書リードコーパス ([KWDLC](https://github.com/ku-nlp/KWDLC))
および京都大学テキストコーパス ([KyotoCorpus](https://github.com/ku-nlp/KyotoCorpus)) のパーサー。  
コーパス文書中から形態素・係り受け関係・述語項構造・共参照関係・固有表現情報を抽出します。

## Requirements

- Python 3.6, 3.7, 3.8
- [pyknp](https://github.com/ku-nlp/pyknp) 0.4.1
- KNP 4.2 (optinal)
- [JumanDIC](https://github.com/ku-nlp/JumanDIC) (optional)

## Installation

```zsh
$ pip install kyoto-reader
```

or

```zsh
$ git clone https://github.com/ku-nlp/kyoto-reader
$ cd kyoto-reader
$ python setup.py install [--prefix=path]
```

## Documents

<https://kyoto-reader.readthedocs.io/en/latest/>

## Authors/Contact

京都大学 黒橋・河原研究室 (contact **at** nlp.ist.i.kyoto-u.ac.jp)

- Nobuhiro Ueda <ueda **at** nlp.ist.i.kyoto-u.ac.jp>
