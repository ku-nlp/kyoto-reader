import logging
from typing import List, Dict, Optional, Iterator

from pyknp import Tag, Morpheme

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class BasePhrase:
    """文中に出現する基本句を表すクラス

    Attributes:
        tag (Tag): KNPの基本句オブジェクト
        sid (str): 自身を含む文の文ID
        dtid (int): 文書レベル基本句ID
        content_dmid (int): 自身に含まれる内容語形態素の文書レベルの形態素ID
        parent (Optional[BasePhrase]): 係り先
        children (List[BasePhrase]): 係り元
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
            tag (Tag): KNPの基本句オブジェクト
            dmid_offset (int): 文書中でこの基本句が始まるまでの文書レベル形態素ID
            dtid (int): 文書レベル基本句ID
            sid (str): 自身を含む文の文ID
            doc_id (str): 自身を含む文書の文書ID
            parent (Optional[BasePhrase]): 係り先
            children (List[BasePhrase]): 係り元
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
        """自身の中の内容語形態素を返す．ない場合は先頭の形態素を返す"""
        for mrph in self.tag.mrph_list():
            if '<内容語>' in mrph.fstring:
                return mrph
        else:
            logger.info(f'{self.sid}: cannot find content word in: {self.tag.midasi}. Use first mrph instead')
            return self.tag.mrph_list()[0]

    @property
    def dmid(self) -> int:
        return self.content_dmid

    @property
    def tid(self) -> int:
        """基本句ID"""
        return self.tag.tag_id

    @property
    def core(self) -> str:
        """助詞等を除いた中心的表現"""
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
        """形態素とその文書レベルIDを紐付ける辞書"""
        return self._mrph2dmid

    @property
    def mrphs(self) -> List[Morpheme]:
        """形態素列"""
        return list(self._mrph2dmid.keys())

    @property
    def dmids(self) -> List[int]:
        """形態素ID列"""
        return list(self._mrph2dmid.values())

    @property
    def surf(self) -> str:
        """表層表現"""
        return self.tag.midasi

    def mrph_list(self) -> List[Morpheme]:
        """形態素列"""
        return self.mrphs

    def __len__(self) -> int:
        """含まれる基本句の数"""
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
        return f'BasePhrase(mrphs: f{" ".join(m.midasi for m in self)}, dtid: {self.dtid}, sid: {self.sid})'
