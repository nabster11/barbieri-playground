#!/usr/bin/python2
import sys, re, os, os.path, email
	"Must be run from an svn project (.svn must be present)"

parser.add_option("-p", "--patch-level", action="store", type=int, default=1,
          help="Option passed to `patch' program")

patch_level = "-p%d" % options.patch_level

rx_addfile = re.compile(r"^-{3}\s+/dev/null\s*$")
rx_delfile = re.compile(r"^[+]{3}\s+/dev/null\s*$")
rx_getfile = re.compile(r"^[+-]{3}\s+(\S+)\s*$")
rx_chfile = re.compile(r"^[+]{3}\s+(\S+)\s*$")
    files = {"add": [], "del": [], "ch": []}
    next_op = None
    last_line = ""
        elif next_op is None:
            if rx_addfile.search(line):
                next_op = "add"
            elif rx_delfile.search(line):
                m = rx_getfile.search(last_line)
                if m:
                    f = '/'.join(m.group(1).split('/')[options.patch_level:])
                    files["del"].append(f)
            elif rx_chfile.search(line):
                m = rx_getfile.search(line)
                if m:
                    f = '/'.join(m.group(1).split('/')[options.patch_level:])
                    files["ch"].append(f)
        elif next_op == "add":
            m = rx_getfile.search(line)
                f = '/'.join(m.group(1).split('/')[options.patch_level:])
                files[next_op].append(f)
                next_op = None
        last_line = line
        for f in files["add"]:
            print "\t+ %r" % f
        for f in files["del"]:
            print "\t- %r" % f
    if files["ch"]:
        for f in files["ch"]:
            print "\t- %r" % f
    system("patch " + patch_level +" < %r", p)

        for f in files["add"]:
            pieces = os.path.dirname(f).split(os.path.sep)
                    system("svn add %r", dname)
                system("svn add %r", f)
                to_commit.append(f)
        for f in files["del"]:
            system("svn rm %r", f)
            to_commit.append(f)
    if files["ch"]:
        for f in files["ch"]:
            to_commit.append(f)
        f.write("\nPatch by: %s\n" % (sender,))