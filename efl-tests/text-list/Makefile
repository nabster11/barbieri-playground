.PHONY: run clean all

all: app app2 default.edj

%.edj: %.edc
	edje_cc $< $@

app: app.c e_box.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

app2: app2.c e_box.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

clean:
	rm -f *~ app app2 default.edj

run: app2 default.edj
	./app2
