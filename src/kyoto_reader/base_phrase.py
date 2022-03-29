import logging
from typing import List, Dict, Optional, Iterator

from pyknp import Tag, Morpheme

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class BasePhrase:
    """文中に出現する基本句を表すクラス

    Attributes:
        tag (Tag): Tag object in pyknp.
        sid (str): Sentence ID.
        dtid (int): Document-wide tag ID.
        content_dmid (int): Document-wide morpheme ID of the content word in the base phrase.
        parent (Optional[BasePhrase]): Dependency parent.
        children (List[BasePhrase]): Dependency children.
    """

    def __init__(self,
                 tag: Tag,
                 dmid_offset: int,
                 dtid: int,
                 sid: str,
                 doc_id: str,
                 parent: Optional['BasePhrase'] = None,
                 children: Optional[List['BasePhrase']] = None,
                 ):
        """

        Args:
            tag (Tag): Tag object in pyknp.
            dmid_offset (int): Document-wide morpheme ID of the previous morpheme.
            dtid (int): Document-wide tag ID.
            sid (str): Sentence ID.
            doc_id (str): Document ID.
            parent (Optional[BasePhrase]): Dependency parent.
            children (List[BasePhrase]): Dependency children.
        """
        self.tag: Tag = tag
        self.dtid: int = dtid
        self.sid: str = sid
        self.doc_id: str = doc_id

        self._mrph2dmid: Dict[Morpheme, int] = {}
        dmid = dmid_offset
        for mrph in tag.mrph_list():
            self._mrph2dmid[mrph] = dmid
            dmid += 1

        self.content: Morpheme = self._get_content_word()
        self.content_dmid: int = self._mrph2dmid[self.content]
        self.parent: Optional['BasePhrase'] = parent
        self.children: List['BasePhrase'] = children if children is not None else []

    def _get_content_word(self) -> Morpheme:
        """Return the first morpheme that is a content word if any. Otherwise, return the first morpheme"""
        for mrph in self.tag.mrph_list():
            if '<内容語>' in mrph.fstring:
                return mrph
        else:
            logger.info(f'{self.sid}: cannot find content word in: {self.tag.midasi}. Use first mrph instead')
            return self.tag.mrph_list()[0]

    @property
    def dmid(self) -> int:
        """Document-wide morpheme ID."""
        return self.content_dmid

    @property
    def tid(self) -> int:
        """Tag ID in pyknp."""
        return self.tag.tag_id

    @property
    def core(self) -> str:
        """A core expression without ancillary words."""
        mrph_list = self.tag.mrph_list()
        sidx = 0
        for i, mrph in enumerate(mrph_list):
            if mrph.hinsi not in ('助詞', '特殊', '判定詞'):
                sidx += i
                break
        eidx = len(mrph_list)
        for i, mrph in enumerate(reversed(mrph_list)):
            if mrph.hinsi not in ('助詞', '特殊', '判定詞'):
                eidx -= i
                break
        ret = ''.join(mrph.midasi for mrph in mrph_list[sidx:eidx])
        if not ret:
            ret = self.tag.midasi
        return ret

    @property
    def mrph2dmid(self) -> Dict[Morpheme, int]:
        """A mapping from morpheme to its document-wide ID."""
        return self._mrph2dmid

    @property
    def mrphs(self) -> List[Morpheme]:
        """A list of morphemes."""
        return list(self._mrph2dmid.keys())

    @property
    def dmids(self) -> List[int]:
        """A list of document-wide morpheme IDs."""
        return list(self._mrph2dmid.values())

    @property
    def surf(self) -> str:
        """A surface expression."""
        return self.tag.midasi

    def mrph_list(self) -> List[Morpheme]:
        """A list of morphemes"""
        return self.mrphs

    def __len__(self) -> int:
        """Number of morphemes in the base phrase"""
        return len(self._mrph2dmid)

    def __getitem__(self, mid: int) -> Optional[Morpheme]:
        if 0 <= mid < len(self):
            return self.mrphs[mid]
        else:
            logger.error(f'{self.sid}: morpheme id: {mid} out of range')
            return None

    def __iter__(self) -> Iterator[Morpheme]:
        return iter(self.mrphs)

    def __eq__(self, other: 'BasePhrase') -> bool:
        return self.sid == other.sid and self.dtid == other.dtid

    def __str__(self) -> str:
        return self.surf

    def __repr__(self) -> str:
        return f'BasePhrase(dtid: {self.dtid}, mrphs: {" ".join(m.midasi for m in self)}, sid: {self.sid})'
