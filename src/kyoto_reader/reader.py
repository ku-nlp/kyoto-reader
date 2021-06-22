import _pickle as cPickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable, Iterable, Collection, Any
from collections import ChainMap
from itertools import repeat
from multiprocessing import Pool

from joblib import Parallel, delayed

from .document import Document
from .constants import ALL_CASES, ALL_COREFS, SID_PTN, SID_PTN_KWDLC

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class KyotoReader:
    """A class to manage a set of corpus documents.

    Args:
        source (Union[Path, str]): 対象の文書へのパス。ディレクトリが指定された場合、その中の全てのファイルを対象とする
        target_cases (Optional[Collection[str]]): 抽出の対象とする格。(default: 全ての格)
        target_corefs (Optional[Collection[str]]): 抽出の対象とする共参照関係(=など)。(default: 全ての関係)
        extract_nes (bool): 固有表現をコーパスから抽出するかどうか (default: True)
        relax_cases (bool): ガ≒格などをガ格として扱うか (default: False)
        knp_ext (str): KWDLC または KC ファイルの拡張子 (default: knp)
        pickle_ext (str): Document を pickle 形式で読む場合の拡張子 (default: pkl)
        use_pas_tag (bool): <rel>タグからではなく、<述語項構造:>タグから PAS を読むかどうか (default: False)
        recursive (bool): source がディレクトリの場合、文書ファイルを再帰的に探索するかどうか (default: False)
        mp_backend (Optional[str]): 'multiprocessing', 'joblib', or None (default: 'multiprocessing')
        n_jobs (int): 文書を読み込む処理の並列数 (default: -1(=コア数))
        did_from_sid (bool): 文書IDを文書中のS-IDから決定する (default: True)
    """

    def __init__(self,
                 source: Union[Path, str],
                 target_cases: Optional[Collection[str]] = None,
                 target_corefs: Optional[Collection[str]] = None,
                 extract_nes: bool = True,
                 relax_cases: bool = False,
                 use_pas_tag: bool = False,
                 knp_ext: str = '.knp',
                 pickle_ext: str = '.pkl',
                 recursive: bool = False,
                 mp_backend: Optional[str] = 'multiprocessing',
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
        self.mp_backend: Optional[str] = mp_backend if n_jobs != 0 else None
        self.n_jobs: int = n_jobs

        args_iter = ((path, did_from_sid) for path in file_paths if path.suffix == knp_ext)
        rets: List[Dict[str, str]] = self._mp_wrapper(KyotoReader.read_knp, args_iter, self.mp_backend, self.n_jobs)

        self.did2knps: Dict[str, str] = dict(ChainMap(*rets))
        self.doc_ids: List[str] = sorted(set(self.did2knps.keys()) | set(self.did2pkls.keys()))

        self.target_cases: Collection[str] = self._get_targets(target_cases, ALL_CASES, 'case')
        self.target_corefs: Collection[str] = self._get_targets(target_corefs, ALL_COREFS, 'coref')
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    @staticmethod
    def read_knp(path: Path, did_from_sid: bool) -> Dict[str, str]:
        """Read KNP format file that is located at the specified path. The file can contain multiple documents.

        Args:
            path (Path): A path to a KNP format file.
            did_from_sid (bool): If True, determine the document ID from the sentence ID in the document.

        Returns:
            Dict[str, str]: A mapping from a document ID to a KNP format string.
        """
        did2knps = {}
        with path.open() as f:
            buff = ''
            did = sid = None
            for line in f:
                if line.startswith('# S-ID:') and did_from_sid:
                    sid_string = line[7:].strip().split()[0]
                    match = SID_PTN_KWDLC.match(sid_string) or SID_PTN.match(sid_string)
                    if match is None:
                        raise ValueError(f'unsupported S-ID format: {sid_string} in {path}')
                    if did != match.group('did') or sid == match.group('sid'):
                        if did is not None:
                            did2knps[did] = buff
                            buff = ''
                        did = match.group('did')
                        sid = match.group('sid')
                buff += line
            if did_from_sid is False:
                did = path.stem
            if did is not None and buff:
                did2knps[did] = buff
            else:
                logger.warning(f'empty file found and skipped: {path}')
        return did2knps

    @staticmethod
    def _get_targets(input_: Optional[Collection],
                     all_: Collection[Any],
                     type_: str,
                     ) -> Collection[Any]:
        """Return a list of known relations."""
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
        """Process one document following the given document ID.

        Args:
            doc_id (str): An ID of a document to process.
        """
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
                          doc_ids: Iterable[str],
                          n_jobs: Optional[int] = None,
                          ) -> List[Optional[Document]]:
        """Process multiple documents following the given document IDs.

        Args:
            doc_ids (List[str]): IDs of documents to process.
            n_jobs (int): The number of processes spawned to finish this task. (default: inherit from self)
        """
        if n_jobs is None:
            n_jobs = self.n_jobs
        args_iter = zip(repeat(self), doc_ids)
        return self._mp_wrapper(KyotoReader.process_document, args_iter, self.mp_backend, n_jobs)

    def process_all_documents(self,
                              n_jobs: Optional[int] = None,
                              ) -> List[Optional[Document]]:
        """Process all documents that KyotoReader has loaded.

        Args:
            n_jobs (int): The number of processes spawned to finish this task. (default: inherit from self)
        """
        if n_jobs is None:
            n_jobs = self.n_jobs
        return self.process_documents(self.doc_ids, n_jobs)

    @staticmethod
    def _mp_wrapper(func: Callable, args: Iterable[tuple], backend: Optional[str], n_jobs: int) -> list:
        """Call func with given args in multiprocess.
        Joblib or multiprocessing are used for multiprocessing backend.
        If None is specified as backend, do not perform multiprocessing.

        Args:
            func (Callable): A function to be called.
            args (List[tuple]): List of arguments for the function.
            backend (Optional[str]): 'multiprocessing', 'joblib', or None (default: 'multiprocessing')

        Returns:
            list: The output of func for each arguments.
        """
        if backend == 'multiprocessing':
            with Pool(n_jobs if n_jobs >= 0 else None) as pool:
                return list(pool.starmap(func, args))
        elif backend == 'joblib':
            parallel = Parallel(n_jobs=n_jobs)
            return parallel([delayed(func)(*arg) for arg in args])
        elif backend is None:
            return [func(*arg) for arg in args]
        else:
            raise NotImplementedError

    def __len__(self):
        return len(self.doc_ids)

    def __getitem__(self, doc_id: str) -> Document:
        return self.process_document(doc_id)
