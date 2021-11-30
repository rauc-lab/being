.. parsed-literal::
    ╭────╮        ╭╮              
    │╭─╮ │        ╰╯              
    │╰─╯╭╯╭────╮  ╭╮  ╭────╮╭────╮
    │╭─╮╰╮│╭──╮│  ││  │╭──╮││╭──╮│
    │╰─╯ ││╰───╮  ││  ││  │││╰──╯│
    ╰────╯╰────╯  ╰╯  ╰╯  ╰╯╰───╮│
                            ╭───╯│
                            ╰────╯

Being
=====

Block based Python middle ware library for the `PATHOS
<https://pathos.ethz.ch>`__ project.
Developed at `RAUC <https://asl.ethz.ch/research/rauc.html>`__.
Makes it possible to steer motors via CAN / CanOpen and process sensor data.
Controllable via a web user interface.

PATHOS
------

PATHOS is a browser based animatronics platform for artists.
The aim is to enable non-technical people to use robotics as an artistic medium of algorithmic motion and response, and over time allow this language to infuse visual culture at large.

The platform facilitates collaboration between engineer and non-engineer and emphasizes an architecture that safeguards the artist’s settings while supporting the life-cycle of a technology dependent artwork, from sketching to producing to repair to remake.

The middleware of PATHOS is called BEING.
We intend to grow and improve its programming and hardware library over time through a contribution model.
Its aim is to translate high level settings into nuanced hardware control and to stay platform independent while interfacing hardware as it comes and goes.

The project is currently developed at the Robotics Aesthetics & Usability Center (RAUC) nested within the `Autonomous Systems Lab <https://asl.ethz.ch>`__ at ETHZ.

PATHOS was initiated by the Indo-Danish art duo Pors & Rao during an artist residency at the `Wyss Zurich <https://www.wysszurich.uzh.ch/projects/outreach-projects/pathos?tx_ogwyssteams_teamlist%5Baction%5D=show&tx_ogwyssteams_teamlist%5Bcontroller%5D=Page&tx_ogwyssteams_teamlist%5Bteamid%5D=266&cHash=309fe1ed2ff78ac4cddd292a3f2b0d2e>`__ in early 2017.
The frustrations they faced over a period of 19 years while working with lifelike physical animation and response informed the enabling of robotics as a performative medium.

Getting Started
---------------

Prerequisites
^^^^^^^^^^^^^

Being can be installed via the setup.py

.. code-block:: bash

    python setup.py install


or via `PyPi <https://pypi.org/project/being/>`__ (check latest version).

.. code-block:: bash

    pip install being

Development enviroment can be set up with

.. code-block:: bash

    python setup.py develop

Running the tests with

.. code-block:: bash

    python3 setup.py test

Platform and Supported Hardware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Being has mainly be developed on macOs and Linux (Ubuntu, Raspberry Pi OS).
Although untested on Windows it should be possible to be run on there as well.
Let us know if you encounter any problems.

Currently supported motor hardware modules are the *Linear Motion Module*.
We will integrate more motors from different vendors in the near future.

Primer
------

Block Network
^^^^^^^^^^^^^

Being provides various blocks which can be connected with each other (e.g. Motor, Sensor, Network blocks).
There are two types of connections: *value* and *message* based.
The former type provides a continuous stream of date while the latter discrete messages.
Payload can be any kind of Python object.

The connections have a `connect()` method which can be used for making connections.
Note that the ``|`` operator has been overloaded to make it possible to *chain* multiple blocks in series.

.. code-block:: python

    # Pipe operator
    a | b | c

    # Is equivalanet to:
    # >>> a.output.connect(b.input)
    # ... b.output.connect(c.input)

Once a block network is defined it can be run with the `awake(*blocks)` function.
This will continuously execute the block network and start up the web server for the web user interface.

Example Being
^^^^^^^^^^^^^

A small example being, based on the one from the ÉCAL workshop (without sensor input which is only available on the Raspberry PI).

.. code-block:: python

    #!/usr/local/python3
    from being.behavior import Behavior
    from being.being import awake
    from being.motion_player import MotionPlayer
    from being.motors import Motor
    from being.resources import manage_resources


    with manage_resources():
        mot0 = Motor(nodeId=1, length=0.100)
        mot1 = Motor(nodeId=2, length=0.100)
        behavior = Behavior.from_config('behavior.json')
        mp = MotionPlayer(ndim=2)
        behavior.associate(mp)
        mp.positionOutputs[0].connect(mot0.input)
        mp.positionOutputs[1].connect(mot1.input)
        awake(behavior)

A `Behavior` block tells a `MotionPlayer` which motions to play.
Motions are multi dimensional splines which will be stored in a content directory next to the program.
The `MotionPlayer` blocks samples the currently playing spline and outputs the values to two `Motor` blocks (CAN IDs 1 and 2).
This will also startup a web UI which can be accessed under `localhost:8080 <http://localhost:8080>`__.

Further Being Programs
^^^^^^^^^^^^^^^^^^^^^^

Please have a look at these other example programs:

* `ecal_being.py <https://github.com/rauc-lab/being/blob/master/ecal_being.py>`__: Being program for the ÉCAL workshop.
* `run_dummy_being.py <https://github.com/rauc-lab/being/blob/master/run_dummy_being.py>`__: Standalone being with two virtual dummy motors for development and testing purposes.


Coding Style
------------

PEP8 / Google flavored.
With the one exception for variable and argument names (`camelCase`). Function and in methods are `snake_case()`.

Workshops
---------

* Tutorial videos for the workshop *Being at ÉCAL* can be found `here <https://pathos.ethz.ch/ecal-workshop-2021.html>`__.

Authors
-------

* Alexander Theler (`RAUC <https://asl.ethz.ch/research/rauc.html>`__, `GitHub <https://github.com/atheler>`__)
* Silvan Januth (`Wyss Zurich <https://www.wysszurich.uzh.ch/technology-platforms/robotics-technologies?tx_ogwyssteams_teamlist%5Baction%5D=show&tx_ogwyssteams_teamlist%5Bcontroller%5D=Page&tx_ogwyssteams_teamlist%5Bteamid%5D=14&cHash=fd397786f38a735838b306d7e9655ca9#c117>`__)


Original Idea & User Interface
------------------------------

* Søren Pors

Acknowledgments
---------------

* Prof. Einar Nielson
* Ilia Sergachev
* Dr. Philipp Reist
* Prof. Roland Siegwart

Supporters
----------

* Faulhaber Minimotor Sa
* Gebert Ruef Foundation
* Google Cultural Institute
