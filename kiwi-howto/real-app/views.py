from kiwi.ui.delegates import Delegate, SlaveDelegate
from kiwi.ui.gadgets import quit_if_last

import models

class Shell( Delegate ):
    def __init__( self ):
        Delegate.__init__( self,
                           gladefile="shell",
                           delete_handler=quit_if_last,
                           widgets=( "edit", "add", "remove", "quit" )
                           )
        self.list = List( toplevel=self )
        self.attach_slave( "list_placeholder", self.list )
        self.list.focus_toplevel()


    def on_quit__activate( self, widget, *args ):
        quit_if_last()


    def on_edit__activate( self, widget, *args ):
        pass


    def on_add__activate( self, widget, *args ):
        editor = Editor( toplevel=self )
        editor.show_all()
        editor.focus_topmost()


    def on_remove__activate( self, widget, *args ):
        pass




class List( SlaveDelegate ):
    def __init__( self, toplevel=None ):
        SlaveDelegate.__init__( self,
                                gladefile="list",
                                toplevel=toplevel,
                                widgets=( "table", )
                                )
        self.load_data()

    def load_data( self ):
        self.table.clear()
        for p in models.Person.select():
            self.table.append( p, select=False )

    def on_table__double_click( self, widget, *args ):
        pass


class Editor( Delegate ):
    def __init__( self, toplevel=None ):
        Delegate.__init__( self,
                           toplevel=toplevel,
                           gladefile="editor",
                           widgets=( "name", "address", "phones",
                                     "add_phone", "edit_phone", "remove_phone",
                                     "birthday", "category",
                                     "cancel", "ok" )
                           )

    def on_cancel__clicked( self, widget, *args ):
        self.toplevel.close()

    def on_ok__clicked( self, widget, *args ):
        self.toplevel.delete()

