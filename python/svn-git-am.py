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

"""

import sys, re, os, os.path, email
from email import message_from_file
from email.header import decode_header
from optparse import OptionParser

usage = "%prog [options] <patches>\n" \
	"Must be run from an svn project (.svn must be present)"
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
(options, args) = parser.parse_args()

if not os.path.isdir(".svn"):
    raise SystemError("no .svn")

patches = args
patches.sort()

has_author = False

rx_authorship = re.compile(r"^[ \t]*(author|by|signed-off)[ \t]*:", re.I)
rx_addfile = re.compile(r"^-{3}\s+/dev/null\s*$")
rx_delfile = re.compile(r"^[+]{3}\s+/dev/null\s*$")
rx_getfile = re.compile(r"^[+-]{3}\s+(\S+)\s*$")
rx_chfile = re.compile(r"^[+]{3}\s+(\S+)\s*$")
rx_newmode = re.compile(r"^new( file)? mode (\d+)$")
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
    if os.system(cmdline) != 0:
        raise SystemError("Could not execute: %r" % (cmdline,))


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

    files = {"add": [], "del": [], "ch": []}
    msg = []
    msg_ended = False
    next_op = None
    last_line = ""
    new_mode = None

    payload = mail.get_payload()
    for line in payload.split('\n'):
        line = line.strip()
        if not msg_ended:
            if rx_endmsg.search(line):
                msg_ended = True
            else:
                if line or last_line:
                    msg.append(line)
                if not has_author and rx_authorship.search(line):
                    has_author = True
        elif next_op is None:
            m = rx_newmode.search(line)
            if m:
                new_mode = int(m.group(2), 8)
            elif rx_addfile.search(line):
                next_op = "add"
            elif rx_delfile.search(line):
                m = rx_getfile.search(last_line)
                if m:
                    f = m.group(1)[2:]
                    files["del"].append(f)
            elif rx_chfile.search(line):
                m = rx_getfile.search(line)
                if m:
                    f = m.group(1)[2:]
                    files["ch"].append((new_mode, f))
                    new_mode = None
        elif next_op == "add":
            m = rx_getfile.search(line)
            if m:
                f = m.group(1)[2:]
                files[next_op].append((new_mode, f))
                next_op = None
                new_mode = None


        last_line = line

    for line in msg:
        print "       %s" % (line,)

    print "\n"
    if files["add"]:
        print "       files to add:"
        for m, f in files["add"]:
            if m:
                print "\t+ %r [mode=%o]" % (f, m)
            else:
                print "\t+ %r" % f
    if files["del"]:
        print "       files to del:"
        for f in files["del"]:
            print "\t- %r" % f
    if files["ch"]:
        print "       files changed:"
        for m, f in files["ch"]:
            if m:
                print "\t* %r [mode=%o]" % (f, m)
            else:
                print "\t* %r" % f

    print "\n"

    system("patch -p1 < %r", p)

    to_commit = []

    if files["add"]:
        for m, f in files["add"]:
            pieces = os.path.dirname(f).split(os.path.sep)
            dname = "."
            for pname in pieces:
                dname = os.path.join(dname, pname)
                if not os.path.isdir(dname + "/.svn"):
                    if m:
                        os.chmod(dname, m)
                    system("svn add %r", dname)
                    to_commit.append(dname)
                    break
            else:
                system("svn add %r", f)
                to_commit.append(f)
    if files["del"]:
        for f in files["del"]:
            system("svn rm %r", f)
            to_commit.append(f)
    if files["ch"]:
        for m, f in files["ch"]:
            if m:
                os.chmod(f, m)
            to_commit.append(f)

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
