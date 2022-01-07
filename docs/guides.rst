Guides
======


Integrating a New Motor Controller
----------------------------------

The following steps are needed for integrating a new motor controller in Being.

1) Subclass :class:`being.motors.controllers.Controller`
    1) Define *emergency descriptions*
    2) Define *supported homing methods*
    3) Overwrite ``apply_motor_direction`` method
    4) [Optional] Overwrite ``init_homing`` method if another homing type than
       :class:`being.motors.homing.CiA402Homing` is required.
2) Register new controller type in :data:`being.motors.blocks.CONTROLLER_TYPES`.

.. code-block:: python

   from typing import List, Set
   from being.motors.controllers import Controller


   class R2D2(Controller):
       EMERGENCY_DESCRIPTIONS: List[tuple] = [
           # Code   Mask    Description
           #(0x0000, 0xFF00, 'No error'),
           ...
       ]
       """(error code, error mask, description) tuples."""

       SUPPORTED_HOMING_METHODS: Set[int] = {1, 2, 3, 4}  # ...
       """Supported homing methods for the controller. See CiA 402
       homing methods.
       """

       def apply_motor_direction(self, direction: float):
           """For direction in -1.0 or 1.0 configure the motor
           direction of the controller.
           """
           pass


Setup on a RPI
--------------
- CAN interface
- Wifi
- Clone being
- systemd service pathos_being.py
- RPI card ready to download
- Image
- CAN setup
- Motor Settings


Position Profile
----------------

How to steers the motors


TODO
----

.. todo::
   - Packing being application as a service
