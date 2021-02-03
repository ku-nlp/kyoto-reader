import _pickle as cPickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from collections import ChainMap
from itertools import repeat

from joblib import Parallel, delayed
from multiprocessing import Pool

from .document import Document
from .constants import ALL_CASES, ALL_COREFS, SID_PTN, SID_PTN_KWDLC

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class KyotoReader:
    """ KWDLC(または Kyoto Corpus)の文書集合を扱うクラス

    Args:
        source (Union[Path, str]): 対象の文書へのパス。ディレクトリが指定された場合、その中の全てのファイルを対象とする
        target_cases (Optional[List[str]]): 抽出の対象とする格。(default: 全ての格)
        target_corefs (Optional[List[str]]): 抽出の対象とする共参照関係(=など)。(default: 全ての関係)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか (default: True)
        relax_cases (bool): ガ≒格などをガ格として扱うか (default: False)
        knp_ext (str): KWDLC または KC ファイルの拡張子 (default: knp)
        pickle_ext (str): Document を pickle 形式で読む場合の拡張子 (default: pkl)
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか (default: False)
        recursive (bool): source がディレクトリの場合、文書ファイルを再帰的に探索するかどうか (default: False)
        n_jobs (int): 文書を読み込む処理の並列数 (default: -1(=コア数))
        did_from_sid (bool): 文書IDを文書中のS-IDから決定する (default: True)
    """

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
                 n_jobs: int = -1,
                 did_from_sid: bool = True,
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
        self.n_jobs = n_jobs

        args_iter = ((path, did_from_sid) for path in file_paths if path.suffix == knp_ext)
        with Pool(n_jobs if n_jobs >= 0 else None) as pool:
            rets: List[Dict[str, str]] = list(pool.starmap(KyotoReader.read_knp, args_iter))

        self.did2knps: Dict[str, str] = dict(ChainMap(*rets))
        self.doc_ids: List[str] = sorted(set(self.did2knps.keys()) | set(self.did2pkls.keys()))

        self.target_cases: List[str] = self._get_targets(target_cases, ALL_CASES, 'case')
        self.target_corefs: List[str] = self._get_targets(target_corefs, ALL_COREFS, 'coref')
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    @staticmethod
    def read_knp(path: Path, did_from_sid: bool) -> Dict[str, str]:
        did2knps = {}
        with path.open() as f:
            buff = ''
            did = sid = None
            for line in f:
                if line.startswith('# S-ID:') and did_from_sid:
                    sid_string = line[7:].strip().split()[0]
                    match = SID_PTN_KWDLC.match(sid_string)
                    if match is None:
                        match = SID_PTN.match(sid_string)
                    if match is None:
                        raise ValueError(f'unsupported S-ID format: {sid_string} in {path}')
                    if did != match.group('did') or sid == match.group('sid'):
                        if did is not None:
                            did2knps[did] = buff
                            buff = ''
                        did = match.group('did')
                        sid = match.group('sid')
                buff += line
            if not did_from_sid:
                did = path.stem
            if did is not None and buff:
                did2knps[did] = buff
            else:
                logger.warning(f'empty file found and skipped: {path}')
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

    def process_document(self, doc_id: str) -> Optional[Document]:
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

    def process_documents(self,
                          doc_ids: List[str],
                          backend: Optional[str] = 'multiprocessing'
                          ) -> List[Optional[Document]]:
        """Process documents following given doc_ids.
        Joblib or multiprocessing are used for multiprocessing backend.
        If None is specified, do not perform multiprocessing.

        Args:
            doc_ids (List[str]): doc_id list to process
            backend (Optional[str]): 'multiprocessing', 'joblib', or None (default: 'multiprocessing')
        """
        if backend == 'multiprocessing':
            self_doc_ids_pair_iter = zip(repeat(self), doc_ids)
            with Pool(self.n_jobs if self.n_jobs >= 0 else None) as pool:
                return list(pool.starmap(KyotoReader._unwrap_self, self_doc_ids_pair_iter))
        elif backend == 'joblib':
            parallel = Parallel(n_jobs=self.n_jobs)
            return parallel([delayed(KyotoReader._unwrap_self)(self, x) for x in doc_ids])
        elif backend is None:
            return [self.process_document(doc_id) for doc_id in doc_ids]
        else:
            raise NotImplementedError

    def process_all_documents(self, backend: Optional[str] = 'multiprocessing') -> List[Optional[Document]]:
        """Process all documents that KyotoReader has loaded.
        Joblib or multiprocessing are used for multiprocessing backend.
        If None is specified, do not perform multiprocessing.

        Args:
            backend (Optional[str]): 'multiprocessing', 'joblib', or None (default: 'multiprocessing')
        """
        return self.process_documents(self.doc_ids, backend)

    @staticmethod
    def _unwrap_self(self_, *arg, **kwarg):
        return KyotoReader.process_document(self_, *arg, **kwarg)

    def __len__(self):
        return len(self.doc_ids)

    def __getitem__(self, doc_id: str) -> Document:
        return self.process_document(doc_id)
