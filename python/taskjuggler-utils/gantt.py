#!/usr/bin/env python

import sys
import datetime
import time
import optparse

try:
    from pyx import *
except ImportError, e:
    raise SystemExit("Missing python module: pyx (http://pyx.sourceforge.net)")

from parser import *


class Plotter(object):
    cm = color.cmyk
    bar_height = 0.8
    bar_vskip = 0.05
    text_skip = 0.08
    text_height = 0.5
    comp_height = 0.1
    page_width = 40.0
    advance1 = 0.1
    advance2 = 0.4
    textsize = "" # r"\footnotesize"

    text_encoding = "latin1"

    label_pos = 0 # 0 is left, 1 is right, 2 is top
    task_format = r"{" + textsize + " {%(text)s}}"
    milestone_format = r"{" + textsize + " {%(text)s}}"
    enclosure_format = r"{" + textsize + " {%(text)s}}"
    resource_format = r"{\tiny \itshape" \
                      r"\parbox{%(resource_maxwidth)fcm}" \
                      r"{\textcolor[rgb]{0.4,0.4,0.4}{" \
                      r"\begin{flushleft}" \
                      r"%(text)s" \
                      r"\end{flushleft}}}}"
    resource_maxwidth = 3.0
    resource_skip = 0.4
    show_resources = True
    show_vacation  = True
    show_deps      = True
    show_days      = True
    align_to_day   = False
    months_on_top  = False
    timeline_height = 0.5

    comp_style = (cm.Black,)
    now_color = cm.Green
    now_skip = 0.3

    status_colors = (cm.Magenta,     # STATUS_UNKNOWN
                     cm.Gray,        # STATUS_NOT_STARTED
                     cm.Salmon,      # STATUS_WIP_LATE
                     cm.Black,       # STATUS_WIP
                     cm.Yellow,      # STATUS_ON_TIME
                     cm.Cyan,        # STATUS_WIP_AHEAD
                     cm.RoyalBlue,   # STATUS_FINISHED
                     cm.Red,         # STATUS_LATE
                     )

    level = 0
    day = 24 * 60 * 60
    time_interval = 7 * day

    week_color = color.gray(0.9)
    week_style = (style.linewidth.THIN, deco.filled([week_color]))
    week_format = "W%d"
    week_line_style = (style.linewidth.THIN, color.gray(0.8),
                       style.linestyle.dashed)
    month_style = (style.linewidth.THIN, deco.filled([week_color]))
    month_format = r"%B, %Y"
    min_month_width = 3.0 # min width for displaying month and year

    dependency_style = (style.linewidth.normal, cm.Black, deco.earrow.normal)
    vacation_style = (style.linewidth.thin, color.gray(0.9),
                      deco.filled([color.gray(0.95)]))
    day_line_style = (style.linewidth.thin, color.gray(0.8))

    now_format = "Now (%a, %d %b %Y)"

    task_style = (color.cmyk.Black, style.linecap.round, style.linewidth.THIN)
    enclosure_style = (color.cmyk.Black, style.linecap.round,
                       style.linewidth.THIN)
    milestone_style = (style.linewidth.THIN, deco.filled([cm.Black]),
                       style.linejoin.bevel, style.linecap.round)


    def __init__(self, doc):
        self.time_start = 0.0
        self.time_end = 0.0
        self.second_size = 1.0
        self.page_height = 0.0
        self.lines = 0
        self.doc = doc
    # __init__()


    def process(self, scenario="plan"):
        self.canvas = canvas.canvas()
        self._setup_text()
        self._setup_page_height()
        self._setup_time_range()
        self.output_document(scenario)
    # process()


    def _setup_text(self):
        text.reset()
        text.set(mode="latex")
        text.preamble(r"\usepackage[%s]{inputenc}" % self.text_encoding)
        text.preamble(r"\usepackage{color}")
        text.preamble(r"\usepackage{bookman}")
        text.preamble(r"\definecolor{now_color}{cmyk}"
                      "{%(c)g,%(m)g,%(y)g,%(k)g}" %
                      self.now_color.color)
        text.preamble(r"\parindent=0pt")
    # _setup_text()


    def _setup_page_height(self):
        tasks = 0
        for p in self.doc.prjs.itervalues():
            tasks = max(tasks, len(p._known_tasks))

        self.lines = tasks
        bar_skip = self.bar_height + self.bar_vskip
        if self.label_pos in (0, 1):
            self.bar_skip = max(bar_skip, self.text_height)
        elif self.label_pos == 2:
            self.bar_skip = bar_skip + self.text_height + self.text_skip

        if self.months_on_top:
            self.header_height = 2 * self.timeline_height
            self.footer_height = 0
        else:
            self.header_height = self.timeline_height
            self.footer_height = self.timeline_height

        self.useful_height = self.bar_skip * self.lines + self.now_skip
        self.page_height = self.footer_height + self.header_height + \
                           self.useful_height
    # _setup_page_height()


    def _setup_time_range(self):
        start = sys.maxint
        end = -sys.maxint - 1
        for prj in self.doc.prjs.itervalues():
            start = min(start, prj.start)
            end = min(end, prj.end)

        start = datetime.date.fromtimestamp(prj.start)
        start -= datetime.timedelta(14)
        weekday = start.isoweekday()
        if weekday != 1:
            start -= datetime.timedelta(weekday - 1)

        end = datetime.date.fromtimestamp(prj.end)
        weekday = end.isoweekday()
        if weekday != 1:
            end += datetime.timedelta(8 - weekday)

        self.time_start = int(time.mktime(start.timetuple()))
        self.time_end = int(time.mktime(end.timetuple()))
        time_range = self.time_end - self.time_start
        self.time_range = time_range + self.time_interval
        self.second_size = self.page_width / float(self.time_range)
        self.day_size = self.seconds_to_coords(self.day)
    # _setup_time_range()


    def seconds_to_coords(self, seconds):
        return self.second_size * seconds
    # seconds_to_coords()


    def seconds_to_x(self, seconds):
        return self.second_size * (seconds - self.time_start)
    # seconds_to_x()


    def status_to_color(self, taskscenario):
        return self.status_colors[taskscenario.status]
    # status_to_color()


    def diamond(self, x, y, w=0.5, h=0.5, style=()):
        dw = w / 2
        dh = h / 2
        shape = path.path(path.moveto(x - dw, y), path.lineto(x, y + dh),
                          path.lineto(x + dw, y), path.lineto(x, y - dh),
                          path.closepath())
        self.canvas.stroke(shape, style)
    # diamond()


    def text(self, x, y, text, style=()):
        if isinstance(text, unicode):
            text = text.encode(self.text_encoding)
        self.canvas.text(x, y, text, style)
    # text()


    def rect(self, x, y, w, h, style=(), fillcolor=None, linecolor=()):
        if fillcolor:
            style += (deco.filled((fillcolor,)),)

        shape = path.rect(x, y, w, h)
        if linecolor is not None:
            style += linecolor
            self.canvas.stroke(shape, style)
        else:
            self.canvas.fill(shape, style)
    # rect()


    def line(self, x0, y0, x1, y1, style=()):
        self.canvas.stroke(path.line(x0, y0, x1, y1), style)
    # line()


    def vline(self, x, y, h, style=()):
        self.canvas.stroke(path.line(x, y, x, y + h), style)
    # vline()


    def hline(self, x, y, w, style=()):
        self.canvas.stroke(path.line(x, y, x + w, y), style)
    # hline()


    def fill(self, shape, style=()):
        self.canvas.fill(shape, style)
    # fill()


    def stroke(self, shape, style=()):
        self.canvas.stroke(shape, style)
    # stroke()

    def arrow(self, x1, y1, x2, y2):
        x12 = x1 + self.advance1
        x22 = x2 - self.advance2


        if (x22 <= x12):
            if y2 > y1:
                midy = y1 + self.bar_skip/2
            else:
                midy = y1 - self.bar_skip/2
            self.canvas.stroke(path.path(path.moveto(x1,y1),
                                         path.lineto(x12,y1),
                                         path.lineto(x12,midy),
                                         path.lineto(x22,midy),
                                         path.lineto(x22,y2),
                                         path.lineto(x2,y2)),
                               self.dependency_style)
        else:
            self.canvas.stroke(path.path(path.moveto(x1,y1),
                                         path.lineto(x12,y1),
                                         path.lineto(x12,y2),
                                         path.lineto(x22,y2),
                                         path.lineto(x2,y2)),
                               self.dependency_style)
#         self.canvas.stroke(path.line(x1,y1,x2,y2), self.dependency_style)
    # arrow()

    def level_to_y(self, level):
        return self.page_height - self.header_height - \
               self.bar_skip * (level + 1)
    # level_to_y()


    def place_label(self, x, y, w, h, label, style=()):
        if self.label_pos == 0:
            tx = x - self.text_skip
            ty = y + h / 2
            flags = (text.halign.boxright, text.vshift.mathaxis)
        elif self.label_pos == 1:
            tx = x + w + self.text_skip
            ty = y + h / 2
            flags = (text.halign.boxleft, text.vshift.mathaxis)
        elif self.label_pos == 2:
            tx = x + w / 2
            ty = y + h + self.text_skip
            flags = (text.halign.boxcenter, text.vshift.bottomzero)

        self.text(tx, ty, label, flags + style)
    # place_label()


    def output_task_milestone(self, prj, task, scenario):
        sc = task.scenarios[scenario]

        x = self.seconds_to_x(sc.start)
        y = self.level_to_y(task.level)

        w = self.bar_height * 0.75
        h = self.bar_height * 0.75
        w2 = w / 2
        h2 = h / 2

        self.diamond(x, y + h2, w, h, self.milestone_style)

        label = self.milestone_format % \
                {"text": task.name,
                 "width": w,
                 "height": h,
                 }
        self.place_label(x - w2, y + h2, w, h, label)
    # output_task_milestone()

    def _day_align(self, t):
        if self.align_to_day:
            dt = datetime.datetime.fromtimestamp(t)
            if dt.hour >= 12:
                return int(time.mktime(dt.date().timetuple())) + self.day
            else:
                return int(time.mktime(dt.date().timetuple()))
        else:
            return t

    def output_task_enclosure(self, prj, task, scenario):
        sc = task.scenarios[scenario]

        start = self._day_align(sc.start)
        end   = self._day_align(sc.end)

        x = self.seconds_to_x(start)
        y = self.level_to_y(task.level)

        w = self.seconds_to_coords(end - start)
        h = self.bar_height * 0.4

        h2 = h / 2
        w2 = min(h2 * 0.75, w / 10.0)

        if sc.complete >= 0:
            print "Missing complete bar"

        r = path.path(path.moveto(x, y + h),
                      path.rlineto(w, 0),
                      path.rlineto(0, -h),
                      path.rlineto(-w2, +h2),
                      path.rlineto(-(w - 2 * w2), 0),
                      path.rlineto(-w2, -h2),
                      path.closepath())

        fillstyle = (self.status_to_color(sc),)
        self.stroke(r, self.enclosure_style + (deco.filled(fillstyle),))

        label = self.enclosure_format % \
                {"text": task.name,
                 "width": w,
                 "height": h,
                 }
        self.place_label(x, y + h2, w, h2, label)
    # output_task_enclosure()


    def output_task_regular(self, prj, task, scenario):
        sc = task.scenarios[scenario]

        start = self._day_align(sc.start)
        end   = self._day_align(sc.end)

        x = self.seconds_to_x(start)
        y = self.level_to_y(task.level)

        w = self.seconds_to_coords(end - start)
        h = self.bar_height

        self.rect(x, y, w, h, style=self.task_style,
                  fillcolor=self.status_to_color(sc))

        if sc.complete >= 0:
            lw = w * sc.complete
            ly = y + (h - self.comp_height)/2
            self.rect(x, ly, lw, self.comp_height, self.comp_style,
                      linecolor=None)

        label = self.task_format % \
                {"text": task.name,
                 "width": w,
                 "height": h,
                 }
        self.place_label(x, y, w, h, label)

        if self.show_resources:
            if self.label_pos != 1:
                tx = x + w + self.resource_skip
                ty = y + h / 2 + self.text_skip / 2
                flags = (text.halign.boxleft, text.valign.middle)
            else:
                tx = x - self.resource_skip
                ty = y + h / 2 + self.text_skip / 2
                flags = (text.halign.boxright, text.valign.middle)

            res = u", ".join(r.name for r in task.resources)
            label = self.resource_format % \
                    {"resource_maxwidth": self.resource_maxwidth,
                     "text": res}
            self.text(tx, ty, label, flags)
    # output_task_regular()

    def output_dep(self, parent, child, scenario):
        if parent.is_milestone:
            start = parent.scenarios[scenario].start
            px = self.seconds_to_x(self._day_align(start)) + 0.3 * \
                 self.bar_height
            py = self.level_to_y(parent.level) + 0.4 * self.bar_height
        else:
            end = parent.scenarios[scenario].end
            px = self.seconds_to_x(self._day_align(end))
            py = self.level_to_y(parent.level) + self.bar_height / 2

        if child.is_milestone:
            start = child.scenarios[scenario].start
            cx = self.seconds_to_x(self._day_align(start)) - 0.375 * \
                 self.bar_height
            cy = self.level_to_y(child.level) + 0.4 * self.bar_height
        else:
            start = child.scenarios[scenario].start
            cx = self.seconds_to_x(self._day_align(start))
            cy = self.level_to_y(child.level)

        self.arrow(px, py, cx, cy)
    # output_dep()

    def set_task_levels(self, task, scenario, level):
        def task_cmp(a, b):
            a_sc = a.scenarios[scenario]
            b_sc = b.scenarios[scenario]
            r = cmp(a_sc.start, b_sc.start)
            if r != 0:
                return r

            if a.is_milestone and not b.is_milestone:
                return -1
            elif not a.is_milestone and b.is_milestone:
                return 1
            elif a.is_milestone and b.is_milestone:
                return 0
            else:
                return cmp(a_sc.duration, b_sc.duration)
        # task_cmp()
        task.tasks.sort(task_cmp)

        task.level = level
        level += 1
        for t in task.tasks:
            level = self.set_task_levels(t, scenario, level)

        return level
    # set_task_levels()

    def output_task(self, prj, task, scenario):
        if task.is_milestone:
            self.output_task_milestone(prj, task, scenario)
        else:
            if task.tasks:
                self.output_task_enclosure(prj, task, scenario)
            else:
                self.output_task_regular(prj, task, scenario)
        for t in task.tasks:
            self.output_task(prj, t, scenario)
    # output_task()


    def output_week_line(self, x):
        self.vline(x, self.footer_height, self.useful_height,
                   self.week_line_style)
    # output_week_line()

    def output_day_line(self, x):
        if not self.show_days:
            return

        self.vline(x, self.footer_height, self.useful_height,
                   self.day_line_style)
    # output_day_line

    def output_week(self, d, x, y, w, h):
        if w <= 0:
            return

        if self.show_vacation:
            self.rect( x + (5 * self.day_size), self.footer_height,
                       2 * self.day_size,
                       self.useful_height,
                       self.vacation_style)
        if self.day_size > 0.1:
            for i in xrange(1, 7, 1):
                self.output_day_line(x + i * self.day_size)

        self.rect(x, y, w, h, self.week_style)
        self.text(x, y + h / 2, self.week_format % d,
                  (text.parbox(w), text.valign.middle,
                   text.halign.flushcenter))
    # output_week()


    def output_month(self, d, x, y, w, h):
        if w <= 0:
            return

        self.rect(x, y, w, h, self.month_style)
        if w >= self.min_month_width:
            self.text(x, y + h/2, d.strftime(self.month_format),
                      (text.parbox(w), text.valign.middle,
                       text.halign.flushcenter))
    # output_month()


    def output_timeline(self):
        h = self.timeline_height
        month_x = self.seconds_to_x(self.time_start)
        if self.months_on_top:
            month_y = self.page_height - h
        else:
            month_y = 0
        week_x = self.seconds_to_x(self.time_start)
        week_y = self.page_height - h
        if self.months_on_top:
            week_y -= h

        ty = h / 2

        self.output_week_line(self.page_width)

        start = datetime.date.fromtimestamp(self.time_start)
        last_week = start.isocalendar()[1]
        last_month = start
        time_end = self.time_range + self.time_start + self.day
        t = self.time_start
        wd = datetime.date.fromtimestamp(self.time_start).isocalendar()[2]
        while t < time_end:
            d = datetime.date.fromtimestamp(t)
            iso = d.isocalendar()

            # Ugly hack to compensate for daylight saving time transitions
            dt = datetime.datetime.fromtimestamp(t)
            if dt.hour == 23:
                t += 3600
            elif dt.hour == 1:
                t -= 3600

            if t == self.time_start:
                t += self.day
                wd = (wd % 7) + 1
                continue

            if wd == 1:
                x1 = self.seconds_to_x(t)
                w = x1 - week_x

                if w > 0:
                    self.output_week_line(week_x)
                    self.output_week(last_week, week_x, week_y, w, h)
                    week_x = x1
                    last_week = iso[1]

            if d.day == 1:
                x1 = self.seconds_to_x(t)
                w = x1 - month_x
                if w > 0:
                    self.output_month(last_month, month_x, month_y, w, h)
                month_x = x1
                last_month = d

            t += self.day
            wd = (wd % 7) + 1

        w = self.page_width - month_x
        self.output_month(d, month_x, month_y, w, h)
        self.hline(0, self.footer_height, self.page_width, self.month_style)

    # output_timeline()

    def output_vacations(self):
        for v in self.doc.vacations:
            self.rect(self.seconds_to_x(v.start), self.footer_height,
                      self.seconds_to_coords(v.end - v.start),
                      self.useful_height, self.vacation_style)
    # output_vacations()


    def output_now_line(self, prj):
        x = self.seconds_to_x(prj.now)
        self.vline(x, self.footer_height,
                   self.useful_height,
                   (style.linewidth.THick, self.now_color))

        now = datetime.datetime.fromtimestamp(prj.now)
        now_str = now.strftime(self.now_format)
        self.text(x + 0.1, self.footer_height + self.text_skip,
                  r"\textsf{\scriptsize \textcolor{now_color}{%s}}" % \
                  (now_str,),
                  (text.vshift.bottomzero,))
    # output_now_line()

    def output_depends(self, prj, task, scenario):
        for dep in task.depends:
            self.output_dep(prj.find_task(dep.dependency), task, scenario)

        for t in task.tasks:
            self.output_depends(prj, t, scenario)
    # output_depends()

    def output_project(self, prj, scenario="plan"):
        level = 0

        def task_cmp(a, b):
            a_sc = a.scenarios[scenario]
            b_sc = b.scenarios[scenario]
            r = cmp(a_sc.start, b_sc.start)
            if r != 0:
                return r

            if a.is_milestone and not b.is_milestone:
                return -1
            elif not a.is_milestone and b.is_milestone:
                return 1
            elif a.is_milestone and b.is_milestone:
                return 0
            else:
                return cmp(a_sc.duration, b_sc.duration)
        # task_cmp()
        prj.tasks.sort(task_cmp)

        for t in prj.tasks:
            level = self.set_task_levels(t, scenario, level)
        if self.show_deps:
            for t in prj.tasks:
                self.output_depends(prj, t, scenario)
        for t in prj.tasks:
            level = self.output_task(prj, t, scenario)

        self.output_now_line(prj)
        self.rect(0, 0, self.page_width, self.page_height)
    # output_project()


    def output_document(self, scenario="plan"):
        if self.show_vacation:
            self.output_vacations()
        self.output_timeline()

        for p in self.doc.prjs.itervalues():
            self.output_project(p, scenario)
    # output_document()


    def save_pdf(self, filename):
        self.canvas.writePDFfile(filename)
    # save_pdf()


    def save_eps(self, filename):
        self.canvas.writeEPSfile(filename)
    # save_eps()


    def save_ps(self, filename):
        self.canvas.writePSfile(filename)
    # save_ps()


    def _to_poster(self, paper_name="A4", paper_width=None,
                   paper_height=None, margin=1.0, length_unit="cm"):

        if paper_name and hasattr(document.paperformat, paper_name):
            paperformat = getattr(document.paperformat, paper_name)
            w = paperformat.width
            h = paperformat.height
        elif paper_width and paper_height and length_unit:
            w = unit.length(float(paper_width), type="t", unit=length_unit)
            h = unit.length(float(paper_height), type="t", unit=length_unit)
            paperformat = document.paperformat(w, h, "User Defined")
        else:
            raise ValueError("Invalid paper spec %r" % paper)

        bbox = self.canvas.bbox()
        canvas_width = unit.tocm(bbox.width())
        canvas_height = unit.tocm(bbox.height())
        canvas_bottom = unit.tocm(bbox.bottom())
        canvas_left = unit.tocm(bbox.left())

        margin = unit.length(float(margin), type="t", unit=length_unit)
        w = unit.tocm(w - 2 * margin)
        h = unit.tocm(h - 2 * margin)

        w1_pages = int(canvas_width / w) + 1
        h1_pages = int(canvas_height / h) + 1
        n1_pages = w1_pages * h1_pages

        w2_pages = int(canvas_width / h) + 1
        h2_pages = int(canvas_height / w) + 1
        n2_pages = w2_pages * h2_pages

        rotate = n1_pages > n2_pages

        if rotate:
            w, h = h, h
            w_pages = w2_pages
            h_pages = h2_pages
        else:
            w_pages = w1_pages
            h_pages = h1_pages

        doc = document.document()
        x = canvas_left
        y = canvas_bottom
        for i in xrange(w_pages):
            y = canvas_bottom

            for j in xrange(h_pages):
                clip = path.rect(x, y, w, h)
                nc = canvas.canvas([canvas.clip(clip)])
                nc.insert(self.canvas)
                doc.append(document.page(nc, paperformat=paperformat,
                                         margin=margin, fittosize=0,
                                         rotated=rotate, centered=1))
                y += h
            # end for h_pages
            x += w
        # end for w_pages
        return doc
    # _to_poster()


    def save_poster_pdf(self, filename, paper_name="A4", paper_width=None,
                        paper_height=None, margin=1.0, length_unit="cm"):
        doc = self._to_poster(paper_name, paper_width, paper_height,
                              margin, length_unit)
        doc.writePDFfile(filename)
    # save_poster_pdf()


    def save_poster_eps(self, filename, paper_name="A4", paper_width=None,
                        paper_height=None, margin=1.0, length_unit="cm"):
        doc = self._to_poster(paper_name, paper_width, paper_height,
                              margin, length_unit)
        doc.writeEPSfile(filename)
    # save_poster_eps()


    def save_poster_ps(self, filename, paper_name="A4", paper_width=None,
                       paper_height=None, margin=1.0, length_unit="cm"):
        doc = self._to_poster(paper_name, paper_width, paper_height,
                              margin, length_unit)
        doc.writePSfile(filename)
    # save_poster_ps()
# Plotter


if __name__ == "__main__":
    usage = "usage: %prog [options] <input.tjx> [output]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-c", "--no-vacation", action="store_true",
                      default=False,
                      help="don't plot vacation")
    parser.add_option("-y", "--no-day", action="store_true",
                      default=False,
                      help="don't plot day lines")
    parser.add_option("-r", "--no-resources", action="store_true",
                      default=False,
                      help="don't show resource allocation")
    parser.add_option("-d", "--no-deps", action="store_true",
                      default=False,
                      help="don't show dependencies")
    parser.add_option("-m", "--months-on-top", action="store_true",
                      default=False,
                      help="place months at the top")
    parser.add_option("-a", "--align-to-day", action="store_true",
                      default=False,
                      help="align tasks to day boundaries")
    parser.add_option("-W", "--chart-width", type="float",
                      default=40.0,
                      help="chart width in centimeters")
    parser.add_option("-w", "--paper-width", type="float",
                      default=10.0,
                      help="paper width in centimeters")
    parser.add_option("-p", "--poster", action="store_true",
                      default=False,
                      help="segment chart into multiple pages")

    options, args = parser.parse_args()
    try:
        infile = args[0]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: infile")

    try:
        outfile = args[1]
    except IndexError:
        outfile = "test.eps"
    print >> sys.stderr, "Writing chart to %s" % outfile

    doc = Document(infile)
    plot = Plotter(doc)
    plot.bar_height = 0.4
    plot.bar_vskip = 0.2
    plot.show_vacation = not options.no_vacation
    plot.show_days = not options.no_day
    plot.show_resources = not options.no_resources
    plot.show_deps = not options.no_deps
    plot.months_on_top = options.months_on_top
    plot.align_to_day = options.align_to_day
    plot.paper_width = options.chart_width
    plot.process("plan")

    if options.poster:
        if outfile.endswith(".eps"):
            plot.save_poster_eps(outfile, paper_width=options.paper_width)
        elif outfile.endswith(".ps"):
            plot.save_poster_ps(outfile)
        else:
            plot.save_poster_pdf(outfile, paper_width=options.paper_width)
    else:
        if outfile.endswith(".eps"):
            plot.save_eps(outfile)
        elif outfile.endswith(".ps"):
            plot.save_ps(outfile)
        else:
            plot.save_pdf(outfile)
