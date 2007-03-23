.PHONY: run clean all

BINS= \
	app \
	app2 \
	app3 \
	test-events

THEMES= \
	default.edj \
	light.edj

BUILT=$(BINS) $(THEMES)

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

%: %.c e_box.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$^ -o $@

clean:
	rm -f *~ $(BUILT)
