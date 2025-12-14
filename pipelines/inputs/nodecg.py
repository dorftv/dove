from api.inputs.nodecg import NodeCGInputDTO
from .wpesrc import WpesrcInput


class NodeCGInput(WpesrcInput):
    """NodeCG input - inherits from WpesrcInput which auto-selects cefsrc or wpesrc."""
    data: NodeCGInputDTO
