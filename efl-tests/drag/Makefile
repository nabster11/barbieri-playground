.PHONY: run clean all

THEMES= \
	simple.edj \
	complete.edj

BINS=

BUILT=$(THEMES) $(BINS)
CFLAGS=-g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`edje-config --cflags` \
	`ecore-config --cflags`

LDFLAGS= `edje-config --libs` \
	`ecore-config --libs`

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

clean:
	rm -f *~ $(BUILT)
