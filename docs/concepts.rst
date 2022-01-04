Concepts
========


Blocks and Connections
----------------------

Blocks are the main building *blocks* in being (pun intended). Each block
encapsulates certain functionalities and can pass data to its connected
neighbors.

.. digraph:: someblocks
   :align: center
   :alt: Some connected blocks.
   :caption: Some connected blocks.
   :name: Some connected blocks.

   node [shape=box];
   rankdir="LR"

   A -> B;
   B -> C [style=dashed];
   B -> C [style=dashed];

There are two kind of connections:

- *Value* (⇢) connections are intended for continuous streams of data. Think
  audio samples or motor position values. Accessed via the ``value``
  attributes.
- *Message* (→) connections ``send`` and ``receive`` discrete messages.

Outputs and inputs can be connected with each other with the *connect* method.
It is possible to connect an output to many inputs but not the other way round.
A small summary of the block attributes:

- :attr:`being.block.Block.inputs`: Input connectables.
- :attr:`being.block.Block.outputs`: Output connectables.
- :attr:`being.block.Block.input`: Primary input.
- :attr:`being.block.Block.output`: Primary output.

The pipe operator ``|`` can be used to chain multiple blocks via there primary
inputs and outputs

.. code-block:: python

   # Pipe operator for 3x blocks
   a | b | c

   # Is equivalanet to:
   # >>> a.output.connect(b.input)
   # ... b.output.connect(c.input)


Block Network and Execution Order
---------------------------------

The blocks together with the connections form a *block network*. This is a
directed graph and forms the core of every being program. Given such a block
network being will try to find a suitable *execution order* of these blocks and
tick every block once per cycle by calling its :meth:`being.block.Block.update`
method.


.. code-block:: python

   from being.block import Block
   from being.execution import determine_execution_order


   class Foo(Block):

       """Example block printing and passing on messages."""

       def __init__(self):
           super().__init__()
           self.add_message_input()
           self.add_message_output()

       def update(self):
           for msg in self.input.receive():
               first, *rest = msg
               print(first)
               self.output.send(rest)


   # Initializing blocks
   a = Foo()
   b = Foo()
   c = Foo()

   # Making the connections
   a | b | c

   # Determining the execution order. One initial block of the network suffices
   execOrder = determine_execution_order([b])

   # Executing a single cycle with some data
   a.input.push(['Hello', 'world', '!'])
   for block in execOrder:
       block.update()

This will output

.. code-block:: bash

   Hello
   world
   !

When running a being block network with the :func:`being.awakening.awake`
function the execution order will be executed indefinitely. The interval
duration is taken from :mod:`being.configuration`.


Splines
-------

Splines are special mathematical functions. They are used to interpolate
between values.

.. math::

   S: [a,b]\to \mathbb{R}^n

Being deals exclusively with *piecewise polynomial parametric curves*. This is
a chain of multiple segments where each segment is a cubic polynomial spline in
the Bernstein basis. Below is a plot with a scalar spline made out of two
segments.

.. plot::

   import matplotlib.pyplot as plt
   from scipy.interpolate import BPoly
   from being.plotting import plot_spline_2

   # Polynomial coefficient matrix
   c = [[0, 2], [0, 2], [2, 1], [2, 1]]

   # Knots or breakpoints
   x = [0, 1, 3]

   spline = BPoly(c, x)

   plot_spline_2(spline)
   plt.xlabel('Time')
   plt.ylabel('Position')
   plt.show()

The shape ``(k, m, ...)`` of the coefficient matrix ``c`` controls the nature
of the spline and its output format. ``k`` is the *spline order* and ``m`` the
number of segments or intervals. Concerning the output values:

- shape ``(k, m)``: Scalar spline outputs ``1.234``.
- shape ``(k, m, 1)``: One dimensional spline outputs ``[1.234]``.
- shape ``(k, m, 3)``: Three dimensional spline outputs ``[1.234, 1.234, 1.234]``.

.. note::

   Because of convience scalar splines are represented as one dimensional
   splines in being.


Curves
------

A :class:`being.curve.Curve` is a container for splines. Each *motion curve*
has multiple individual splines. These are independent and do not share any
break points or coefficients. Each of these splines defines a motion channel
which can be routed to motors.

.. plot::

   import numpy as np
   import matplotlib.pyplot as plt
   from scipy.interpolate import BPoly

   from being.curve import Curve

   first = BPoly([[[0], [1]], [[0], [1]], [[1], [0]], [[1], [0]] ], [0, 1, 3])
   second = BPoly([[[1]], [[1]], [[0]], [[0]]], [0, 2])

   curve = Curve([first, second])
   t = np.linspace(0, 3, 100)
   plt.plot(t, curve(t, extrapolate=False))
   plt.xlabel('Time')
   plt.ylabel('Position')
   plt.show()


Serialization
-------------

JSON serialization of the different being object is defined in
:mod:`being.serialization`. Custom types get mapped to and from dictionary
representation which can be converted to JSON strings.

This conversion is taken care by :func:`being.serialization.dumps` and
:func:`being.serialization.loads`.

.. digraph:: jsonserialization
   :align: center
   :alt: JSON serialization of being objects.
   :caption: JSON serialization of being objects.
   :name: JSON serialization of being objects.

   rankdir="LR"
   Object -> JSON [label="dumps()"];
   JSON -> Object [label="loads()"];

It is also possible to serialize named tuples and enums. But these types have
to be registered after creation
(:func:`being.serialization.register_named_tuple.` and
:func:`being.serialization.register_enum`).

.. code-block:: python

   from typing import NamedTuple
   from being.serialization import register_named_tuple, dumps


   class Foo(NamedTuple):
      first: str = 'hello'
      second: int = 42


   register_named_tuple(Foo)
   foo = Foo(second='tuple')
   print(dumps(foo))
   # {"type": "Foo", "first": "hello", "second": "tuple"}


Content
-------

A :class:`being.content.Content` instance manages all user defined motion
curves inside a directory. Curves are saved as JSON files in this folder.


Motion Player
-------------

The :class:`being.motion_player.MotionPlayer` block plays motion curves on the
motors. It accepts *motion commands* messages as instructions for which curve
to schedule next. Curves are loaded from the content directory, sampled and
outputted via the position outputs
(:attr:`being.motion_player.MotionPlayer.positionOutputs`).

.. digraph:: motionplayer
   :align: center
   :alt: Motion Player steering multiple motors
   :caption: Motion Player steering multiple motors
   :name: Motion Player steering multiple motors

   rankdir="LR"
   dummy [label="", shape=none, height=0, width=0]
   MP [shape=box, label="Motion Player"];
   A [shape=box, label="Motor 1"];
   B [shape=box, label="Motor 2"];
   C [shape=box, label="Motor 3"];

   dummy -> MP [label="Motion Command"]
   MP -> A [style=dashed, label="Target Position"]
   MP -> B [style=dashed]
   MP -> C [style=dashed]

.. note::

   The reason for the additional `positionOutputs` attribute is, that at some
   point it was planed to add feedback connection to notify when a motion curve
   had been played succefully or not. `outputs` would then have an addional
   entry.


Resources
---------

System resources have limited availability and need to be released when the
program shuts down. In the context of being this refers to the CAN interface
and network sockets. These resources are handled by a global
:class:`contextlib.ExitStack` in :mod:`being.resources`.

When resources are acquired at run-time it is important to use the
:func:`being.resources.manage_resources` context manager so that the collected
resources can be released at the end.

.. code-block:: python

   from being.networking import NetworkIn
   from being.resources import manage_resources

   with manage_resources():
      # Creates and binds a socket internally
      incoming = NetworkIn(address=('', 56790))

   # Socket gets released here

The same logic applies to the CAN interface, RPi GPIO, port audio backend...


Single Instance Cache
---------------------

For comforts, some types get instantiated implicitly when needed. For example,
when creating a :class:`being.motors.blocks.CanMotor` block, by default a
:class:`being.backend.CanBackend` instance gets created as well. Similarly
every :class:`being.motion_player.MotionPlayer` block needs a
:class:`being.clock.Clock` and a :class:`being.content.Content` instance.

The :class:`being.utils.SingleInstanceCache` base class caches all these
instances. These de-facto global variables are an anti-pattern but opposed to
the classical singleton pattern single instantiation is not enforced and these
single instances are only used as *default* values. All classes, which make use
of single instances, also accept them via their initialize method (dependency
injection).


Motors
------

A motor block accepts *target position* and outputs *actual position* values.

.. digraph:: motorblock
   :align: center
   :alt: Motor block input and output values.
   :caption: Motor block input and output values.
   :name: Motor block input and output values.

   rankdir="LR"
   in[shape=none, label=""]
   motor[label="Motor Block", shape=box]
   out[shape=none, label=""]
   in -> motor [label="Target Position"]
   motor -> out [label="Actual Position"]

Motor blocks come in different flavors, depending on the physical configuration
(linear vs. Rotary motors, different rotary motor variations). All of these are
represented by the different classes in :mod:`being.motors.blocks`.

Since many motors have relative encoders they need to be *homed* after turning
them on so that they can orient them self and find their initial position.

Motor blocks can be *enabled* or *disabled*. This corresponds to the *Operation
Enabled* and *Ready to Switch On* states of the *CiA 402 State Machine*.

By default, CAN motors are run in the *Cyclic Synchronous Position (CSP)*
operation mode. Every cycle a new target position value is send to the motor
via PDO.  Trajectory generation is mostly done on the application side.  Note
although, that this is handled very differently between the different vendors.
It is also possible to run motor blocks in the *Profiled Position* mode. In
this case, the target position input is ignored. Instead the motor block
accepts :class:`being.motors.definitions.PositionProfile` messages which will
be relayed to the motor.

TODO


CAN Nodes and State Switching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A CanOpen CiA 402 node has a standardized state machine which controls the
device. Different states must be passed through in order to enable the drive.


The node state can be changed either via SDO or PDO.

By default both the statusword as well as the controlword are registered for PDO communcation.


CAN Controllers
^^^^^^^^^^^^^^^


Motor Settings
^^^^^^^^^^^^^^


Motor Homing
^^^^^^^^^^^^


Cyclic Synchronous Position (CSP) vs Profile Position mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Possible Topics Todo
--------------------

- Behavior
- Web / API
  - Components

- Being Architecture

- Communication SDO / PDO
- Parallel State Change / Homing

- Pacemaker

- Configs and Parameters
- Networking

- Logging
- Packing being application as a service
- Running the tests
