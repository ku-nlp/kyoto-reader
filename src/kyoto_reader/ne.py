from typing import Dict

from pyknp import Morpheme

from .sentence import Sentence


class NamedEntity:
    """A class to represent a named entity (NE).

    Args:
        category (str): A category of a NE.
        name (str): A name of a NE.
        sentence (Sentence): A sentence that contains a NE.
        mid_range (range): A range of IDs of morphemes that constitute a NE.
        mrph2dmid (dict): A mapping from morpheme to its document-wide ID.

    Attributes:
        category (str): A category of a NE.
        name (str): A name of a NE.
        sid (str): A sentence ID of a sentence that contains a NE.
        mid_range (range): A range of IDs of morphemes that constitute a NE.
        dmid_range (range): A range of document-wide IDs of morphemes that constitute a NE.
    """

    def __init__(self,
                 category: str,
                 name: str,
                 sentence: Sentence,
                 mid_range: range,
                 mrph2dmid: Dict[Morpheme, int]):
        self.category: str = category
        self.name: str = name
        self.sid: str = sentence.sid
        self.mid_range: range = mid_range
        dmid_start = mrph2dmid[sentence.mrph_list()[mid_range[0]]]
        dmid_end = mrph2dmid[sentence.mrph_list()[mid_range[-1]]]
        self.dmid_range: range = range(dmid_start, dmid_end + 1)

    def __str__(self) -> str:
        return self.name
