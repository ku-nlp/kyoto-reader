import logging
from collections import ChainMap
from typing import List, Dict, Optional, Iterator

from pyknp import BList, Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Sentence:
    """ KWDLC(または Kyoto Corpus)の1文書を扱うクラス

    Attributes:
        blist (BList): KNPのBListオブジェクト
        doc_id (str): 文書ID
        bps (List[BasePhrase]): 含まれる基本句のリスト
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
        dtid = dtid_offset
        dmid = dmid_offset
        for tag in self.blist.tag_list():
            base_phrase = BasePhrase(tag, dmid, dtid, self.blist.sid, doc_id)
            self.bps.append(base_phrase)
            dtid += 1
            dmid += len(base_phrase)

        self._mrph2dmid: Dict[Morpheme, int] = dict(ChainMap(*(bp.mrph2dmid for bp in self.bps)))

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
    def dtids(self) -> List[int]:
        return [bp.dtid for bp in self.bps]

    @property
    def mrph2dmid(self) -> Dict[Morpheme, int]:
        """形態素とその文書レベルIDを紐付ける辞書"""
        return self._mrph2dmid

    @property
    def surf(self) -> str:
        """表層表現"""
        return ''.join(bp.surf for bp in self.bps)

    def bnst_list(self):
        return self.blist.bnst_list()

    def tag_list(self):
        return self.blist.tag_list()

    def mrph_list(self):
        return self.blist.mrph_list()

    def __len__(self) -> int:
        """含まれる基本句の数"""
        return len(self.bps)

    def __getitem__(self, tid: int) -> Optional[BasePhrase]:
        if 0 <= tid < len(self):
            return self.bps[tid]
        else:
            logger.error(f'base phrase: {tid} out of range')
            return None

    def __iter__(self) -> Iterator[BasePhrase]:
        return iter(self.bps)

    def __eq__(self, other: 'Sentence') -> bool:
        return self.sid == other.sid

    def __str__(self) -> str:
        return self.surf

    def __repr__(self) -> str:
        return f'Sentence(\'{self.surf}\', sid: {self.sid})'
