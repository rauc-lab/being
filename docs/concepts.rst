Concepts
========

Possible Topics
---------------

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

- Pacemaker

- Configs and Parameters
- Networking

- Logging
- Packing being application as a service
- Running the tests

Blocks and Connections
----------------------

- Interconnected blocks forming the block network.
- Value and message based connections.
- Execution order.

Motion Curves
-------------

- A curve consists of multiple splines.
- Each spline is a piecewise polynomial curve where each segment is Bézier spline.

Motion Player
-------------

- Plays motion curves and outputs their samples


Splines
-------

.. plot::

   import matplotlib.pyplot as plt

   from being.plotting import plot_spline_2

   from scipy.interpolate import BPoly


   c = [[0, 2], [0, 2], [2, 1], [2, 1]]
   x = [0, 1, 3]

   spline = BPoly(c, x)

   plot_spline_2(spline)
   prettify_plot()
   plt.show()
