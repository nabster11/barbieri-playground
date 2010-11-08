                 IMPLEMENTING SYSTEMD ON YOUR GENTOO
                 ===================================

= Disclaimer =

I was running Gentoo with OpenRC + BaseLayout 2, network using
connmand and not /etc/init.d/net.$IFNAME. I use Enlightenment DR17 as
desktop environment and slim as graphical login manager (auto-login on
e17 with locked screen, so I still have to type password but
everything is loaded).

As I use my system as a desktop, I gave preference for
systemd-kmsg-syslogd over metalog, so all my log is kept in memory
instead of going to disk (faster, process is more lightweight, but you
loose track after reboot). If you want to try:

    systemctl enable systemd-kmsg-syslogd.socket

As I just connect to my machine in rare failure cases, I'm using ssh
activated from socket, so I just pay the price when I actually use
it:

    systemctl enable sshd.socket

My specific files (systemd units and dbus services) are kept under files/


= Packages =

The following packages are recommended for best performance.

== Upstream ==
 * emerge >=sys-auth/consolekit-0.4.2 after systemd is installed (need to report bug of auto-discovery, --with-systemdsystemunitdir= should be explicitly set/unset)

== Upstream in Portage Overlay ==
 * emerge >=sys-fs/udev-162[systemd]

== Upstream But Not in Portage ==
 * BlueZ:
   * Link: http://article.gmane.org/gmane.linux.bluez.kernel/6479
   * add /lib/systemd/system/bluetooth.service
   * add /usr/share/dbus-1/system-services/org.bluez.service
   * remove /lib/udev/rules.d/97-bluetooth.rules as systemd does that
   * comment bluetooth.sh from /etc/udev/rules.d/70-bluetooth.rules

 * acpid:
   * Link: https://bugzilla.redhat.com/show_bug.cgi?id=617317
   * add /lib/systemd/system/acpid.service (with extra -f option!)

== Not upstream ==
 * ssh http://0pointer.de/public/systemd-units/
 * metalog
 * slim
 * vixie-cron
 * comment/remove /lib/udev/rules.d/90-network.rules
 * add -f to your /lib/systemd/system/{reboot,poweroff}.service,
   otherwise your system will not shutdown. Patch not sent upstream as
   we're working on a native systemd approach that will remove such
   hack.


= Tips & Tricks =

My first attempts with systemd were not so amazing as I was still
getting high PID number. After some investigation I've found that I
had sys-apps/hotplug installed. If you do, please remove it.

Also remove /sbin/hotplug as CONFIG_UEVENT_HELPER_PATH if you happen
to have it set (leave it empty), I did and that alone was causing
around 1500 pid counter difference! (it was not slowing things down
that much after I removed sys-apps/hotplug as the forks were all
failing, but worth noticing).

If you're sane, drop all but one tty from
/etc/systemd/system/getty.target.wants/ and use "screen" to have more
than one shell if bad things happen.


= Numbers =

My system has a kernel with most modules built-in (just those buggy
that need to be removed and added again occasionally were left as
modules). It boots in 2.8s.

After removal of sys-apps/hal, sys-apps/hotplug and
CONFIG_UEVENT_HELPER_PATH, I got my system into Enlightenment DR17
with PID around 500.

My machine is a Macbook SantaRosa 4.1 (white) with slow HD at 5400RPM,
with my current setup it starts Enlightenment DR17 in 17 seconds.
