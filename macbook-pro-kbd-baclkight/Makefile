STRIP = strip
macbook-pro-kbd-baclkight: macbook-pro-kbd-baclkight.c
	$(CC) $^ -o $@ -O2 -Wall -Wextra -fdata-sections -ffunction-sections -Wl,--as-needed -Wl,--gc-sections
	$(STRIP) -s $@
	sudo chown root:root $@
	sudo chmod +s $@

clean:
	rm -f macbook-pro-kbd-baclkight

