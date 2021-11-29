.. Being documentation master file, created by
   sphinx-quickstart on Tue Nov 16 14:16:30 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

================
Welcome to Being
================

.. image:: images/pathos\ logo.png
   :alt: PATHOS logo

Robotic middleware library for easy to use robotic project.

.. _GitHub: https://github.com/rauc-lab/being


Key Features
============

- Block logic
- Supports CAN based motor controllers
- Spline based motion curves
- Web based user interface


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

Tutorial
========

TODO

Source Code
===========

This project is hosted on GitHub_.

Dependencies
============

TODO Needed?

Communication channels
======================

TODO Needed?

Contributing
============

TODO

Authors and License
===================

The ``being`` package is written by Alexander Theler and is licensed under the
MIT license. Feel free to use and improve this project.

Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   concepts
   tutorials
   guides
   reference/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
