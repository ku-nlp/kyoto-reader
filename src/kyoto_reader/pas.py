import logging
from typing import List, Dict
from collections import defaultdict
from abc import abstractmethod

from pyknp import Morpheme

from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


# 述語を表すクラス
Predicate = BasePhrase


class BaseArgument:
    """全ての項の基底クラス"""
    def __init__(self, dep_type: str, mode: str):
        self.dep_type: str = dep_type
        self.mode: str = mode
        self.optional = False

    @property
    def is_special(self) -> bool:
        return self.dep_type == 'exo'

    @property
    @abstractmethod
    def midasi(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other) -> bool:
        raise NotImplementedError

    # for test
    @abstractmethod
    def __iter__(self):
        raise NotImplementedError


class Argument(BasePhrase, BaseArgument):
    """ 文中に出現する(外界ではない)項を表すオブジェクト

    Args:
        bp (BasePhrase): 基本句
        dep_type (str): 係り受けタイプ ("overt", "dep", "intra", "inter", "exo")
        mode (str): モード
        mrph2dmid (dict): 形態素とその文書レベルIDを紐付ける辞書
    """

    def __init__(self,
                 bp: BasePhrase,
                 dep_type: str,
                 mode: str,
                 mrph2dmid: Dict[Morpheme, int]
                 ) -> None:
        # initialize BasePhrase
        super(Argument, self).__init__(bp.tag, bp.dtid, bp.sid, mrph2dmid, parent=bp.parent, children=bp.children)
        super(BasePhrase, self).__init__(dep_type, mode)  # initialize BaseArgument

    # for test
    def __iter__(self):
        yield self.midasi
        yield self.tid
        yield self.dtid
        yield self.sid
        yield self.dep_type
        yield self.mode

    def __str__(self):
        return f'{self.midasi} (sid: {self.sid}, tid: {self.tid}, dtid: {self.dtid})'

    def __eq__(self, other: BaseArgument):
        return isinstance(other, Argument) and self.dtid == other.dtid


class SpecialArgument(BaseArgument):
    """外界を指す項を表すオブジェクト

    Args:
        exophor (str): 外界照応詞 (不特定:人など)
        eid (int): 外界照応詞のエンティティID
        mode (str): モード
    """
    def __init__(self, exophor: str, eid: int, mode: str):
        self.eid = eid
        dep_type = 'exo'
        super().__init__(dep_type, mode)
        self.exophor: str = exophor

    @property
    def midasi(self) -> str:
        return self.exophor

    # for test
    def __iter__(self):
        yield self.midasi
        yield self.eid
        yield self.dep_type
        yield self.mode

    def __eq__(self, other: BaseArgument):
        return isinstance(other, SpecialArgument) and self.exophor == other.exophor


class Pas:
    """ 述語項構造を保持するオブジェクト

    Args:
        pred_bp (BasePhrase): 述語となる基本句

    Attributes:
        predicate (Predicate): 述語
        arguments (dict): 格と項
    """

    def __init__(self, pred_bp: BasePhrase):
        # self.predicate = Predicate(pred_bp.tag, pred_bp.dtid, pred_bp.sid)
        self.predicate: Predicate = pred_bp
        self.arguments: Dict[str, List[BaseArgument]] = defaultdict(list)

    def add_argument(self, case: str, bp: BasePhrase, mode: str, mrph2dmid: Dict[Morpheme, int]):
        dep_type = self._get_dep_type(self.predicate, bp, case)
        argument = Argument(bp, dep_type, mode, mrph2dmid)
        if argument not in self.arguments[case]:
            self.arguments[case].append(argument)

    @staticmethod
    def _get_dep_type(pred: BasePhrase, arg: BasePhrase, case: str) -> str:
        if arg in pred.children:
            dep_case = arg.tag.features.get('係', '').rstrip('格')
            if (case == dep_case) or (case == '判ガ' and dep_case == 'ガ') or (case == 'ノ？' and dep_case == 'ノ'):
                return 'overt'
            else:
                return 'dep'
        elif pred.parent is not None and arg == pred.parent:
            return 'dep'
        elif arg.sid == pred.sid:
            return 'intra'
        else:
            return 'inter'

    def add_special_argument(self, case: str, exophor: str, eid: int, mode: str) -> None:
        special_argument = SpecialArgument(exophor, eid, mode)
        if special_argument not in self.arguments[case]:
            self.arguments[case].append(special_argument)

    def set_arguments_optional(self, case: str) -> None:
        if not self.arguments[case]:
            logger.info(f'{self.sid:24}no preceding argument found. なし is ignored')
            return
        for arg in self.arguments[case]:
            arg.optional = True
            logger.info(f'{self.sid:24}marked {arg.midasi} as optional')

    @property
    def dtid(self) -> int:
        return self.predicate.dtid

    @property
    def sid(self) -> str:
        return self.predicate.sid

    @property
    def dmid(self) -> int:
        """述語の中の内容語形態素の文書レベル形態素ID"""
        return self.predicate.dmid
