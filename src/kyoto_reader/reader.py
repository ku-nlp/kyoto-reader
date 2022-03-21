import _pickle as cPickle
import gzip
import logging
import tarfile
import zipfile
from collections import ChainMap
from dataclasses import dataclass
from functools import partial
from itertools import repeat, product
from multiprocessing import Pool
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable, Iterable, Collection, Any

from joblib import Parallel, delayed

from .constants import ALL_CASES, ALL_COREFS, SID_PTN, SID_PTN_KWDLC
from .document import Document

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


@dataclass
class ArchiveHandler:
    opener: Callable
    # Name of function to list up all files in the archive
    list_func_name: str


tar_gzip_handler = ArchiveHandler(tarfile.open, "getnames")
zip_handler = ArchiveHandler(zipfile.ZipFile, "namelist")


class KyotoReader:
    """A class to manage a set of corpus documents.
    Compressed file is supported.
    However, nested compression (e.g. .knp.gz in zip file) is not supported.

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

    ARCHIVE2HANDLER: Dict[str, Callable] = {
        ".tar.gz": tar_gzip_handler,
        ".zip": zip_handler
    }

    COMPRESS2OPENER: Dict[str, Callable] = {
        ".gz": partial(gzip.open, mode='rt'),
    }

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
        # Yields all allowed single-file extension (e.g. .knp, .pkl.gz)
        allowed_single_file_ext = list(
            "".join(x) for x in product((knp_ext, pickle_ext), (("",) + tuple(KyotoReader.COMPRESS2OPENER.keys()))))
        source = Path(source)
        source_suffix = source.suffix
        self.archive_path, self.archive_handler = None, None

        if source.is_dir():
            logger.info(f'got directory path, files in the directory is treated as source files')
            file_paths: List[Path] = []
            for ext in allowed_single_file_ext:
                file_paths += sorted(source.glob(f'**/*{ext}' if recursive else f'*{ext}'))
        # If source file is an archive, remember its path and handler
        elif source_suffix in KyotoReader.ARCHIVE2HANDLER:
            logger.info(f'got compressed file, files in the compressed file are treated as source files')
            self.archive_path = source
            self.archive_handler = KyotoReader.ARCHIVE2HANDLER[source_suffix]
            with self.archive_handler.opener(source) as f:
                file_paths = sorted(
                    Path(x) for x in getattr(f, KyotoReader.ARCHIVE2HANDLER[source_suffix].list_func_name)()
                    if Path(x).suffix in allowed_single_file_ext
                )
        else:
            logger.info(f'got file path, this file is treated as a source knp file')
            file_paths = [source]
        self.did2pkls: Dict[str, Path] = {path.stem: path for path in file_paths if pickle_ext in path.suffixes}
        self.mp_backend: Optional[str] = mp_backend if n_jobs != 0 else None
        if self.mp_backend is not None and self.archive_path is not None:
            logger.info("Multiprocessing with archive is too slow, so it is disabled")
            logger.info(
                "Run without multiprocessing can be relatively slow, so please consider unarchive the archive file")
            self.mp_backend = None
        self.n_jobs: int = n_jobs

        if self.archive_path is not None:
            args_iter = (
                (path, did_from_sid, self.archive_handler.opener, self.archive_path)
                for path in file_paths if knp_ext in path.suffixes
            )
            with self.archive_handler.opener(self.archive_path) as archive:
                args_iter = (
                    (path, did_from_sid, archive)
                    for path in file_paths if knp_ext in path.suffixes
                )
                rets: List[Dict[str, str]] = self._mp_wrapper(KyotoReader.read_knp, args_iter, self.mp_backend,
                                                              self.n_jobs)
        else:
            args_iter = ((path, did_from_sid) for path in file_paths if knp_ext in path.suffixes)
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
    def read_knp(
        path: Path,
        did_from_sid: bool,
        archive: Optional[Union[zipfile.ZipFile, tarfile.TarFile]] = None
    ) -> Dict[str, str]:
        """Read KNP format file that is located at the specified path. The file can contain multiple documents.

        Args:
            path (Path): A path to a KNP format file.
            did_from_sid (bool): If True, determine the document ID from the sentence ID in the document.
            archive (Optional[Union[zipfile.ZipFile, tarfile.TarFile]]): An archive to read the document from.

        Returns:
            Dict[str, str]: A mapping from a document ID to a KNP format string.
        """
        did2knps = {}

        def _read_knp(f):
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

        if archive is not None:
            with archive.open(str(path)) as f:
                text = f.read().decode("utf-8")
                _read_knp(text.split("\n"))
        else:
            if any(key in path.suffixes for key in KyotoReader.COMPRESS2OPENER):
                compress = set(path.suffixes) & set(KyotoReader.COMPRESS2OPENER.keys())
                assert len(compress) == 1
                opener = KyotoReader.COMPRESS2OPENER[compress.pop()]
            else:
                opener = open
            with opener(path) as f:
                _read_knp(f.readlines())

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

    def process_document(
        self,
        doc_id: str,
        archive: Optional[Union[zipfile.ZipFile, tarfile.TarFile]] = None
    ) -> Optional[Document]:
        """Process one document following the given document ID.

        Args:
            doc_id (str): An ID of a document to process.
            archive (Optional[Union[zipfile.ZipFile, tarfile.TarFile]]): An archive to read the document from.
        """
        if doc_id in self.did2pkls:
            opener = open if archive is None else archive.open
            with opener(self.did2pkls[doc_id], 'rb') as f:
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
        if self.archive_path is not None:
            assert self.mp_backend is None
            with self.archive_handler.opener(self.archive_path) as archive:
                args_iter = zip(repeat(self), doc_ids, repeat(archive))
                return self._mp_wrapper(KyotoReader.process_document, args_iter, self.mp_backend, n_jobs)
        else:
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
