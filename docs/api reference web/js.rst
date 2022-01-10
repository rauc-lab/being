js
==


Submodules
----------


js/api
------


API definitions for communication with back-end.

.. js:autoclass:: Api
   :members:


js/array
--------


Numpy style array helpers. Most of these functions operate on standard and
nested JS arrays (like [0, 1, 2, 3] or [[0, 1, 2], [3, 4, 5]]).

.. js:autofunction:: array.array_shape


.. js:autofunction:: array.array_ndims


.. js:autofunction:: array.array_reshape


.. js:autofunction:: array.array_min


.. js:autofunction:: array.array_max


.. js:autofunction:: array.zeros


.. js:autofunction:: array.arange


.. js:autofunction:: array.linspace


.. js:autofunction:: array.add_arrays


.. js:autofunction:: array.multiply_scalar


.. js:autofunction:: array.divide_arrays


.. js:autofunction:: array.subtract_arrays


.. js:autofunction:: array.transpose_array


.. js:autofunction:: array.array_full


.. js:autofunction:: array.diff_array


js/bbox
-------


Bounding box. Progressively expand a 2D region.

.. js:autoclass:: BBox
   :members:


js/button
---------


Button helpers. Wrappers around material icons. Button icon can be specified
with the `iconName` string (see `Google Material Design Icon Gallery <https://fonts.google.com/icons>`_
for available icons).

Toggle buttons are normal buttons with the checked attribute set.

.. js:autofunction:: button.create_button


.. js:autofunction:: button.toggle_button


.. js:autofunction:: button.switch_button_off


.. js:autofunction:: button.switch_button_on


.. js:autofunction:: button.switch_button_to


.. js:autofunction:: button.is_checked


.. js:autofunction:: button.enable_button


.. js:autofunction:: button.disable_button


js/color_map
------------


Color maps. Currently only batlowK color map is available (see website of
`Fabio Crameri <https://www.fabiocrameri.ch/batlow/>`_).

.. js:autofunction:: color_map.get_color


js/config
---------


Some configuration values / definitions.

.. js:autoattribute:: INTERVAL


.. js:autoattribute:: API


.. js:autoattribute:: WS_ADDRESS


js/constants
------------


All kind of constants.

.. js:autoattribute:: MS


.. js:autoattribute:: PI


.. js:autoattribute:: TAU


.. js:autoattribute:: LEFT_MOUSE_BUTTON


.. js:autoattribute:: ONE_D


.. js:autoattribute:: TWO_D


js/curve
--------


Curve container.

.. js:autoattribute:: ALL_CHANNELS


.. js:autoclass:: Curve
   :members:


.. js:autofunction:: curve.Curve.from_dict


js/deque
--------


Double ended queue.

.. js:autoclass:: Deque
   :members:


js/draggable
------------


Make something draggable.

.. js:autofunction:: draggable.make_draggable


js/editable_text
----------------


Editable text field.

.. js:autofunction:: editable_text.make_editable


js/fetching
-----------


Wrapper verbs around standard JS fetch.

.. js:autofunction:: fetching.get


.. js:autofunction:: fetching.put


.. js:autofunction:: fetching.post


.. js:autofunction:: fetching.delete_fetch


.. js:autofunction:: fetching.fetch_json


.. js:autofunction:: fetching.get_json


.. js:autofunction:: fetching.post_json


.. js:autofunction:: fetching.put_json


js/history
----------


Editing history.

.. js:autoclass:: History
   :members:


js/layout
---------


Graphical layout helpers. Only finding nice tick labels for now. Taken from
here: `Nice label Algorithm For Charts With Minimum Ticks
<https://stackoverflow.com/questions/8506881/nice-label-algorithm-for-charts-with-minimum-ticks/16363437>`_.

.. js:autofunction:: layout.nice_number


.. js:autofunction:: layout.tick_space


js/math
-------


All kinds of math helpers.

.. js:autofunction:: math.clip


.. js:autofunction:: math.round


.. js:autofunction:: math.normal


.. js:autofunction:: math.mod


.. js:autofunction:: math.floor_division


.. js:autofunction:: math.isclose


js/notification_center
----------------------


Notification central. Puts notifications to the upper right of the screen.
Builds on top of
`AlertifyJS <https://alertifyjs.com>`_.

.. js:autofunction:: notification_center.remodel_notification


.. js:autoclass:: NotificationCenter
   :members:


js/serialization
----------------


Serializing and deserializing splines and curve objects.

.. js:autofunction:: serialization.objectify


.. js:autofunction:: serialization.anthropomorphify


js/spline
---------


Spline stuff. Some constants and BPoly wrapper. Spline data container. No
spline evaluation. Sampling splines for plotting is handled by SVG. Helpers
for manipulating the shape of the spline:

- Moving control points around
- Changing the derivative at a given knot
- Inserting / removing knots

.. js:autoattribute:: KNOT


.. js:autoattribute:: FIRST_CP


.. js:autoattribute:: SECOND_CP


.. js:autoattribute:: Order


.. js:autoattribute:: Degree


.. js:autoattribute:: LEFT


.. js:autoattribute:: RIGHT


.. js:autoattribute:: COEFFICIENTS_DEPTH


.. js:autofunction:: spline.spline_order


.. js:autofunction:: spline.spline_degree


.. js:autofunction:: spline.zero_spline


.. js:autoclass:: BPoly
   :members:


.. js:autofunction:: spline.BPoly.from_dict


js/svg
------


Working with SVG elements.

.. js:autofunction:: svg.create_element


.. js:autofunction:: svg.setattr


.. js:autofunction:: svg.getattr


.. js:autofunction:: svg.path_d


.. js:autofunction:: svg.draw_path


.. js:autofunction:: svg.draw_circle


.. js:autofunction:: svg.draw_line


js/utils
--------


This and that.

.. js:autofunction:: utils.ready


.. js:autofunction:: utils.remove_all_children


.. js:autofunction:: utils.clear_array


.. js:autofunction:: utils.last_element


.. js:autofunction:: utils.deep_copy


.. js:autofunction:: utils.cycle


.. js:autofunction:: utils.arrays_equal


.. js:autofunction:: utils.assert


.. js:autofunction:: utils.searchsorted


.. js:autofunction:: utils.add_option


.. js:autofunction:: utils.is_valid_filename


.. js:autofunction:: utils.insert_in_array


.. js:autofunction:: utils.remove_from_array


.. js:autofunction:: utils.defaultdict


.. js:autofunction:: utils.sleep


.. js:autofunction:: utils.rename_map_key


.. js:autofunction:: utils.find_map_key_for_value


.. js:autofunction:: utils.insert_after


.. js:autofunction:: utils.emit_event


.. js:autofunction:: utils.emit_custom_event


js/web_socket
-------------



.. js:autoclass:: WebSocketCentral
   :members:


js/widget
---------


Widget base class for being HTML web components. Simple HTMLElement with an
additional toolbar div.

.. js:autofunction:: widget.append_template_to


.. js:autofunction:: widget.append_link_to


.. js:autofunction:: widget.create_select


.. js:autoclass:: WidgetBase
   :members:


.. js:autoclass:: Widget
   :members:

