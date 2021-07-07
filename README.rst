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
<https://www.wysszurich.uzh.ch/projects/outreach-projects/pathos>`_ project.
Developed at `RAUC <https://asl.ethz.ch/research/rauc.html>`_.
Makes it possible to steer motors via CAN / CanOpen and process sensor data.
Controllable via a web user interface.

Getting Started
---------------

Prerequisites
^^^^^^^^^^^^^

Being can be installed via PyPi / pip or directly via setup.py

.. code-block:: bash

    python3 setup.py install

Running the tests
^^^^^^^^^^^^^^^^^

.. code-block:: bash

    python3 setup.py test

Primer
------

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

Coding Style
------------

PEP8 / Google flavored. With the one exception for variable and argument names
(`camelCase`). Function and in methods are `snake_case()`.

Authors
-------

* **Alexander Theler** (`GitHub <https://github.com/atheler>`_)
* **Silvan Januth** (`Wyss Zurich <https://www.wysszurich.uzh.ch/technology-platforms/robotics-technologies?tx_ogwyssteams_teamlist%5Baction%5D=show&tx_ogwyssteams_teamlist%5Bcontroller%5D=Page&tx_ogwyssteams_teamlist%5Bteamid%5D=14&cHash=fd397786f38a735838b306d7e9655ca9#c117>`_)

Acknowledgments
---------------

We like to thank everyone who worked on the PATHOS project before us.
