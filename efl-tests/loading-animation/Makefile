.PHONY: run clean all

all: app

%.edj: %.edc
	edje_cc $< $@

app: app.c
	gcc \
	`edje-config --cflags --libs` \
	`ecore-config --cflags --libs` \
	$< -o $@

clean:
	rm -f *~ app default.edj

run: app default.edj
	./app
