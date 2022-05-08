import _pickle as cPickle
import copy
import io
import logging
from collections import OrderedDict, ChainMap, defaultdict
from typing import List, Dict, Set, Optional, Iterator, TextIO, Collection

import jaconv
from pyknp import BList, Bunsetsu, Tag, Morpheme, Rel

from .base_phrase import BasePhrase
from .constants import ALL_CASES, ALL_EXOPHORS, ALL_COREFS, NE_CATEGORIES
from .coreference import Mention, Entity
from .ne import NamedEntity
from .pas import Pas, Predicate, BaseArgument, Argument, SpecialArgument
from .sentence import Sentence

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Document:
    """A class to represent a document of KWDLC, KyotoCorpus, or AnnotatedFKCCorpus.

    Args:
        knp_string (str): KNP format string of the document.
        doc_id (str): A document ID.
        cases (Collection[str]): Cases to extract.
        corefs (Collection[str]): Coreference relations to extract.
        relax_cases (bool): Whether to consider relations with "≒" as those without "≒" (e.g. ガ≒格 -> ガ格).
        extract_nes (bool): Whether to extract named entities.
        use_pas_tag (bool): Whether to read predicate-argument structures from <述語項構造: > tags, not <rel> tags.

    Attributes:
        knp_string (str): KNP format string of the document.
        doc_id (str): A document ID.
        cases (Collection[str]): Cases to extract.
        corefs (Collection[str]): Coreference relations to extract.
        extract_nes (bool): Whether to extract named entities.
        sid2sentence (Dict[str, Sentence]): A mapping from a sentence ID to the corresponding sentence.
        mentions (Dict[int, Mention]): A mapping from a document-wide tag ID to the corresponding mention.
        entities (Dict[int, Entity]): A mapping from a entity ID to the corresponding entity.
        named_entities (List[NamedEntity]): Extracted named entities.
    """

    def __init__(self,
                 knp_string: str,
                 doc_id: str,
                 cases: Collection[str],
                 corefs: Collection[str],
                 relax_cases: bool,
                 extract_nes: bool,
                 use_pas_tag: bool,
                 ) -> None:
        self.knp_string: str = knp_string
        self.doc_id: str = doc_id
        self.cases: Collection[str] = cases
        self.corefs: Collection[str] = corefs
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
                    logger.warning(f'{sentence.sid}: duplicated sid found')
                self.sid2sentence[sentence.sid] = sentence
                dtid += len(sentence)
                dmid += len(sentence.mrph_list())
                buff = ''

        self._mrph2dmid: Dict[Morpheme, int] = dict(ChainMap(*(sent.mrph2dmid for sent in self.sentences)))

        self._pas: Dict[int, Pas] = OrderedDict()
        self.mentions: Dict[int, Mention] = {}
        self.entities: Dict[int, Entity] = {}
        if use_pas_tag:
            self._analyze_pas()
        else:
            self._analyze_rel()

        if extract_nes:
            self.named_entities: List[NamedEntity] = []
            self._extract_nes()

    def _analyze_pas(self) -> None:
        """Extract predicate-argument structures represented in <述語項構造: > tags."""
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
                        pas.add_argument(case, arg_bp, '')
            if pas.arguments:
                self._pas[pas.dtid] = pas

    def _analyze_rel(self) -> None:
        """Extract predicate-argument structures and coreference relations represented in <rel> tags"""
        for bp in self.bp_list():
            rels = []
            for rel in self._extract_rel_tags(bp.tag):
                if self.relax_cases:
                    if rel.atype in ALL_CASES and rel.atype.endswith('≒'):
                        rel.atype = rel.atype.rstrip('≒')  # ガ≒ -> ガ
                valid = True
                if rel.sid is not None and rel.sid not in self.sid2sentence:
                    logger.warning(f'{bp.sid}: sentence: {rel.sid} not found in {self.doc_id}')
                    valid = False
                if rel.atype in (ALL_CASES + ALL_COREFS):
                    if not (rel.atype in self.cases or rel.atype in self.corefs):
                        logger.info(f'{bp.sid}: relation type: {rel.atype} is ignored')
                        valid = False
                else:
                    logger.warning(f'{bp.sid}: unknown relation: {rel.atype}')
                if valid is True:
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
                        # create a mention and an entity when an argument is found
                        _ = self._create_mention(arg_bp)
                        pas.add_argument(rel.atype, arg_bp, rel.mode)
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

    # to extract rels with mode: '?', rewrite initializer of pyknp Features class
    @staticmethod
    def _extract_rel_tags(tag: Tag) -> List[Rel]:
        """Parse tag.fstring to extract <rel> tags."""
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
        """Add a coreference relation."""
        if rel.sid is not None:
            target_bp = self._get_bp(rel.sid, rel.tid)
            if target_bp is None:
                return
            if target_bp.dtid == source_bp.dtid:
                logger.warning(f'{source_bp.sid}: coreference with self found: {source_bp}')
                return
        else:
            target_bp = None
            if rel.target not in ALL_EXOPHORS:
                logger.warning(f'{source_bp.sid}: unknown exophor: {rel.target}')
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
        """Create a mention from the corresponding base phrase.

        If the base phrase has not registered as a mention yet, create a new mention as well as an entity.
        Otherwise, return the registered mention.

        Args:
            bp (BasePhrase): A base phrase corresponding to the mention to be created.

        Returns:
            Mention: A mention.
        """
        if bp.dtid not in self.mentions:
            # make a new coreference cluster
            mention = Mention(bp)
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
        """Create an entity.

        exophor が singleton entity だった場合を除き、新しく Entity のインスタンスを作成して返す
        singleton entity とは、「著者」や「不特定:人１」などの必ず一つしか存在しないような entity
        一方で、「不特定:人」や「不特定:物」は複数存在しうるので singleton entity ではない
        eid を指定しない場合、最後に作成した entity の次の eid を選択

        Args:
            exophor (Optional[str]): 外界照応詞(optional)
            eid (Optional[int]): エンティティID(省略推奨)

        Returns:
             Entity: An entity to be created.
        """
        if exophor:
            if exophor not in ('不特定:人', '不特定:物', '不特定:状況'):  # exophor が singleton entity だった時
                entities = [e for e in self.entities.values() if exophor == e.exophor]
                # すでに singleton entity が存在した場合、新しい entity は作らずにその entity を返す
                if entities:
                    assert len(entities) == 1  # singleton entity が1つしかないことを保証
                    return entities[0]
        eids: Set[int] = {e.eid for e in self.entities.values()}
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
        """Merge two entities.

        source_mention と se, target_mention と te の間には mention が張られているが、
        source と target 間には張られていないので、add_mention する
        se と te が同一のエンティティであり、exophor も同じか片方が None ならば te の方を削除する

        Args:
            source_mention (Mention): A source mention.
            target_mention (Mention, optional): A target mention.
            se (Entity): A source entity.
            te (Entity): A target entity.
            uncertain (bool): Whether the relation between source and target mentions is uncertain (i.e., annotated \
            with "≒").
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
        """Delete an entity.

        Remove the target entity from all the mentions of the entity as well as from self.entities.
        Note that entity IDs can have a missing number.

        Args:
            eid (int): The entity ID of the entity to be deleted.
            sid (int): The sentence ID of the sentence being analyzed when the entity is deleted.
        """
        if eid not in self.entities:
            return
        entity = self.entities[eid]
        logger.info(f'{sid}: delete entity: {eid} ({entity})')
        for mention in entity.all_mentions:
            entity.remove_mention(mention)
        self.entities.pop(eid)

    def _get_bp(self,
                sid: str,
                tid: int,
                ) -> Optional[BasePhrase]:
        """Get a base phrase from sentence ID and tag ID.

        Args:
            sid (str): A sentence ID.
            tid (int): A tag ID.

        Returns:
            Optional[BasePhrase]: The base phrase that has sentence ID of sid and tag ID of tid.
        """
        sentence = self[sid]
        if not (0 <= tid < len(sentence.bps)):
            logger.warning(f'{sid}: tag id: {tid} out of range')
            return None
        return sentence.bps[tid]

    def _extract_nes(self) -> None:
        """Extract named entities referring tag objects."""
        for sentence in self.sentences:
            tag_list = sentence.tag_list()
            # tag.features = {'NE': 'LOCATION:ダーマ神殿'}
            for tag in tag_list:
                if 'NE' not in tag.features:
                    continue
                category, name = tag.features['NE'].split(':', maxsplit=1)
                if category not in NE_CATEGORIES:
                    logger.warning(f'{sentence.sid}: unknown NE category: {category}')
                    continue
                mrph_list = [m for t in tag_list[:tag.tag_id + 1] for m in t.mrph_list()]
                mrph_span = self._find_mrph_span(name, mrph_list, tag)
                if mrph_span is None:
                    logger.warning(f'{sentence.sid}: mrph span of \'{name}\' not found')
                    continue
                ne = NamedEntity(category, name, sentence, mrph_span, self._mrph2dmid)
                self.named_entities.append(ne)

    @staticmethod
    def _find_mrph_span(name: str,
                        mrph_list: List[Morpheme],
                        tag: Tag
                        ) -> Optional[range]:
        """nameにマッチする形態素の範囲を返す"""
        for i in range(len(tag.mrph_list())):
            end_mid = len(mrph_list) - i
            mrph_span = ''
            for mrph in reversed(mrph_list[:end_mid]):
                mrph_span = mrph.midasi + mrph_span
                if mrph_span == name:
                    return range(mrph.mrph_id, end_mid)
        return None

    @property
    def sentences(self) -> List['Sentence']:
        """List of sentences in this document.

        Returns:
            List[Sentence]
        """
        return list(self.sid2sentence.values())

    @property
    def mrph2dmid(self) -> Dict[Morpheme, int]:
        """A mapping from morpheme to its document-wide ID."""
        return self._mrph2dmid

    @property
    def surf(self) -> str:
        """A surface expression of this document."""
        return ''.join(sent.surf for sent in self.sentences)

    def bnst_list(self) -> List[Bunsetsu]:
        """Return list of Bunsetsu object in pyknp."""
        return [bnst for sentence in self.sentences for bnst in sentence.bnst_list()]

    def bp_list(self) -> List[BasePhrase]:
        """Return list of base phrases."""
        return [bp for sentence in self.sentences for bp in sentence.bps]

    def tag_list(self) -> List[Tag]:
        """Return list of Tag object in pyknp."""
        return [tag for sentence in self.sentences for tag in sentence.tag_list()]

    def mrph_list(self) -> List[Morpheme]:
        """Return list of Morpheme object in pyknp."""
        return [mrph for sentence in self.sentences for mrph in sentence.mrph_list()]

    def get_entities(self, bp: BasePhrase, include_uncertain: bool = False) -> List[Entity]:
        """Return list of entities that the specified mention refers to. The mention is given as a type of BasePhrase.

        Args:
            bp (BasePhrase): A base phrase corresponds to the mention.
            include_uncertain (bool): Whether to return entities that has uncertain relation with the mention.
        """
        if bp.dtid not in self.mentions:
            return []
        mention = self.mentions[bp.dtid]
        eids = mention.all_eids if include_uncertain else mention.eids
        return [self.entities[eid] for eid in eids]

    def pas_list(self) -> List[Pas]:
        """Return list of predicate-argument structures."""
        return list(self._pas.values())

    def get_predicates(self) -> List[Predicate]:
        """Return list of predicates."""
        return [pas.predicate for pas in self._pas.values()]

    def get_arguments(self,
                      predicate: Predicate,
                      relax: bool = False,
                      include_optional: bool = False,
                      ) -> Dict[str, List[BaseArgument]]:
        """Return all the arguments that the given predicate has.

        Args:
            predicate (Predicate): A predicate.
            relax (bool): If True, return arguments that have a coreference relation with the arguments the predicate \
            has.
            include_optional (bool): If True, return adverbial arguments such as "すぐに" as well.

        Returns:
            Dict[str, List[BaseArgument]]: A mapping from a case to arguments.
        """
        if predicate.dtid not in self._pas:
            return defaultdict(list)
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
                        if entity.is_special and entity.exophor != str(arg):
                            pas.add_special_argument(case, entity.exophor, entity.eid, 'AND')
                        for mention in entity.all_mentions:
                            if isinstance(arg, Argument) and mention.dtid == arg.dtid:
                                continue
                            pas.add_argument(case, mention, 'AND')

        return pas.arguments

    def get_siblings(self, mention: Mention, relax: bool = False) -> Set[Mention]:
        """Return all the mentions that have coreference chains with the specified mention.

        Args:
            mention (Mention): A mention.
            relax (bool): If True, return coreferent mentions as well.

        Returns:
            Set[Mention]: A set of mentions.
        """
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
                  sid: Optional[str] = None,
                  coreference: bool = True,
                  fh: Optional[TextIO] = None,
                  ) -> None:
        """Write out the PAS and coreference relations in the specified sentence in a tree format.

        If sid is not specified, write out trees in all the sentences in this document.

        Args:
           sid (str, optional): A sentence ID of the target sentence.
           coreference (bool): If True, write out coreference relations as well.
           fh (TextIO, optional): The output stream.
        """
        if sid is None:
            for _sid in self.sid2sentence.keys():
                self._draw_sent_tree(_sid, coreference, fh)
        else:
            self._draw_sent_tree(sid, coreference, fh)

    def _draw_sent_tree(self,
                        sid: str,
                        coreference: bool,
                        fh: Optional[TextIO] = None,
                        ) -> None:
        """Write out the PAS and coreference relations in the specified sentence in a tree format.

        Args:
           sid (str): A sentence ID of the target sentence.
           coreference (bool): If True, write out coreference relations as well.
           fh (Optional[TextIO]): The output stream.
        """
        blist: BList = self[sid].blist
        with io.StringIO() as string:
            blist.draw_tag_tree(fh=string, show_pos=False)
            tree_strings = string.getvalue().rstrip('\n').split('\n')
        assert len(tree_strings) == len(blist.tag_list())
        all_targets = [str(m) for m in self.mentions.values()]
        tid2mention = {mention.tid: mention for mention in self.mentions.values() if mention.sid == sid}
        for bp in self[sid].bps:
            tree_strings[bp.tid] += '  '
            # predicate-argument structure
            arguments = self.get_arguments(bp)
            for case in self.cases:
                args = arguments[case]
                targets = set()
                for arg in args:
                    target = str(arg)
                    if all_targets.count(str(arg)) > 1 and isinstance(arg, Argument):
                        target += str(arg.dtid)
                    targets.add(target)
                if targets:
                    tree_strings[bp.tid] += f'{case}:{",".join(targets)} '
            # coreference
            if coreference and bp.tid in tid2mention:
                src_mention = tid2mention[bp.tid]
                tgt_mentions = [tgt for tgt in self.get_siblings(src_mention) if tgt.dtid < src_mention.dtid]
                targets = set()
                for tgt_mention in tgt_mentions:
                    target = str(tgt_mention)
                    if all_targets.count(target) > 1:
                        target += str(tgt_mention.dtid)
                    targets.add(target)
                for eid in src_mention.eids:
                    entity = self.entities[eid]
                    if entity.is_special:
                        targets.add(entity.exophor)
                if targets:
                    tree_strings[src_mention.tid] += f'＝:{",".join(targets)}'

        print('\n'.join(tree_strings), file=fh)

    def stat(self) -> dict:
        """Calculate various kinds of statistics of this document."""
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

    def __eq__(self, other: 'Document') -> bool:
        return isinstance(other, Document) and self.doc_id == other.doc_id

    def __str__(self):
        return self.surf

    def __repr__(self) -> str:
        return f'Document([' + ', '.join(sent.surf for sent in self) + f'], did={self.doc_id})'
