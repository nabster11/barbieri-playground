.PHONY: run clean all

BINS= \
	app \
	app2 \
	app3 \
	app4 \
	app5 \
	test-events

THEMES= \
	default.edj \
	light.edj

BUILT=$(BINS) $(THEMES)

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

%: %.c e_box.c key_monitor.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

app5: app5.c vlist.c key_monitor.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

clean:
	rm -f *~ $(BUILT)
