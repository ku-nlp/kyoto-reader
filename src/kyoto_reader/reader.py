import io
import sys
import copy
import _pickle as cPickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Union
from collections import OrderedDict

from pyknp import BList, Bunsetsu, Tag, Morpheme, Rel
import mojimoji

from kyoto_reader.pas import Pas, Predicate, BaseArgument, Argument, SpecialArgument
from kyoto_reader.coreference import Mention, Entity
from kyoto_reader.ne import NamedEntity
from kyoto_reader.constants import ALL_CASES, CORE_CASES, ALL_EXOPHORS, ALL_COREFS, CORE_COREFS, NE_CATEGORIES
from kyoto_reader.base_phrase import BasePhrase


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

"""
# TODO

# MEMO
- corefタグは用言に対しても振られる
- 用言かつ体言の基本句もある
"""


class KyotoReader:
    """ KWDLC(または Kyoto Corpus)の文書集合を扱うクラス

    Args:
        source (Path or str): 入力ソース．Path オブジェクトを指定するとその場所のファイルを読む
        target_cases (list): 抽出の対象とする格
        target_corefs (list): 抽出の対象とする共参照関係(=など)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        knp_ext (str): KWDLC (or KC) ファイルの拡張子
        pickle_ext (str): Document を pickle 形式で読む場合の拡張子
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか
    """
    def __init__(self,
                 source: Union[Path, str],
                 target_cases: Optional[List[str]],
                 target_corefs: Optional[List[str]],
                 extract_nes: bool = True,
                 use_pas_tag: bool = False,
                 knp_ext: str = '.knp',
                 pickle_ext: str = '.pkl',
                 ) -> None:
        if not (isinstance(source, Path) or isinstance(source, str)):
            raise TypeError(f'source must be Path or str type, but got {type(source)}')
        if isinstance(source, Path):
            if source.is_dir():
                logger.info(f'got directory path, files in the directory is treated as source files')
                file_paths: List[Path] = sorted(source.glob(f'*{knp_ext}')) + sorted(source.glob(f'*{pickle_ext}'))
                self.did2source: Dict[str, Union[Path, str]] = OrderedDict((path.stem, path) for path in file_paths)
            else:
                logger.info(f'got file path, this file is treated as a source knp file')
                self.did2source: Dict[str, Union[Path, str]] = {source.stem: source}
        else:
            logger.info(f'got string, this string is treated as a source knp string')
            self.did2source: Dict[str, Union[Path, str]] = {'doc': source}

        self.target_cases: List[str] = self._get_target(target_cases, ALL_CASES, CORE_CASES, 'case')
        self.target_corefs: List[str] = self._get_target(target_corefs, ALL_COREFS, CORE_COREFS, 'coref')
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    @staticmethod
    def _get_target(input_: Optional[list],
                    all_: list,
                    default: list,
                    type_: str,
                    ) -> list:
        if input_ is None:
            return default
        target = []
        for item in input_:
            if item not in all_:
                logger.warning(f'unknown target {type_}: {item}')
                continue
            target.append(item)

        return target

    def get_doc_ids(self) -> List[str]:
        return list(self.did2source.keys())

    def process_document(self, doc_id: str) -> Optional['Document']:
        if doc_id not in self.did2source:
            logger.error(f'unknown document id: {doc_id}')
            return None
        if isinstance(self.did2source[doc_id], Path):
            if self.did2source[doc_id].suffix == self.pickle_ext:
                with self.did2source[doc_id].open(mode='rb') as f:
                    return cPickle.load(f)
            elif self.did2source[doc_id].suffix == self.knp_ext:
                with self.did2source[doc_id].open() as f:
                    input_string = f.read()
            else:
                return None
        else:
            input_string = self.did2source[doc_id]
        return Document(input_string,
                        doc_id,
                        self.target_cases,
                        self.target_corefs,
                        self.extract_nes,
                        self.use_pas_tag)

    def process_documents(self, doc_ids: List[str]) -> Iterator[Optional['Document']]:
        for doc_id in doc_ids:
            yield self.process_document(doc_id)

    def process_all_documents(self) -> Iterator['Document']:
        for doc_id in self.did2source.keys():
            yield self.process_document(doc_id)


class Document:
    """ KWDLC(または Kyoto Corpus)の1文書を扱うクラス

    Args:
        knp_string (str): 文書ファイルの内容(knp形式)
        doc_id (str): 文書ID
        target_cases (list): 抽出の対象とする格
        target_corefs (list): 抽出の対象とする共参照関係(=など)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか

    Attributes:
        knp_string (str): 文書ファイルの内容(knp形式)
        doc_id (str): 文書ID(ファイル名から拡張子を除いたもの)
        target_cases (list): 抽出の対象とする格
        target_corefs (list): 抽出の対象とする共参照関係(=など)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか
        sid2sentence (dict): 文IDと文を紐付ける辞書
        bnst2dbid (dict): 文節IDと文書レベルの文節IDを紐付ける辞書
        tag2dtid (dict): 基本句IDと文書レベルの基本句IDを紐付ける辞書
        mrph2dmid (dict): 形態素IDと文書レベルの形態素IDを紐付ける辞書
        mentions (dict): dtid を key とする mention の辞書
        entities (dict): entity id を key として entity オブジェクトが格納されている
        named_entities (list): 抽出した固有表現
    """
    def __init__(self,
                 knp_string: str,
                 doc_id: str,
                 target_cases: List[str],
                 target_corefs: List[str],
                 extract_nes: bool,
                 use_pas_tag: bool,
                 ) -> None:
        self.knp_string = knp_string
        self.doc_id = doc_id
        self.target_cases: List[str] = target_cases
        self.target_corefs: List[str] = target_corefs
        self.extract_nes: bool = extract_nes

        self.sid2sentence: Dict[str, BList] = OrderedDict()
        buff = []
        for line in knp_string.strip().split('\n'):
            buff.append(line)
            if line.strip() == 'EOS':
                sentence = BList('\n'.join(buff) + '\n')
                self.sid2sentence[sentence.sid] = sentence
                buff = []

        self.bnst2dbid = {}
        self.tag2dtid = {}
        self.mrph2dmid = {}
        self._assign_document_wide_id()

        self._pas: Dict[int, Pas] = OrderedDict()
        self.mentions: Dict[int, Mention] = OrderedDict()
        self.entities: Dict[int, Entity] = OrderedDict()
        if use_pas_tag:
            self._extract_pas()
        else:
            self._extract_relations()

        if extract_nes:
            self.named_entities: List[NamedEntity] = []
            self._extract_nes()

    def _assign_document_wide_id(self) -> None:
        """文節・基本句・形態素に文書全体に渡る通し番号を振る"""
        dbid, dtid, dmid = 0, 0, 0
        for sentence in self.sentences:
            for bnst in sentence.bnst_list():
                for tag in bnst.tag_list():
                    for mrph in tag.mrph_list():
                        self.mrph2dmid[mrph] = dmid
                        dmid += 1
                    self.tag2dtid[tag] = dtid
                    dtid += 1
                self.bnst2dbid[bnst] = dbid
                dbid += 1

    def _extract_pas(self) -> None:
        """extract predicate argument structure from <述語項構造:> tag in knp string"""
        sid2idx = {sid: idx for idx, sid in enumerate(self.sid2sentence.keys())}
        for tag in self.tag_list():
            if tag.pas is None:
                continue
            pas = Pas(BasePhrase(tag, self.tag2dtid[tag], tag.pas.sid, self.mrph2dmid))
            for case, arguments in tag.pas.arguments.items():
                for arg in arguments:
                    arg.midasi = mojimoji.han_to_zen(arg.midasi, ascii=False)  # 不特定:人1 -> 不特定:人１
                    # exophor
                    if arg.flag == 'E':
                        entity = self._create_entity(exophor=arg.midasi, eid=arg.eid)
                        pas.add_special_argument(case, arg.midasi, entity.eid, '')
                    else:
                        sid = self.sentences[sid2idx[arg.sid] - arg.sdist].sid
                        arg_bp = self._get_bp(sid, arg.tid)
                        mention = self._create_mention(arg_bp)
                        pas.add_argument(case, mention, arg.midasi, '', self.mrph2dmid)
            if pas.arguments:
                self._pas[pas.dtid] = pas

    def _extract_relations(self) -> None:
        """extract predicate argument structure and coreference relation from <rel> tag in knp string"""
        tag2sid = {tag: sentence.sid for sentence in self.sentences for tag in sentence.tag_list()}
        for tag in self.tag_list():
            rels = []
            for rel in self._extract_rel_tags(tag):
                if rel.sid is not None and rel.sid not in self.sid2sentence:
                    logger.warning(f'{tag2sid[tag]:24}sentence: {rel.sid} not found in {self.doc_id}')
                    continue
                if rel.atype not in (self.target_cases + self.target_corefs):
                    logger.info(f'{tag2sid[tag]:24}relation type: {rel.atype} is ignored')
                    continue
                rels.append(rel)
            src_bp = BasePhrase(tag, self.tag2dtid[tag], tag2sid[tag], self.mrph2dmid)
            # extract PAS
            pas = Pas(src_bp)
            for rel in rels:
                if rel.atype in self.target_cases:
                    if rel.sid is not None:
                        assert rel.tid is not None
                        arg_bp = self._get_bp(rel.sid, rel.tid)
                        if arg_bp is None:
                            continue
                        mention = self._create_mention(arg_bp)  # 項を発見したら同時に mention と entity を作成
                        pas.add_argument(rel.atype, mention, rel.target, rel.mode, self.mrph2dmid)
                    # exophora
                    else:
                        if rel.target == 'なし':
                            pas.set_arguments_optional(rel.atype)
                            continue
                        if rel.target not in ALL_EXOPHORS:
                            logger.warning(f'{pas.sid:24}unknown exophor: {rel.target}')
                            continue
                        entity = self._create_entity(rel.target)
                        pas.add_special_argument(rel.atype, rel.target, entity.eid, rel.mode)
            if pas.arguments:
                self._pas[pas.dtid] = pas

            # extract coreference
            for rel in rels:
                if rel.atype in self.target_corefs:
                    if rel.mode in ('', 'AND'):  # ignore "OR" and "?"
                        self._add_corefs(src_bp, rel)

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
                    rel.target = mojimoji.han_to_zen(rel.target, ascii=False)  # 不特定:人1 -> 不特定:人１
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
                logger.warning(f'{source_bp.sid:24}coreference with self found: {source_bp.midasi}')
                return
        else:
            target_bp = None
            if rel.target not in ALL_EXOPHORS:
                logger.warning(f'{source_bp.sid:24}unknown exophor: {rel.target}')
                return

        source_mention = self._create_mention(source_bp)
        for eid in list(source_mention.eids):
            source_entity = self.entities[eid]
            if rel.sid is not None:
                target_mention = self._create_mention(target_bp)
                for target_eid in list(target_mention.eids):
                    target_entity = self.entities[target_eid]
                    self._merge_entities(source_mention, target_mention, source_entity, target_entity)
            else:
                target_entity = self._create_entity(exophor=rel.target)
                self._merge_entities(source_mention, None, source_entity, target_entity)

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
            entity.add_mention(mention)
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
            logger.warning(f'{self.doc_id:24}eid: {eid_} is already used. use eid: {eid} instead.')
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
                        ) -> None:
        """2つのエンティティをマージする

        片方だけが exophor だった場合、se を exophor になるようにして te を削除
        両方が同じ exophor だった場合、te を削除
        両方が違う exophor だった場合、互いに mention を張り、どちらも残す

        Args:
            source_mention (Mention): 参照元メンション
            target_mention (Mention?): 参照先メンション
            se: 参照元エンティティ
            te: 参照先エンティティ
        """
        if se is te:
            return
        if se.exophor is not None and te.exophor is not None and se.exophor != te.exophor:
            if target_mention is not None:
                se.add_mention(target_mention)
            te.add_mention(source_mention)
            return
        if se.exophor is None:
            se.exophor = te.exophor
        for tm in te.mentions:
            se.add_mention(tm)
        for arg in [arg for pas in self._pas.values() for args in pas.arguments.values() for arg in args]:
            if isinstance(arg, SpecialArgument) and arg.eid == te.eid:
                arg.eid = se.eid
        self._delete_entity(te.eid, source_mention.sid)

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
        logger.info(f'{sid:24}delete entity: {eid} ({entity.midasi})')
        for mention in entity.mentions:
            mention.eids.remove(eid)
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
        tag_list = self.sid2sentence[sid].tag_list()
        if not (0 <= tid < len(tag_list)):
            logger.warning(f'{sid:24}tag id: {tid} out of range')
            return None
        tag = tag_list[tid]
        return BasePhrase(tag, self.tag2dtid[tag], sid, self.mrph2dmid)

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
                    logger.warning(f'{sentence.sid:24}unknown NE category: {category}')
                    continue
                mrph_list = [m for t in tag_list[:tag.tag_id + 1] for m in t.mrph_list()]
                mrph_span = self._find_mrph_span(midasi, mrph_list, tag)
                if mrph_span is None:
                    logger.warning(f'{sentence.sid:24}mrph span of "{midasi}" not found')
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
    def sentences(self) -> List[BList]:
        return list(self.sid2sentence.values())

    def bnst_list(self) -> List[Bunsetsu]:
        return [bnst for sentence in self.sentences for bnst in sentence.bnst_list()]

    def tag_list(self) -> List[Tag]:
        return [tag for sentence in self.sentences for tag in sentence.tag_list()]

    def mrph_list(self) -> List[Morpheme]:
        return [mrph for sentence in self.sentences for mrph in sentence.mrph_list()]

    def get_entities(self, tag: Tag) -> List[Entity]:
        return [e for e in self.entities.values() for m in e.mentions if m.dtid == self.tag2dtid[tag]]

    def pas_list(self) -> List[Pas]:
        return list(self._pas.values())

    def get_predicates(self) -> List[Predicate]:
        return [pas.predicate for pas in self._pas.values()]

    def get_arguments(self,
                      predicate: Predicate,
                      relax: bool = False,
                      include_optional: bool = False,  # 「すぐに」などの修飾的な項も返すかどうか
                      ) -> Dict[str, List[BaseArgument]]:
        if predicate.dtid not in self._pas:
            return {}
        pas = copy.copy(self._pas[predicate.dtid])
        pas.arguments = cPickle.loads(cPickle.dumps(pas.arguments, -1))
        if include_optional is False:
            for case in self.target_cases:
                pas.arguments[case] = list(filter(lambda a: a.optional is False, pas.arguments[case]))

        if relax is True:
            for case, args in self._pas[predicate.dtid].arguments.items():
                for arg in args:
                    for eid in arg.eids:
                        entity = self.entities[eid]
                        if entity.is_special and entity.exophor != arg.midasi:
                            pas.add_special_argument(case, entity.exophor, entity.eid, 'AND')
                        for mention in entity.mentions:
                            if isinstance(arg, Argument) and mention.dtid == arg.dtid:
                                continue
                            pas.add_argument(case, mention, mention.midasi, 'AND', self.mrph2dmid)

        return pas.arguments

    def get_siblings(self, mention: Mention) -> List[Mention]:
        """mention と共参照関係にある他の全ての mention を返す"""
        mentions = []
        for eid in mention.eids:
            entity = self.entities[eid]
            for mention_ in entity.mentions:
                if mention_ == mention or mention_ in mentions:
                    continue
                mentions.append(mention_)
        return mentions

    def draw_tree(self,
                  sid: str,
                  fh=None,
                  ) -> None:
        sentence: BList = self[sid]
        with io.StringIO() as string:
            sentence.draw_tag_tree(fh=string)
            tree_strings = string.getvalue().rstrip('\n').split('\n')
        tag_list = sentence.tag_list()
        assert len(tree_strings) == len(tag_list)
        predicates: List[Predicate] = [p for p in self.get_predicates() if p.sid == sid]
        for predicate in predicates:
            idx = predicate.tid
            arguments = self.get_arguments(predicate)
            tree_strings[idx] += '  '
            for case in self.target_cases:
                argument = arguments[case]
                arg = argument[0].midasi if argument else 'NULL'
                tree_strings[idx] += f'{arg}:{case} '

        for src_mention in self.mentions.values():
            tgt_mentions = [tgt for tgt in self.get_siblings(src_mention) if tgt.dtid < src_mention.dtid]
            if not tgt_mentions:
                continue
            idx = src_mention.tid
            tree_strings[idx] += '  =:'
            targets = set()
            for tgt_mention in tgt_mentions:
                target = ''.join(mrph.midasi for mrph in tgt_mention.tag.mrph_list() if '<内容語>' in mrph.fstring)
                if not target:
                    target = tgt_mention.midasi
                targets.add(target + str(tgt_mention.dtid))
            for eid in src_mention.eids:
                entity = self.entities[eid]
                if entity.is_special:
                    targets.add(entity.exophor)
            tree_strings[idx] += ' '.join(targets)

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
            tgt_mentions: List[Mention] = self.get_siblings(src_mention)
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

    def __getitem__(self, sid: str):
        if sid in self.sid2sentence:
            return self.sid2sentence[sid]
        else:
            logger.error(f'sentence: {sid} is not in this document')
            return None

    def __iter__(self):
        return iter(self.sid2sentence.values())
