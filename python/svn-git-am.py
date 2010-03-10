#!/usr/bin/env python

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

if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
    print """
Usage:

   %s <patches>

and must be run from a svn project (.svn must be present).
""" % (sys.argv[0],)
    raise SystemExit()


if not os.path.isdir(".svn"):
    raise SystemError("no .svn")

patches = sys.argv[1:]
patches.sort()

rx_authorship = re.compile(r"^[ \t]*(author|by|signed-off)[ \t]*:", re.I)
rx_addfile = re.compile(r"^-{3}\s+/dev/null\s*$")
rx_delfile = re.compile(r"^[+]{3}\s+/dev/null\s*$")
rx_getfile = re.compile(r"^[+-]{3}\s+(\S+)\s*$")
rx_chfile = re.compile(r"^[+]{3}\s+(\S+)\s*$")
rx_endmsg = re.compile(r"^---\s*$")

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
    sender = header2utf8(mail["From"])

    if subject.startswith("[PATCH] "):
        subject = subject[len("[PATCH] "):]

    print "      ", sender
    print "      ", subject
    print

    files = {"add": [], "del": [], "ch": []}
    msg = []
    msg_ended = False
    has_author = False
    next_op = None
    last_line = ""

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
            if rx_addfile.search(line):
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
                    files["ch"].append(f)
        elif next_op == "add":
            m = rx_getfile.search(line)
            if m:
                f = m.group(1)[2:]
                files[next_op].append(f)
                next_op = None


        last_line = line

    for line in msg:
        print "       %s" % (line,)


    if files["add"]:
        print "       files to add:"
        for f in files["add"]:
            print "\t+ %r" % f
    if files["del"]:
        print "       files to del:"
        for f in files["del"]:
            print "\t- %r" % f
    if files["ch"]:
        print "       files changed:"
        for f in files["ch"]:
            print "\t- %r" % f

    print "\n"

    system("patch -p1 < %r", p)

    to_commit = []

    if files["add"]:
        for f in files["add"]:
            pieces = os.path.dirname(f).split(os.path.sep)
            dname = "."
            for pname in pieces:
                dname = os.path.join(dname, pname)
                if not os.path.isdir(dname + "/.svn"):
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
        for f in files["ch"]:
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
    if not has_author:
        f.write("\nBy: %s\n" % (sender,))
    f.write("\n--This line, and those below, will be ignored--\n")
    f.close()

    answer = raw_input("Commit [Y/n]? ").strip().lower()
    if answer in ("n", "no"):
        raise SystemExit("stopped at patch %r (message at %r)" % (p, tmpfile))
    else:
        to_commit_str = " ".join(repr(x) for x in to_commit)
        system("svn commit -F %r %s", tmpfile, to_commit_str)
        os.unlink(tmpfile)
