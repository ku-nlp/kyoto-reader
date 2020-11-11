import io
import re
import copy
import _pickle as cPickle
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Iterator, Union, TextIO
from collections import OrderedDict, ChainMap

import jaconv
from joblib import Parallel, delayed
from pyknp import BList, Bunsetsu, Tag, Morpheme, Rel

from .sentence import Sentence
from .pas import Pas, Predicate, BaseArgument, Argument, SpecialArgument
from .coreference import Mention, Entity
from .ne import NamedEntity
from .constants import ALL_CASES, ALL_EXOPHORS, ALL_COREFS, NE_CATEGORIES
from .base_phrase import BasePhrase

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class KyotoReader:
    """ KWDLC(または Kyoto Corpus)の文書集合を扱うクラス

    Args:
        source (Union[Path, str]): 対象の文書へのパス。ディレクトリが指定された場合、その中の全てのファイルを対象とする
        target_cases (Optional[List[str]]): 抽出の対象とする格。指定されなかった場合、全ての格を対象とする
        target_corefs (Optional[List[str]]): 抽出の対象とする共参照関係(=など)。指定されなかった場合、全ての関係を対象とする
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        relax_cases (bool): ガ≒格などをガ格として扱うか
        knp_ext (str): KWDLC または KC ファイルの拡張子
        pickle_ext (str): Document を pickle 形式で読む場合の拡張子
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか
        recursive (bool): source がディレクトリの場合、文書ファイルを再帰的に探索するかどうか
    """
    SID_PTN = re.compile(r'^# S-ID:\s*([a-zA-Z0-9-_]+)-(\d+) .*$')

    def __init__(self,
                 source: Union[Path, str],
                 target_cases: Optional[List[str]] = None,
                 target_corefs: Optional[List[str]] = None,
                 extract_nes: bool = True,
                 relax_cases: bool = False,
                 use_pas_tag: bool = False,
                 knp_ext: str = '.knp',
                 pickle_ext: str = '.pkl',
                 recursive: bool = False,
                 ) -> None:
        if not (isinstance(source, Path) or isinstance(source, str)):
            raise TypeError(f"document source must be Path or str type, but got '{type(source)}' type")
        source = Path(source)
        if source.is_dir():
            logger.info(f'got directory path, files in the directory is treated as source files')
            file_paths: List[Path] = []
            for ext in (knp_ext, pickle_ext):
                file_paths += sorted(source.glob(f'**/*{ext}' if recursive else f'*{ext}'))
        else:
            logger.info(f'got file path, this file is treated as a source knp file')
            file_paths = [source]
        self.did2pkls: Dict[str, Path] = {path.stem: path for path in file_paths if path.suffix == pickle_ext}
        parallel = Parallel(n_jobs=-1)
        rets = parallel([delayed(KyotoReader._read_knp)(path) for path in file_paths if path.suffix == knp_ext])
        self.did2knps: Dict[str, str] = dict(ChainMap(*rets))

        self.target_cases: List[str] = self._get_targets(target_cases, ALL_CASES, 'case')
        self.target_corefs: List[str] = self._get_targets(target_corefs, ALL_COREFS, 'coref')
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    @staticmethod
    def _read_knp(path: Path) -> Dict[str, str]:
        did2knps = {}
        with path.open() as f:
            buff = ''
            did = None
            for line in f:
                match = KyotoReader.SID_PTN.match(line.strip())
                if match:
                    # sid = match.group(1) + '-' + match.group(2)
                    if did != match.group(1):
                        if did is not None:
                            did2knps[did] = buff
                            buff = ''
                        did = match.group(1)
                buff += line
            did2knps[did] = buff
        return did2knps

    @staticmethod
    def _get_targets(input_: Optional[list],
                     all_: list,
                     type_: str,
                     ) -> list:
        if input_ is None:
            return all_
        target = []
        for item in input_:
            if item not in all_:
                logger.warning(f'unknown target {type_}: {item}')
                continue
            target.append(item)
        return target

    def doc_ids(self) -> List[str]:
        return list(set(self.did2knps.keys()) | set(self.did2pkls.keys()))

    def process_document(self, doc_id: str) -> Optional['Document']:
        if doc_id in self.did2pkls:
            with self.did2pkls[doc_id].open(mode='rb') as f:
                return cPickle.load(f)
        elif doc_id in self.did2knps:
            return Document(self.did2knps[doc_id],
                            doc_id,
                            self.target_cases,
                            self.target_corefs,
                            self.relax_cases,
                            self.extract_nes,
                            self.use_pas_tag)
        else:
            logger.error(f'unknown document id: {doc_id}')
            return None

    def process_documents(self, doc_ids: List[str]) -> Iterator[Optional['Document']]:
        for doc_id in doc_ids:
            yield self.process_document(doc_id)

    def process_all_documents(self) -> Iterator['Document']:
        for doc_id in self.doc_ids():
            yield self.process_document(doc_id)

    def __len__(self):
        return len(self.doc_ids())


class Document:
    """ KWDLC(または Kyoto Corpus)の1文書を扱うクラス

    Args:
        knp_string (str): 文書ファイルの内容(knp形式)
        doc_id (str): 文書ID
        cases (List[str]): 抽出の対象とする格
        corefs (List[str]): 抽出の対象とする共参照関係(=など)
        relax_cases (bool): ガ≒格などをガ格として扱うか
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか

    Attributes:
        knp_string (str): 文書ファイルの内容(knp形式)
        doc_id (str): 文書ID(ファイル名から拡張子を除いたもの)
        cases (List[str]): 抽出の対象とする格
        corefs (List[str]): 抽出の対象とする共参照関係(=など)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        sid2sentence (dict): 文IDと文を紐付ける辞書
        mrph2dmid (dict): 形態素IDと文書レベルの形態素IDを紐付ける辞書
        mentions (dict): dtid を key とする mention の辞書
        entities (dict): entity id を key として entity オブジェクトが格納されている
        named_entities (list): 抽出した固有表現
    """
    def __init__(self,
                 knp_string: str,
                 doc_id: str,
                 cases: List[str],
                 corefs: List[str],
                 relax_cases: bool,
                 extract_nes: bool,
                 use_pas_tag: bool,
                 ) -> None:
        self.knp_string: str = knp_string
        self.doc_id: str = doc_id
        self.cases: List[str] = cases
        self.corefs: List[str] = corefs
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag

        self.sid2sentence: Dict[str, Sentence] = OrderedDict()
        dtid = dmid = 0
        buff = ''
        for line in knp_string.strip().split('\n'):
            buff += line + '\n'
            if line.strip() == 'EOS':
                sentence = Sentence(buff, dtid, dmid, doc_id)
                if sentence.sid in self.sid2sentence:
                    logger.warning(f'{sentence.sid}:duplicated sid found')
                self.sid2sentence[sentence.sid] = sentence
                dtid += len(sentence.bps)
                dmid += len(sentence.mrph_list())
                buff = ''

        self.mrph2dmid = {mrph: dmid for sent in self.sentences for mrph, dmid in sent.mrph2dmid.items()}

        self._pas: Dict[int, Pas] = OrderedDict()
        self.mentions: Dict[int, Mention] = OrderedDict()
        self.entities: Dict[int, Entity] = OrderedDict()
        if use_pas_tag:
            self._analyze_pas()
        else:
            self._analyze_rel()

        if extract_nes:
            self.named_entities: List[NamedEntity] = []
            self._extract_nes()

    def _analyze_pas(self) -> None:
        """extract predicate argument structure from <述語項構造:> tag in knp string"""
        sid2idx = {sid: idx for idx, sid in enumerate(self.sid2sentence.keys())}
        for bp in self.bp_list():
            if bp.tag.pas is None:
                continue
            pas = Pas(bp)
            for case, arguments in bp.tag.pas.arguments.items():
                if self.relax_cases:
                    if case in ALL_CASES and case.endswith('≒'):
                        case = case.rstrip('≒')  # ガ≒ -> ガ
                for arg in arguments:
                    arg.midasi = jaconv.h2z(arg.midasi, digit=True)  # 不特定:人1 -> 不特定:人１
                    # exophor
                    if arg.flag == 'E':
                        entity = self._create_entity(exophor=arg.midasi, eid=arg.eid)
                        pas.add_special_argument(case, arg.midasi, entity.eid, '')
                    else:
                        sid = self.sentences[sid2idx[arg.sid] - arg.sdist].sid
                        arg_bp = self._get_bp(sid, arg.tid)
                        _ = self._create_mention(arg_bp)
                        pas.add_argument(case, arg_bp, '', self.mrph2dmid)
            if pas.arguments:
                self._pas[pas.dtid] = pas

    def _analyze_rel(self) -> None:
        """extract predicate argument structure and coreference relation from <rel> tag in knp string"""
        for bp in self.bp_list():
            rels = []
            for rel in self._extract_rel_tags(bp.tag):
                if self.relax_cases:
                    if rel.atype in ALL_CASES and rel.atype.endswith('≒'):
                        rel.atype = rel.atype.rstrip('≒')  # ガ≒ -> ガ
                valid = True
                if rel.sid is not None and rel.sid not in self.sid2sentence:
                    logger.warning(f'{bp.sid}:sentence: {rel.sid} not found in {self.doc_id}')
                    valid = False
                if rel.atype in (ALL_CASES + ALL_COREFS):
                    if rel.atype not in (self.cases + self.corefs):
                        logger.info(f'{bp.sid}:relation type: {rel.atype} is ignored')
                        valid = False
                else:
                    logger.warning(f'{bp.sid}:unknown relation: {rel.atype}')
                if valid:
                    rels.append(rel)

            # extract PAS
            pas = Pas(bp)
            for rel in rels:
                if rel.atype in self.cases:
                    if rel.sid is not None:
                        assert rel.tid is not None
                        arg_bp = self._get_bp(rel.sid, rel.tid)
                        if arg_bp is None:
                            continue
                        # 項を発見したら同時に mention と entity を作成
                        _ = self._create_mention(arg_bp)
                        pas.add_argument(rel.atype, arg_bp, rel.mode, self.mrph2dmid)
                    # exophora
                    else:
                        if rel.target == 'なし':
                            pas.set_arguments_optional(rel.atype)
                            continue
                        if rel.target not in ALL_EXOPHORS:
                            logger.warning(f'{pas.sid}:unknown exophor: {rel.target}')
                            continue
                        entity = self._create_entity(rel.target)
                        pas.add_special_argument(rel.atype, rel.target, entity.eid, rel.mode)
            if pas.arguments:
                self._pas[pas.dtid] = pas

            # extract coreference
            for rel in rels:
                if rel.atype in self.corefs:
                    if rel.mode in ('', 'AND'):  # ignore "OR" and "?"
                        self._add_corefs(bp, rel)

    # to extract rels with mode: '?', rewrite initializer of pyknp Futures class
    @staticmethod
    def _extract_rel_tags(tag: Tag) -> List[Rel]:
        """parse tag.fstring to extract <rel> tags"""
        splitter = "><"
        rels = []
        spec = tag.fstring

        tag_start = 1
        tag_end = None
        while tag_end != -1:
            tag_end = spec.find(splitter, tag_start)
            if spec[tag_start:].startswith('rel '):
                rel = Rel(spec[tag_start:tag_end])
                if rel.target:
                    rel.target = jaconv.h2z(rel.target, digit=True)  # 不特定:人1 -> 不特定:人１
                if rel.atype is not None:
                    rels.append(rel)

            tag_start = tag_end + len(splitter)
        return rels

    def _add_corefs(self,
                    source_bp: BasePhrase,
                    rel: Rel,
                    ) -> None:
        if rel.sid is not None:
            target_bp = self._get_bp(rel.sid, rel.tid)
            if target_bp is None:
                return
            if target_bp.dtid == source_bp.dtid:
                logger.warning(f'{source_bp.sid}:coreference with self found: {source_bp.midasi}')
                return
        else:
            target_bp = None
            if rel.target not in ALL_EXOPHORS:
                logger.warning(f'{source_bp.sid}:unknown exophor: {rel.target}')
                return

        uncertain: bool = rel.atype.endswith('≒')
        source_mention = self._create_mention(source_bp)
        for eid in source_mention.all_eids:
            # _merge_entities によって source_mention の eid が削除されているかもしれない
            if eid not in self.entities:
                continue
            source_entity = self.entities[eid]
            if rel.sid is not None:
                target_mention = self._create_mention(target_bp)
                for target_eid in target_mention.all_eids:
                    target_entity = self.entities[target_eid]
                    self._merge_entities(source_mention, target_mention, source_entity, target_entity, uncertain)
            else:
                target_entity = self._create_entity(exophor=rel.target)
                self._merge_entities(source_mention, None, source_entity, target_entity, uncertain)

    def _create_mention(self, bp: BasePhrase) -> Mention:
        """メンションを作成
        bp がまだ mention として登録されていなければ新しく entity と共に作成．
        登録されていればその mention を返す．

        Args:
            bp (BasePhrase): 基本句

        Returns:
            Mention: メンション
        """
        if bp.dtid not in self.mentions:
            # new coreference cluster is made
            mention = Mention(bp, self.mrph2dmid)
            self.mentions[bp.dtid] = mention
            entity = self._create_entity()
            entity.add_mention(mention, uncertain=False)
        else:
            mention = self.mentions[bp.dtid]
        return mention

    def _create_entity(self,
                       exophor: Optional[str] = None,
                       eid: Optional[int] = None,
                       ) -> Entity:
        """エンティティを作成

        exophor が singleton entity だった場合を除き、新しく Entity のインスタンスを作成して返す
        singleton entity とは、「著者」や「不特定:人１」などの必ず一つしか存在しないような entity
        一方で、「不特定:人」や「不特定:物」は複数存在しうるので singleton entity ではない
        eid を指定しない場合、最後に作成した entity の次の eid を選択

        Args:
            exophor (Optional[str]): 外界照応詞(optional)
            eid (Optional[int]): エンティティID(省略推奨)

        Returns:
             Entity: エンティティ
        """
        if exophor:
            if exophor not in ('不特定:人', '不特定:物', '不特定:状況'):  # exophor が singleton entity だった時
                entities = [e for e in self.entities.values() if exophor == e.exophor]
                # すでに singleton entity が存在した場合、新しい entity は作らずにその entity を返す
                if entities:
                    assert len(entities) == 1  # singleton entity が1つしかないことを保証
                    return entities[0]
        eids: List[int] = [e.eid for e in self.entities.values()]
        if eid in eids:
            eid_ = eid
            eid: int = max(eids) + 1
            logger.warning(f'{self.doc_id}:eid: {eid_} is already used. use eid: {eid} instead.')
        elif eid is None or eid < 0:
            eid: int = max(eids) + 1 if eids else 0
        entity = Entity(eid, exophor=exophor)
        self.entities[eid] = entity
        return entity

    def _merge_entities(self,
                        source_mention: Mention,
                        target_mention: Optional[Mention],
                        se: Entity,
                        te: Entity,
                        uncertain: bool,
                        ) -> None:
        """2つのエンティティをマージする

        source_mention と se, target_mention と te の間には mention が張られているが、
        source と target 間には張られていないので、add_mention する
        se と te が同一のエンティティであり、exophor も同じか片方が None ならば te の方を削除する

        Args:
            source_mention (Mention): 参照元メンション
            target_mention (Mention?): 参照先メンション
            se (Entity): 参照元エンティティ
            te (Entity): 参照先エンティティ
            uncertain (bool): source_mention と target_mention のアノテーションが ≒ かどうか
        """
        uncertain_tgt = (target_mention is not None) and target_mention.is_uncertain_to(te)
        uncertain_src = source_mention.is_uncertain_to(se)
        if se is te:
            if not uncertain:
                # se(te), source_mention, target_mention の三角形のうち2辺が certain ならもう1辺も certain
                if (not uncertain_src) and uncertain_tgt:
                    se.add_mention(target_mention, uncertain=False)
                if uncertain_src and (not uncertain_tgt):
                    se.add_mention(source_mention, uncertain=False)
            return
        if target_mention is not None:
            se.add_mention(target_mention, uncertain=(uncertain or uncertain_src))
        te.add_mention(source_mention, uncertain=(uncertain or uncertain_tgt))
        # se と te が同一でない可能性が拭えない場合、te は削除しない
        if uncertain_src or uncertain or uncertain_tgt:
            return
        # se と te が同一でも exophor が異なれば te は削除しない
        if se.exophor is not None and te.exophor is not None and se.exophor != te.exophor:
            return
        # 以下 te を削除する準備
        if se.exophor is None:
            se.exophor = te.exophor
        for tm in te.all_mentions:
            se.add_mention(tm, uncertain=tm.is_uncertain_to(te))
        # argument も eid を持っているので eid が変わった場合はこちらも更新
        for arg in [arg for pas in self._pas.values() for args in pas.arguments.values() for arg in args]:
            if isinstance(arg, SpecialArgument) and arg.eid == te.eid:
                arg.eid = se.eid
        self._delete_entity(te.eid, source_mention.sid)  # delete target entity

    def _delete_entity(self,
                       eid: int,
                       sid: str
                       ) -> None:
        """entity を削除する

        対象の entity を entities から削除すると共に、
        その entity を参照する全ての mention からも削除
        eid に欠番ができる

        Args:
            eid (int): 削除対象の entity の EID
            sid (int): 削除された時解析されていた文の文ID
        """
        if eid not in self.entities:
            return
        entity = self.entities[eid]
        logger.info(f'{sid}:delete entity: {eid} ({entity.midasi})')
        for mention in entity.all_mentions:
            entity.remove_mention(mention)
        self.entities.pop(eid)

    def _get_bp(self,
                sid: str,
                tid: int,
                ) -> Optional[BasePhrase]:
        """文IDと基本句IDから基本句を得る

        Args:
            sid (str): 文ID
            tid (int): 基本句ID

        Returns:
            Optional[BasePhrase]: 対応する基本句
        """
        sentence = self[sid]
        if not (0 <= tid < len(sentence.bps)):
            logger.warning(f'{sid}:tag id: {tid} out of range')
            return None
        return sentence.bps[tid]

    def _extract_nes(self) -> None:
        """KNP の tag を参照して文書中から固有表現を抽出する"""
        for sentence in self.sentences:
            tag_list = sentence.tag_list()
            # tag.features = {'NE': 'LOCATION:ダーマ神殿'}
            for tag in tag_list:
                if 'NE' not in tag.features:
                    continue
                category, midasi = tag.features['NE'].split(':', maxsplit=1)
                if category not in NE_CATEGORIES:
                    logger.warning(f'{sentence.sid}:unknown NE category: {category}')
                    continue
                mrph_list = [m for t in tag_list[:tag.tag_id + 1] for m in t.mrph_list()]
                mrph_span = self._find_mrph_span(midasi, mrph_list, tag)
                if mrph_span is None:
                    logger.warning(f'{sentence.sid}:mrph span of "{midasi}" not found')
                    continue
                ne = NamedEntity(category, midasi, sentence, mrph_span, self.mrph2dmid)
                self.named_entities.append(ne)

    @staticmethod
    def _find_mrph_span(midasi: str,
                        mrph_list: List[Morpheme],
                        tag: Tag
                        ) -> Optional[range]:
        """midasiにマッチする形態素の範囲を返す"""
        for i in range(len(tag.mrph_list())):
            end_mid = len(mrph_list) - i
            mrph_span = ''
            for mrph in reversed(mrph_list[:end_mid]):
                mrph_span = mrph.midasi + mrph_span
                if mrph_span == midasi:
                    return range(mrph.mrph_id, end_mid)
        return None

    @property
    def sentences(self) -> List['Sentence']:
        """文を構成する全文節列オブジェクト

        Returns:
            List[Sentence]
        """
        return list(self.sid2sentence.values())

    def bnst_list(self) -> List[Bunsetsu]:
        return [bnst for sentence in self.sentences for bnst in sentence.bnst_list()]

    def bp_list(self) -> List[BasePhrase]:
        return [bp for sentence in self.sentences for bp in sentence.bps]

    def tag_list(self) -> List[Tag]:
        return [tag for sentence in self.sentences for tag in sentence.tag_list()]

    def mrph_list(self) -> List[Morpheme]:
        return [mrph for sentence in self.sentences for mrph in sentence.mrph_list()]

    def get_entities(self, bp: BasePhrase, include_uncertain: bool = False) -> List[Entity]:
        """基本句が参照するエンティティを返す

        Args:
            bp (BasePhrase): 基本句
            include_uncertain (bool): 参照しているか不確かなエンティティも返すかどうか
        """
        if bp.dtid not in self.mentions:
            return []
        mention = self.mentions[bp.dtid]
        eids = mention.all_eids if include_uncertain else mention.eids
        return [self.entities[eid] for eid in eids]

    def pas_list(self) -> List[Pas]:
        return list(self._pas.values())

    def get_predicates(self) -> List[Predicate]:
        return [pas.predicate for pas in self._pas.values()]

    def get_arguments(self,
                      predicate: Predicate,
                      relax: bool = False,
                      include_optional: bool = False,
                      ) -> Dict[str, List[BaseArgument]]:
        """述語 predicate が持つ全ての項を返す

        Args:
            predicate (Predicate): 述語
            relax (bool): coreference chain によってより多くの項を返すかどうか
            include_optional (bool): 「すぐに」などの修飾的な項も返すかどうか

        Returns:
            Dict[str, List[BaseArgument]]: 格を key とする述語の項の辞書
        """
        if predicate.dtid not in self._pas:
            return {}
        pas = copy.copy(self._pas[predicate.dtid])
        pas.arguments = cPickle.loads(cPickle.dumps(pas.arguments, -1))
        if include_optional is False:
            for case in self.cases:
                pas.arguments[case] = list(filter(lambda a: a.optional is False, pas.arguments[case]))

        if relax is True:
            for case, args in self._pas[predicate.dtid].arguments.items():
                for arg in args:
                    if isinstance(arg, SpecialArgument):
                        entities = [self.entities[arg.eid]]
                    else:
                        assert isinstance(arg, Argument)
                        entities = self.get_entities(arg, include_uncertain=True)
                    for entity in entities:
                        if entity.is_special and entity.exophor != arg.midasi:
                            pas.add_special_argument(case, entity.exophor, entity.eid, 'AND')
                        for mention in entity.all_mentions:
                            if isinstance(arg, Argument) and mention.dtid == arg.dtid:
                                continue
                            pas.add_argument(case, mention, 'AND', self.mrph2dmid)

        return pas.arguments

    def get_siblings(self, mention: Mention, relax: bool = False) -> Set[Mention]:
        """mention と共参照関係にある他の全ての mention を返す"""
        mentions = set()
        for eid in mention.eids:
            entity = self.entities[eid]
            mentions.update(entity.mentions)
        if relax is True:
            for eid in mention.eids_unc:
                entity = self.entities[eid]
                mentions.update(entity.all_mentions)
        if mention in mentions:
            mentions.remove(mention)
        return mentions

    def draw_tree(self,
                  sid: str,
                  coreference: bool,
                  fh: Optional[TextIO] = None,
                  ) -> None:
        """sid で指定された文の述語項構造・共参照関係をツリー形式で fh に書き出す

        Args:
           sid (str): 出力対象の文ID
           coreference (bool): 共参照関係も出力するかどうか
           fh (Optional[TextIO]): 出力ストリーム
        """
        blist: BList = self[sid].blist
        with io.StringIO() as string:
            blist.draw_tag_tree(fh=string)
            tree_strings = string.getvalue().rstrip('\n').split('\n')
        assert len(tree_strings) == len(blist.tag_list())
        all_midasis = [m.midasi for m in self.mentions.values()]
        for predicate in filter(lambda p: p.sid == sid, self.get_predicates()):
            idx = predicate.tid
            tree_strings[idx] += '  '
            arguments = self.get_arguments(predicate)
            for case in self.cases:
                args = arguments[case]
                targets = set()
                for arg in args:
                    target = arg.midasi
                    if all_midasis.count(arg.midasi) > 1 and isinstance(arg, Argument):
                        target += str(arg.dtid)
                    targets.add(target)
                tree_strings[idx] += f'{",".join(targets)}:{case} '
        if coreference:
            for src_mention in filter(lambda m: m.sid == sid, self.mentions.values()):
                tgt_mentions = [tgt for tgt in self.get_siblings(src_mention) if tgt.dtid < src_mention.dtid]
                targets = set()
                for tgt_mention in tgt_mentions:
                    target = tgt_mention.midasi
                    if all_midasis.count(target) > 1:
                        target += str(tgt_mention.dtid)
                    targets.add(target)
                for eid in src_mention.eids:
                    entity = self.entities[eid]
                    if entity.is_special:
                        targets.add(entity.exophor)
                if not targets:
                    continue
                idx = src_mention.tid
                tree_strings[idx] += '  ＝:'
                tree_strings[idx] += ','.join(targets)

        print('\n'.join(tree_strings), file=fh)

    def stat(self) -> dict:
        """calculate document statistics"""
        ret = dict()
        ret['num_sents'] = len(self)
        ret['num_tags'] = len(self.tag_list())
        ret['num_mrphs'] = len(self.mrph_list())
        ret['num_taigen'] = sum(1 for tag in self.tag_list() if '体言' in tag.features)
        ret['num_yougen'] = sum(1 for tag in self.tag_list() if '用言' in tag.features)
        ret['num_entities'] = len(self.entities)
        ret['num_special_entities'] = sum(1 for ent in self.entities.values() if ent.is_special)

        num_mention = num_taigen = num_yougen = 0
        for src_mention in self.mentions.values():
            tgt_mentions: Set[Mention] = self.get_siblings(src_mention)
            if tgt_mentions:
                num_mention += 1
            for tgt_mention in tgt_mentions:
                if '体言' in tgt_mention.tag.features:
                    num_taigen += 1
                if '用言' in tgt_mention.tag.features:
                    num_yougen += 1
        ret['num_mentions'] = num_mention
        ret['num_taigen_mentions'] = num_taigen
        ret['num_yougen_mentions'] = num_yougen

        return ret

    def __len__(self):
        return len(self.sid2sentence)

    def __getitem__(self, sid: str) -> Optional[Sentence]:
        if sid in self.sid2sentence:
            return self.sid2sentence[sid]
        else:
            logger.error(f'sentence: {sid} is not in this document')
            return None

    def __iter__(self) -> Iterator[Sentence]:
        return iter(self.sid2sentence.values())

    def __str__(self):
        return ''.join(sent.midasi for sent in self)
