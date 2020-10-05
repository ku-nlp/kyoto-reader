from typing import List, Dict

from kyoto_reader import KyotoReader, Mention, Entity, Predicate, SpecialArgument, Argument


def test_pas(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060050')
    predicates: List[Predicate] = document.get_predicates()
    assert len(predicates) == 12

    sid1 = 'w201106-0000060050-1'
    sid2 = 'w201106-0000060050-2'
    sid3 = 'w201106-0000060050-3'

    arguments = document.get_arguments(predicates[0])
    assert predicates[0].midasi == 'トス'
    assert len([_ for args in arguments.values() for _ in args]) == 2
    arg = arguments['ガ'][0]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('不特定:人', 0, 'exo', '')
    arg = arguments['ヲ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('コイン', 0, 0, sid1, 'dep', '')

    arguments = document.get_arguments(predicates[1])
    assert predicates[1].midasi == '行う'
    assert len([_ for args in arguments.values() for _ in args]) == 4
    arg = arguments['ガ'][0]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('不特定:人', 2, 'exo', '')
    arg = arguments['ガ'][1]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('読者', 3, 'exo', '？')
    arg = arguments['ガ'][2]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('著者', 4, 'exo', '？')
    arg = arguments['ヲ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('トス', 1, 1, sid1, 'overt', '')

    arguments = document.get_arguments(predicates[2])
    assert predicates[2].midasi == '表'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['ノ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('コイン', 0, 0, sid1, 'inter', '')

    arguments = document.get_arguments(predicates[3])
    assert predicates[3].midasi == '出た'
    assert len([_ for args in arguments.values() for _ in args]) == 2
    arg = arguments['ガ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('表', 0, 4, sid2, 'overt', '')
    arg = arguments['外の関係'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('数', 2, 6, sid2, 'dep', '')

    arguments = document.get_arguments(predicates[4])
    assert predicates[4].midasi == '数'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['ノ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('出た', 1, 5, sid2, 'dep', '')

    arguments = document.get_arguments(predicates[5])
    assert predicates[5].midasi == 'モンスター'
    assert len([_ for args in arguments.values() for _ in args]) == 2
    arg = arguments['修飾'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('フィールド上', 3, 7, sid2, 'dep', '')
    arg = arguments['修飾'][1]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('数', 2, 6, sid2, 'intra', 'AND')

    arguments = document.get_arguments(predicates[6])
    assert predicates[6].midasi == '破壊する'
    assert len([_ for args in arguments.values() for _ in args]) == 2
    arg = arguments['ガ'][0]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('不特定:状況', 11, 'exo', '')
    arg = arguments['ヲ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('モンスター', 4, 8, sid2, 'overt', '')

    arguments = document.get_arguments(predicates[7])
    assert predicates[7].midasi == '効果'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['トイウ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('破壊する', 5, 9, sid2, 'inter', '')

    arguments = document.get_arguments(predicates[8])
    assert predicates[8].midasi == '１度'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['ニ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('ターン', 3, 13, sid3, 'overt', '')

    arguments = document.get_arguments(predicates[9])
    assert predicates[9].midasi == 'メイン'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['ガ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('フェイズ', 7, 17, sid3, 'dep', '')

    arguments = document.get_arguments(predicates[10])
    assert predicates[10].midasi == 'フェイズ'
    assert len([_ for args in arguments.values() for _ in args]) == 1
    arg = arguments['ノ？'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('自分', 5, 15, sid3, 'overt', '')

    arguments = document.get_arguments(predicates[11])
    assert predicates[11].midasi == '使用する事ができる'
    assert len([_ for args in arguments.values() for _ in args]) == 5
    arg = arguments['ガ'][0]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('不特定:人', 17, 'exo', '')
    arg = arguments['ガ'][1]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('著者', 4, 'exo', '？')
    arg = arguments['ガ'][2]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('読者', 3, 'exo', '？')
    arg = arguments['ヲ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('効果', 1, 11, sid3, 'dep', '')
    arg = arguments['ニ'][0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('フェイズ', 7, 17, sid3, 'overt', '')


def test_dep_type(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0002000028')
    predicate: Predicate = document.get_predicates()[4]
    assert predicate.midasi == '同じ'
    arg = document.get_arguments(predicate, relax=True)['ガ'][1]
    assert isinstance(arg, Argument)
    assert arg.midasi == 'フランス'
    assert arg.dtid == 10
    assert arg.dep_type == 'dep'


def test_pas_relax(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060560')
    predicates: List[Predicate] = document.get_predicates()
    arguments = document.get_arguments(predicates[9], relax=True)
    sid1 = 'w201106-0000060560-1'
    sid2 = 'w201106-0000060560-2'
    sid3 = 'w201106-0000060560-3'
    assert predicates[9].midasi == 'ご協力'
    assert len([_ for args in arguments.values() for _ in args]) == 6
    args = sorted(arguments['ガ'], key=lambda a: a.dtid)
    arg = args[0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('ドクター', 7, 7, sid1, 'inter', 'AND')
    arg = args[1]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('ドクター', 2, 11, sid2, 'inter', 'AND')
    arg = args[2]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('ドクター', 0, 16, sid3, 'intra', 'AND')
    arg = args[3]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('皆様', 1, 17, sid3, 'intra', '')
    args = sorted(arguments['ニ'], key=lambda a: a.midasi)
    arg = args[0]
    assert isinstance(arg, Argument)
    assert tuple(arg) == ('コーナー', 5, 14, sid2, 'inter', '？')
    arg = args[1]
    assert isinstance(arg, SpecialArgument)
    assert tuple(arg) == ('著者', 5, 'exo', '')


def test_coref1(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060050')
    entities: Dict[int, Entity] = document.entities
    assert len(entities) == 19

    entity = entities[0]
    assert (entity.taigen, entity.yougen) == (None, None)
    assert entity.exophor == '不特定:人'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 0

    entity = entities[1]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('コイン', 0)
    assert mentions[0].eids == {1}

    entity = entities[2]
    assert (entity.taigen, entity.yougen) == (None, None)
    assert entity.exophor == '不特定:人'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 0

    entity = entities[3]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor == '読者'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('自分', 15)
    assert mentions[0].eids == {14}
    assert mentions[0].eids_unc == {3, 4, 15}

    entity = entities[4]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor == '著者'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('自分', 15)
    assert mentions[0].eids == {14}
    assert mentions[0].eids_unc == {3, 4, 15}

    entity = entities[5]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('トス', 1)
    assert mentions[0].eids == {5}

    entity = entities[6]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('表', 4)
    assert mentions[0].eids == {6}

    entity = entities[7]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('数', 6)
    assert mentions[0].eids == {7}

    entity = entities[8]
    assert (entity.taigen, entity.yougen) == (False, True)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('出た', 5)
    assert mentions[0].eids == {8}

    entity = entities[9]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('フィールド上', 7)
    assert mentions[0].eids == {9}

    entity = entities[10]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('モンスター', 8)
    assert mentions[0].eids == {10}

    entity = entities[11]
    assert (entity.taigen, entity.yougen) == (None, None)
    assert entity.exophor == '不特定:状況'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 0

    entity = entities[12]
    assert (entity.taigen, entity.yougen) == (False, True)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('破壊する', 9)
    assert mentions[0].eids == {12}

    entity = entities[13]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('ターン', 13)
    assert mentions[0].eids == {13}

    entity = entities[14]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('自分', 15)
    assert mentions[0].eids == {14}

    entity = entities[15]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor == '不特定:人'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('自分', 15)
    assert mentions[0].eids == {14}

    entity = entities[16]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('フェイズ', 17)
    assert mentions[0].eids == {16}

    entity = entities[17]
    assert (entity.taigen, entity.yougen) == (None, None)
    assert entity.exophor == '不特定:人'
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 0

    entity = entities[18]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 1
    assert (mentions[0].midasi, mentions[0].dtid) == ('効果', 11)
    assert mentions[0].eids == {18}


def test_coref2(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060560')
    entities: Dict[int, Entity] = document.entities
    assert len(entities) == 15

    entity: Entity = entities[14]
    assert (entity.taigen, entity.yougen) == (True, False)
    assert entity.exophor is None
    mentions: List[Mention] = sorted(entity.all_mentions, key=lambda x: x.dtid)
    assert len(mentions) == 4
    assert (mentions[0].midasi, mentions[0].dtid, mentions[0].eids) == ('ドクター', 7, {4})
    assert (mentions[1].midasi, mentions[1].dtid, mentions[1].eids) == ('ドクター', 11, {14})
    assert (mentions[2].midasi, mentions[2].dtid, mentions[2].eids) == ('ドクター', 16, {14})
    assert (mentions[3].midasi, mentions[3].dtid, mentions[3].eids) == ('皆様', 17, {14})


def test_coref_link1(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060050')
    for entity in document.entities.values():
        for mention in entity.mentions:
            assert entity.eid in mention.eids
        for mention in entity.mentions_unc:
            assert entity.eid in mention.eids_unc
    for mention in document.mentions.values():
        for eid in mention.eids:
            assert mention in document.entities[eid].mentions
        for eid in mention.eids_unc:
            assert mention in document.entities[eid].mentions_unc


def test_coref_link2(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060560')
    for entity in document.entities.values():
        for mention in entity.mentions:
            assert entity.eid in mention.eids
        for mention in entity.mentions_unc:
            assert entity.eid in mention.eids_unc
    for mention in document.mentions.values():
        for eid in mention.eids:
            assert mention in document.entities[eid].mentions
        for eid in mention.eids_unc:
            assert mention in document.entities[eid].mentions_unc


def test_coref_link3(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060877')
    for entity in document.entities.values():
        for mention in entity.mentions:
            assert entity.eid in mention.eids
        for mention in entity.mentions_unc:
            assert entity.eid in mention.eids_unc
    for mention in document.mentions.values():
        for eid in mention.eids:
            assert mention in document.entities[eid].mentions
        for eid in mention.eids_unc:
            assert mention in document.entities[eid].mentions_unc


def test_ne(fixture_kyoto_reader: KyotoReader):
    document = fixture_kyoto_reader.process_document('w201106-0000060877')
    nes = document.named_entities
    assert len(nes) == 2
    ne = nes[0]
    assert (ne.category, ne.midasi, ne.dmid_range) == ('ORGANIZATION', '柏市ひまわり園', range(5, 9))
    ne = nes[1]
    assert (ne.category, ne.midasi, ne.dmid_range) == ('DATE', '平成２３年度', range(11, 14))

    document = fixture_kyoto_reader.process_document('w201106-0000074273')
    nes = document.named_entities
    assert len(nes) == 3
    ne = nes[0]
    assert (ne.category, ne.midasi, ne.dmid_range) == ('LOCATION', 'ダーマ神殿', range(15, 17))
    ne = nes[1]
    assert (ne.category, ne.midasi, ne.dmid_range) == ('ARTIFACT', '天の箱舟', range(24, 27))
    ne = nes[2]
    assert (ne.category, ne.midasi, ne.dmid_range) == ('LOCATION', 'ナザム村', range(39, 41))
