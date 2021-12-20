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


Bounding box class.

.. js:autoclass:: BBox
   :members:


js/button
---------


Button helper stuff. Helper functions for using buttons as toggle buttons.

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



js/config
---------


Some basic configurations.

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



.. js:autoclass:: Curve
   :members:


js/deque
--------


Deque array type with maxlen and better clearer naming (from Pythons
 collections.deque).

js/draggable
------------


Make something draggable. Manage mouse events for draggable actions.

.. js:autofunction:: draggable.make_draggable


js/editable_text
----------------


Make text field editable by double clicking it.

js/fetching
-----------


Wrapper verbs around standard fetch.

.. js:autofunction:: fetching.fetch_json


js/history
----------


Edit history class.

.. js:autoclass:: History
   :members:


js/layout
---------


Graphical layout helpers. Only finding nice tick labels for now. Taken from
 here:
 https://stackoverflow.com/questions/8506881/nice-label-algorithm-for-charts-with-minimum-ticks/16363437

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


Notification central.

.. js:autofunction:: notification_center.remodel_notification


.. js:autoclass:: NotificationCenter
   :members:


js/serialization
----------------



.. js:autofunction:: serialization.objectify


js/spline
---------


Spline stuff. Some constants and BPoly wrapper. Spline data container.

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


Working with SVG element helpers.

.. js:autofunction:: svg.create_element


.. js:autofunction:: svg.setattr


.. js:autofunction:: svg.getattr


.. js:autofunction:: svg.path_d


.. js:autofunction:: svg.draw_path


.. js:autofunction:: svg.draw_circle


.. js:autofunction:: svg.draw_line


js/utils
--------


All kinds of util. Lots from http://youmightnotneedjquery.com.

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


js/web_socket
-------------


Small web socket wrapper.

.. js:autoclass:: WebSocketCentral
   :members:


js/widget
---------


Base class for HTML web component. Simple HTMLElement with a toolbar div.

.. js:autofunction:: widget.append_template_to


.. js:autofunction:: widget.append_link_to


.. js:autofunction:: widget.create_select


.. js:autoclass:: WidgetBase
   :members:


.. js:autoclass:: Widget
   :members:

