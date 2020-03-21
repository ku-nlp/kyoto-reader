# Jumanの意味情報がついていない昔のコーパスに意味情報を付加するプログラム

# by harashima (06/08/22)
# modified by shibata (06/09/06)

# 晩 ばん 晩 名詞 6 時相名詞 10 * 0 * 0
#
#        ↓↓↓↓↓
#
# 晩 ばん 晩 名詞 6 時相名詞 10 * 0 * 0 "漢字読み:音 代表表記:晩/ばん"

# usage:
# perl add-imis.pl --dir /some/where/juman/dic 2002_10_17.in
# (一括処理の場合) perl add-imis.pl --dir /some/where/juman/dic -inext knp2 -outext knp

# --dirでContentW.dicの場所を指定
# JumanLib.pmが必要

# 注意

# 昔の解析結果が現在の解析結果と異なっていることがある
# 例：プログラムの出力結果
# 使って つかって 使う 動詞 2 * 0 子音動詞ワ行 12 タ系連用テ形 11 "代表表記:使う/つかう"
# 現在のjumanの解析結果
# 使って つかって 使う 動詞 2 * 0 子音動詞ワ行 12 タ系連用テ形 12 "代表表記:使う/つかう"

# 入力の原形がひらがなの場合は入力の読みに一致する単語の中でJUMAN辞書で一番上にある単語の意味情報が付加される
# 例：入力が「あいしょう」のときは「愛唱」の意味情報が付加される (--pos オプションが付いている場合。そうでなければ細分類も見るので)
# --remainderオプションを用いると、一番上以外の形態素を@行として出力する

# デフォルトでは、表記、品詞、品詞細分類を用いてマッチングを行う
# --posオプションを用いると表記と品詞のみで照合する
# --yomiオプションを用いるとさらに読みも照合する(soft match)


import argparse
from pathlib import Path
from typing import List, Union
from collections import defaultdict
import re

from pyknp import Juman

from kyoto_reader.scripts.sexp import parse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', default='.', type=str,
                        help='path to directory where input files exist')
    parser.add_argument('--output-dir', default='.', type=str,
                        help='path to directory where output files are exported')
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
    parser.add_argument('--remainder', default=None, type=str,
                        help='')
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
                feature['品詞'] = pos
                if isinstance(obj2[0], str):
                    pos2, feats = obj2
                    feature['品詞細分類'] = pos2
                else:
                    feats = obj2
                feature.update({k: v for k, *v in feats})
                features.append(feature)

    rep2imis = defaultdict(list)
    for feature in features:
        midasis: List[Union[str, list]] = feature['見出し語']
        yomi: str = feature['読み'][0]
        hinsi: str = feature['品詞']
        hinsi_bunrui: str = feature.get('品詞細分類', '')
        imi: str = feature['意味情報'][0].strip('"')
        if not imi:
            continue

        for midasi in midasis:
            if isinstance(midasi, list):
                assert len(midasi) == 2
                midasi = midasi[0]
            rep = (midasi, hinsi)
            if args.pos is False and hinsi_bunrui:
                rep += (hinsi_bunrui,)
            rep2imis[rep].append(imi)
            if args.yomi:
                rep += (yomi,)
                rep2imis[rep].append(imi)
            # print(rep)

    for input_file in Path(args.input_dir).glob('*.knp'):
        with input_file.open() as f:
            for line in f:
                print(add_imis(line, rep2imis, args), end='')


def add_imis(input_line: str, rep2imis, args):
    if input_line[0] in ('#', '*', '+') or input_line.strip() == 'EOS':
        return input_line

    midasi, yomi, genkei, hinsi, _, hinsi_bunrui, _, _, _, _, _, *imis = input_line.strip().split()
    if imis:
        org_imi: str = imis[0].strip('"')
    else:
        org_imi: str = ''
    rep = (midasi, hinsi)
    if args.pos is False and hinsi_bunrui:
        rep += (hinsi_bunrui,)
    rep_yomi = rep + (yomi,)

    # 意味情報の手前まで
    newline: str = ' '.join(input_line.split()[:11])
    output_line = newline

    if args.yomi and rep_yomi in rep2imis:
        key = rep_yomi
    else:
        key = rep

    if key in rep2imis:
        first_imi: str = rep2imis[key][0]  # 該当する形態素のうち JumanDIC で最初にヒットしたものの意味情報を採用
        # jumanpp を使って代表表記を得る
        if args.use_jumanpp and '代表表記' not in first_imi:
            repname = get_repname_using_jumanpp(genkei, hinsi)
            first_imi = f'代表表記:{repname} ' + first_imi

        output_line += f' "{first_imi}'

        match = re.match(r'(NE:\S+?)[ "]', org_imi)
        if match:
            output_line += ' ' + match.group(1)
        output_line += '"\n'

        # 1つ目以外の形態素候補を@行として表示する場合
        if args.remainder:
            for imi in rep2imis[key][1:]:
                output_line += f'@ {newline} "{imi}"\n'
    else:
        # jumanpp を使って代表表記を得る
        if args.use_jumanpp and '代表表記' not in org_imi:
            repname = get_repname_using_jumanpp(genkei, hinsi)
            imi = f'代表表記:{repname}' + (f' {org_imi}' if org_imi else '')
            output_line += f' "{imi}"\n'
        else:
            output_line += f' "{org_imi}"\n' if org_imi else '\n'

    return output_line


def get_repname_using_jumanpp(genkei: str, hinsi: str) -> str:
    if hinsi == '助詞':
        return f'{genkei}/{genkei}'

    juman = Juman(option='-s 1')
    mrphs = juman.analysis(genkei)
    # 形態素解析が誤っていないか(=1形態素になっているか)をチェック
    if len(mrphs) == 1:
        return mrphs[0].repname

    return f'{genkei}/{genkei}'


if __name__ == '__main__':
    main()
