from pathlib import Path

from kyoto_reader import KyotoReader


def test_process_documents(fixture_kyoto_reader: KyotoReader):
    documents = fixture_kyoto_reader.process_all_documents()
    assert [doc.doc_id for doc in documents] == fixture_kyoto_reader.doc_ids


def test_zip(fixture_kyoto_reader: KyotoReader):
    data_dir = Path(__file__).parent / 'data'
    zip_reader = KyotoReader(data_dir / 'compress_knp/knp.zip', n_jobs=0)
    assert fixture_kyoto_reader.doc_ids == zip_reader.doc_ids
    assert all(
        fixture_kyoto_reader.process_document(doc_id) == zip_reader.process_document(doc_id)
        for doc_id in fixture_kyoto_reader.doc_ids
    )


def test_tar_gzip(fixture_kyoto_reader: KyotoReader):
    data_dir = Path(__file__).parent / 'data'
    tar_gzip_reader = KyotoReader(data_dir / 'compress_knp/knp.tar.gz', n_jobs=0)
    assert fixture_kyoto_reader.doc_ids == tar_gzip_reader.doc_ids
    assert all(
        fixture_kyoto_reader.process_document(doc_id) == tar_gzip_reader.process_document(doc_id)
        for doc_id in fixture_kyoto_reader.doc_ids
    )


def test_gzip(fixture_kyoto_reader: KyotoReader):
    data_dir = Path(__file__).parent / 'data'
    gzip_reader = KyotoReader(data_dir / 'gzip_knp', n_jobs=0)
    assert fixture_kyoto_reader.doc_ids == gzip_reader.doc_ids
    assert all(
        fixture_kyoto_reader.process_document(doc_id) == gzip_reader.process_document(doc_id)
        for doc_id in fixture_kyoto_reader.doc_ids
    )


def test_lazy_load(fixture_kyoto_reader: KyotoReader):
    data_dir = Path(__file__).parent / 'data'
    reader = KyotoReader(data_dir / 'knp', did_from_sid=False, n_jobs=0)
    assert fixture_kyoto_reader.doc_ids == reader.doc_ids
    assert fixture_kyoto_reader.process_all_documents() == reader.process_all_documents()


def test_lazy_load_mp(fixture_kyoto_reader: KyotoReader):
    data_dir = Path(__file__).parent / 'data'
    reader = KyotoReader(data_dir / 'knp', did_from_sid=False, n_jobs=4)
    assert fixture_kyoto_reader.doc_ids == reader.doc_ids
    assert fixture_kyoto_reader.process_all_documents() == reader.process_all_documents()
