CC = gcc
RM = rm -f

GLIB_LDFLAGS := $$(pkg-config --libs glib-2.0)
GLIB_CFLAGS := $$(pkg-config --cflags glib-2.0)

LDFLAGS += \
	$(GLIB_LDFLAGS)

CFLAGS += \
	-Wall \
	$(GLIB_CFLAGS)

SOURCES = parser.c
OBJECTS = $(patsubst %.c,%.o,$(SOURCES))

liburl-query-parser.so: $(OBJECTS)
	$(CC) $(LDFLAGS) -shared $(OBJECTS) -o $@


%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

test: liburl-query-parser.so test.o
	$(CC) $(LDFLAGS) -L. -Wl,-rpath=. -lurl-query-parser test.o -o $@


.PHONY: clean
clean: $(OBJECTS) test test.o liburl-query-parser.so
	$(RM) $(OBJECTS)
	$(RM) test
	$(RM) test.o
	$(RM) liburl-query-parser.so