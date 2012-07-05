#!/usr/bin/python2

"""
Copyright (C) 2009-2010 Gustavo Barbieri <barbieri@profusion.mobi>
Copyright (C) 2010-2012 ProFUSION Embedded Systems
Copyright (C) 2010-2012 Lucas De Marchi <lucas.demarchi@profusion.mobi>

"""

"""
Apply a patch received formatted as by git-format-patch, applying to
the current SVN.

It will:

  - Get patch author from "From:" header, if it's not the same as returned by
    `git config user.email' it will add a "Patch-by: XXXXXXXX <yyyyy@aaaaaaaa>"
    in the end of commit message.  Author, By or Signed-off in the message
    body.
  - Apply the patch
  - Automatically "svn add" or "svn rm"
  - Ask if it should commit and allow user to edit commit message

TODO:
  - Change file mode
  - Mark file as binary

"""

import sys, re, os, os.path, email
from email import message_from_file
from email.header import decode_header
from optparse import OptionParser
import subprocess, tempfile

usage = "%prog [options] <patches>\n" \
	"Must be run from an svn project (.svn must be present)"
parser = OptionParser(usage=usage)
parser.add_option("-e", "--edit-message", action="store_true", default=False,
		  help="Open $EDITOR to edit each commit message")
parser.add_option("-k", "--keep-subject", action="store_true", default=False,
		  help="Do not strip the string between [ and ] from the " \
		       "beginning of the subject")
parser.add_option("-p", "--patch-level", action="store", type=int, default=1,
          help="Option passed to `patch' program")
parser.add_option("-n", "--dry-run", action="store_true", default=False,
          help="Don't apply the patch, just check it can be applied")

(options, args) = parser.parse_args()

patches = args
patch_level = "-p%d" % options.patch_level

rx_endmsg = re.compile(r"^---\s*$")
rx_email = re.compile(r"<(?P<email>.*)>")
rx_subject_prefix = re.compile("\[[^\]]*\]\s*")
rx_create = re.compile(r'^ create mode')
rx_delete = re.compile(r'^ delete mode')
rx_change_mode = re.compile(r'^ change mode')

def find_project_root():
    p = os.path.realpath(".")
    l = p.split("/")
    t = p

    for i in range(0, len(l)):
        if os.path.isdir(t + "/.svn"):
            break
        l.pop()
        t = "/".join(l)

    return t

def header2utf8(header):
    result = []
    for s, enc in decode_header(header):
        if enc is None:
            result.append(s)
        else:
            result.append(s.decode(enc).encode("utf-8"))

    return " ".join(result)

def parse_email_header(mail):
    subject = header2utf8(mail["Subject"])
    sender = header2utf8(mail["From"])
    author = rx_email.search(sender).groupdict()['email']
    if author == gituser:
        sender = None
    if not options.keep_subject:
        subject = rx_subject_prefix.sub("", subject, 1)

    return subject, sender

def parse_commit_message(subject, author, body):
    (fd, fn) = tempfile.mkstemp(prefix="svn-commit.tmp", text=True)
    f = os.fdopen(fd, "w")

    f.write(subject)
    f.write("\n\n")

    for line in body.split('\n'):
        if rx_endmsg.search(line):
            break
        print(line)
        f.write(line)
        f.write('\n')

    if author:
        print("\n\nPatch by: %s\n" % author)
        f.write("\n\nPatch by: %s\n" % author)
    f.write("\n--This line, and those below, will be ignored--\n")
    f.close()
    return fn

def parse_stat(out):
    stat = {}
    stat['added'] = []
    stat['deleted'] = []
    stat['modechanged'] = []
    stat['tocommit'] = []

    lines = out.split('\n')
    i = 0

    # --stat
    for line in lines:
        if not line or line[0] != ' ':
            break
        print(line)
        i += 1

    # --numstat
    for line in lines[i:]:
        if not line or line[0] == ' ':
            break
        stat['tocommit'].append(line.split()[2])
        i += 1

    # --summary
    for line in lines[i:]:
        if not line:
            break

        if rx_create.search(line):
            fn = line.split()[3]
            stat['added'].append(fn)
            if not options.dry_run:
                subprocess.check_call([ "svn", "add", fn ])
        elif rx_delete.search(line):
            fn = line.split()[3]
            stat['deleted'].append(fn)
            if not options.dry_run:
                subprocess.check_call([ "svn", "delete", fn ])
        elif rx_change_mode.search(line):
            stat['modechanged'].append(line.split()[6])

    return stat

def system(cmd, *args):
    cmdline = cmd % args
    print "EXEC:", cmdline
    if os.system(cmdline) != 0:
        raise SystemError("Could not execute: %r" % (cmdline,))


root = find_project_root()
if root == '':
    raise SystemError("Could not find project root: no .svn")

gituser = subprocess.check_output("git config user.email".split()).strip()

for p in patches:
    print "patch: %s" % (p,)

    mail = message_from_file(open(p))
    if not mail:
        raise SystemError("could not parse email %s" % (p,))

    (subject, author) = parse_email_header(mail)
    print("From: %s" % author)
    print("Subject: %s\n" % subject)

    commitfn = parse_commit_message(subject, author, mail.get_payload())

    try:
        if options.dry_run:
            a = ""
        else:
            a = "--apply"
        cmd = "git apply -p%d --numstat --stat --summary %s %s" %\
              (options.patch_level, a, p)
        print("\nExec: %s" % cmd)
        out = subprocess.check_output(cmd.split())
    except subprocess.CalledProcessError:
        print("Could not apply patch %r. Commit message saved to %r" % (p, commitfn))
        sys.exit(1)

    print("Summary:")
    stat = parse_stat(out)

    print("\nFiles to commit:")
    for f in stat['tocommit']:
        print("\t %s" % f)

    if options.edit_message:
        system("%s %s" % (os.environ.get("EDITOR"), commitfn))

    if not options.dry_run:
        answer = raw_input("Commit [Y/n]? ").strip().lower()
        if answer in ("n", "no"):
            raise SystemExit("stopped at patch %r (message at %r)" % (p, commitfn))

        to_commit_str = " ".join(repr(x) for x in stat['tocommit'])
        system("svn commit -F %r %s", commitfn, to_commit_str)
        os.unlink(commitfn)
    else:
        print('\nCommit message saved in %r' % commitfn)
