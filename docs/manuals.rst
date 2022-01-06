Manuals
=======

Control Panel
-------------

.. image:: images/control\ panel\ widget.png
   :alt: Control panel widget

The control panel shows the block diagram of the running being program. Solid
lines correspond to *message* and dashed lines to *value* connections. The
lines are animated and indicate if data is flowing through (moving red dots and
dash animation).

The block names are defined inside the being program. By default these
correspond to the block type but can be set to arbitrary names representing the
installation.

With the *on / off button* the motors can be enabled or disabled. The *home
button* can be used to re-home the motors. With the *console* button to the
right some of the log messages can be shown and copied to the clipboard.


Behavior
--------

.. image:: images/behavior\ widget.png
   :alt: Behavior widget.

This widget corresponds to a behavior block. It shows the 3x behavior states (I
- III). Each state has its own *motion repertoire*, a subset of all available
motion curves from the content. These define which motions get played for a
given state. If a trigger occurs the behavior jumps to the state III and
traverse back to state II and then I. If no motion is selected a state can also
get skipped. Only one motion for state III will be played and duration inside
state II can be controlled with the *minimum duration* slider. The active state
is highlighted with a black drop shadow.

The behavior can be stopped with the *play / pause button* and the *now
playing* label indicate the currently playing motion.


Editor
------

.. image:: images/editor\ widget.png
   :alt: Editor widget.

This widget can be used to create, edit and playback motion curves. All motion
curves are listed in the left sidebar and can be renamed by double clicking the
name.

Black circles are *knots* and red circles *control points.*. Both can be
dragged around with the mouse. By double clicking new knots can be inserted or
deleted. Multiple knots / control point can be selected and moved at the same
time.

For navigation hold the shift key and move the canvas around. This can also be
used to zoom in and out.

Clicking on the canvas relocates the *transport*. The current playback
position. Playback will be resumed from this position (*play / pause button* or
hitting the space bar).


Toolbar
^^^^^^^

.. figure:: images/toolbar/1history.png
   :alt: Editing history.
   :height: 32px
   :align: left

   Undo and redo edits. Each action on the curve is auto saved and every curve
   has its own editing history.

.. figure:: images/toolbar/2navigation.png
   :alt: Navigation and zooming.
   :height: 32px
   :align: left

   Zoom in and out. Reset viewport to see entire curve.

.. figure:: images/toolbar/3playback.png
   :alt: Playback and looping.
   :height: 32px
   :align: left

   Motion player selection. This controls on which motion player / motor set
   the curve is played. Playback control, motion recording and looping.

.. figure:: images/toolbar/4curves.png
   :alt: Curve selection.
   :height: 32px
   :align: left

   Curve selection. Select which spline in the curve is shown. Remove and add
   new splines.

.. figure:: images/toolbar/5tools.png
   :alt: Tools.
   :height: 32px
   :align: left

   Snap to grid, line continuity at knot, limit curve to motor range and live
   preview positions on the motor when moving knots.

.. figure:: images/toolbar/6manipulation.png
   :alt: Manipulation.
   :height: 32px
   :align: left

   Actions: Scale, stretch, shift, flip and erase.

.. figure:: images/toolbar/7importexport.png
   :alt: Importing and exporting.
   :height: 32px
   :align: left

   Upload or download motion curves.
