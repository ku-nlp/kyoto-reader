# kyoto-reader: A processor for KWDLC, KyotoCorpus, and AnnotatedFKCCorpus

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

京都大学 黒橋・村脇研究室 (contact **at** nlp.ist.i.kyoto-u.ac.jp)

- Nobuhiro Ueda <ueda **at** nlp.ist.i.kyoto-u.ac.jp>
