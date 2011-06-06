#!/usr/bin/env python

"""
Copyright (C) 2009-2010 Gustavo Barbieri <barbieri@profusion.mobi>
Copyright (C) 2010 ProFUSION Embedded Systems
Copyright (C) 2010 Lucas De Marchi <lucas.demarchi@profusion.mobi>

"""

"""
Apply a patch received formatted as by git-format-patch, applying to
the current SVN.

It will:

  - get patch author from "From:" header, if there is no:
    Author, By or Signed-off in the message body.

  - apply the patch

  - automatically "svn add" or "svn rm" based on diff against /dev/null.

  - ask if it should commit.


TODO:

  - check if chmod is enough or svn:executable needs to be set
  - convert gitignore into svn:ignore

"""

import sys, re, os, os.path, email, zlib
from email import message_from_file
from email.header import decode_header
from optparse import OptionParser

usage = "%prog [options] <patches>\n" \
	"Must be run from an svn project (.svn must be present).\n\n" \
        "Given patches will be sorted, so names provided by git-format-patch "\
        "will work nicely."
parser = OptionParser(usage=usage)
parser.add_option("-a", "--parse-author", action="store_true", default=False,
                  help="Parse author in email to include in commit message. " \
		       "Useful when you receive a patch from someone and would " \
		       "like to give him the credits")
parser.add_option("-e", "--edit-message", action="store_true", default=False,
		  help="Open $EDITOR to edit each commit message")
parser.add_option("-k", "--keep-subject", action="store_true", default=False,
		  help="Do not strip the string between [ and ] from the " \
		       "beginning of the subject")
parser.add_option("-D", "--dry-run", action="store_true", default=False,
                  help="Do not execute real commands or apply patches")
(options, args) = parser.parse_args()

if not os.path.isdir(".svn"):
    raise SystemError("no .svn")

dry_run = options.dry_run
patches = args
patches.sort()

has_author = False

rx_authorship = re.compile(r"^[ \t]*(author|by|signed-off)[ \t]*:", re.I)
rx_diffcmd = re.compile(r"^diff --git (.*)$")
rx_newfile = re.compile(r"^new file mode (\d+)$")
rx_delfile = re.compile(r"^deleted file mode (\d+)$")
rx_idxfile = re.compile(r"^index ([a-zA-Z0-9]+)[.][.]([a-zA-Z0-9]+)( [0-9]+)?$")
rx_endmsg = re.compile(r"^---\s*$")
rx_subject_prefix = re.compile("\[[^\]]*\]\s*")

def header2utf8(header):
    result = []
    for s, enc in decode_header(header):
        if enc is None:
            result.append(s)
        else:
            result.append(s.decode(enc).encode("utf-8"))

    return " ".join(result)


def system(cmd, *args):
    cmdline = cmd % args
    print "EXEC:", cmdline
    if dry_run:
        return
    if os.system(cmdline) != 0:
        raise SystemError("Could not execute: %r" % (cmdline,))

def touch(fname):
    print "TOUCH: %r" % (fname,)
    if dry_run:
        return
    f = open(fname, "wb")
    f.close()

def chmod(fname, mod):
    print "CHMOD: %o %r" % (mod, fname)
    if dry_run:
        return
    os.chmod(fname, mod)

def writefile(fname, data):
    print "WRITE: %s (%d bytes)" % (fname, len(data))
    if dry_run:
        return
    if os.path.exists(fname):
        os.unlink(fname)
    f = open(fname, "wb")
    f.write(data)
    f.close()

# From git file: delta.h
def delta_hdr_size(buf):
    size = 0
    i = 0
    while buf:
        cmd = buf.pop(0)
        size |= (cmd & 0x7f) << i
        i += 7
        if cmd & 0x80 == 0:
            break
    return size


# From git file: patch-delta.c
def patch_delta(fname, delta_buf):
    delta_buf = list(ord(x) for x in delta_buf)

    f = open(fname, "rb")
    src_buf = list(ord(x) for x in f.read())
    f.close()

    size = delta_hdr_size(delta_buf)
    if size != len(src_buf):
        raise ValueError("%s is %d bytes, but patch delta needs %d" %
                         (fname, len(src_buf), size))

    dst_size = size = delta_hdr_size(delta_buf)
    dst_buf = []
    bytes_copied = 0
    while delta_buf:
        cmd = delta_buf.pop(0)
        if cmd & 0x80:
            cp_off = 0
            cp_size = 0
            if cmd & 0x01:
                cp_off = delta_buf.pop(0)
            if cmd & 0x02:
                cp_off |= delta_buf.pop(0) << 8
            if cmd & 0x04:
                cp_off |= delta_buf.pop(0) << 16
            if cmd & 0x08:
                cp_off |= delta_buf.pop(0) << 24

            if cmd & 0x10:
                cp_size = delta_buf.pop(0)
            if cmd & 0x20:
                cp_size |= delta_buf.pop(0) << 8
            if cmd & 0x40:
                cp_size |= delta_buf.pop(0) << 16

            #print "delta: cp from %s, %s bytes" % (cp_off, cp_size)

            if cp_size == 0:
                cp_size = 0x10000
            if cp_off + cp_size < cp_size or \
               cp_off + cp_size > len(src_buf) or \
               cp_size > size:
                break

            dst_buf += src_buf[cp_off : cp_off + cp_size]
            size -= cp_size
            bytes_copied += cp_size
        elif cmd:
            if cmd > size:
                break

            #print "delta: overwrite %s bytes [%s]" % \
            #     (cmd, "".join(chr(x) for x in delta_buf[:cmd]))
            while cmd > 0:
                dst_buf.append(delta_buf.pop(0))
                cmd -= 1
                size -= 1
        else:
            raise ValueError("cmd == 0 is unsupported")

    if len(dst_buf) != dst_size:
        raise ValueError("dst_buf is %d bytes, but %d were expected!" %
                         (len(dst_buf), dst_size))

    data = "".join(chr(x) for x in dst_buf)
    if len(data) > 0:
        reused = bytes_copied * 100 / len(data)
    else:
        reused = 0
    print "DELTA PATCH: %s (bytes total: %d->%d, reused %d%%)" % \
          (fname, len(src_buf), len(data), reused)
    if dry_run:
        return
    if os.path.exists(fname):
        os.unlink(fname)
    f = open(fname, "wb")
    f.write(data)
    f.close()


def check_git_binary_patch(lines):
    if not lines:
        return False
    ln = lines[0]
    if ln == "GIT binary patch":
        return True
    if ln.endswith(" differ") and ln.startswith("Binary files "):
        return True
    return False

# From git file: base85.c:
en85 = (
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
    'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
    'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
    'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
    'u', 'v', 'w', 'x', 'y', 'z',
    '!', '#', '$', '%', '&', '(', ')', '*', '+', '-',
    ';', '<', '=', '>', '?', '@', '^', '_', '`', '{',
    '|', '}', '~',
    )
de85 = {}
for i, ch in enumerate(en85):
    de85[ch] = i # not + 1 as using a dict in Python.

def decode_85(buf, length):
    # From git file: base85.c:
    data = []
    #print "decode_85: %s" % buf
    buf = list(buf)
    while length > 0:
        acc = 0
        for cnt in xrange(4):
            ch = buf.pop(0)
            de = de85[ch] # will raise KeyError uppon invalid alphabet
                          # no need to if (--de) return error(...)
            #print "decode %c -> %d" % (ch, de)
            acc = acc * 85 + de
        ch = buf.pop(0)
        de = de85[ch]
        if 0xffffffff / 85 < acc:
            raise ValueError("invalid base85 sequence (overflow)")
        acc *= 85
        if 0xffffffff - de < acc:
            raise ValueError("invalid base85 sequence (overflow)")
        acc += de
        for cnt in xrange(min(4, length)):
            acc = (acc << 8) | (acc >> 24)
            data.append(acc & 0xff)
            length -= 1
    # print data
    return data


def parse_git_binary_hunk(lines):
    # From git file: builtin/apply.c:
    ##  Expect a line that begins with binary patch method ("literal"
    ##  or "delta"), followed by the length of data before deflating.
    ##  a sequence of 'length-byte' followed by base-85 encoded data
    ##  should follow, terminated by a newline.
    ##
    ##  Each 5-byte sequence of base-85 encodes up to 4 bytes,
    ##  and we would limit the patch line to 66 characters,
    ##  so one line can fit up to 13 groups that would decode
    ##  to 52 bytes max.  The length byte 'A'-'Z' corresponds
    ##  to 1-26 bytes, and 'a'-'z' corresponds to 27-52 bytes.
    ln = lines.pop(0)
    if ln.startswith("delta "):
        method = "delta"
        origlen = int(ln[len("delta "):], 10)
    elif ln.startswith("literal "):
        method = "literal"
        origlen = int(ln[len("literal "):], 10)
    else:
        raise ValueError("Unsupported git binary patch method: %r" % (ln,))

    # This tries to match git file builtin/apply.c as much as possible!
    data = []
    while True:
        ln = lines.pop(0)
        llen = len(ln) + 1 # match C algorithm that accounts '\n'
        if llen == 1:
            break
        # Minimum line is "A00000\n" which is 7-byte long,
        # and the line length must be multiple of 5 plus 2.
        if llen < 7 or (llen - 2) % 5:
            raise ValueError("corrupted patch contains line of size %d" % llen)
        max_byte_length = (llen - 2) / 5 * 4
        byte_length = ln[0]
        if 'A' <= byte_length and byte_length <= 'Z':
            byte_length = ord(byte_length) - ord('A') + 1
        elif 'a' <= byte_length and byte_length <= 'z':
            byte_length = ord(byte_length) - ord('a') + 27
        else:
            raise ValueError("corrupted patch contains line starting with %s" %
                             byte_length)

        # if the input length was not multiple of 4, we would
        # have filler at the end but the filler should never
        # exceed 3 bytes
        if max_byte_length < byte_length or byte_length <= max_byte_length - 4:
            raise ValueError("corrupted patch of invalid size %d (max %d)" %
                             (byte_length, max_byte_length))

        payload = ln[1:]
        data += decode_85(payload, byte_length)

    #print "data:", data
    data = zlib.decompress("".join(chr(x) for x in data))
    if len(data) != origlen:
        raise ValueError("zlib inflated data is %d bytes while %d were expected"
                         % (len(data), origlen))
    return method, data


def apply_git_binary_patch(fname, lines):
    if lines[0].endswith(" differ") and lines[0].startswith("Binary files "):
        print "Binary files differ, but patch not included! (--no-binary used?)"
        return

    assert lines[0] == "GIT binary patch"
    # From git file: builtin/apply.c:
    ##  We have read "GIT binary patch\n"; what follows is a line
    ##  that says the patch method (currently, either "literal" or
    ##  "delta") and the length of data before deflating; a
    ##  sequence of 'length-byte' followed by base-85 encoded data
    ##  follows.
    ##
    ##  When a binary patch is reversible, there is another binary
    ##  hunk in the same format, starting with patch method (either
    ##  "literal" or "delta") with the length of data, and a sequence
    ##  of length-byte + base-85 encoded data, terminated with another
    ##  empty line.  This data, when applied to the postimage, produces
    ##  the preimage.

    lines = list(lines[1:])
    forward_method, forward_data = parse_git_binary_hunk(lines)
    # no use for reverse patch right now
    # reverse_method, reverse_data = parse_git_binary_hunk(lines)

    # TODO:
    # - git-apply checks for old_sha1 before applying, but it requires .git/
    # - git-apply handle cases where sha1 (obj) already exists, and reads it
    # - git-apply checks for the new_sha1 after applying, but it requires .git/
    if forward_method == "literal":
        writefile(fname, forward_data)
    elif forward_method == "delta":
        patch_delta(fname, forward_data)
    else:
        raise ValueError("unknown binary patch method %r" % (forward_method,))


class Patch(object):
    def __init__(self, name):
        self.name = name
        self.action = "change"
        self.mode = None
        self.src_index = None
        self.dst_index = None
        self.contents = []

    def __hash__(self):
        return hash("%s %s..%s" % (self.name, self.src_index, self.dst_index))

    def __str__(self):
        if self.mode:
            m = oct(self.mode)
        else:
            m = None
        return "Patch(%r, %s, %s, %s..%s)" % \
               (self.name, self.action, m, self.src_index, self.dst_index)
    __repr__ = __str__

    def apply(self, fixed_patch):
        if self.action == "add":
            if not self.contents:
                touch(self.name)
            else:
                if check_git_binary_patch(self.contents):
                    apply_git_binary_patch(self.name, self.contents)
                else:
                    fixed_patch.append("diff --git a/%s b/%s" %
                                       (self.name, self.name))
                    fixed_patch.extend(self.contents)
        elif self.action == "change":
            if check_git_binary_patch(self.contents):
                apply_git_binary_patch(self.name, self.contents)
            else:
                fixed_patch.append("diff --git a/%s b/%s" %
                                   (self.name, self.name))
                fixed_patch.extend(self.contents)


for p in patches:
    print "patch: %s" % (p,)

    mail = message_from_file(open(p))
    if not mail:
        raise SystemError("could not parse email %s" % (p,))

    subject = header2utf8(mail["Subject"])
    if options.parse_author:
        sender = header2utf8(mail["From"])
        has_author = True
    else:
        sender = ""
        has_author = False

    if not options.keep_subject:
        subject = rx_subject_prefix.sub("", subject, 1)

    print "      ", sender
    print "      ", subject
    print

    patches = []
    msg = []
    msg_ended = False
    patch = None

    payload = mail.get_payload()
    for line in payload.split('\n'):
        if line and line[-1] == "\n":
            line = line[:-1]
        if not msg_ended:
            if rx_endmsg.search(line):
                msg_ended = True
            else:
                if line or last_line:
                    msg.append(line)
                if not has_author and rx_authorship.search(line):
                    has_author = True
        else:
            m = rx_diffcmd.search(line)
            if m:
                s = m.group(1)
                fname = s[2: len(s) / 2] # skip 'a/', get up to half of it
                if patch:
                    patches.append(patch)
                patch = Patch(fname)
                continue

            m = rx_newfile.search(line)
            if m:
                patch.mode = int(m.group(1), 8)
                patch.action = "add"
                continue

            m = rx_delfile.search(line)
            if m:
                patch.mode = int(m.group(1), 8)
                patch.action = "del"
                continue

            m = rx_idxfile.search(line)
            if m:
                patch.src_index = m.group(1)
                patch.dst_index = m.group(2)
                if m.group(3) and not patch.mode:
                    patch.mode = int(m.group(3), 8)
                continue

            if patch:
                patch.contents.append(line)

    if patch:
        patches.append(patch)

    for line in msg:
        print "       %s" % (line,)

    print "\n"

    files = {"add": [], "del": [], "change": [], "mv": []}
    for patch in patches:
        files[patch.action].append(patch)

    # can't move directly as GIT tracks objects by their content hash
    # so files with same content have the same ID (ie: empty files)
    mv_src_candidates = {}
    for src in files["del"]:
        for dst in files["add"]:
            if src.src_index == dst.dst_index:
                assert src != dst
                mv_src_candidates.setdefault(src, []).append(dst)

    # if a file is source of multiple destinations
    for src, targets in tuple(mv_src_candidates.iteritems()):
        if len(targets) > 1:
            del mv_src_candidates[src]

    for src, targets in mv_src_candidates.iteritems():
        assert len(targets) == 1
        dst = targets[0]
        files["del"].remove(src)
        files["add"].remove(dst)
        files["mv"].append((src, dst))

    if files["add"]:
        print "       files to add:"
        for patch in files["add"]:
            if patch.mode:
                print "\t+ %r [mode=%o]" % (patch.name, patch.mode)
            else:
                print "\t+ %r" % patch.name
    if files["del"]:
        print "       files to del:"
        for patch in files["del"]:
            print "\t- %r" % patch.name
    if files["change"]:
        print "       files changed:"
        for patch in files["change"]:
            if patch.mode:
                print "\t* %r [mode=%o]" % (patch.name, patch.mode)
            else:
                print "\t* %r" % patch.name
    if files["mv"]:
        print "       files moved:"
        for src, dst in files["mv"]:
            if src.mode:
                s = "%r [mode=%o]" % (src.name, src.mode)
            else:
                s = repr(src.name)
            if dst.mode:
                d = "%r [mode=%o]" % (dst.name, dst.mode)
            else:
                d = repr(dst.name)

            print "\tmv %s %s" % (s, d)

    print "\n"

    to_commit = []
    to_add = []
    fixed_patch = []

    if files["add"]:
        for patch in files["add"]:
            pieces = os.path.dirname(patch.name).split(os.path.sep)
            dname = "."
            for pname in pieces:
                dname = os.path.join(dname, pname)
                if not os.path.isdir(dname + "/.svn"):
                    if patch.mode:
                        chmod(dname, patch.mode)
                    patch.apply(fixed_patch)
                    to_add.append(dname)
                    to_commit.append(dname)
                    break
            else:
                patch.apply(fixed_patch)
                to_add.append(patch.name)
                to_commit.append(patch.name)
    if files["del"]:
        for patch in files["del"]:
            system("svn rm %r", patch.name)
            to_commit.append(patch.name)
    if files["change"]:
        for patch in files["change"]:
            if patch.mode:
                # XXX TODO: is svn smart enough to detect this? Or do we need
                # XXX TODO: to check old mode and set svn:executable?
                chmod(patch.name, patch.mode)
            patch.apply(fixed_patch)
            to_commit.append(patch.name)
    if files["mv"]:
        for src, dst in files["mv"]:
            system("svn mv %r %r", src.name, dst.name)
            if dst.mode:
                chmod(dst.name, dst.mode)
            to_commit.append(src.name)
            to_commit.append(dst.name)

    tmpn = "%s.svn-fixed" % p
    f = open(tmpn, "wb+")
    f.write("\n".join(fixed_patch))
    f.close()
    system("patch -p1 < %r", tmpn)
    os.unlink(tmpn)

    # just add after patch is applied
    for f in to_add:
        system("svn add %r", f)

    tmpfile = "svn-commit.tmp"
    idx = 1
    while os.path.exists(tmpfile):
        idx += 1
        tmpfile = "svn-commit.%d.tmp" % (idx,)

    f = open(tmpfile, "wb+")
    f.write(subject)
    f.write("\n")
    for line in msg:
        f.write(line)
        f.write("\n")
    if has_author and sender != "":
        f.write("\nBy: %s\n" % (sender,))
    f.write("\n--This line, and those below, will be ignored--\n")
    f.close()

    if options.edit_message:
        system("%s %s" % (os.environ.get("EDITOR"), tmpfile))
    answer = raw_input("Commit [Y/n]? ").strip().lower()
    if answer in ("n", "no"):
        raise SystemExit("stopped at patch %r (message at %r)" % (p, tmpfile))
    else:
        to_commit_str = " ".join(repr(x) for x in to_commit)
        system("svn commit -F %r %s", tmpfile, to_commit_str)
        os.unlink(tmpfile)
