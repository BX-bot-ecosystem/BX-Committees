from .bar import Bar
from .base import Committee_hub_base
_temp = [Bar]
committees = {ob().name: ob() for ob in _temp}