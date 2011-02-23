.PHONY: clean all

all: evas-img-resizer evas-img-viewer

clean:
	rm -f evas-img-resizer evas-img-viewer

evas-img-resizer: evas-img-resizer.c Makefile
	$(CC) `pkg-config --cflags --libs evas ecore-evas` -Wall -Wextra -o $@ $<

evas-img-viewer: evas-img-viewer.c Makefile
	$(CC) `pkg-config --cflags --libs evas ecore-evas` -Wall -Wextra -o $@ $<
