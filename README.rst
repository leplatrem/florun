.. image :: http://mathieu-leplatre.info/media/2009-florun.gif

=====
USAGE
=====

The editor comes up by default (requires PyQt4)
  ./flo-run

Run a flow
  ./flo-run --execute=FILE


=======
AUTHORS
=======
    * Mathieu Leplatre <contact@mathieu-leplatre.info>


=======
LICENSE
=======

    * GNU Public License


===========
TRANSLATION
===========

Notes about extracting and compiling translations

Qt Gui
------

1. Extract
  pylupdate4 -verbose florun/gui.py -ts florun/locale/fr_FR/gui.ts

2. Compile
  lrelease florun/locale/fr_FR/gui.ts


Python
------

1. Extract
  xgettext -k_ -o florun/locale/florun.pot *.py florun/*.py

2. Init lang
  msginit -i florun/locale/florun.pot -o fr_FR/LC_MESSAGES/florun.po
or
  msgmerge -U fr_FR/LC_MESSAGES/florun.po florun/locale/florun.pot

3. Compile
  msgfmt florun/locale/fr_FR/LC_MESSAGES/florun.po -o florun/locale/fr_FR/LC_MESSAGES/florun.mo


=========
CHANGELOG
=========

0.2.0
-----

    * Bug #152: Drop position of items is not centered under mouse
    * Bug #264: Fix flag itemChange() introduced in 4.6
    * Bug #265: Catch keyboard interrupt in editor
    * Feature #128: Export flow to image
    * Feature #129: Editor Preferences system
    * Feature #145: Distinguish start nodes from other in GUI
    * Feature #148: Arrows on connectors
    * Feature #155: ParameterEditor : press enter in field should apply changes
    * Feature #157: Flow readonly while process running
    * Feature #228: Allow to run unsaved flow
    * Refactoring #267: Write some tests, at last !



0.1.0
-----

    * Bug #110: constraints on splitview
    * Bug #112: z-order on node titles
    * Bug #130: segfault when activate/desactivate slot parameter
    * Bug #131: Use prefix when running python florun.py
    * Bug #132: Prevent start unsaved flow
    * Bug #133: Cross stays when leaving slot without passing over node
    * Bug #134: Icon missing on ParameterEditor buttons
    * Bug #135: Run modified flow after accepting to save
    * Bug #136: sometimes connectors are not removed when node deleted
    * Bug #137: Prevent adding twice the same connector
    * Bug #138: Slot sometimes appears purple whereas it has no connectors
    * Bug #139: NoneType error on connector remove
    * Bug #142: Unload ParameterEditor when unselect item
    * Bug #147: Prevent scrollbars on view when unnecessary
    * Bug #149: ParameterEditor : hide/show slot does not enables Apply/Undo
    * Bug #150: ParameterEditor : discard changes does not restore slots
    * Bug #151: ParameterEditor : don't ask to apply on Cancel
    * Bug #156: clear console and switch to editor when open Flow
    * Bug #158: Prevent start when no flow loaded
    * Bug #159: Cannot interrupt running flow with Ctrl+C
    * Bug #160: Cannot run command "grep toto" in Process nodes
    * Feature #108: disable save when no change
    * Feature #109: show star when changed
    * Feature #111: style wrapper for stock icons
    * Feature #116: Args field on console if flow contains CLIParamValue
    * Feature #119: add title + icon + description for node in parametereditor
    * Feature #122: prevent loosing changes in ParameterEditor
    * Feature #125: Locales initialization
    * Feature #141: Tooltips on Items slots with interfaces description
    * Feature #143: Move execution of QProcess to a thread
    * Feature #144: order nodes by flow sequence
    * Refactoring #127: Log levels

0.0.1
-----

    * Initial base code
