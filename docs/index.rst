.. Being documentation master file, created by
   sphinx-quickstart on Tue Nov 16 14:16:30 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

================
Welcome to Being
================

.. image:: images/pathos\ logo.png
   :alt: PATHOS logo

Robotic middleware library for easy to use robotic projects.

.. _GitHub: https://github.com/rauc-lab/being

The goal of being is it, to abstract away most of the low-level heavy lifting
when working with motors and sensors. Engineers and programmers should be able
to focus on developing slim, high-level programs which operate on *behavior*
and *character* to capture the expressive intent of artists.


Key Features
============

- Connected block logic
- CAN based motor controllers
- Spline based motion curves
- Adaptive web based user interface


Library Installation
====================

.. code-block:: bash

   $ pip install being


Getting Started
===============

Our first being with one dummy motor. This will create a ``content`` directory
in the current working directory where the motion curves will be stored.

.. code-block:: python

    from being.awakening import awake
    from being.motion_player import MotionPlayer
    from being.motors.blocks import DummyMotor

    # Create blocks
    mp = MotionPlayer()
    motor = DummyMotor(length=0.1)

    # Make connections
    mp.positionOutputs[0].connect(motor.input)

    # Run being
    awake(mp)

Now inspect the web-based user interface under `<http://localhost:8080/>`_.


Going Further
=============

- Core :doc:`concepts` of Being
- :doc:`manuals` of the frontend widgets
- A couple of quick :doc:`tutorials`.


Source Code
===========

This project is hosted on GitHub_.


Dependencies
============

TODO Needed?


Communication Channels
======================

TODO Needed?


Contributing
============

Coding style is mostly compatible with
`Google Python Style Guide <https://google.github.io/styleguide/pyguide.html>`_
with one exception: `camelCase <https://en.wikipedia.org/wiki/Camel_case>`_ for
variables, arguments and attributes.
`snake_case <https://en.wikipedia.org/wiki/Snake_case>`_ for functions, methods
and properties.

TODO


Authors and License
===================

The ``being`` package is written by Alexander Theler and is licensed under the
MIT license. Feel free to use and improve this project.


Todo
====

.. todo::
   - Behavior
   - Being Architecture
   - Communication SDO / PDO
   - Parallel State Change / Homing
   - Logging
   - Packing being application as a service
   - Running the tests


Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   concepts
   manuals
   tutorials
   guides
   api-reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
