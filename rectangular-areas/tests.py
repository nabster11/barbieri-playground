#!/usr/bin/python

cases = (
    ("side-by-side-horizontal",
     ((0, 0, 100, 100), (100, 0, 100, 100))),
    ("side-by-side-vertical",
     ((0, 0, 100, 100), (0, 100, 100, 100))),
    ("contained",
     ((0, 0, 100, 100), (25, 25, 50, 50))),
    ("contains",
     ((25, 25, 50, 50), (0, 0, 100, 100))),
    ("horizontal",
     ((0, 0, 100, 100), (50, 0, 100, 100))),
    ("vertical",
     ((0, 0, 100, 100), (0, 50, 100, 100))),
    ("cascade-no-merge_1",
     ((0, 0, 100, 100), (50, 50, 100, 100), (100, 100, 100, 100))),
    ("cascade-no-merge_2",
     ((100, 100, 100, 100), (50, 50, 100, 100), (0, 0, 100, 100))),
    ("cascade-no-merge_3",
     ((50, 50, 100, 100), (100, 100, 100, 100), (0, 0, 100, 100))),
    ("cascade-no-merge_4",
     ((50, 50, 100, 100), (0, 0, 100, 100), (100, 100, 100, 100))),
    ("cascade-merge_1",
     ((0, 0, 100, 100), (4, 4, 100, 100), (8, 8, 100, 100))),
    ("cascade-merge_2",
     ((8, 8, 100, 100), (4, 4, 100, 100), (0, 0, 100, 100))),
    ("cascade-merge_3",
     ((4, 4, 100, 100), (8, 8, 100, 100), (0, 0, 100, 100))),
    ("cascade-merge_4",
     ((4, 4, 100, 100), (0, 0, 100, 100), (8, 8, 100, 100))),
    ("cross-all-fat_1",
     ((50, 0, 50, 150), (0, 50, 150, 50))),
    ("cross-all-fat_2",
     ((0, 50, 150, 50), (50, 0, 50, 150))),
    ("cross-all-thin_1",
     ((50, 0, 4, 150), (0, 50, 150, 4))),
    ("cross-all-thin_2",
     ((0, 50, 150, 4), (50, 0, 4, 150))),
   ("cross-horiz-fat-vert-thin_1",
    ((50, 0, 4, 150), (0, 50, 150, 50))),
    ("cross-horiz-fat-vert-thin_2",
     ((0, 50, 150, 50), (50, 0, 4, 150))),
    ("cross-horiz-thin-vert-fat_1",
     ((50, 0, 50, 150), (0, 50, 150, 4))),
    ("cross-horiz-thin-vert-fat_2",
     ((0, 50, 150, 4), (50, 0, 50, 150))),
    ("checker-big",
     ((0, 0, 50, 50), (100, 0, 50, 50),
      (50, 50, 50, 50),
      (0, 100, 50, 50), (100, 100, 50, 50))),
    ("checker-small",
     ((0, 0, 5, 5), (10, 0, 5, 5),
      (5, 5, 5, 5),
      (0, 10, 5, 5), (10, 10, 5, 5))),
    ("snake_1",
     ((0, 0, 50, 50), (3, 3, 50, 50), (6, 6, 50, 50), (9, 9, 50, 50),
      (6, 12, 50, 50), (3, 15, 50, 50), (0, 18, 50, 50))),
    ("snake_2",
     ((0, 18, 50, 50), (3, 15, 50, 50), (6, 12, 50, 50), (9, 9, 50, 50),
      (6, 6, 50, 50), (3, 3, 50, 50), (0, 0, 50, 50))),
    ("snake_3",
     ((9, 9, 50, 50), (0, 18, 50, 50), (3, 15, 50, 50), (6, 12, 50, 50),
      (6, 6, 50, 50), (3, 3, 50, 50), (0, 0, 50, 50))),
    ("snake_4",
     ((9, 9, 50, 50), (0, 18, 50, 50), (3, 15, 50, 50), (6, 12, 50, 50),
      (6, 6, 50, 50), (3, 3, 50, 50), (0, 0, 50, 50))),
    )

if __name__ == "__main__":
    import split
    import pprint
    import pygame
    from pygame.locals import *

    pygame.init()
    screen = pygame.display.set_mode((800, 480), 0, 16)
    screen.fill(0xffffff)
    pygame.display.flip()

    color = (
        (255, 0, 0, 100),
        (0, 255, 0, 100),
        (0, 0, 255, 100),
        (255, 255, 0, 100),
        (255, 0, 255, 100),
        (0, 255, 255, 100),
        (255, 100, 100, 100),
        (100, 255, 100, 100),
        (100, 100, 255, 100),
        (255, 255, 100, 100),
        (255, 100, 255, 100),
        (100, 255, 255, 100),
        )

    no_wait = False
    def wait():
        if no_wait:
            return
        while 1:
            for e in pygame.event.get():
                if e.type == QUIT:
                    raise SystemExit()
                elif e.type == KEYDOWN:
                    return

    def draw_rect(r, c, dx, dy):
        surf = pygame.Surface(r.size, SRCALPHA, 32).convert_alpha()
        r2 = (0, 0) + r.size
        surf.fill(c, r2)
        pygame.draw.rect(surf, (0, 0, 0, 255), r2, 1)
        r = Rect(r)
        r.left += dx
        r.top += dy
        screen.blit(surf, r)

    for name, rects in cases:
        print "test:", name
        pygame.display.set_caption("test: %s" % name)

        max_x = 0
        max_y = 0
        for i, r in enumerate(rects):
            x, y, w, h = r
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
            r = Rect(x, y, w, h)
            draw_rect(r, color[i % len(color)], 100, 50)
        pygame.display.flip()

        dx = screen.get_size()[0] - max_x - 100
        dy = 50
        r_clear = Rect(dx, dy, max_x, max_y)

        non_overlaps = split.RectSplitter()
        for r in rects:
            print "ADD:", split.Rect(r)
            idx = len(non_overlaps.rects)
            idx -= non_overlaps._split(split.Rect(*r), accepted_error=300)

            for i, r2 in enumerate(non_overlaps.rects):
                pygame.display.set_caption("test: %s, split after %s, HIT ENTER..." % \
                                           (name, r))
                draw_rect(r2, color[i % len(color)], dx, dy)
            pygame.display.flip()
            wait()
            screen.fill(0xffffff, r_clear)


            non_overlaps._merge(idx, accepted_error=300)

#            non_overlaps.add(split.Rect(*r), accepted_error=300)
#            non_overlaps.split_strict(split.Rect(*r))

            for i, r2 in enumerate(non_overlaps.rects):
                pygame.display.set_caption("test: %s, add %s, HIT ENTER..." % \
                                           (name, r))
                draw_rect(r2, color[i % len(color)], dx, dy)
            pygame.display.flip()
            wait()
            screen.fill(0xffffff, r_clear)

        for i, r in enumerate(rects):
            draw_rect(Rect(r), (0, 0, 0, 20), dx, dy)

        pprint.pprint(non_overlaps.rects)
        for i, r in enumerate(non_overlaps.rects):
            pygame.display.set_caption("test: %s, DONE! HIT ENTER..." % name)
            draw_rect(r, color[i % len(color)], dx, dy)
            pygame.display.flip()
            wait()

        screen.fill(0xffffff)

