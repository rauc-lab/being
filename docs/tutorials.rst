Tutorials
=========


Building a Sine Block
---------------------

Example how to build a being block which outputs a sine curve. Most custom
being blocks are of the same form:

1) Initialize connectables and states inside ``__init__()``
2) Do some work and set output values in ``update()``

A Sine block should have an output for the sine values.

.. code-block:: python

   import math
   import time
   from being.block import Block

   class Sine(Block):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add_value_output()

       def update(self):
           phase = TAU * time.time()
           self.output.value = math.sin(phase)

This implementation has a couple shortcomings:

- Frequency can not be set nor change
- Depends on system time. Different start phase every time.
- ``update()`` will not be called *exactly* in the same interval. Using system
  time add jitter.

Let fix this by adding a phase attribute, using the interval duration from the
configuration and add an additional value input for the frequency.

.. code-block:: python

   import math
   from being.block import Block
   from being.configuration import CONFIG
   from being.constants import TAU


   INTERVAL = CONFIG['General']['INTERVAL']


   class Sine(Block):
       def __init__(self, frequency=1.0, **kwargs):
           super().__init__(**kwargs)
           self.add_value_input('frequency')  # frequency attribute input alias
           self.add_value_output()

           self.frequency.value = frequency  # Set initial frequency value
           self.phase = 0.0

       def update(self):
           self.output.value = math.sin(self.phase)

           # Compute the phase increment
           self.phase += TAU * self.frequency.value * INTERVAL
           self.phase %= TAU


Building a Motion Looper Block
------------------------------

TODO


Creating a New Being
--------------------

TODO


Creating a New Web Component
----------------------------

TODO
