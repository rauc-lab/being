#!/usr/local/python3

import logging

from being.awakening import awake
from being.backends import CanBackend
from being.behavior import Behavior
from being.constants import FORWARD, BACKWARD, TAU
from being.logging import setup_logging, suppress_other_loggers
from being.motion_player import MotionPlayer
from being.motors import RotaryMotor
from being.resources import register_resource, manage_resources
from being.can.cia_402_stepper import StepperCiA402Node
from being.can import load_object_dictionary_from_eds

log_level = logging.DEBUG
logging.basicConfig(level=log_level)
setup_logging(level=log_level)
suppress_other_loggers()

with manage_resources():
    network = CanBackend.single_instance_setdefault()
    register_resource(network, duplicates=False)

    nodeId = 16
    od = load_object_dictionary_from_eds(
        'eds_files/pathos_stepper_controller.eds',
        nodeId
    )
    mot0 = RotaryMotor(
        nodeId=nodeId,
        node=StepperCiA402Node(nodeId=nodeId,
                               network=network,
                               objectDictionary=od,
                               ),
        motor='ST-PM35-15-11C',
        profiled=True,
        length=TAU,
        direction=FORWARD,
        # homingMethod=-3,
        settings={'vmax': 10000,
                  'acc': 10000,
                  'dec': 10000,
                  }
    )

    behavior = Behavior.from_config('behavior.json')
    mp = MotionPlayer(ndim=1)

    behavior | mp

    mp.positionOutputs[0].connect(mot0.input)

    awake(behavior, usePacemaker=False, homeMotors=True, web=True)
