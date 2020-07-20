import logging
from typing import Dict, Optional, Set

from pyknp import Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Mention(BasePhrase):
    """ 共参照における mention を扱うクラス

    Args:
        bp (BasePhrase): mention の基本句オブジェクト
        mrph2dmid (dict): 形態素とその文書レベルIDを紐付ける辞書

    Attributes:
        eids (set): entity ids
        eids_unc (set): uncertain entity ids
    """
    def __init__(self, bp: BasePhrase, mrph2dmid: Dict[Morpheme, int]):
        super().__init__(bp.tag, bp.dtid, bp.sid, mrph2dmid, parent=bp.parent, children=bp.children)
        self.eids: Set[int] = set()
        self.eids_unc: Set[int] = set()

    @property
    def all_eids(self) -> Set[int]:
        return self.eids | self.eids_unc

    def is_uncertain_to(self, entity: 'Entity') -> bool:
        if entity.eid in self.eids:
            return False
        else:
            assert entity.eid in self.eids_unc
            return True

    def __eq__(self, other: 'Mention'):
        return self.dtid == other.dtid and self.sid == other.sid

    def __hash__(self):
        return hash((self.dtid, self.sid))


class Entity:
    """ 共参照における entity を扱うクラス
    自身を参照している mention の eids の管理も行う

    Args:
        eid (int): entity id
        exophor (str?): entity が外界照応の場合はその種類

    Attributes:
        eid (int): entity id
        exophor (str): 外界照応詞
        mentions (set): この entity への mention 集合
        mentions_unc (set): mention が不確実なもの
        taigen (bool): entityが体言かどうか
        yougen (bool): entityが用言かどうか
    """
    def __init__(self, eid: int, exophor: Optional[str] = None):
        self.eid: int = eid
        self.exophor: Optional[str] = exophor
        self.mentions: Set[Mention] = set()
        self.mentions_unc: Set[Mention] = set()
        self.taigen: Optional[bool] = None
        self.yougen: Optional[bool] = None

    @property
    def is_special(self) -> bool:
        return self.exophor is not None

    @property
    def midasi(self) -> Optional[str]:
        if self.is_special:
            return self.exophor
        if self.mentions:
            return list(self.mentions)[0].midasi
        elif self.mentions_unc:
            return list(self.mentions_unc)[0].midasi
        else:
            return None

    @property
    def all_mentions(self) -> Set[Mention]:
        return self.mentions | self.mentions_unc

    def add_mention(self, mention: Mention, uncertain: bool) -> None:
        """この entity を参照する mention を追加する

        uncertain でない mention が add された時、
        その mention がすでに uncertain な mention として登録されていれば
        uncertain でないものとして上書きする

        Args:
            mention (Mention): メンション
            uncertain (bool): mention が =≒ などの不確実なものか
        """
        if uncertain:
            if mention in self.all_mentions:
                return
            mention.eids_unc.add(self.eid)
            self.mentions_unc.add(mention)
        else:
            if mention in self.mentions_unc:
                self.remove_mention(mention)
            mention.eids.add(self.eid)
            self.mentions.add(mention)
        # 全ての mention の品詞が一致した場合のみ entity に品詞を設定
        self.yougen = (self.yougen is not False) and ('用言' in mention.tag.features)
        self.taigen = (self.taigen is not False) and ('体言' in mention.tag.features)

    def remove_mention(self, mention: Mention) -> None:
        """entity に登録されている mention を削除する"""
        if mention in self.mentions:
            self.mentions.remove(mention)
            mention.eids.remove(self.eid)
        if mention in self.mentions_unc:
            self.mentions_unc.remove(mention)
            mention.eids_unc.remove(self.eid)
