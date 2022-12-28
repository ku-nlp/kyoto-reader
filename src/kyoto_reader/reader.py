import gzip
import io
import logging
import os
import pickle
import tarfile
import zipfile
from collections import ChainMap
from concurrent import futures
from contextlib import contextmanager, nullcontext
from enum import Enum
from functools import partial
from pathlib import Path
from typing import List, Dict, Optional, Union, Iterable, Collection, Any, BinaryIO, TextIO

from .constants import ALL_CASES, ALL_COREFS, SID_PTN, SID_PTN_KWDLC, SID_PTN_WAC
from .document import Document

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class ArchiveType(Enum):
    """Enum for file collection types."""
    TAR_GZ = '.tar.gz'
    ZIP = '.zip'


ArchiveFile = Union[tarfile.TarFile, zipfile.ZipFile]


class ArchiveHandler:
    def __init__(self, path: Path) -> None:
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
    def open(self) -> ArchiveFile:
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
    def open_member(self, archive: ArchiveFile, member: str) -> BinaryIO:
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
    def __init__(self, path: Path) -> None:
        self.path: Path = path
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
    def open(self, *args, **kwargs) -> TextIO:
        file = None
        try:
            if self.type == FileType.GZ:
                file = gzip.open(self.path, *args, **kwargs)
            elif self.type == FileType.UNCOMPRESSED:
                file = self.path.open(*args, **kwargs)
            else:
                raise ValueError(f'Unsupported collection type: {self.type}')
            yield file
        finally:
            hasattr(file, 'close') and file.close()

    def __lt__(self, other) -> bool:
        return self.path < other.path


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
        n_jobs (int): 文書を読み込む処理の並列数。0: 並列処理なし、-1: コア数 (default: -1)
        did_from_sid (bool): 文書IDを文書中のS-IDから決定する (default: True)

    Note:
        サポートされる入力パス (i.e. `source` argument)
        - 単一ファイル (.knp, .knp.gz, .pkl, .pkl.gz)
        - 単一ファイルを含むディレクトリ
        - 単一非圧縮ファイルを含むアーカイブファイル (.tar.gz, .zip)
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
                 n_jobs: int = -1,
                 did_from_sid: bool = True,
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
        elif source.is_file():
            logger.info(f'got a single file path, this file is treated as a source file')
            file_paths: List[FileHandler] = [FileHandler(source)]
        else:
            raise ValueError(f'document source: {source} not found')

        # If True, determine the document ID from the sentence ID in the document.
        self.did_from_sid: bool = did_from_sid

        self._did2pkl = {file.path.stem: file for file in file_paths if file.content_basename.endswith(pickle_ext)}
        if n_jobs == -1:
            self.n_jobs = os.cpu_count()
        elif n_jobs >= 0:
            self.n_jobs = n_jobs
        else:
            raise ValueError(f'n_jobs must be >= 0 or -1, but got {n_jobs}')
        if self.n_jobs > 0 and self.archive_handler is not None:
            logger.info('Multiprocessing with archive is too slow, so it is disabled')
            logger.info(
                'Running without multiprocessing can be relatively slow, consider unarchiving the input file in advance'
            )
            self.n_jobs = 0

        self._did2knp: Dict[str, str] = {}
        self._did2file: Dict[str, FileHandler] = {}
        if self.did_from_sid is True:
            with (self.archive_handler.open() if self.archive_handler else nullcontext()) as archive:
                args_iter = (
                    (self, file, archive) for file in file_paths if file.content_basename.endswith(knp_ext)
                )
                if self.n_jobs > 0:
                    with futures.ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
                        rets: Iterable[Dict[str, str]] = executor.map(KyotoReader._read_knp_wrapper, *zip(*args_iter))
                else:
                    rets: List[Dict[str, str]] = [KyotoReader._read_knp_wrapper(*args) for args in args_iter]
            self._did2knp.update(dict(ChainMap(*rets)))
        else:
            self._did2file.update(
                {file.path.stem: file for file in file_paths if file.content_basename.endswith(knp_ext)}
            )

        self.doc_ids: List[str] = sorted({*self._did2knp.keys(), *self._did2pkl.keys(), *self._did2file.keys()})

        self.target_cases: Collection[str] = self._get_targets(target_cases, ALL_CASES, 'case')
        self.target_corefs: Collection[str] = self._get_targets(target_corefs, ALL_COREFS, 'coref')
        self.relax_cases: bool = relax_cases
        self.extract_nes: bool = extract_nes
        self.use_pas_tag: bool = use_pas_tag
        self.knp_ext: str = knp_ext
        self.pickle_ext: str = pickle_ext

    def get_knp(self, did: str) -> str:
        if did in self._did2knp:
            return self._did2knp[did]
        with (self.archive_handler.open() if self.archive_handler else nullcontext()) as archive:
            if did in self._did2file:
                self._did2knp.update(self._read_knp_wrapper(self._did2file[did], archive))
                return self._did2knp[did]
            if did in self._did2pkl:
                if archive is not None:
                    with self.archive_handler.open_member(archive, str(self._did2pkl[did].path)) as f:
                        document = pickle.load(f)
                else:
                    with self._did2pkl[did].open(mode='rb') as f:
                        document = pickle.load(f)
                self._did2knp[did] = document.knp_string
                return self._did2knp[did]
        raise ValueError(f'document id: {did} not found')

    def _read_knp_wrapper(self,
                          file: FileHandler,
                          archive: Optional[ArchiveFile] = None,
                          ) -> Dict[str, str]:
        """Read KNP format file that is located at the specified path. The file can contain multiple documents.

        Args:
            file (FileHandler): A file handler indicating a path to a KNP format file.
            archive (Optional[ArchiveFile]): An archive to read the document from.

        Returns:
            Dict[str, str]: A mapping from a document ID to a KNP format string.
        """

        if archive is not None:
            with self.archive_handler.open_member(archive, str(file.path)) as f:
                return self._read_knp(io.TextIOWrapper(f, encoding='utf-8'), file.path, did_from_sid=self.did_from_sid)
        else:
            with file.open(mode='rt') as f:
                return self._read_knp(f, file.path, did_from_sid=self.did_from_sid)

    @staticmethod
    def _read_knp(file: TextIO,
                  path: Path,
                  did_from_sid: bool
                  ) -> Dict[str, str]:
        buff = ''
        did = sid = None
        did2knps = {}
        for line in file:
            if line.startswith('# S-ID:') and did_from_sid is True:
                sid_string = line[7:].strip().split()[0]
                match = SID_PTN_KWDLC.match(sid_string) or SID_PTN_WAC.match(sid_string) or SID_PTN.match(sid_string)
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

    def process_document(self,
                         doc_id: str,
                         archive: Optional[ArchiveFile] = None
                         ) -> Optional[Document]:
        """Process one document following the given document ID.

        Args:
            doc_id (str): An ID of a document to process.
            archive (Optional[ArchiveFile]): An archive to read the document from.
        """
        if doc_id in self._did2pkl:
            if archive is not None:
                with self.archive_handler.open_member(archive, str(self._did2pkl[doc_id].path)) as f:
                    return pickle.load(f)
            else:
                with self._did2pkl[doc_id].open(mode='rb') as f:
                    return pickle.load(f)
        return Document(self.get_knp(doc_id),
                        doc_id,
                        self.target_cases,
                        self.target_corefs,
                        self.relax_cases,
                        self.extract_nes,
                        self.use_pas_tag)

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
        elif n_jobs == -1:
            n_jobs = os.cpu_count()
        elif n_jobs < -1:
            raise ValueError(f'n_jobs must be >= 0 or -1, but got {n_jobs}')
        if self.archive_handler is not None:
            assert n_jobs == 0
        with (self.archive_handler.open() if self.archive_handler else nullcontext()) as archive:
            process_document = partial(KyotoReader.process_document, self, archive=archive)
            if n_jobs > 0:
                with futures.ProcessPoolExecutor(max_workers=n_jobs) as executor:
                    rets: Iterable[Optional[Document]] = executor.map(process_document, doc_ids)
            else:
                rets: Iterable[Optional[Document]] = map(process_document, doc_ids)
            return list(rets)

    def process_all_documents(self,
                              n_jobs: Optional[int] = None,
                              ) -> List[Optional[Document]]:
        """Process all documents that KyotoReader has loaded.

        Args:
            n_jobs (int): The number of processes spawned to finish this task. (default: inherit from self)
        """
        return self.process_documents(self.doc_ids, n_jobs)

    def __len__(self):
        return len(self.doc_ids)

    def __getitem__(self, doc_id: str) -> Document:
        return self.process_document(doc_id)
