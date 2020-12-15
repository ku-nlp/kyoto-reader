from typing import Dict

from pyknp import Morpheme

from .sentence import Sentence


class NamedEntity:
    """ 固有表現に関する情報を保持するオブジェクト

    Args:
        category (str): 固有表現の種類
        name (str): 固有表現名
        sentence (Sentence): 固有表現を含む文
        mid_range (range): 形態素レベルの固有表現のスパン
        mrph2dmid (dict): 形態素とその文書レベルIDを紐付ける辞書

    Attributes:
        category (str): 固有表現の種類
        name (str): 固有表現名
        sid (str): 文ID
        mid_range (range): 形態素レベルの固有表現のスパン
        dmid_range (range): mid_range の文書レベル版
    """

    def __init__(self,
                 category: str,
                 name: str,
                 sentence: Sentence,
                 mid_range: range,
                 mrph2dmid: Dict[Morpheme, int]):
        self.category: str = category
        self.name: str = name
        self.sid: str = sentence.sid
        self.mid_range: range = mid_range
        dmid_start = mrph2dmid[sentence.mrph_list()[mid_range[0]]]
        dmid_end = mrph2dmid[sentence.mrph_list()[mid_range[-1]]]
        self.dmid_range: range = range(dmid_start, dmid_end + 1)

    def __str__(self) -> str:
        return self.name