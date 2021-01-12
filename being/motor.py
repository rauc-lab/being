"""Motor block."""
from typing import Optional

from canopen import BaseNode402

from being.backends import CanBackend
from being.block import Block
from being.can import load_object_dictionary
from being.connectables import ValueInput, ValueOutput
from being.kinematics import State, kinematic_filter
from being.math import sign
from being.resources import register_resource



INTERVAL = .05


class Motor(Block):
    def __init__(self, nodeId: int, length: Optional[float] = None,
            direction: float = 1, network: CanBackend = None):
        """Args:
            nodeId: CANopen node id.

        Kwargs:
            length: Rod length.
            direction: Movement direction.
        """
        super().__init__()
        if not network:
            network = CanBackend.default()
            register_resource(network, duplicates=False)

        self.nodeId = nodeId
        self.length = length
        self.direction = sign(direction)
        self.network = network

        self.position, = self.inputs = [ValueInput(owner=self)]
        self.istPosition, = self.outputs = [ValueOutput(owner=self)]
        self.state = State()
        self.node = None

        self.setup_node()

    def setup_node(self):
        od = load_object_dictionary(self.network, self.nodeId)
        self.node = BaseNode402(self.nodeId, od)

    def update(self):
        self.state = kinematic_filter(
            targets=self.input.value,
            dt=INTERVAL,
            state=self.state,
            maxSpeed=1.,
            maxAcc=1.,
        )

        soll = self.state.position
        print('Go to', soll)

    def __str__(self):
        return f'{type(self).__name__}(nodeId={self.nodeId})'



if __name__ == '__main__':
    from being.resources import manage_resources

    with manage_resources():
        mot = Motor(8)
        print(mot)
