import logging
from typing import List, Dict, Optional, Set

from pyknp import Morpheme

from kyoto_reader.base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Mention(BasePhrase):
    """ 共参照における mention を扱うクラス

    Args:
        bp (BasePhrase): mention の基本句オブジェクト
        mrph2dmid (dict): 形態素とその文書レベルIDを紐付ける辞書

    Attributes:
        eids (set): entity id
    """
    def __init__(self, bp: BasePhrase, mrph2dmid: Dict[Morpheme, int]):
        super().__init__(bp.tag, bp.dtid, bp.sid, mrph2dmid)
        self.eids: Set[int] = set()

    def __eq__(self, other: 'Mention'):
        return self.dtid == other.dtid and self.sid == other.sid


class Entity:
    """ 共参照における entity を扱うクラス

    Args:
        eid (int): entity id
        exophor (str?): entity が外界照応の場合はその種類

    Attributes:
        eid (int): entity id
        exophor (str): 外界照応詞
        mentions (list): この entity への mention 集合
        taigen (bool): entityが体言かどうか
        yougen (bool): entityが用言かどうか
    """
    def __init__(self, eid: int, exophor: Optional[str] = None):
        self.eid: int = eid
        self.exophor: Optional[str] = exophor
        self.mentions: List[Mention] = []
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
            return self.mentions[0].midasi
        else:
            return None

    def add_mention(self, mention: Mention) -> None:
        """この entity を参照する mention を追加する

        Args:
            mention (Mention): メンション
        """
        if mention in self.mentions:
            return
        mention.eids.add(self.eid)
        self.mentions.append(mention)
        # 全てのmentionの品詞が一致した場合のみentityに品詞を設定
        self.yougen = (self.yougen is not False) and ('用言' in mention.tag.features)
        self.taigen = (self.taigen is not False) and ('体言' in mention.tag.features)
