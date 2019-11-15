ALL_CASES = [
    "ガ２",
    "ガ",
    "ヲ",
    "ニ",
    "ノ",
    "ト",
    "デ",
    "カラ",
    "ヨリ",
    "ヘ",
    "マデ",
    "マデニ",
    "時間",
    "外の関係",
    "無",  # <係:無格>
    "ニタイシテ",
    "ノ？",
    "トイウ",
    "修飾",
]

CORE_CASES = [
    "ガ２",
    "ガ",
    "ヲ",
    "ニ",
]

ALL_COREFS = [
    "=",
    "=構",
    "=≒",
]

CORE_COREFS = [
    "=",
    "=構",
]

UNCERTAIN = "[不明]"

UNSPECIFIED_PERSON = [
    "不特定:人１",
    "不特定:人２",
    "不特定:人３",
    "不特定:人４",
    "不特定:人５",
    "不特定:人６",
    "不特定:人７",
    "不特定:人８",
    "不特定:人９",
    "不特定:人１０",
    "不特定:人１１",
]

UNSPECIFIED_OBJECT = [
    "不特定:物１",
    "不特定:物２",
    "不特定:物３",
    "不特定:物４",
    "不特定:物５",
    "不特定:物６",
    "不特定:物７",
    "不特定:物８",
    "不特定:物９",
]

UNSPECIFIED_CIRCUMSTANCES = [
    "不特定:状況１",
    "不特定:状況２",
    "不特定:状況３",
    "不特定:状況４",
    "不特定:状況５",
    "不特定:状況６",
    "不特定:状況７",
    "不特定:状況８",
    "不特定:状況９",
]

ALL_EXOPHORS = [
    "著者",
    "読者",
    "不特定:人",
    "不特定:物",
    "不特定:状況",
    "前文",
    "後文",
] + [UNCERTAIN] + UNSPECIFIED_PERSON + UNSPECIFIED_OBJECT + UNSPECIFIED_CIRCUMSTANCES

DEP_TYPES = [
    "overt",
    "dep",
    "intra",
    "inter",
    "exo",
]

NE_CATEGORIES = [
    "ORGANIZATION",
    "PERSON",
    "LOCATION",
    "ARTIFACT",
    "DATE",
    "TIME",
    "MONEY",
    "PERCENT",
    "OPTIONAL",
]
