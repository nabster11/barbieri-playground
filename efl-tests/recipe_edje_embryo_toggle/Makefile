CFLAGS = `edje-config --cflags`
LDFLAGS = `edje-config --libs`

BUILT = edje_exec edje_template $(patsubst %.edc, %.edj, $(wildcard *.edc))

.PHONY: all clean

all: $(BUILT)

clean:
	rm -f *~ *.o $(BUILT)

%.edj: %.edc
	edje_cc $< $@
