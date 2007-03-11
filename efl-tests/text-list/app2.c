#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>
#include "e_box.h"

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Text List Test"
#define WM_NAME "TextList"
#define WM_CLASS "main"

typedef struct app
{
    char *infile;
    Evas_Object *edje_main;
    Evas_Object *e_box;
    Evas_Object *arrow_up;
    Evas_Object *arrow_down;
    Ecore_Evas  *ee;
    Evas *evas;
    Evas_List *items;
    int current;
    Evas_Object **evas_items;
    int n_evas_items;
    struct {
        Ecore_Timer *timer;
        double start_align;
        double stop_align;
        double step_align;
        void (*stop_cb)(void *data);
    } scroll;
} app_t;

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

static inline void
_add_item(app_t *app, const char *txt)
{
    app->items = evas_list_append(app->items, strdup(txt));
}

static void
_populate(app_t *app)
{
    FILE *fp;
    char *line;
    unsigned n;

    if (app->infile) {
        fp = fopen(app->infile, "r");
        if (fp == NULL) {
            fprintf(stderr, "Could not open file for reading \"%s\": %s\n",
                    app->infile, strerror(errno));
            return;
        }
    } else {
        fprintf(stderr, "No input file provided, reading from stdin.\n");
        fp = stdin;
    }


    line = malloc(128);
    n = 128;

    while (!feof(fp)) {
        int i;

        i = getline(&line, &n, fp);
        if (i < 0)
            break;
        else if (i == 0)
            continue;

        line[i - 1] = '\0';

        _add_item(app, line);
    }

    free(line);

    if (fp != stdin)
        fclose(fp);
}

static Evas_Object *
_new_list_item(app_t *app, const char *text)
{
    Evas_Object *obj;

    obj = edje_object_add(app->evas);
    edje_object_file_set(obj, THEME, "list_item");
    edje_object_part_text_set(obj, "label", text);

    return obj;
}

static inline void
_set_item_text(app_t *app, int index, const char *text)
{
    Evas_Object *obj;

    obj = app->evas_items[index];

    edje_object_part_text_set(obj, "label", text);
}

static void
fill_gui_list(app_t *app)
{
    int i, j, last, n_items, last_evas, c;
    Evas_List *itr;
    float p;

    j = 0;
    i = app->current - 1;
    last_evas = app->n_evas_items;
    last = app->current + last_evas - 1;
    n_items = evas_list_count(app->items);

    if (n_items < 1)
        return;

    e_box_freeze(app->e_box);
    /* if required, fill head with empty items */
    for (; i < 0; i++, j++)
        _set_item_text(app, j, "");

    /* if required, fill tail with empty items */
    for (; last > n_items; last--, last_evas--)
        _set_item_text(app, last_evas - 1, "");

    itr = evas_list_nth_list(app->items, i);
    for (; i < last; i++, j++, itr = evas_list_next(itr)) {
        char *text;

        text = evas_list_data(itr);
        _set_item_text(app, j, text);
    }
    e_box_thaw(app->e_box);

    /* dim arrows */
    p = ((float)(app->current + 1)) / ((float)n_items);
    c = 255 * p;
    evas_object_color_set(app->arrow_up, c, c, c, c);

    p = (float)app->current / ((float)n_items);
    c = 255 * (1.0 - p);
    evas_object_color_set(app->arrow_down, c, c, c, c);
}

static void
destroy_gui_list(app_t *app)
{
    if (!app->evas_items)
        return;

    e_box_freeze(app->e_box);
    while (app->n_evas_items > 0) {
        Evas_Object *obj;

        app->n_evas_items--;

        obj = app->evas_items[app->n_evas_items];

        e_box_unpack(obj);
        evas_object_del(obj);
    }
    e_box_thaw(app->e_box);

    free(app->evas_items);
    app->evas_items = NULL;
}

static void
setup_gui_list(app_t *app)
{
    Evas_Object *obj;
    int item_w, item_h, box_w, box_h, i, n_items;

    destroy_gui_list(app);

    obj = _new_list_item(app, NULL);
    edje_object_size_min_calc(obj, &item_w, &item_h);
    evas_object_del(obj);

    e_box_freeze(app->e_box);
    evas_object_geometry_get(app->e_box, NULL, NULL, &box_w, &box_h);

    n_items = box_h / item_h + 1;

    app->n_evas_items = n_items;
    app->evas_items = malloc(n_items * sizeof(Evas_Object *));
    for (i = 0; i < n_items; i++) {
        Evas_Object *obj;

        obj = _new_list_item(app, "");
        app->evas_items[i] = obj;
        e_box_pack_end(app->e_box, obj);
        edje_object_size_min_calc(obj, &item_w, &item_h);
        e_box_pack_options_set(obj, 1, 1, 1, 0, 0.0, 0.5,
                               item_w, item_h, 9999, item_h);
        evas_object_show(obj);
    }

    e_box_align_set(app->e_box, 0.0, 1.0);

    app->arrow_down = edje_object_part_object_get(app->edje_main,
                                                  "arrow_down");
    app->arrow_up = edje_object_part_object_get(app->edje_main,
                                                "arrow_up");

    fill_gui_list(app);
    e_box_thaw(app->e_box);
}

static void
select_item(app_t *app,
            int index)
{
    if (index < 0 || index >= evas_list_count(app->items))
        return;

    app->current = index;
    fill_gui_list(app);
}

static int
scroll(void *data)
{
    app_t *app = data;
    double amount, d;

    e_box_align_get(app->e_box, NULL, &d);

    amount = app->scroll.stop_align - d;
    if (amount < 0)
        amount = -amount;

    if (amount < 0.0001) {
        e_box_align_set(app->e_box, 0.0, app->scroll.stop_align);
        if (app->scroll.stop_cb)
            app->scroll.stop_cb(data);

        app->scroll.timer = NULL;
        return 0;
    } else {
        e_box_align_set(app->e_box, 0.0, d + app->scroll.step_align);
        return 1;
    }
}

static void
move_down_done(void *data)
{
    app_t *app = data;

    e_box_freeze(app->e_box);
    select_item(app, app->current);
    e_box_align_set(app->e_box, 0.0, 1.0);
    e_box_thaw(app->e_box);
}

static void
move_down(app_t *app)
{
    if (app->current + 1 >= evas_list_count(app->items) || app->scroll.timer)
        return;

    app->current++;
    app->scroll.start_align = 1.0;
    app->scroll.stop_align = 0.0;
    app->scroll.step_align = -0.1;
    app->scroll.stop_cb = move_down_done;
    app->scroll.timer = ecore_timer_add(1.0/30.0, scroll, app);
}

static void
move_up_done(void *data)
{
    app_t *app = data;

    e_box_align_set(app->e_box, 0.0, 1.0);
}

static void
move_up(app_t *app)
{
    if (app->current < 1 || app->scroll.timer)
        return;

    app->current--;
    select_item(app, app->current);
    e_box_align_set(app->e_box, 0.0, 0.0);
    app->scroll.start_align = 0.0;
    app->scroll.stop_align = 1.0;
    app->scroll.step_align = 0.1;
    app->scroll.stop_cb = move_up_done;
    app->scroll.timer = ecore_timer_add(1.0/30.0, scroll, app);
}

static void
key_down(void *data, Evas *e, Evas_Object *obj, void *event_info)
{
    Evas_Event_Key_Down *ev;
    app_t *app;
    const char *k;

    ev = (Evas_Event_Key_Down *)event_info;
    app = (app_t *)data;

    k = ev->keyname;

    if (eq(k, "Down"))
        move_down(app);
    else if (eq(k, "Up"))
        move_up(app);
    else if (eq(k, "Escape"))
        ecore_main_loop_quit();
    else if (eq(k, "f")) {
        if (ecore_evas_fullscreen_get(app->ee)) {
            ecore_evas_fullscreen_set(app->ee, 0);
            ecore_evas_cursor_set(app->ee, NULL, 0, 0, 0);
        } else {
            ecore_evas_fullscreen_set(app->ee, 1);
            ecore_evas_cursor_set(app->ee, " ", 999, 0, 0);
        }
    }
}

static int
app_signal_exit(void *data, int type, void *event)
{

    ecore_main_loop_quit();
    return 1;
}

static void
resize_cb(Ecore_Evas *ee)
{
    app_t *app;
    Evas_Coord w, h;

    app = ecore_evas_data_get(ee, "app");
    evas_output_viewport_get(app->evas, NULL, NULL, &w, &h);
    evas_object_resize(app->edje_main, w, h);
    setup_gui_list(app);
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    edje_frametime_set(1.0 / 30.0);

    memset(&app, 0, sizeof(app));

    app.ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
    ecore_evas_data_set(app.ee, "app", &app);
    ecore_evas_title_set(app.ee, TITLE);
    ecore_evas_name_class_set(app.ee, WM_NAME, WM_CLASS);

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            ecore_evas_fullscreen_set(app.ee, 1);
        else if (argv[i][0] != '-')
            app.infile = argv[i];

    app.evas = ecore_evas_get(app.ee);

    app.edje_main = edje_object_add(app.evas);
    evas_data_attach_set(app.evas, &app);
    if (!edje_object_file_set(app.edje_main, THEME, THEME_GROUP)) {
        fprintf(stderr, "Failed to load file \"%s\", part \"%s\".\n",
                THEME, THEME_GROUP);
        return 1;
    }


    evas_object_move(app.edje_main, 0, 0);
    evas_object_resize(app.edje_main, WIDTH, HEIGHT);

    app.e_box = e_box_add(app.evas);
    e_box_orientation_set(app.e_box, 0);
    e_box_homogenous_set(app.e_box, 0);
    e_box_align_set(app.e_box, 0.0, 0.5);

    edje_object_part_swallow(app.edje_main, "contents_swallow", app.e_box);

    evas_object_show(app.edje_main);
    evas_object_show(app.e_box);
    ecore_evas_show(app.ee);

    _populate(&app);
    setup_gui_list(&app);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_focus_set(app.edje_main, 1);

    ecore_main_loop_begin();

    return 0;
}
