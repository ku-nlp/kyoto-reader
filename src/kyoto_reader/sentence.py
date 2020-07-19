import logging
from typing import List, Dict

from pyknp import BList, Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Sentence:
    def __init__(self,
                 knp_string: str,
                 dtid_offset: int,
                 dmid_offset: int,
                 doc_id: str,
                 ) -> None:
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

    @property
    def sid(self) -> str:
        return self.blist.sid

    @property
    def midasi(self) -> str:
        return self.__str__()

    def bnst_list(self):
        return self.blist.bnst_list()

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
        return ''.join(bp.midasi for bp in self.bps)
