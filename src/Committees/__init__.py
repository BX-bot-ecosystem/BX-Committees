from .bar import Bar
from .base import Committee_hub_base
import json


with open('data/committees.json') as f:
    committees_info = json.load(f)


_temp = [Bar]
customized_committees = [ob().name for ob in _temp]
committees_names_for_base= [name for name in committees_info.keys() if name not in customized_committees]
committee_handlers = [ob().handler for ob in _temp] + [Committee_hub_base(name).handler for name in committees_names_for_base]
committees = {ob().name: ob() for ob in _temp}