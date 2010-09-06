# Copyright 1999-2010 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header $

EAPI="2"

DESCRIPTION="Provides a daemon for managing internet connections"
HOMEPAGE="http://connman.net"
SRC_URI=""

inherit git
EGIT_REPO_URI="git://git.kernel.org/pub/scm/network/connman/connman.git"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~arm ~amd64 ~x86"
IUSE="bluetooth +caps debug +dhclient dnsproxy doc +ethernet hh2serial-gps google meego ntpd ofono policykit threads tools +udev +wifi +portal"
# ospm openconnect wimax

RDEPEND=">=dev-libs/glib-2.16
	>=sys-apps/dbus-1.3
	bluetooth? ( net-wireless/bluez )
	caps? ( sys-libs/libcap-ng )
	dhclient? ( net-misc/dhcp )
	ntpd? ( net-misc/ntp )
	ofono? ( net-misc/ofono )
	policykit? ( >=sys-auth/policykit-0.7 )
	tools? ( net-firewall/iptables )
	udev? ( >=sys-fs/udev-141 )
	wifi? ( >=net-wireless/wpa_supplicant-0.7[dbus] )"

DEPEND="${RDEPEND}
	doc? ( dev-util/gtk-doc )"

src_configure() {
	[ ! -x "configure" ] && ./bootstrap
	econf \
		--localstatedir=/var \
		--enable-client \
		--enable-datafiles \
		--enable-loopback=builtin \
		$(use_enable caps capng) \
		$(use_enable ethernet ethernet builtin) \
		$(use_enable wifi wifi builtin) \
		$(use_enable bluetooth bluetooth builtin) \
		$(use_enable ofono ofono builtin) \
		$(use_enable dhclient dhclient builtin) \
		$(use_enable dnsproxy dnsproxy builtin) \
		$(use_enable google google builtin) \
		$(use_enable meego meego builtin) \
		$(use_enable policykit polkit builtin) \
		$(use_enable portal portal builtin) \
		$(use_enable ntpd ntpd builtin) \
		$(use_enable hh2serial-gps hh2serial-gps builtin) \
		$(use_enable debug) \
		$(use_enable doc gtk-doc) \
		$(use_enable threads) \
		$(use_enable tools) \
		$(use_enable udev) \
		--disable-fake \
		--disable-iwmx \
		--disable-iospm \
		--disable-openconnect

}

src_install() {
	emake DESTDIR="${D}" install || die "emake install failed"
	dobin client/cm || die "client installation failed"

	keepdir /var/lib/${PN} || die
	newinitd "${FILESDIR}"/${PN}.initd ${PN} || die
	newconfd "${FILESDIR}"/${PN}.confd ${PN} || die
}
