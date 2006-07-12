from sqlobject import *

connection = None

class Person( SQLObject ):
    _lazyUpdate = True
    name     = StringCol( length=100 )
    address  = StringCol( default=None )
    birthday = DateCol( default=None )
    phones   = MultipleJoin( "Phone" )
    category = RelatedJoin( "Phone" )

class Phone( SQLObject ):
    _lazyUpdate = True
    number = StringCol( length=20 )
    person = ForeignKey( "Person" )

class Category( SQLObject ):
    _lazyUpdate = True
    name    = StringCol( length=20, alternateID=True )
    persons = RelatedJoin( "Person" )


def createTables( ifNotExists=True ):
    Person.createTable( ifNotExists=ifNotExists )
    Phone.createTable( ifNotExists=ifNotExists )
    Category.createTable( ifNotExists=ifNotExists )

def setConnection( conn ):
    global connection

    if isinstance( conn, str ):
        conn = connectionForURI( conn )

    connection = conn
    Person._connection = connection
    Phone._connection = connection
    Category._connection = connection

