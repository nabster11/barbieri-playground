.PHONY: run clean all

all: app app2 app3 default.edj light.edj

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

app3: app3.c e_box.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

clean:
	rm -f *~ app app2 app3 default.edj

run: app2 default.edj
	./app2

run3: app3 default.edj
	./app3
