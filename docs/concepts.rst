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
   A -> B [style=dashed];
   B -> A;
   B -> C;
   B -> C;

There are two kind of connections:

- *Value* connections are intended for continuous streams of data. Think audio
  samples or motor position values.
- *Message* connections send and receive discrete messages.

The blocks together with the connections form a *block network*. This is at the
core of every being program. Given such a block network being will try to find
a suitable *execution order* of these blocks and tick every block once per
cycle.


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

   c = [[0, 2], [0, 2], [2, 1], [2, 1]]
   x = [0, 1, 3]

   spline = BPoly(c, x)

   plot_spline_2(spline)
   plt.show()


Curves
------

A :class:`being.curve.Curve` is a container for splines. Each *motion curve*
has multiple individual splines. These are independent and do not share any
break points or coefficients. Each of these splines defines a motion channel
which can be routed to motors.


Motion Player
-------------

- Plays motion curves and outputs their samples




Possible Topics Todo
--------------------

- Blocks / Connections

- Motion Curves
- Motion Player
- Content

- Web / API
  - Components
- Serialization

- Resources in being
- Single Instance Cache

- Motors
   - CAN Nodes and State Switching
   - CAN Controllers
   - Motor Settings
   - Motor Homing
   - Cyclic Synchronous Position (CSP) vs Profile Position mode

- Communication SDO / PDO
- Parallel State Change / Homing

- Being Architecture
- Pacemaker

- Configs and Parameters
- Networking

- Logging
- Packing being application as a service
- Running the tests
