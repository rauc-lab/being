.. Being documentation master file, created by

================
Welcome to Being
================

.. image:: images/pathos\ logo.png
   :alt: PATHOS logo

Robotic middleware library for easy to use robotic projects.

.. _GitHub: https://github.com/rauc-lab/being

Being enables engineers and programmers to quickly build robotic programs.
Abstracting away most of the low-level heavy lifting when working with motors
and sensors. The emphasis lies with slim, high-level programs which operate on
*behavior* and *character* to capture the expressive intent of artists. An
integrated web interface makes the resulting applications accessible and
formable at runtime.


Key Features
============

- Connected block logic
- CAN based motor controllers
- Spline based motion curves
- Web based user interface


Library Installation
====================

.. code-block:: bash

   pip install being

The following third-party libraries are optional:

- `RPi.GPIO <https://pypi.org/project/RPi.GPIO/>`_ for accessing Raspberry Pi GPIO
- `PyAudio <https://pypi.org/project/PyAudio/>`_ for audio streams. Python
  bindings for PortAudio which needs to be installed separately.

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
- A couple of quick :doc:`tutorials` and examples
- Common pitfalls :doc:`faq`
- :doc:`guides` for extending being
- Programming reference :doc:`api-reference`


Source Code
===========

This project is hosted on GitHub_.


Dependencies
============

This project uses the usual suspects of the scientific Python stack. Some
additional third party libraries for HTTP server, CAN/CanOpen and different
configuration formats with round trip preservation.

The Python Raspberry Pi library `RPi.GPIO <https://pypi.org/project/RPi.GPIO/>`_ 
is an optional dependency for accessing the GPIO on a Raspberry Pi which is not
available on non Raspberry PI platforms.

The frontend uses pure JavaScript and is directly hosted by an aiohttp web
server from within Being. No additional JavaScript frameworks needed.


Documentation
-------------

Some *non-Python* dependencies are needed for building the documentation:

- Node.js with the `JSDoc <https://www.npmjs.com/package/jsdoc>`_ package
- `Graphviz <https://graphviz.org>`_

Python bindings and additional packages can be installed with

.. code-block:: bash

   pip install -r docs/requirements.txt

.. warning::

   The `sphinx-js <https://github.com/mozilla/sphinx-js>`_ package has a pinned
   version of Jinja2 which is in conflict with the version needed by Being.
   Upgrade Jinja2 after intalling the documentation requirements or reinstall
   the Being requirements.


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
