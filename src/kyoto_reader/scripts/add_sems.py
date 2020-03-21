# Jumanの意味情報がついていない昔のコーパスに意味情報を付加するプログラム

# https://bitbucket.org/ku_nlp/anaphora-test/src/master/scripts/add-imis.perl の Python 実装

# 晩 ばん 晩 名詞 6 時相名詞 10 * 0 * 0
#
#        ↓↓↓↓↓
#
# 晩 ばん 晩 名詞 6 時相名詞 10 * 0 * 0 "漢字読み:音 代表表記:晩/ばん"

# usage:
# python add-sems.py --dic-dir /somewhere/juman/dic -i /somewhere/without/sems.knp -o /somewhere/with/sems.knp2
# -i (--input-file) や -o (--output-file) を指定しなかれば std{in/out} が使用される

# 注意

# 昔の解析結果が現在の解析結果と異なっていることがある
# 例：プログラムの出力結果
# 使って つかって 使う 動詞 2 * 0 子音動詞ワ行 12 タ系連用テ形 11 "代表表記:使う/つかう"
# 現在のjumanの解析結果
# 使って つかって 使う 動詞 2 * 0 子音動詞ワ行 12 タ系連用テ形 12 "代表表記:使う/つかう"

# 入力の原形がひらがなの場合は入力の読みに一致する単語の中でJUMAN辞書で一番上にある単語の意味情報が付加される
# 例：入力が「あいしょう」のときは「愛唱」の意味情報が付加される (--pos オプションが付いている場合のみ。そうでなければ入力の細分類による)
# --remainder オプションを用いると、一番上以外の形態素を@行として出力する

# デフォルトでは、原形、品詞、品詞細分類を用いてマッチングを行う
# --pos オプションを用いると原形と品詞のみで照合する
# --yomi オプションを用いるとさらに読みも照合する(soft match)


import re
import sys
import argparse
from pathlib import Path
from typing import List, Union
from collections import defaultdict

from pyknp import Juman, JUMAN_FORMAT

from kyoto_reader.scripts.sexp import parse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', '-i', default=None, type=str,
                        help='path to input knp file')
    parser.add_argument('--output-file', '-o', default=None, type=str,
                        help='path to output knp file')
    parser.add_argument('--dic-dir', default=None, type=str,
                        help='path to directory where JumanDIC files exist')
    parser.add_argument('--dic-file', default=None, type=str,
                        help='path to JumanDIC file')
    # parser.add_argument('--use-autodic', default=None, type=str,
    #                     help='')
    parser.add_argument('--use-wikipediadic', action='store_true', default=False,
                        help='use dictionary obtained automatically from Wikipedia')
    parser.add_argument('--use-jumanpp', action='store_true', default=False,
                        help='add 代表表記 to all morpheme even if it does not exist in jumandic')
    parser.add_argument('--remainder', action='store_true', default=False,
                        help='output 意味情報 of other morphemes as well')
    parser.add_argument('--pos', action='store_true', default=False,
                        help='use only midasi and pos')
    parser.add_argument('--yomi', action='store_true', default=False,
                        help='use only midasi and pos and yomi')
    args = parser.parse_args()

    # Jumanの辞書の読み込み
    dicfiles: List[Path] = []
    if args.dic_dir:
        dicdir = Path(args.dic_dir)
        dicfiles += [file for file in dicdir.glob('*.dic') if file.name != 'Rengo.dic']

        # if args.use_autodic:
        #     dicfile = dicdir.parent / 'autodic' / 'Auto.dic'
        #     if dicfile.exists():
        #         dicfiles.append(dicfile)
        if args.use_wikipediadic:
            dicfiles += list((dicdir.parent / 'wikipediadic').glob('Wikipedia.dic*'))
    if args.dic_file:
        dicfiles.append(Path(args.dic_file))

    features = []
    for dicfile in dicfiles:
        with dicfile.open() as f:
            for line in f:
                feature = {}
                obj = parse(line.strip())
                if not obj:
                    continue
                pos, obj2 = obj[0]
                if pos == '連語':
                    continue
                feature['品詞'] = pos
                if isinstance(obj2[0], str):
                    pos2, feats = obj2
                    feature['品詞細分類'] = pos2
                else:
                    feats = obj2
                feature.update({k: v for k, *v in feats})
                if pos == '特殊' and pos2 == '空白':
                    feature['見出し語'] = ['　']
                    feature['読み'] = ['　']
                features.append(feature)

    sems_dic = defaultdict(list)
    for feature in features:
        pos: str = feature['品詞']
        pos2: str = feature.get('品詞細分類', '')
        midasis: List[Union[str, list]] = feature['見出し語']
        yomi: str = feature['読み'][0]
        sem: str = feature['意味情報'][0].strip('"')
        if not sem:
            continue

        for midasi in midasis:
            if isinstance(midasi, list):
                assert len(midasi) == 2
                midasi = midasi[0]
            key = (midasi, pos)
            if args.pos is False and pos2:
                key += (pos2,)
            sems_dic[key].append(sem)
            if args.yomi:
                key += (yomi,)
                sems_dic[key].append(sem)

    with open(args.input_file, mode='rt') if args.input_file else sys.stdin as fin:
        with open(args.output_file, mode='wt') if args.output_file else sys.stdout as fout:
            for line in fin:
                fout.write(add_sems(line, sems_dic, args))


def add_sems(input_line: str, sems_dic, args):
    if input_line[0] in ('#', '*', '+') or input_line.strip() == 'EOS':
        return input_line

    _, yomi, genkei, pos, _, pos2, _, _, _, _, _, *sems = input_line.strip().split()
    if sems:
        org_sem: str = sems[0].strip('"')
    else:
        org_sem: str = ''
    key = (genkei, pos)
    if args.pos is False and pos2 != '*':
        key += (pos2,)
    key_yomi = key + (yomi,)

    # 意味情報の手前まで
    newline: str = ' '.join(input_line.split()[:11])
    output_line = newline

    if args.yomi and key_yomi in sems_dic:
        key = key_yomi

    if key in sems_dic:
        first_sem: str = sems_dic[key][0]  # 該当する形態素のうち JumanDIC で最初にヒットしたものの意味情報を採用
        # jumanpp を使って代表表記を得る
        if args.use_jumanpp and '代表表記' not in first_sem:
            repname = get_repname_using_jumanpp(genkei, pos)
            first_sem = f'代表表記:{repname} ' + first_sem

        output_line += f' "{first_sem}'

        match = re.match(r'(NE:\S+?)[ "]', org_sem)
        if match:
            output_line += ' ' + match.group(1)
        output_line += '"\n'

        # 1つ目以外の形態素候補を@行として表示する場合
        if args.remainder:
            for sem in sems_dic[key][1:]:
                output_line += f'@ {newline} "{sem}"\n'
    else:
        # jumanpp を使って代表表記を得る
        if args.use_jumanpp and '代表表記' not in org_sem:
            repname = get_repname_using_jumanpp(genkei, pos)
            sem = f'代表表記:{repname}' + (f' {org_sem}' if org_sem else '')
            output_line += f' "{sem}"\n'
        else:
            output_line += f' "{org_sem}"\n' if org_sem else '\n'

    return output_line


def get_repname_using_jumanpp(genkei: str, pos: str) -> str:
    if pos == '助詞':
        return f'{genkei}/{genkei}'

    juman = Juman(option='-s 1')
    mrphs = juman.analysis(genkei, juman_format=JUMAN_FORMAT.LATTICE_TOP_ONE)
    # 形態素解析が誤っていないか(=1形態素になっているか)をチェック
    if len(mrphs) == 1:
        return mrphs[0].repname

    return f'{genkei}/{genkei}'


if __name__ == '__main__':
    main()
