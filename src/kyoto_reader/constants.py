import re

ALL_CASES = [
    'ガ',
    'デ',
    'ト',
    'ニ',
    'ノ',
    'ヘ',
    'ヲ',
    'カラ',
    'ガ２',
    'ノ？',
    'マデ',
    'ヨリ',
    'トイウ',
    'トシテ',
    'トスル',
    'ニオク',
    'ニシテ',
    'ニツク',
    'ニトル',
    'ニヨル',
    'マデニ',
    'ニオイテ',
    'ニカワル',
    'ニソッテ',
    'ニツイテ',
    'ニトッテ',
    'ニムケテ',
    'ニムケル',
    'ニヨッテ',
    'ニヨラズ',
    'ニアワセテ',
    'ニカギッテ',
    'ニカギラズ',
    'ニカランデ',
    'ニカワッテ',
    'ニカンシテ',
    'ニカンスル',
    'ニクラベテ',
    'ニクワエテ',
    'ニタイシテ',
    'ニタイスル',
    'ニツヅイテ',
    'ニナランデ',
    'ヲツウジテ',
    'ヲツウジル',
    'ヲノゾイテ',
    'ヲフクメテ',
    'ヲメグッテ',
    'ニトモナッテ',
    'ニモトヅイテ',
    '無',
    '修飾',
    '判ガ',
    '時間',
    '外の関係',
]
ALL_CASES += [case + '≒' for case in ALL_CASES]

ALL_COREFS = [
    '=',
    '=構',
    '=役',
]
ALL_COREFS += [case + '≒' for case in ALL_COREFS]

UNCERTAIN = '[不明]'  # used only in crowd sourcing annotations

UNSPECIFIED_PERSON = [
    '不特定:人１',
    '不特定:人２',
    '不特定:人３',
    '不特定:人４',
    '不特定:人５',
    '不特定:人６',
    '不特定:人７',
    '不特定:人８',
    '不特定:人９',
    '不特定:人１０',
    '不特定:人１１',
]

UNSPECIFIED_OBJECT = [
    '不特定:物１',
    '不特定:物２',
    '不特定:物３',
    '不特定:物４',
    '不特定:物５',
    '不特定:物６',
    '不特定:物７',
    '不特定:物８',
    '不特定:物９',
    '不特定:物１０',
]

UNSPECIFIED_CIRCUMSTANCES = [
    '不特定:状況１',
    '不特定:状況２',
    '不特定:状況３',
    '不特定:状況４',
    '不特定:状況５',
    '不特定:状況６',
    '不特定:状況７',
    '不特定:状況８',
    '不特定:状況９',
    '不特定:状況１０',
]

ALL_EXOPHORS = [
    '著者',
    '読者',
    '不特定:人',
    '不特定:物',
    '不特定:状況',
    '前文',
    '後文',
] + [UNCERTAIN] + UNSPECIFIED_PERSON + UNSPECIFIED_OBJECT + UNSPECIFIED_CIRCUMSTANCES

NE_CATEGORIES = [
    'ORGANIZATION',
    'PERSON',
    'LOCATION',
    'ARTIFACT',
    'DATE',
    'TIME',
    'MONEY',
    'PERCENT',
    'OPTIONAL',
]

SID_PTN = re.compile(r'^(?P<sid>(?P<did>[a-zA-Z0-9-_]+?)(-(\d+))?)$')
SID_PTN_KWDLC = re.compile(r'^(?P<sid>(?P<did>w\d{6}-\d{10})(-\d+)(-\d{2})?)$')
# Wikipedia Annotated Corpus (under construction)
SID_PTN_WAC = re.compile(r'^(?P<sid>(?P<did>wiki\d{8})(-\d{2})(-\d{2})?)$')
