import gzip
import io
import logging
import pickle
import tarfile
import zipfile
from collections import ChainMap
from contextlib import contextmanager, nullcontext
from enum import Enum
from itertools import repeat
from multiprocessing import Pool
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable, Iterable, Collection, Any, BinaryIO, TextIO

from joblib import Parallel, delayed

from .constants import ALL_CASES, ALL_COREFS, SID_PTN, SID_PTN_KWDLC
from .document import Document

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# 実装方針
"""
dir と archive は分ける
.gz.zip は無理なのでサポートしない
または予め archive は tmp dir に吐くとか
サポートするのは以下
- archive
- directory
- compressed files in directory
- file
- compressed file
"""


class ArchiveType(Enum):
    """
    Enum for file collection types.
    """
    TAR_GZ = '.tar.gz'
    ZIP = '.zip'


class ArchiveHandler:
    def __init__(self, path: Path):
        self.path: Path = path
        self.type: ArchiveType = self._get_type(path)
        self.members: List[str] = self._list_members()

    @staticmethod
    def _get_type(path: Path) -> ArchiveType:
        assert path.is_file() is True
        if str(path).endswith(ArchiveType.TAR_GZ.value):
            return ArchiveType.TAR_GZ
        elif str(path).endswith(ArchiveType.ZIP.value):
            return ArchiveType.ZIP
        else:
            raise ValueError(f'Unsupported archive type: {path}')

    def _list_members(self) -> List[str]:
        if self.type == ArchiveType.TAR_GZ:
            with tarfile.open(self.path, mode='r') as f:
                return f.getnames()
        elif self.type == ArchiveType.ZIP:
            with zipfile.ZipFile(self.path, mode='r') as f:
                return f.namelist()
        else:
            raise ValueError(f'Unsupported archive type: {self.type}')

    @contextmanager
    def open(self) -> Union[zipfile.ZipFile, tarfile.TarFile]:
        file = None
        try:
            if self.type == ArchiveType.TAR_GZ:
                file = tarfile.open(self.path, mode='r')
            elif self.type == ArchiveType.ZIP:
                file = zipfile.ZipFile(self.path, mode='r')
            else:
                raise ValueError(f'Unsupported archive type: {self.type}')
            yield file
        finally:
            hasattr(file, 'close') and file.close()

    @contextmanager
    def open_member(self, archive: Union[zipfile.ZipFile, tarfile.TarFile], member: str) -> BinaryIO:
        file = None
        try:
            if self.type == ArchiveType.TAR_GZ:
                file = archive.extractfile(member)
            elif self.type == ArchiveType.ZIP:
                file = archive.open(member)
            else:
                raise ValueError(f'Unsupported archive type: {self.type}')
            yield file
        finally:
            hasattr(file, 'close') and file.close()

    @classmethod
    def is_supported_path(cls, path: Path) -> bool:
        return any(str(path).endswith(t.value) for t in ArchiveType)


class FileType(Enum):
    """Enum for file types."""
    GZ = '.gz'
    # XZ = '.xz'
    UNCOMPRESSED = ''


class FileHandler:
    def __init__(self, path: Path):
        self.path = path
        self.type: FileType = self._get_type(path)

    @property
    def content_basename(self) -> str:
        if self.type == FileType.UNCOMPRESSED:
            return self.path.name
        return self.path.name[:-len(self.type.value)]

    @staticmethod
    def _get_type(path: Path) -> FileType:
        if path.suffix == FileType.GZ.value:
            return FileType.GZ
        return FileType.UNCOMPRESSED

    @contextmanager
    def open(self):
        file = None
        try:
            if self.type == FileType.GZ:
                file = gzip.open(self.path, mode='rt')
            elif self.type == FileType.UNCOMPRESSED:
                file = self.path.open(mode='rt')
            else:
                raise ValueError(f'Unsupported collection type: {self.type}')
            yield file
        finally:
            hasattr(file, 'close') and file.close()

    def __lt__(self, other):
        return self.path < other.path


# COMPRESS2OPEN: Dict[str, Callable] = {
#     ".gz": partial(gzip.open, mode='rt'),
# }


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
                 # recursive: bool = False,
                 mp_backend: Optional[str] = 'multiprocessing',
                 n_jobs: int = -1,
                 did_from_sid: bool = True,
                 # archive2handler: Dict[str, ArchiveHandler] = ARCHIVE2HANDLER,
                 # compress2open: Dict[str, Callable] = COMPRESS2OPEN
                 ) -> None:
        if not (isinstance(source, Path) or isinstance(source, str)):
            raise TypeError(f"document source must be Path or str type, but got '{type(source)}' type")
        source = Path(source)
        self.archive_handler = None

        if source.is_dir():
            logger.info(f'got a directory path, files in the directory are treated as source files')
            file_paths: List[FileHandler] = sorted(FileHandler(p) for p in source.glob(f'**/*') if p.is_file())
        elif ArchiveHandler.is_supported_path(source):
            logger.info(f'got an archive file path, files in the archive are treated as source files')
            self.archive_handler = ArchiveHandler(source)
            file_paths: List[FileHandler] = sorted(FileHandler(Path(p)) for p in self.archive_handler.members)
        else:
            logger.info(f'got a single file path, this file is treated as a source file')
            assert source.is_file() is True
            file_paths: List[FileHandler] = [FileHandler(source)]

        self.did2pkls = {path: path for path in file_paths if path.content_basename.endswith(pickle_ext)}

        self.mp_backend: Optional[str] = mp_backend if n_jobs != 0 else None
        if self.mp_backend is not None and self.archive_handler is not None:
            logger.info('Multiprocessing with archive is too slow, so it is disabled')
            logger.info(
                'Running without multiprocessing can be relatively slow, consider unarchiving the input file in advance'
            )
            self.mp_backend = None
        self.n_jobs: int = n_jobs

        with (self.archive_handler.open() if self.archive_handler else nullcontext()) as archive:
            args_iter = (
                (self, path, did_from_sid, archive) for path in file_paths if path.content_basename.endswith(knp_ext)
            )
            rets: List[Dict[str, str]] = self._mp_wrapper(
                KyotoReader.read_knp, args_iter, self.mp_backend, self.n_jobs
            )
        self.did2knps: Dict[str, str] = dict(ChainMap(*rets))

        self.doc_ids: List[str] = sorted(
            set(self.did2knps.keys()) | set(self.did2pkls.keys()))

        self.target_cases: Collection[str] = self._get_targets(
            target_cases, ALL_CASES, 'case')
        self.target_corefs: Collection[str] = self._get_targets(
            target_corefs, ALL_COREFS, 'coref')
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    def read_knp(
        self,
        file: FileHandler,
        did_from_sid: bool,
        archive: Optional[Union[zipfile.ZipFile, tarfile.TarFile]] = None,
    ) -> Dict[str, str]:
        """Read KNP format file that is located at the specified path. The file can contain multiple documents.

        Args:
            file (FileHandler): A file handler indicating a path to a KNP format file.
            did_from_sid (bool): If True, determine the document ID from the sentence ID in the document.
            archive (Optional[Union[zipfile.ZipFile, tarfile.TarFile]]): An archive to read the document from.

        Returns:
            Dict[str, str]: A mapping from a document ID to a KNP format string.
        """

        if archive is not None:
            with self.archive_handler.open_member(archive, str(file.path)) as f:
                return self._read_knp(io.TextIOWrapper(f, encoding='utf-8'), file.path, did_from_sid)
        else:
            with file.open() as f:
                return self._read_knp(f, file.path, did_from_sid)

    @staticmethod
    def _read_knp(file: TextIO,
                  path: Path,
                  did_from_sid: bool
                  ):
        buff = ''
        did = sid = None
        did2knps = {}
        for line in file:
            if line.startswith('# S-ID:') and did_from_sid:
                sid_string = line[7:].strip().split()[0]
                match = SID_PTN_KWDLC.match(
                    sid_string) or SID_PTN.match(sid_string)
                if match is None:
                    raise ValueError(
                        f'unsupported S-ID format: {sid_string} in {path}')
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
            if archive is not None:
                with self.archive_handler.open_member(archive, str(self.did2pkls[doc_id].path)) as f:
                    return pickle.load(f)
            else:
                with self.did2pkls[doc_id].open(mode='rb') as f:
                    return pickle.load(f)
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
        if self.archive_handler is not None:
            assert self.mp_backend is None
        with (self.archive_handler.open() if self.archive_handler else nullcontext()) as archive:
            args_iter = zip(repeat(self), doc_ids, repeat(archive))
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
