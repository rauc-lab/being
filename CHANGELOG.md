# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2022-01-19

### Fixed
- Unnecessary PCAN patch causes errors on Darwin

## [1.0.1] - 2022-01-19

### Fixed
- Missing templates package data

## [1.0.0] - 2022-01-19

### Added
- Notify user that Being is running when invoking `awake()`
- `AudioBackend` and `Mic` block for audio onset detection.
- Stop ongoing homing when pressing homing button again
- Finalizing documentation
- `audio` and `rpi` extra requirements

### Changed
- `DummySensor` now resides in `being.sensors` module.
- Changed being config file to YAML
- *Alphabetical* instead of *most recently modified* order for motion curves
- Max height for behavior and editor widget
- Deactivate power and homing button when there are no motors
- Resize editor when new content messages arrive
- Only display widgets when the corresponding blocks exist

### Removed
- Relay connectables

### Fixed
- Installation issue. `patch_pcan_on_darwin()` only when can & canopen are installed.

## [0.3.6] - 2021-12-23

### Changed
- Default PDO mapping: `TARGET_POSITION` and `TARGET_VELOCITY` both over PDO 2.
- `Current Actual Value` via PDO instead of SDO.
- Controller now tries to restore node's state after homing.

### Removed
- Homing's capture, restore and teardown methods.
- Replaced `switch_off_drives` method `CanBackend` with `turn_off_motors` method (which disables drives with a timeout).

### Fixed
- `CrudeHoming` with timeout during homing

## [0.3.5] - 2021-12-14

### Fixed

- Bugfix for `named_tuple_from_dict`. With Python 3.7 named tuples without default values have no `_field_defaults` attribute.

## [0.3.4] - 2021-11-29

### Fixed

- Unselected / wrong knots got deleted because Array.sort() defaults to lexicographic order for numbers. See [further resources](https://javascriptwtf.com/wtf/numbers-sorted-alphabetically).

## [0.3.3] - 2021-11-29

### Added

- Draggable selection. Knots / paths can be selected and dragged around. Also horizontal selection rectangle.
- Drawer with keyboard shortcuts

### Changed

- Improved snapping to grid. Selected knots are excluded from grid.
- Drawer drag navigation secondary with shift key.
- `make_draggable()` helper functions with callback object as argument. Also click / dblclick suppression when moved.
- `Plotter` / `Drawer`: Separation of `draw_canvas()` and `draw_svg()` (formerly `_draw_curve_elements()`).

### Fixed

- Do not redraw SVG elements on each being state message.

## [0.3.2] - 2021-11-24

### Fixed

- Wrong maximum current value during crude homing lead to motors getting stuck
- Expand software position limits by default

## [0.3.1] - 2021-11-24

### Changed

- `CiA402Node` state switching. The state switching job now continuously tries to replan the state trajectory if anything changes.
- Default motor settings as ordered dictionaries
- Drawer refactor: Control points inside group with fading out effect.
- UI buttons now hold an  `<i></i>` element holding the icon (so that we can rotate it independently from button). `change_icon(newIcon)` button "method" for changing the icon later on.
- Viewport not resizing when making a change and already zoomed in
- JS `arange()` array function with start, stop, step arguments

### Added

- Scan for node ids network helper method
- Timeout is now mandatory for state switching job. Controller / Homing both catch TimeoutErrors
- Editor flip curve horizontally / vertically buttons.
- New pathos_being.py program which scans for available nodes and initializes a LinearMotor for each one.

### Fixed

- Hanging state transition during crude homing. Single SDO based state transition seemed to clash with PDO based ones. To be tested...
- `get_logger()` not returning being root logger for some arguments
- Plotting lines order did not correspond with motor id order

## [0.3.0] - 2021-11-18

### Changed

- Splines became curves
- Web socket broker via aiohttp on startup
- Behavior.associate() method deprecated
- Content methods
- EC 45 default settings
- API changes for curves
- Signal handling via aiohttp application
- Motion editor rework with curves and support for simultaneous playback on multiple motion players

### Added

- Content with Files instance handling file system access

### Fixed

- Missing position profile support for WindupMotor block
- Web socket connection reset error
- JS safari compatibility issues

### Removed

- Old JS curver widget

## [0.2.5] - 2021-10-07

### Changed

- Being `CONFIG` instance now resides in module `being.configuration` (renamed `being.config` -> `being.configuration`)
- Block value and message connection helper methods return created inputs / outputs for concatenation

### Added

- `Config` / `ConfigFile` implementations for TOML, YAML, JSON and INI formats
- Parameter blocks: `Slider`, `SingleSelection`, `MultiSelection` and `MotionSelection`. With UI integration
- `NestedDict` mutable mapping

## [0.2.4] - 2021-09-16

### Added

- Profiled position mode via message connections
- New motor blocks: `BeltDriveMotor`, `LeadScrewMotor` and `WindupMotor`
- Some CiA 402 test cases

### Changed

- `Pacemaker` separate from `Being` object
- `MotorBlock` base class with ABC method `get_length()` .
- Change node operation mode via `Controller`
- Motor with `deviceUnits`

### Fixed

- Stuck in SDO state change job

### Removed

- `Sawtooth` block
- Old scripts

## [0.2.3] - 2021-09-14

### Added

- Support for generator based `CiA402Node` state switching
- Node settings path now support int parts
- `MotorInterface` ABC, `MotorState`
- `CiA402Node` `move_to()` / `move_with()` methods

### Changed

- SYNC thread now in `Pacemaker` class
- Homing
- Being root logger

### Fixed

- Typo State.OPERATION_ENABLE -> State.OPERATION_ENABLED

### Removed

- Deactivating PDO communication during state switching

## [0.2.2] - 2021-09-07

### Added

- Dedicated SYNC message sender thread
- Enabling / disabling motor with optional timeout
- Motor blocks done homing event
- Software side position controller for `Epos4`

### Changed

- `proper_homing()` routine

### Fixed

- Motor state change timeout issues
- Wrong NMT state causing on errors on some controllers
- Wrong CiA 402 state change command

## [0.2.1] - 2021-09-02

### Fixed

- Reset software position limits on Faulhaber motors
- No overlap with plotting lines

## [0.2.0] - 2021-09-01

### Added

- License
- CiA 402 homings
- Choreo to spline conversion
- EPOS4 support
- Web UI control panel with block diagram
- Web UI notifications
- Some third-party JS libraries

### Changed

- Readme
- Motor blocks, controllers, motors
- Motion players / motors web API
- Web UI console moved to control panel
