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

   pip install being

The following third-party libraries are optional:

- `RPi.GPIO <https://pypi.org/project/RPi.GPIO/>`_ for accessing Raspberry Pi GPIO
- `PyAudio <https://pypi.org/project/PyAudio/>`_ for audio streams. Python
  bindings for PortAudio which needs to be installed separately

These can be installed manually or by using `extras`:

.. code-block:: bash

   pip install being[rpi, audio]


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
- A couple of quick :doc:`tutorials`
- Common pitfalls :doc:`faq`
- Guides for extending being :doc:`guides`
- Programming reference :doc:`api-reference`


Source Code
===========

This project is hosted on GitHub_.


Dependencies
============

This project uses the usual suspects of the scientific Python stack. Some
additional third party libraries for HTTP server, CAN/CanOpen and different
configuration formats with round trip preservation.

The Python Raspberry Pi library `RPi.GPIO
<https://pypi.org/project/RPi.GPIO/>`_ is an optional dependency. That Being
can also be used on non Raspberry Pi platforms. When used on a RPI and GPIOs
need to be accessed needs to be installed manually.

The frontend uses pure JavaScript and is directly hosted by an aiohttp web
server from within Being. No JavaScript framework. Static folder is directly
served.


Developing
==========

When downloading the source code it is easiest to install Being as a
development project.

.. code-block:: bash

   $ python3 setup.py install develop

The tests can then be run with

.. code-block:: bash

   $ python3 setup.py test


Contributing
============

Coding style is mostly compatible with
`Google Python Style Guide <https://google.github.io/styleguide/pyguide.html>`_
with one exception: `camelCase <https://en.wikipedia.org/wiki/Camel_case>`_ for
variables, arguments and attributes.
`snake_case <https://en.wikipedia.org/wiki/Snake_case>`_ for functions, methods
and properties.


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
   manuals
   tutorials
   faq
   guides
   api-reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
