# Copyright 1999-2011 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header$

EAPI=4

inherit autotools-utils

DESCRIPTION="library and tools for managing linux kernel modules"
HOMEPAGE="http://modules.wiki.kernel.org/"
SRC_URI="http://packages.profusion.mobi/kmod/${P}.tar.xz"

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="~alpha ~amd64 ~arm ~hppa ~ia64 ~m68k ~mips ~ppc ~ppc64 ~s390 ~sh ~sparc ~x86"
IUSE="+tools"

DEPEND="sys-libs/zlib
	>=sys-apps/baselayout-2.0.1
	!sys-apps/modutils"

src_configure() {
	local myeconfargs=(
		--enable-zlib
		$(use_enable tools)
	)
	autotools-utils_src_configure
}
