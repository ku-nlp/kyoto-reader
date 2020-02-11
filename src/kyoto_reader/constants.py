ALL_CASES = [
    "ガ",
    "デ",
    "ト",
    "ニ",
    "ノ",
    "ヘ",
    "ヲ",
    "カラ",
    "ガ２",
    "ノ？",
    "マデ",
    "ヨリ",
    "トイウ",
    "トシテ",
    "トスル",
    "ニオク",
    "ニシテ",
    "ニツク",
    "ニトル",
    "ニヨル",
    "マデニ",
    "ニオイテ",
    "ニカワル",
    "ニソッテ",
    "ニツイテ",
    "ニトッテ",
    "ニムケテ",
    "ニムケル",
    "ニヨッテ",
    "ニヨラズ",
    "ニアワセテ",
    "ニカギッテ",
    "ニカギラズ",
    "ニカランデ",
    "ニカワッテ",
    "ニカンシテ",
    "ニカンスル",
    "ニクラベテ",
    "ニクワエテ",
    "ニタイシテ",
    "ニタイスル",
    "ニツヅイテ",
    "ニナランデ",
    "ヲツウジテ",
    "ヲツウジル",
    "ヲノゾイテ",
    "ヲフクメテ",
    "ヲメグッテ",
    "ニトモナッテ",
    "ニモトヅイテ",
    "無",  # <係:無格>
    "修飾",
    "判ガ",
    "時間",
    "外の関係",
]
ALL_CASES += [case + '≒' for case in ALL_CASES]

CORE_CASES = [
    "ガ２",
    "ガ",
    "ヲ",
    "ニ",
]

ALL_COREFS = [
    "=",
    "=構",
    "=役",
]
ALL_COREFS += [case + '≒' for case in ALL_COREFS]

CORE_COREFS = [
    "=",
    "=構",
    "=役",
]

UNCERTAIN = "[不明]"  # used only in crowd sourcing annotations

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
