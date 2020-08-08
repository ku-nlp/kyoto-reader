import logging
from typing import List, Dict, Optional

from pyknp import Tag, Morpheme

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class BasePhrase:
    """文中に出現する基本句を表すクラス

    Attributes:
        tag (Tag): KNPの基本句オブジェクト
        sid (str): 自身を含む文の文ID
        dtid (int): 文書レベル基本句ID
        dmid (int): 自身に含まれる内容語形態素の文書レベルの形態素ID
        parent (Optional[BasePhrase]): 係り先
        children (List[BasePhrase]): 係り元
    """
    def __init__(self,
                 tag: Tag,
                 dtid: int,
                 sid: str,
                 mrph2dmid: Dict[Morpheme, int],
                 parent: Optional['BasePhrase'] = None,
                 children: Optional[List['BasePhrase']] = None,
                 ):
        """

        Args:
            tag (Tag): KNPの基本句オブジェクト
            dtid (int): 文書レベル基本句ID
            sid (str): 自身を含む文の文ID
            mrph2dmid (dict): 形態素とその文書レベルIDを紐付ける辞書
            parent (Optional[BasePhrase]): 係り先
            children (List[BasePhrase]): 係り元
        """
        self.tag: Tag = tag
        self.dtid: int = dtid
        self.sid: str = sid
        self.dmid: int = self._get_content_word(mrph2dmid)
        self.parent: Optional['BasePhrase'] = parent
        self.children: List['BasePhrase'] = children if children is not None else []

    def _get_content_word(self, mrph2dmid: Dict[Morpheme, int]) -> int:
        """自身の中の内容語形態素を返す．ない場合は先頭の形態素を返す"""
        for mrph in self.tag.mrph_list():
            if '<内容語>' in mrph.fstring:
                return mrph2dmid[mrph]
        else:
            logger.info(f'{self.sid:24}cannot find content word in: {self.tag.midasi}. Use first mrph instead')
            return mrph2dmid[self.tag.mrph_list()[0]]
    
    @property
    def tid(self) -> int:
        """基本句ID"""
        return self.tag.tag_id

    @property
    def midasi(self) -> str:
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

    def mrph_list(self) -> List[Morpheme]:
        """形態素列"""
        return self.tag.mrph_list()

    def __eq__(self, other: 'BasePhrase'):
        return self.sid == other.sid and self.dtid == other.dtid

    def __str__(self) -> str:
        return self.tag.midasi
