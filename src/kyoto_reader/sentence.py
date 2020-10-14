import logging
from typing import List, Dict

from pyknp import BList, Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Sentence:
    """ KWDLC(または Kyoto Corpus)の1文書を扱うクラス

    Attributes:
        blist (BList): KNPのBListオブジェクト
        doc_id (str): 文書ID
        bps (List[BasePhrase]): 文に含まれる基本句のリスト
        mrph2dmid (dict): 形態素IDと文書レベルの形態素IDを紐付ける辞書
    """
    def __init__(self,
                 knp_string: str,
                 dtid_offset: int,
                 dmid_offset: int,
                 doc_id: str,
                 ) -> None:
        """

        Args:
            knp_string(str): 1文についてのKNPのtab出力
            dtid_offset (int): 文書中でこの文が始まるまでの文書レベル基本句ID
            dmid_offset (int): 文書中でこの文が始まるまでの文書レベル形態素ID
            doc_id(str): 文書ID
        """

        self.blist = BList(knp_string)
        self.doc_id: str = doc_id

        self.bps: List[BasePhrase] = []
        self.mrph2dmid: Dict[Morpheme, int] = {}
        dtid = dtid_offset
        dmid = dmid_offset
        for tag in self.tag_list():
            for mrph in tag.mrph_list():
                self.mrph2dmid[mrph] = dmid
                dmid += 1
            self.bps.append(BasePhrase(tag, dtid, self.sid, self.mrph2dmid))
            dtid += 1

        for bp in self.bps:
            if bp.tag.parent_id >= 0:
                bp.parent = self.bps[bp.tag.parent_id]
            for child in bp.tag.children:
                bp.children.append(self.bps[child.tag_id])

    @property
    def sid(self) -> str:
        """文ID"""
        return self.blist.sid

    @property
    def midasi(self) -> str:
        return self.__str__()

    def bnst_list(self):
        return self.blist.bnst_list()

    def bp_list(self):
        return self.bps

    def tag_list(self):
        return self.blist.tag_list()

    def mrph_list(self):
        return self.blist.mrph_list()

    def __len__(self):
        return len(self.bps)

    def __getitem__(self, tid: int):
        if 0 <= tid < len(self):
            return self.bps[tid]
        else:
            logger.error(f'base phrase: {tid} out of range')
            return None

    def __iter__(self):
        return iter(self.bps)

    def __str__(self):
        return ''.join(str(bp) for bp in self.bps)
