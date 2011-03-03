#!/usr/bin/python2

import sys
import os
import optparse
import re
from ConfigParser import SafeConfigParser as ConfigParser

re_doublespaces = re.compile('\s\s+')

def header_tokenize(header_file, cfg):
    ignore_tokens = config_get_regexp(cfg, "global", "ignore-tokens-regexp")
    f = open(header_file)
    in_comment = False
    in_macro = False
    buf = []
    for line in f.readlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            in_macro = line.endswith("\\")
            continue
        if in_macro:
            in_macro = line.endswith("\\")
            continue

        while line:
            if in_comment:
                x = line.find("*/")
                if x < 0:
                    line = ""
                    break
                else:
                    line = line[x + 2:]
                    in_comment = False

            x = line.find("//")
            if x >= 0:
                line = line[:x]
                break

            x = line.find("/*")
            if x >= 0:
                y = line.find("*/", x + 2)
                if y >= 0:
                    line = line[:x] + line[y + 2:]
                else:
                    line = line[:x]
                    in_comment = True
            else:
                break

        line = line.replace("*", " * ").strip()
        if not line:
            continue

        buf.append(line)

    buf = " ".join(buf)
    tokens = []
    attribute_regexp = re.compile("""\
__attribute__\s*[(]{2}(\
(\s+|[a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*){0,1}|\
(([a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*),\
([a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*))+\
)[)]{2}""")
    for line in buf.split(";"):
        line = line.strip()
        if not line:
            continue
        last_i = 0
        line = re_doublespaces.sub(' ', line)
        if ignore_tokens:
            line = ignore_tokens.sub("", line).strip()
            if not line:
                continue
        if line.startswith("static "):
            continue
        line = attribute_regexp.sub("", line).strip()
        for i, c in enumerate(line):
            if c in (",", "{", "}", "(", ")"):
                x = line[last_i:i].strip()
                if x:
                    tokens.append(x)
                tokens.append(c)
                last_i = i + 1

        x = line[last_i:].strip()
        if x:
            tokens.append(x)

        tokens.append(";")

    f.close()
    return tokens


class Enum(object):
    def __init__(self, name):
        self.name = name
        self.members = []

    def add_member(self, name, value=None):
        self.members.append((name, value))

    def decl_name(self):
        return "enum %s" % (self.name,)

    def __str__(self):
        members = []
        for k, v in self.members:
            if v:
                members.append("%s = %s" % (k, v))
            else:
                members.append(k)
        members = ", ".join(members)
        return "enum %s {%s};" % (self.name, members)

    def __repr__(self):
        return "Enum(%s)" % (self.name,)


class Struct(object):
    def __init__(self, name):
        self.name = name
        self.members = []

    def add_member(self, type, name, func=None):
        if func is not None:
            self.members.append((type, name, func))
        else:
            self.members.append((type, name))

    def decl_name(self):
        return "struct %s" % (self.name,)

    def __str__(self):
        members = []
        for m in self.members:
            if len(m) == 2:
                members.append("%s %s;" % m)
            else:
                args = ", ".join(m[2])
                members.append("%s (*%s)(%s);" % (m[0], m[1], args))
        members = " ".join(members)
        return "struct %s {%s};" % (self.name, members)

    def __repr__(self):
        return "Struct(%s)" % (self.name,)


class Typedef(object):
    def __init__(self, name, reference, func=None):
        self.name = name
        self.reference = reference
        self.func = func

    def decl_name(self):
        return self.name

    def __str__(self):
        if self.func is not None:
            params = ", ".join(self.func)
            return "typedef %s (*%s)(%s);" % (self.reference, self.name, params)
        else:
            return "typedef %s %s;" % (self.reference, self.name)

    def __repr__(self):
        return "Typedef(%s)" % (self.name,)


class Function(object):
    def __init__(self, name, ret_type, parameters=None):
        self.name = name
        self.ret_type = ret_type
        self.parameters = parameters or []

    def add_parameter(self, type, name=None, func=None):
        if func:
            self.parameters.append((type, name, func))
        elif name:
            self.parameters.append((type, name))
        else:
            self.parameters.append((type,))

    def decl_name(self):
        return str(self)

    def parameters_unnamed_fix(self, prefix=""):
        for i, p in enumerate(self.parameters):
            if len(p) == 1 and p[0] != "void":
                self.parameters[i] = p + (prefix + ("_par%d" % i),)
            elif len(p) > 2 and not p[1]:
                self.parameters[i] = ((p[0],) + (prefix + ("_par%d" % i),) + \
                                      p[2:])

    def parameters_names_str(self):
        if not self.parameters:
            return ""
        if self.parameters[0][0] == "void":
            return ""

        params = []
        self.parameters_unnamed_fix()
        for p in self.parameters:
            params.append(p[1])
        return ", ".join(params)

    def parameters_str(self):
        params = []
        for p in self.parameters:
            if len(p) == 1:
                params.append(p[0])
            elif len(p) == 2:
                params.append("%s %s" % (p[0], p[1]))
            else:
                if p[1]:
                    name = p[1]
                else:
                    name = ""
                args = ", ".join(p[2])
                params.append("%s (*%s)(%s)" % (p[0], name, args))
        return ", ".join(params)

    def __str__(self):
        return "%s %s(%s);" % (self.ret_type, self.name, self.parameters_str())

    def __repr__(self):
        return "Function(%s)" % (self.name,)


class Variable(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return "%s %s;" % (self.type, self.name)


class Node(object):
    def __init__(self, parent, parts, children=None):
        self.parent = parent
        self.parts = parts
        self.children = children or []
        self.enclosure = None
        self.pending = True

    def __str__(self):
        return "<%s>" % ",".join(str(x) for x in self.parts)

    def __repr__(self):
        s = "Node(parts=[%s]" % ",".join(str(x) for x in self.parts)
        if self.parent:
            s += ", parent=[%s]" % ",".join(str(x) for x in self.parent.parts)
        if self.children:
            s += ", children=[%s]" % ",".join(str(x) for x in self.children)
        return s + ")"


enclosure_close = {"{":"}", "(":")"}
def node_tree_flattern(node, include_parts=True):
    if include_parts:
        flat = " ".join(node.parts)
        flat += " "
    else:
        flat = ""

    if node.enclosure:
        flat += node.enclosure
    for x in node.children:
        if isinstance(x, Node):
            v = node_tree_flattern(x)
            flat += " %s " % (v,)
        else:
            flat += " ".join(x)
    if node.enclosure:
        flat += enclosure_close[node.enclosure]
    return flat


def pointer_fix(type, name):
    first = True
    while name.startswith("*"):
        if first:
            type += " "
            first = False
        type += "*"
        name = name[1:]
    return type, name


def convert_func_params(node):
    s = " ".join(node.parts)
    s += " (%s)" % ("".join(node.children[0]),)
    s += "("
    params = []
    for c in node.children[1:]:
        if isinstance(c, Node):
            params.append(convert_func_params(c))
        elif isinstance(c, list):
            params.append(" ".join(c))
        else:
            params.append(c)
    s += ", ".join(params)
    s += ")"
    return s


def process(data, node, last_node=None):
    #print "\033[1;35mNODE:", repr(node), "\033[0m"
    if node.parts[0] == "enum":
        name = node.parts[1]
        p = Enum(name)
        if not node.children:
            return data["enum"].setdefault(name, p)
        else:
            for v in node.children:
                if isinstance(v, Node):
                    name = v.parts[0]
                    value = node_tree_flattern(v, include_parts=False)
                elif len(v) > 2:
                    name = v[0]
                    value = " ".join(v[2:])
                else:
                    name = v[0]
                    value = None

                p.add_member(name, value)
            data["enum"][p.name] = p
            return p

    elif node.parts[0] == "struct":
        if len(node.parts) > 1:
            name = node.parts[1]
        else:
            tmp = node
            name = ""
            while tmp and len(tmp.parts) == 1:
                name += "<anonymous-inside>"
                tmp = tmp.parent
            if tmp:
                name += tmp.parts[-1]

        p = Struct(name)
        if not node.children:
            return data["struct"].setdefault(name, p)
        else:
            last_member = None
            for v in node.children:
                if isinstance(v, Node):
                    if v.parts[0] in ("struct", "enum") and \
                           len(v.parts) <= 2:
                        last_member = process(data, v)
                    elif len(v.parts) >= 2 and not v.children:
                        # regular "type name;"
                        type = " ".join(v.parts[0:-1])
                        name = v.parts[-1]
                        type, name = pointer_fix(type, name)
                        if type and not type.startswith("*"):
                            p.add_member(type, name)
                        elif last_member:
                            if type:
                                type = last_member.decl_name() + " " + type
                            else:
                                type = last_member.decl_name()
                            p.add_member(type, name)
                        elif p.members:
                            prev = p.members[-1]
                            type = prev[0].replace("*", "").strip() + type
                            p.add_member(type, name)
                        else:
                            print "UNSUPPORTED:", repr(v)
                        last_member = None
                    elif last_member:
                        # struct { int x; } name;
                        type = last_member.decl_name()
                        name = v.parts[0]
                        type, name = pointer_fix(type, name)
                        p.add_member(type, name)
                        last_member = None
                    elif len(v.parts) == 1 and not v.children and p.members:
                        # int a, b;
                        prev = p.members[-1]
                        name = v.parts[0]
                        type = prev[0].replace("*", "").strip()
                        p.add_member(type, name)
                        last_member = None
                    elif v.parts and v.children and v.children[0][0] == "*":
                        # function pointer:  type (*cb)(int a, int b);
                        type = " ".join(v.parts)
                        name = "".join(v.children[0][1:])
                        func = []
                        for a in v.children[1:]:
                            if isinstance(a, Node):
                                func.append(convert_func_params(a))
                            else:
                                func.append(" ".join(a))
                        p.add_member(type, name, func)
                        last_member = None
                    else:
                        print "UNSUPPORTED-1:", repr(v)
                else:
                    # plain "int a"
                    name = v[-1]
                    type = " ".join(v[:-1])
                    type, name = pointer_fix(type, name)
                    if type and not type.startswith("*"):
                        p.add_member(type, name)
                        continue
                    elif last_member:
                        # repetition "struct { decl...; } a, b;"
                        if type:
                            type = last_member.decl_name() + " " + type
                        else:
                            type = last_member.decl_name()
                        p.add_member(type, name)
                        last_member = None
                    elif p.members:
                        # repetition "unsigned long *a, **b, ***c;"
                        prev = p.members[-1]
                        type = prev[0].replace("*", "").strip()
                        type += " ".join(v[:-1])
                        p.add_member(type, name)
                        last_member = None
                    else:
                        print "UNSUPPORTED-2:", repr(v)

            data["struct"][p.name] = p
            return p

    elif node.parts[0] == "typedef":
        if len(node.parts) < 3 and not node.children:
            print "Ignoring typedef forward declaration:"
        else:
            if not node.children:
                name = node.parts[-1]
                reference = " ".join(node.parts[1:-1])
                reference, name = pointer_fix(reference, name)
                p = Typedef(name, reference)
                data["typedef"][p.name] = p
                return p
            elif last_node and not isinstance(node.children[0], Node) and \
                     node.children[0][0] == "*":
                node.pending = False
                # function pointer?
                type = " ".join(node.parts[1:])
                name = "".join(node.children[0][1:])
                func = []
                for a in node.children[1:]:
                    if isinstance(a, Node):
                        func.append(convert_func_params(a))
                    else:
                        func.append(" ".join(a))
                p = Typedef(name, type, func)
                data["typedef"][p.name] = p
                return p
            else:
                node.pending = True
                #print "typedef with declaration inside, process next time."
    else:
        if last_node and last_node.pending \
               and last_node.parts[0] == "typedef" \
               and not (node.children and not isinstance(node.children[0], Node)
                        and node.children[0][0] == "*"):
            last_node.pending = False
            sub = Node(last_node, last_node.parts[1:], last_node.children)
            name = node.parts[-1]
            leading = node.parts[:-1]
            while name.startswith("*"):
                leading.append("*")
                name = name[1:]
            parts = leading + [name]
            last_node.parts = ["typedef"] + parts
            last_node.children = None
            subp = process(data, sub)
            last_node.parts = ["typedef", subp.decl_name()] + parts
            p = process(data, last_node)
            data["typedef"][p.name] = p
            return p
        else:
            if node.parts and node.children:
                # likely a function?
                if "=" in node.parts: # inside enums, etc
                    return
                if node.parts[0] == "extern" and node.parts[1].startswith('"'):
                    # extern "C" and like
                    return
                tmp = node
                while tmp:
                    if tmp.parent and \
                           tmp.parent.parts[0] in ("struct", "enum", "typedef"):
                        return
                    tmp = tmp.parent

                if node.parent and node.children and node.children[0][0] == "*":
                    # callback parameter
                    return

                name = node.parts[-1]
                type = " ".join(node.parts[:-1])
                type, name = pointer_fix(type, name)
                p = Function(name, type)
                for v in node.children:
                    if isinstance(v, Node):
                        if v.children and v.children[0][0] == "*":
                            type = " ".join(v.parts)
                            if len(v.children[0]) == 1:
                                name = None
                            else:
                                name = "".join(v.children[0][1:])

                            func = []
                            for a in v.children[1:]:
                                if isinstance(a, Node):
                                    func.append(convert_func_params(a))
                                else:
                                    func.append(" ".join(a))
                            p.add_parameter(type, name, func)

                    else:
                        if len(v) == 1:
                            p.add_parameter(v[0])
                        else:
                            name = v[-1]
                            type = " ".join(v[:-1])
                            type, name = pointer_fix(type, name)
                            if name:
                                p.add_parameter(type, name)
                            else:
                                p.add_parameter(type)
                data["function"][p.name] = p
                return p
            elif node.parts[0] == "extern":
                name = node.parts[-1]
                type = node.parts[1:-1]
                type, name = pointer_fix(type, name)
                p = Variable(name, " ".join(type))
                data["global"][p.name] = p
                return p
            print "Don't know what to do with node:", repr(node)


def header_tree(header_file, cfg=None):
    tokens = header_tokenize(header_file, cfg)
    data = {"enum": {}, "struct": {}, "function": {}, "typedef": {},
            "global": {}}
    pending = []
    root = None
    current = None
    last_p = None
    last_node = None
    for t in tokens:
        p = t.split(" ")
        if p[0] == ";":
            #print "\033[1;31mFINISH\033[0m", current, pending
            if pending:
                assert(len(pending) == 1)
                n = Node(current, pending[0])
                pending = []
                if current:
                    current.children.append(n)
                else:
                    process(data, n, last_node)
                    last_node = n
            elif last_p and last_p[0] not in ("}", ")"):
                if current:
                    if not current.parent:
                        process(data, current, last_node)
                        last_node = current
                    current = current.parent
                    if current is None:
                        root = None
                else:
                    print "NO CURRENT"

        elif p[0] in ("{", "("):
            if pending:
                assert(len(pending) == 1)
                n = Node(current, pending[0])
                n.enclosure = p[0]
                pending = []
                #print "\033[1;32mPUSH\033[0m", t, n
            else:
                #print "\033[32mNOTHING TO PUSH?", t, repr(current)
                pass

            current = n
            if root is None:
                root = n

        elif p[0] in ("}", ")", ","):
            #print "\033[1;33mPOP\033[0m", t, current, pending
            if pending:
                current.children.extend(pending)
                pending = []
            if p[0] in ("}", ")"):
                if current.parent and current not in current.parent.children:
                    current.parent.children.append(current)
                process(data, current, last_node)
                last_node = current
                current = current.parent
                if current is None:
                    root = None
        else:
            #print "\033[1;36mPENDING\033[0m", t
            pending.append(p)

        last_p = p
    return data


def generate_preamble(f, ctxt):
    f.write("""
/* this file was auto-generated from %(header)s by %(progname)s. */

#include <%(header)s>
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <errno.h>

#ifdef %(prefix)s_USE_COLORS
#define %(prefix)s_COLOR_ERROR \"\\033[1;31m\"
#define %(prefix)s_COLOR_WARN \"\\033[1;33m\"
#define %(prefix)s_COLOR_OK \"\\033[1;32m\"
#define %(prefix)s_COLOR_ENTER \"\\033[1;36m\"
#define %(prefix)s_COLOR_EXIT \"\\033[1;35m\"
#define %(prefix)s_COLOR_CLEAR \"\\033[0m\"
#else
#define %(prefix)s_COLOR_ERROR \"\"
#define %(prefix)s_COLOR_WARN \"\"
#define %(prefix)s_COLOR_OK \"\"
#define %(prefix)s_COLOR_ENTER \"\"
#define %(prefix)s_COLOR_EXIT \"\"
#define %(prefix)s_COLOR_CLEAR \"\"
#endif

#ifdef %(prefix)s_HAVE_THREADS
#include <pthread.h>
static pthread_mutex_t %(prefix)s_th_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_t %(prefix)s_th_main = 0;
static unsigned char %(prefix)s_th_initted = 0;
#define %(prefix)s_THREADS_INIT \\
    do { \\
        pthread_mutex_lock(&%(prefix)s_th_mutex); \\
        if (!%(prefix)s_th_initted) { \\
            %(prefix)s_th_initted = 1; \\
            %(prefix)s_th_main = pthread_self(); \\
        } \\
        pthread_mutex_unlock(&%(prefix)s_th_mutex); \\
    } while(0)
#define %(prefix)s_IS_MAIN_THREAD (%(prefix)s_th_main == pthread_self())
#define %(prefix)s_THREAD_ID ((unsigned long)pthread_self())
#define %(prefix)s_LOCK pthread_mutex_lock(&%(prefix)s_th_mutex)
#define %(prefix)s_UNLOCK pthread_mutex_unlock(&%(prefix)s_th_mutex)
#define %(prefix)s_THREAD_LOCAL __thread
#else
#define %(prefix)s_THREADS_INIT do{}while(0)
#define %(prefix)s_IS_MAIN_THREAD (1)
#define %(prefix)s_THREAD_ID (0UL)
#define %(prefix)s_LOCK do{}while(0)
#define %(prefix)s_UNLOCK do{}while(0)
#define %(prefix)s_THREAD_LOCAL
#endif

#ifdef %(prefix)s_LOGFILE
static FILE *%(prefix)s_log_fp = NULL;
#define %(prefix)s_LOG_PREPARE \\
    do { if (!%(prefix)s_log_fp) %(prefix)s_log_prepare(); } while (0)

static void %(prefix)s_log_prepare(void)
{
    %(prefix)s_LOCK;
    if (!%(prefix)s_log_fp) {
        %(prefix)s_log_fp = fopen(%(prefix)s_LOGFILE, \"a+\");
        if (!%(prefix)s_log_fp) {
            fprintf(stderr,
                    %(prefix)s_COLOR_ERROR
                    \"ERROR: could not open logfile %%s: %%s.\"
                    \" Using stderr!\\n\"
                    %(prefix)s_COLOR_CLEAR,
                    %(prefix)s_LOGFILE, strerror(errno));
            %(prefix)s_log_fp = stderr;
        }
    }
    %(prefix)s_UNLOCK;
}
#else
static FILE *%(prefix)s_log_fp = NULL;
#define %(prefix)s_LOG_PREPARE \\
    do{ if (!%(prefix)s_log_fp) %(prefix)s_log_fp = stderr; }while(0)
#endif

#ifdef %(prefix)s_LOG_TIMESTAMP
#ifdef %(prefix)s_LOG_TIMESTAMP_CLOCK_GETTIME
#include <time.h>

#ifndef %(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE
#define %(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE CLOCK_MONOTONIC
#endif

#define %(prefix)s_LOG_TIMESTAMP_SHOW \\
    do { \\
        struct timespec spec = {0, 0}; \\
        clock_gettime(%(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE, &spec); \\
        fprintf(%(prefix)s_log_fp, \"[%%5lu.%%06lu] \", \\
                (unsigned long)tv.tv_sec, \\
                (unsigned long)tv.tv_usec / 1000); \\
    } while (0)

#else /* fallback to gettimeofday() */

#include <sys/time.h>
#define %(prefix)s_LOG_TIMESTAMP_SHOW \\
    do { \\
        struct timeval tv = {0, 0}; \\
        gettimeofday(&tv, NULL); \\
        fprintf(%(prefix)s_log_fp, \"[%%5lu.%%06lu] \", \\
                (unsigned long)tv.tv_sec, \\
                (unsigned long)tv.tv_usec); \\
    } while (0)

#endif
#else
#define %(prefix)s_LOG_TIMESTAMP_SHOW do{}while(0)
#endif

static void *%(prefix)s_dl_handle = NULL;

static unsigned char %(prefix)s_dl_prepare(void)
{
    unsigned char ok;

    %(prefix)s_THREADS_INIT;

    %(prefix)s_LOCK;
    ok = !!%(prefix)s_dl_handle;
    if (!ok) {
        char *errmsg;
        %(prefix)s_dl_handle = dlopen(\"%(libname)s\", RTLD_LAZY);
        errmsg = dlerror();
        if (errmsg) {
            %(prefix)s_dl_handle = NULL;
            fprintf(stderr,
                    %(prefix)s_COLOR_ERROR
                    \"ERROR: could not dlopen(%(libname)s): %%s\\n\"
                    %(prefix)s_COLOR_CLEAR, errmsg);
        }
        ok = !!%(prefix)s_dl_handle;
    }
    %(prefix)s_UNLOCK;

    return ok;
}

#define %(prefix)s_GET_SYM(v, name, ...) \\
    do { \\
        if (!%(prefix)s_dl_handle) { \\
            if (!%(prefix)s_dl_prepare()) \\
                return __VA_ARGS__; \\
        } \\
        %(prefix)s_LOCK; \\
        if (!v) { \\
            char *%(prefix)s_dl_err; \\
            v = dlsym(%(prefix)s_dl_handle, name); \\
            %(prefix)s_dl_err = dlerror(); \\
            if (%(prefix)s_dl_err) { \\
                fprintf(stderr, \\
                        %(prefix)s_COLOR_ERROR \\
                        \"ERROR: could not dlsym(%%s): %%s\\n\" \\
                        %(prefix)s_COLOR_CLEAR, \\
                        name, %(prefix)s_dl_err); \\
            } \\
        } \\
        %(prefix)s_UNLOCK; \\
        if (!v) \\
            return __VA_ARGS__; \\
    } while (0)


static inline void %(prefix)s_log_params_begin(void)
{
    putc('(', %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_param_continue(void)
{
    fputs(\", \", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_params_end(void)
{
    putc(')', %(prefix)s_log_fp);
}

#ifdef %(prefix)s_LOG_INDENT
static %(prefix)s_THREAD_LOCAL int %(prefix)s_log_indentation = 0;
#endif

static inline void %(prefix)s_log_enter_start(const char *name)
{
    %(prefix)s_LOG_PREPARE;
    %(prefix)s_LOCK;

    %(prefix)s_LOG_TIMESTAMP_SHOW;

#ifdef %(prefix)s_LOG_INDENT
    int i;

    for (i = 0; i < %(prefix)s_log_indentation; i++)
        fputs(%(prefix)s_LOG_INDENT, %(prefix)s_log_fp);
    %(prefix)s_log_indentation++;
#endif

    if (!%(prefix)s_IS_MAIN_THREAD)
        fprintf(%(prefix)s_log_fp, \"[T:%%lu]\", %(prefix)s_THREAD_ID);

    fprintf(%(prefix)s_log_fp, %(prefix)s_COLOR_ENTER \"LOG> %%s\", name);
}

static inline void %(prefix)s_log_enter_end(const char *name)
{
    fputs(%(prefix)s_COLOR_CLEAR \"\\n\", %(prefix)s_log_fp);
    fflush(%(prefix)s_log_fp);
    %(prefix)s_UNLOCK;
    (void)name;
}

static inline void %(prefix)s_log_exit_start(const char *name)
{
    %(prefix)s_LOG_PREPARE;
    %(prefix)s_LOCK;

    %(prefix)s_LOG_TIMESTAMP_SHOW;

#ifdef %(prefix)s_LOG_INDENT
    int i;

    %(prefix)s_log_indentation--;
    for (i = 0; i < %(prefix)s_log_indentation; i++)
        fputs(%(prefix)s_LOG_INDENT, %(prefix)s_log_fp);
#endif

    if (!%(prefix)s_IS_MAIN_THREAD)
        fprintf(%(prefix)s_log_fp, \"[T:%%lu]\", %(prefix)s_THREAD_ID);
    fprintf(%(prefix)s_log_fp, %(prefix)s_COLOR_EXIT \"LOG< %%s\", name);
}

static inline void %(prefix)s_log_exit_return(void)
{
    fputs(\" = \", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_exit_end(const char *name)
{
    fputs(%(prefix)s_COLOR_CLEAR \"\\n\", %(prefix)s_log_fp);
    fflush(%(prefix)s_log_fp);
    %(prefix)s_UNLOCK;
    (void)name;
}

static inline void %(prefix)s_log_fmt_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%d\", type, name, value);
    else
        fprintf(p, \"(%%s)%%d\", type, value);
}

static inline void %(prefix)s_log_fmt_uint(FILE *p, const char *type, const char *name, unsigned int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%u\", type, name, value);
    else
        fprintf(p, \"(%%s)%%u\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#x\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#x\", type, value);
}

static inline void %(prefix)s_log_fmt_errno(FILE *p, const char *type, const char *name, int value)
{
    const char *msg;
    switch (value) {
        case E2BIG: msg = \"E2BIG\"; break;
        case EACCES: msg = \"EACCES\"; break;
        case EADDRINUSE: msg = \"EADDRINUSE\"; break;
        case EADDRNOTAVAIL: msg = \"EADDRNOTAVAIL\"; break;
        case EAFNOSUPPORT: msg = \"EAFNOSUPPORT\"; break;
        case EAGAIN: msg = \"EAGAIN\"; break;
        case EALREADY: msg = \"EALREADY\"; break;
        case EBADF: msg = \"EBADF\"; break;
        case EBADMSG: msg = \"EBADMSG\"; break;
        case EBUSY: msg = \"EBUSY\"; break;
        case ECANCELED: msg = \"ECANCELED\"; break;
        case ECHILD: msg = \"ECHILD\"; break;
        case ECONNABORTED: msg = \"ECONNABORTED\"; break;
        case ECONNREFUSED: msg = \"ECONNREFUSED\"; break;
        case ECONNRESET: msg = \"ECONNRESET\"; break;
        case EDEADLK: msg = \"EDEADLK\"; break;
        case EDESTADDRREQ: msg = \"EDESTADDRREQ\"; break;
        case EDOM: msg = \"EDOM\"; break;
        case EDQUOT: msg = \"EDQUOT\"; break;
        case EEXIST: msg = \"EEXIST\"; break;
        case EFAULT: msg = \"EFAULT\"; break;
        case EFBIG: msg = \"EFBIG\"; break;
        case EHOSTUNREACH: msg = \"EHOSTUNREACH\"; break;
        case EIDRM: msg = \"EIDRM\"; break;
        case EILSEQ: msg = \"EILSEQ\"; break;
        case EINPROGRESS: msg = \"EINPROGRESS\"; break;
        case EINTR: msg = \"EINTR\"; break;
        case EINVAL: msg = \"EINVAL\"; break;
        case EIO: msg = \"EIO\"; break;
        case EISCONN: msg = \"EISCONN\"; break;
        case EISDIR: msg = \"EISDIR\"; break;
        case ELOOP: msg = \"ELOOP\"; break;
        case EMFILE: msg = \"EMFILE\"; break;
        case EMLINK: msg = \"EMLINK\"; break;
        case EMSGSIZE: msg = \"EMSGSIZE\"; break;
        case EMULTIHOP: msg = \"EMULTIHOP\"; break;
        case ENAMETOOLONG: msg = \"ENAMETOOLONG\"; break;
        case ENETDOWN: msg = \"ENETDOWN\"; break;
        case ENETRESET: msg = \"ENETRESET\"; break;
        case ENETUNREACH: msg = \"ENETUNREACH\"; break;
        case ENFILE: msg = \"ENFILE\"; break;
        case ENOBUFS: msg = \"ENOBUFS\"; break;
        case ENODATA: msg = \"ENODATA\"; break;
        case ENODEV: msg = \"ENODEV\"; break;
        case ENOENT: msg = \"ENOENT\"; break;
        case ENOEXEC: msg = \"ENOEXEC\"; break;
        case ENOLCK: msg = \"ENOLCK\"; break;
        case ENOLINK: msg = \"ENOLINK\"; break;
        case ENOMEM: msg = \"ENOMEM\"; break;
        case ENOMSG: msg = \"ENOMSG\"; break;
        case ENOPROTOOPT: msg = \"ENOPROTOOPT\"; break;
        case ENOSPC: msg = \"ENOSPC\"; break;
        case ENOSR: msg = \"ENOSR\"; break;
        case ENOSTR: msg = \"ENOSTR\"; break;
        case ENOSYS: msg = \"ENOSYS\"; break;
        case ENOTCONN: msg = \"ENOTCONN\"; break;
        case ENOTDIR: msg = \"ENOTDIR\"; break;
        case ENOTEMPTY: msg = \"ENOTEMPTY\"; break;
        case ENOTSOCK: msg = \"ENOTSOCK\"; break;
        case ENOTSUP: msg = \"ENOTSUP\"; break;
        case ENOTTY: msg = \"ENOTTY\"; break;
        case ENXIO: msg = \"ENXIO\"; break;
        //case EOPNOTSUPP: msg = \"EOPNOTSUPP\"; break;
        case EOVERFLOW: msg = \"EOVERFLOW\"; break;
        case EPERM: msg = \"EPERM\"; break;
        case EPIPE: msg = \"EPIPE\"; break;
        case EPROTO: msg = \"EPROTO\"; break;
        case EPROTONOSUPPORT: msg = \"EPROTONOSUPPORT\"; break;
        case EPROTOTYPE: msg = \"EPROTOTYPE\"; break;
        case ERANGE: msg = \"ERANGE\"; break;
        case EROFS: msg = \"EROFS\"; break;
        case ESPIPE: msg = \"ESPIPE\"; break;
        case ESRCH: msg = \"ESRCH\"; break;
        case ESTALE: msg = \"ESTALE\"; break;
        case ETIME: msg = \"ETIME\"; break;
        case ETIMEDOUT: msg = \"ETIMEDOUT\"; break;
        case ETXTBSY: msg = \"ETXTBSY\"; break;
        //case EWOULDBLOCK: msg = \"EWOULDBLOCK\"; break;
        case EXDEV: msg = \"EXDEV\"; break;
        default: msg = \"?UNKNOWN?\";
    };
    if (name)
        fprintf(p, \"%%s %%s=%%d %%s\", type, name, value, msg);
    else
        fprintf(p, \"(%%s)%%d %%s\", type, value, msg);
}

static inline void %(prefix)s_log_fmt_octal_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#o\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#o\", type, value);
}

static inline void %(prefix)s_log_fmt_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hhd (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%hhd (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_uchar(FILE *p, const char *type, const char *name, unsigned char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hhu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hhu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hhx (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%#hhx (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_octal_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hho (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%#hho (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_short(FILE *p, const char *type, const char *name, short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hd\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hd\", type, value);
}

static inline void %(prefix)s_log_fmt_ushort(FILE *p, const char *type, const char *name, unsigned short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_short(FILE *p, const char *type, const char *name, short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#hx\", type, value);
}

static inline void %(prefix)s_log_fmt_long(FILE *p, const char *type, const char *name, long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%ld\", type, name, value);
    else
        fprintf(p, \"(%%s)%%ld\", type, value);
}

static inline void %(prefix)s_log_fmt_ulong(FILE *p, const char *type, const char *name, unsigned long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%lu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%lu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_long(FILE *p, const char *type, const char *name, long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#lx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#lx\", type, value);
}

static inline void %(prefix)s_log_fmt_long_long(FILE *p, const char *type, const char *name, long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%lld\", type, name, value);
    else
        fprintf(p, \"(%%s)%%lld\", type, value);
}

static inline void %(prefix)s_log_fmt_ulong_long(FILE *p, const char *type, const char *name, unsigned long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%llu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%llu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_long_long(FILE *p, const char *type, const char *name, long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#llx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#llx\", type, value);
}

static inline void %(prefix)s_log_fmt_bool(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%s\", type, name, value ? \"true\" : \"false\");
    else
        fprintf(p, \"(%%s)%%s\", type, value ? \"true\" : \"false\");
}

static inline void %(prefix)s_log_fmt_string(FILE *p, const char *type, const char *name, const char *value)
{
    if (name) {
        if (value)
            fprintf(p, \"%%s %%s=\\\"%%s\\\"\", type, name, value);
        else
            fprintf(p, \"%%s %%s=(null)\", type, name);
    } else {
        if (value)
            fprintf(p, \"(%%s)\\\"%%s\\\"\", type, value);
        else
            fprintf(p, \"(%%s)(null)\", type);
    }
}

static inline void %(prefix)s_log_fmt_double(FILE *p, const char *type, const char *name, double value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%g\", type, name, value);
    else
        fprintf(p, \"(%%s)%%g\", type, value);
}

static inline void %(prefix)s_log_fmt_pointer(FILE *p, const char *type, const char *name, const void *value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%p\", type, name, value);
    else
        fprintf(p, \"(%%s)%%p\", type, value);
}

static inline void %(prefix)s_log_checker_null(FILE *p, const char *type, const void *value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"NULL was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_non_null(FILE *p, const char *type, const void *value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"non-NULL was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_zero(FILE *p, const char *type, long long value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"ZERO was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_non_zero(FILE *p, const char *type, long long value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"non-ZERO was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_false(FILE *p, const char *type, long long value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"FALSE was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_true(FILE *p, const char *type, long long value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"TRUE was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_errno(FILE *p, const char *type, long long value)
{
    if (!errno) fprintf(p, %(prefix)s_COLOR_ERROR \"%%s\", strerror(errno));
    (void)type;
    (void)value;
}

""" % {"header": ctxt["header"],
       "prefix": ctxt["prefix"],
       "libname": ctxt["libname"],
       "progname": os.path.basename(sys.argv[0]),
       })
    cfg = ctxt["cfg"]
    if cfg:
        try:
            headers = cfg.get("global", "headers")
        except Exception, e:
            headers = None
        if headers:
            for h in headers.split(","):
                f.write("#include <%s>\n" % h)

        try:
            overrides = cfg.get("global", "overrides")
        except Exception, e:
            overrides = None
        if overrides:
            for o in overrides.split(","):
                f.write("#include \"%s\"\n" % o)


provided_formatters = {
    "int": "%(prefix)s_log_fmt_int",
    "signed-int": "%(prefix)s_log_fmt_int",
    "unsigned-int": "%(prefix)s_log_fmt_uint",
    "unsigned": "%(prefix)s_log_fmt_uint",
    "int32_t": "%(prefix)s_log_fmt_int",
    "uint32_t": "%(prefix)s_log_fmt_uint",

    "char": "%(prefix)s_log_fmt_char",
    "signed-char": "%(prefix)s_log_fmt_char",
    "unsigned-char": "%(prefix)s_log_fmt_uchar",
    "int8_t": "%(prefix)s_log_fmt_char",
    "uint8_t": "%(prefix)s_log_fmt_uchar",

    "short": "%(prefix)s_log_fmt_short",
    "signed-short": "%(prefix)s_log_fmt_short",
    "unsigned-short": "%(prefix)s_log_fmt_ushort",
    "signed-short-int": "%(prefix)s_log_fmt_short",
    "unsigned-short-int": "%(prefix)s_log_fmt_ushort",
    "int16_t": "%(prefix)s_log_fmt_short",
    "uint16_t": "%(prefix)s_log_fmt_ushort",

    "long": "%(prefix)s_log_fmt_long",
    "signed-long": "%(prefix)s_log_fmt_long",
    "unsigned-long": "%(prefix)s_log_fmt_ulong",
    "signed-long-int": "%(prefix)s_log_fmt_long",
    "unsigned-long-int": "%(prefix)s_log_fmt_ulong",

    "long-long": "%(prefix)s_log_fmt_long_long",
    "signed-long-long": "%(prefix)s_log_fmt_long_long",
    "unsigned-long-long": "%(prefix)s_log_fmt_ulong_long",
    "signed-long-long-int": "%(prefix)s_log_fmt_long_long",
    "unsigned-long-long-int": "%(prefix)s_log_fmt_ulong_long",
    "int64_t": "%(prefix)s_log_fmt_long_long",
    "uint64_t": "%(prefix)s_log_fmt_ulong_long",

    "bool": "%(prefix)s_log_fmt_bool",
    "Bool": "%(prefix)s_log_fmt_bool",
    "_Bool": "%(prefix)s_log_fmt_bool",
    "BOOL": "%(prefix)s_log_fmt_bool",

    "double": "%(prefix)s_log_fmt_double",
    "float": "%(prefix)s_log_fmt_double",

    "char-*": "%(prefix)s_log_fmt_string",
    "const-char-*": "%(prefix)s_log_fmt_string",
    "const-*-char-*": "%(prefix)s_log_fmt_string",
    "void-*": "%(prefix)s_log_fmt_pointer",
    }

def get_type_formatter(func, name, type, ctxt):
    type = type.replace(" ", "-")

    formatter = "%(prefix)s_log_fmt_long_long"
    if "*" in type or type == "va_list":
        formatter = "%(prefix)s_log_fmt_pointer"
    elif type in provided_formatters:
        formatter = provided_formatters[type]
    formatter = formatter % ctxt

    cfg = ctxt["cfg"]
    if not cfg:
        return formatter

    safe = False
    try:
        safe = cfg.getboolean("global", "assume-safe-formatters")
    except Exception, e:
        pass

    try:
        custom_formatter = cfg.get("type-formatters", type, vars=ctxt)
    except Exception, e:
        custom_formatter = None

    section = "func-%s" % (func,)

    if name == "return":
        key = "return"
    else:
        key = "parameter-%s" % name

    try:
        safe = cfg.getboolean(section, key + "-safe")
    except Exception, e:
        pass

    try:
        param_formatter = cfg.get(section, key + "-formatter", vars=ctxt)
    except Exception, e:
        param_formatter = None

    if param_formatter:
        return param_formatter
    if safe:
        if custom_formatter:
            return custom_formatter
        elif "*" in type and type in provided_formatters:
            formatter = provided_formatters[type] % ctxt
    return formatter


# checkers:
#     %(prefix)s_log_checker_null
#     %(prefix)s_log_checker_non_null
#     %(prefix)s_log_checker_zero
#     %(prefix)s_log_checker_non_zero
#     %(prefix)s_log_checker_false
#     %(prefix)s_log_checker_true
#     %(prefix)s_log_checker_errno
def get_return_checker(func, type, ctxt):
    cfg = ctxt["cfg"]
    if not cfg:
        return

    type = type.replace(" ", "-")
    try:
        checker = cfg.get("return-checkers", type, vars=ctxt)
    except Exception, e:
        checker = None

    section = "func-%s" % (func,)
    try:
        custom_checker = cfg.get(section, "return-checker", vars=ctxt)
    except Exception, e:
        custom_checker = None

    return custom_checker or checker


def generate_log_params(f, func, ctxt):
    if not func.parameters or func.parameters[0][0] == "void":
        return
    prefix = ctxt["prefix"]
    f.write("    %s_log_params_begin();\n" % (prefix,))
    for i, p in enumerate(func.parameters):
        type = p[0]
        name = p[1]
        formatter = get_type_formatter(func.name, name, type, ctxt)
        f.write("    errno = %s_bkp_errno;\n" % prefix)
        f.write("    %s(%s_log_fp, \"%s\", \"%s\", %s);\n" %
                (formatter, prefix, type, name, name))
        if i + 1 < len(func.parameters):
            f.write("    %s_log_param_continue();\n" % (prefix,))
    f.write("    %s_log_params_end();\n" % (prefix,))


def generate_func(f, func, ctxt):
    if func.parameters and func.parameters[-1][0] == "...":
        print "Ignored: %s() cannot handle variable arguments" % (func.name,)
        return

    if "*" in func.ret_type:
        ret_default = "NULL"
    else:
        ret_default = "0"

    cfg_section = "func-%s" % func.name
    if ctxt["cfg"]:
        try:
            ret_default = ctxt["cfg"].get(cfg_section, "return-default")
        except Exception, e:
            pass

    prefix = ctxt["prefix"]
    func.parameters_unnamed_fix(prefix + "_p_")
    repl = {
        "prefix": prefix,
        "name": func.name,
        "internal_name": "%s_f_%s" % (prefix, func.name),
        "ret_type": func.ret_type,
        "ret_name": "%s_ret" % (prefix,),
        "ret_default": ret_default,
        "params_decl": func.parameters_str(),
        "params_names": func.parameters_names_str(),
        }
    f.write("""
%(ret_type)s %(name)s(%(params_decl)s)
{
    %(ret_type)s (*%(internal_name)s)(%(params_decl)s) = NULL;
    int %(prefix)s_bkp_errno = errno;
""" % repl)
    if func.ret_type != "void":
        f.write("""\
    %(ret_type)s %(ret_name)s = %(ret_default)s;
    %(prefix)s_GET_SYM(%(internal_name)s, \"%(name)s\", %(ret_name)s);
""" % repl)
    else:
        f.write("    %(prefix)s_GET_SYM(%(internal_name)s, \"%(name)s\");\n" %
                repl)

    f.write("\n    %(prefix)s_log_enter_start(\"%(name)s\");\n" % repl)
    generate_log_params(f, func, ctxt)
    f.write("    %(prefix)s_log_enter_end(\"%(name)s\");\n" % repl)

    f.write("\n    errno = %(prefix)s_bkp_errno;\n    " % repl)

    if func.ret_type != "void":
        f.write("%(ret_name)s = " % repl)

    override = None
    if ctxt["cfg"]:
        try:
            override = ctxt["cfg"].get(cfg_section, "override")
        except Exception, e:
            pass
    if override:
        repl["override"] = override
        f.write("%(override)s(%(internal_name)s, %(params_names)s);\n" % repl)
    else:
        f.write("%(internal_name)s(%(params_names)s);\n" % repl)

    f.write("    %(prefix)s_bkp_errno = errno;\n" % repl)
    f.write("\n    %(prefix)s_log_exit_start(\"%(name)s\");\n" % repl)
    generate_log_params(f, func, ctxt)

    if func.ret_type != "void":
        formatter = get_type_formatter(func.name, "return", func.ret_type, ctxt)
        f.write("    %(prefix)s_log_exit_return();\n" % repl)
        f.write("    errno = %(prefix)s_bkp_errno;\n" % repl)
        f.write("    %s(%s_log_fp, \"%s\", NULL, %s);\n" %
                (formatter, prefix, func.ret_type, repl["ret_name"]))
        checker = get_return_checker(func.name, func.ret_type, ctxt)
        if checker:
            f.write("    errno = %(prefix)s_bkp_errno;\n" % repl)
            f.write("    %s(%s_log_fp, \"%s\", %s);\n" %
                    (checker, prefix, func.ret_type, repl["ret_name"]))

    f.write("    %(prefix)s_log_exit_end(\"%(name)s\");\n" % repl)

    if func.ret_type != "void":
        f.write("\n    errno = %(prefix)s_bkp_errno;\n" % repl)
        f.write("    return %(ret_name)s;\n" % repl)

    f.write("}\n")


def generate(outfile, ctxt):
    f = open(outfile, "w")

    cfg = ctxt["cfg"]
    fignore_regexp = config_get_regexp(cfg, "global", "ignore-functions-regexp")

    generate_preamble(f, ctxt)
    funcs = ctxt["header_contents"]["function"].items()
    funcs.sort(cmp=lambda a, b: cmp(a[0], b[0]))
    for name, func in funcs:
        if fignore_regexp and fignore_regexp.match(name):
            print "Ignoring %s as requested" % (name,)
            continue
        generate_func(f, func, ctxt)
    f.close()


def generate_makefile(makefile, sourcefile, ctxt):
    source_dir = os.path.dirname(sourcefile)
    makefile_dir = os.path.dirname(makefile)

    if source_dir == makefile_dir:
        sourcename = os.path.basename(sourcefile)
        makefile_tmpl = os.path.basename(sourcefile)
    else:
        print ("WARNING: source and makefile are not in the same folder, "
               "using absolute paths!")
        sourcename = sourcefile
        makefile_tmpl = makefile

    sourcename = os.path.splitext(sourcename)[0]

    repl = {
        "prefix": ctxt["prefix"],
        "sourcefile": sourcefile,
        "sourcename": sourcename,
        "makefile": makefile_tmpl,
        }
    f = open(makefile, "w")
    f.write("""\
CFLAGS = -Wall -Wextra
LDFLAGS = -ldl -fPIC

BINS = \\
    %(sourcename)s.so \\
    %(sourcename)s-color.so \\
    %(sourcename)s-color-timestamp.so \\
    %(sourcename)s-color-threads.so \\
    %(sourcename)s-color-threads-timestamp.so \\
    %(sourcename)s-color-indent.so \\
    %(sourcename)s-color-indent-timestamp.so \\
    %(sourcename)s-color-indent-threads.so \\
    %(sourcename)s-color-indent-threads-timestamp.so

.PHONY: all clean
all: $(BINS)
clean:
\trm -f $(BINS) *~

%(sourcename)s.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-threads.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_HAVE_THREADS=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-threads-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_HAVE_THREADS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-indent.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-indent-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-indent-threads.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_HAVE_THREADS=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-indent-threads-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_HAVE_THREADS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

""" % repl)
    f.close()


def prefix_from_libname(libname):
    prefix = libname
    if prefix.startswith("lib"):
        prefix = prefix[len("lib"):]
    try:
        prefix = prefix[:prefix.index(".")]
    except ValueError:
        pass
    return "_log_" + prefix


def config_get_regexp(cfg, section, key, default=None):
    if cfg:
        try:
            s = cfg.get(section, key)
            if s:
                return re.compile(s)
        except Exception, e:
            pass
    if default:
        return re.compile(default)
    return None


if __name__ == "__main__":
    usage = "usage: %prog [options] <header.h> <libname.so> <outfile.c>"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-c", "--config", action="store", default=None,
                      help="Configuration file to use with this library")
    parser.add_option("-p", "--prefix", action="store", default=None,
                      help="Symbol prefix to use (defaults to autogenerated)")
    parser.add_option("-M", "--makefile", action="store", default=None,
                      help="Generate sample makefile")

    options, args = parser.parse_args()
    try:
        header = args[0]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: header.h")
    try:
        libname = args[1]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: libname.so")
    try:
        outfile = args[2]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: outfile.c")

    cfg = None
    if options.config:
        cfg = ConfigParser()
        cfg.read([options.config])

    header_contents = header_tree(header, cfg)
    debug = False
    if debug: # XXX cmdline opt? remove?
        hc = header_contents.items()
        hc.sort(cmp=lambda a, b: cmp(a[0], b[0]))
        for k, v in hc:
            print
            print k
            c = v.values()
            c.sort(cmp=lambda a, b: cmp(a.name, b.name))
            for p in c:
                print "\t%s" % (p,)

    prefix = options.prefix
    if not prefix:
        prefix = prefix_from_libname(libname)

    prefix = re.sub("[^a-zA-z0-9_]", "_", prefix)

    ctxt = {
        "header": header,
        "header_contents": header_contents,
        "prefix": prefix,
        "libname": libname,
        "cfg": cfg,
        }
    generate(outfile, ctxt)

    if options.makefile:
        generate_makefile(options.makefile, outfile, ctxt)

