from pathlib import Path
__version__ = Path(__file__).parent.joinpath('VERSION').open().read().rstrip()


from .reader import KyotoReader
from .document import Document
from .sentence import Sentence
from .base_phrase import BasePhrase
from .pas import Predicate, BaseArgument, Argument, SpecialArgument, Pas
from .coreference import Mention, Entity
from .constants import *
