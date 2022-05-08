import logging
from typing import Optional, Set

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Mention(BasePhrase):
    """A class to represent a mention in coreference.

    Args:
        bp (BasePhrase): A base phrase object that corresponds to this mention.

    Attributes:
        eids (set): Entity IDs.
        eids_unc (set): Uncertain entity IDs. "Uncertain" means the mention is annotated with "≒".
    """

    def __init__(self, bp: BasePhrase):
        super().__init__(bp.tag, bp.dmids[0], bp.dtid, bp.sid, bp.doc_id, parent=bp.parent, children=bp.children)
        self.eids: Set[int] = set()
        self.eids_unc: Set[int] = set()

    @property
    def all_eids(self) -> Set[int]:
        """All entity IDs this mention refers to."""
        return self.eids | self.eids_unc

    def is_uncertain_to(self, entity: 'Entity') -> bool:
        """Whether this mention has uncertain relation with a specified entity."""
        if entity.eid in self.eids:
            return False
        else:
            assert entity.eid in self.eids_unc
            return True

    def __repr__(self) -> str:
        return f'Mention(bp: {repr(super())}, eids: {repr(self.eids)}, eids_unc: {repr(self.eids_unc)})'

    def __str__(self) -> str:
        return self.core

    def __hash__(self) -> int:
        return hash((self.dtid, self.sid))


class Entity:
    """A class to represent an entity in coreference.
    This class manages entity IDs of mentions that refer to this entity.

    Args:
        eid (int): An Entity ID.
        exophor (str, optional): The kind of exophor if this entity corresponds to some exophor. Otherwise, None.

    Attributes:
        eid (int): An Entity ID.
        exophor (str, optional): A string to represent exophor, such as "著者", "読者", and "不特定:人".
        mentions (Set[Mention]): A set of mentions that refer to this entity.
        mentions_unc (Set[Mention]): Mentions that have uncertain relation with this entity.
        taigen (bool, optional): Whether this entity is 体言 or not.
        yougen (bool, optional): Whether this entity is 用言 or not.
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
        """Whether this entity corresponds to special entity, such as exophor."""
        return self.exophor is not None

    @property
    def all_mentions(self) -> Set[Mention]:
        """All mentions that refer to this entity, including uncertain ones."""
        return self.mentions | self.mentions_unc

    def add_mention(self, mention: Mention, uncertain: bool) -> None:
        """Add a mention that refers to this entity.

        When a non-uncertain mention is added and the mention has already been registered as an uncertain
        mention, it will be overwritten as non-uncertain.

        Args:
            mention (Mention): A mention
            uncertain (bool): Whether the mention is uncertain (i.e., annotated with "≒").
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
        """Remove a mention that is managed by this entity."""
        if mention in self.mentions:
            self.mentions.remove(mention)
            mention.eids.remove(self.eid)
        if mention in self.mentions_unc:
            self.mentions_unc.remove(mention)
            mention.eids_unc.remove(self.eid)

    def __str__(self) -> Optional[str]:
        if self.is_special:
            return self.exophor
        if self.mentions:
            return list(self.mentions)[0].__str__()
        elif self.mentions_unc:
            return list(self.mentions_unc)[0].__str__()
        else:
            return str(None)
