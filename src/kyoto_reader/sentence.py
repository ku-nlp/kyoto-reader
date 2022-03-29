import logging
from collections import ChainMap
from typing import List, Dict, Optional, Iterator

from pyknp import BList, Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Sentence:
    """A class to represent a single sentence.

    Attributes:
        blist (BList): BList object of pyknp.
        doc_id (str): The document ID of this sentence.
        bps (List[BasePhrase]): Base phrases in this sentence.
    """

    def __init__(self,
                 knp_string: str,
                 dtid_offset: int,
                 dmid_offset: int,
                 doc_id: str,
                 ) -> None:
        """

        Args:
            knp_string(str): KNP format string of this sentence.
            dtid_offset (int): The document-wide tag ID of the previous base phrase.
            dmid_offset (int): The document-wide morpheme ID of the previous morpheme.
            doc_id(str): The document ID of this sentence.
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
        """A sentence ID."""
        return self.blist.sid

    @property
    def dtids(self) -> List[int]:
        """A document-wide tag ID."""
        return [bp.dtid for bp in self.bps]

    @property
    def mrph2dmid(self) -> Dict[Morpheme, int]:
        """A mapping from morpheme to its document-wide ID."""
        return self._mrph2dmid

    @property
    def surf(self) -> str:
        """A surface expression"""
        return ''.join(bp.surf for bp in self.bps)

    def bnst_list(self):
        """Return list of Bunsetsu object in pyknp."""
        return self.blist.bnst_list()

    def tag_list(self):
        """Return list of Tag object in pyknp."""
        return self.blist.tag_list()

    def mrph_list(self):
        """Return list of Morpheme object in pyknp."""
        return self.blist.mrph_list()

    def __len__(self) -> int:
        """Number of base phrases in this sentence"""
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
