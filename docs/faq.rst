FAQ
===

Some common pitfalls

Every Other Time I have to disconnect the CAN interface
-------------------------------------------------------

Are you releasing your resources after your program has ran?

.. code-block:: python

   from being.backends import CanBackend

   with CanBackend() as network:  # <- will disconnect network after exiting `with` block
       ...


Strange Errors in Browser Developers Tools
------------------------------------------

Try *hard-refreshing* the webpage. When making changes on the code the cached
JS code in the browser can lead to unexpected errors


I See No Logs
-------------

Being uses the standard Python logging system which can be tricky. This
Stackoverflow post is a good summary how to work with the Python logging system
`Python Logging Not Outputting Anything <https://stackoverflow.com/questions/7016056/python-logging-not-outputting-anything>`_.
In general every logger instance in Being is a child logger of the being root logger
:data:`being.logging.BEING_LOGGER`. New logger get created with
:func:`being.logging.get_logger`. When setting the logger level to :data:`logging.DEBUG`:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

this will also set every other logger to DEBUG (e.g. ``can`` will log every CAN
message). There is a util function to suppress other loggers besides Being
:func:`being.logging.suppress_other_loggers`. But caution, this will also
suppress every HTTP request by default!


Web Server Not Starting up With Many Motors on a Raspberry Pi
-------------------------------------------------------------

The default interval rate is quite sportive and with more than two motors a
Raspberry Pi might come to its performance limit. Try increasing the interval
rate in :data:`being.configuration` or changing your design from stream `target
postion` values to one using `profiled position` instead.
