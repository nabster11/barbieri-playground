#!/usr/bin/env python

"""
Questions:
 - What's the right way to use proxies, is set_entry() right?
   How to make it work when deleted the item?
 - How to get kiwi.ui.widgets.list.List updated as user types?
 - There is a better way to connect the SlaveDelegate "result" signal
   with its parent?
"""

import gtk

from kiwi.ui.delegates import Delegate, SlaveDelegate
from kiwi.ui.gadgets import quit_if_last
from kiwi.models import Model
from kiwi.utils import gsignal


class EntryEditor( SlaveDelegate ):
    def __init__( self ):
        SlaveDelegate.__init__( self,
                                gladefile="entry_editor",
                                widgets=( "name", "address", "phone" ),
                                )

    def set_entry( self, obj ):
        if not self.proxies:
            self.add_proxy( obj )
        else:
            self.proxies[ 0 ].new_model( obj )

    def unset_entry( self ):
        if self.proxies:
            self.proxies[ 0 ].new_model( None, relax_type=True )

    def set_sensitive( self, v ):
        self.toplevel.set_sensitive( v )



class ListEntries( SlaveDelegate ):
    def __init__( self ):
        SlaveDelegate.__init__( self,
                                gladefile="list_entries",
                                widgets=( "table", ),
                                )

    def add( self, obj, selected=True ):
        self.table.append( obj, selected )

    def get_selected( self ):
        return self.table.get_selected()

    def remove( self, obj ):
        self.table.remove( obj )

    def on_table__selection_changed( self, table, obj ):
        self.emit( "result", obj )



class Addressbook( Delegate ):
    def __init__( self ):
        keyactions = {
            gtk.keysyms.Escape: quit_if_last,
            gtk.keysyms.F1: self.my_f1_handler,
            gtk.keysyms.F2: self.my_f2_handler,
            }
        Delegate.__init__( self,
                           gladefile="addressbook",
                           widgets=( "add", "remove" ),
                           delete_handler=quit_if_last,
                           keyactions=keyactions,
                           )

        self.entry_editor = EntryEditor()
	self.entry_editor.set_sensitive( 0 )
        self.attach_slave( "entry_editor", self.entry_editor )

        self.list_entries = ListEntries()
        self.list_entries.connect( "result", self.entry_selected )
        self.attach_slave( "list", self.list_entries )

    def entry_selected( self, table, obj ):
        if obj is not None:
            self.entry_editor.set_sensitive( 1 )
            self.entry_editor.set_entry( obj )

    def add_entry( self ):
        self.list_entries.add( Person() )

    def del_entry( self ):
        obj = self.list_entries.get_selected()
        if obj is not None:
            self.list_entries.remove( obj )
            self.entry_editor.unset_entry()
            self.entry_editor.set_sensitive( 0 )

    def on_add__clicked( self, *args ):
        self.add_entry()

    def on_remove__clicked( self, *args ):
        self.del_entry()

    def my_f1_handler( self, widget, event, args ):
        self.add_entry()

    def my_f2_handler( self, widget, event, args ):
        self.del_entry()





class Person( Model ):
    def __init__( self, name="", address="", phone="" ):
        self.name = name
        self.address = address
        self.phone = phone





addressbook = Addressbook()
addressbook.show_all()
addressbook.focus_topmost()
gtk.main()
