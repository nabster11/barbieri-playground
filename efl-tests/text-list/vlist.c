#define _GNU_SOURCE
#include "vlist.h"
#include <Edje.h>
#include <Ecore.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h> /* XXXXX */
#include <stdarg.h>
#include <strings.h>
#include <assert.h>
#include <sys/time.h>

#define ITEM "list_item"
#define LABEL "label"
#define DATA_KEY "vlist_node"

#define F_PRECISION 0.00001
#define SELECTED_ITEM_OFFSET 1

static int _vlist_error = VLIST_ERROR_NONE;
static inline Evas_Smart *_vlist_get_smart(void);

struct scroll_param
{
    double y;
    vlist_scroll_dir_t dir;
    struct timeval t0;
    int y0;
    double v0;
    double accel;
    enum {
        STOP_NONE = 0,
        STOP_INIT = 1,
        STOP_CHECK = 2
    } stop;
};

struct priv
{
    Evas *evas;
    const char *theme;
    Evas_Coord item_h;
    Evas_List *contents;
    Evas_List *objs;
    Evas_List *selected_content;
    Evas_List *last_used_obj;
    Evas_Object *clip;
    struct {
        Evas_Coord x;
        Evas_Coord y;
        Evas_Coord w;
        Evas_Coord h;
    } geometry;
    struct {
        struct scroll_param param;
        struct {
            double speed;
            double accel;
        } init;
        Evas_Coord y_min;
        Evas_Coord y_max;
        Ecore_Animator *anim;
    } scroll;
};

struct item
{
    char *text;
    void *data;
    Evas_Object *obj;
    int flags;
};

#define DECL_PRIV(o)                                                    \
   struct priv *priv = evas_object_smart_data_get((o))
#define DECL_PRIV_SAFE(o)                                               \
   struct priv *priv = (o) ? evas_object_smart_data_get((o)) : NULL
#define DECL_SCROLL_PARAM(priv)                                          \
   struct scroll_param *scroll_param = &(priv)->scroll.param
#define DECL_SCROLL_PARAM_SAFE(priv)                                    \
   struct scroll_param *scroll_param = (priv) ? &(priv)->scroll.param : NULL

#define RETURN_IF_ZERO(v)                                               \
   do { if ((v) == 0) return; } while (0)
#define RETURN_IF_NULL(v)                                               \
   do { if ((v) == NULL) return; } while(0)
#define RETURN_VAL_IF_NULL(v, r)                                        \
   do { if ((v) == NULL) return (r); } while(0)

#ifndef _NDEBUG
static inline void
_dbg(const char *file, int line, const char *func, const char *fmt, ...)
{
    va_list ap;
    const char *f;

    f = rindex(file, '/');
    if (!f)
        f = file;

    fprintf(stderr, "%s:%d:%s() ", f, line, func);

    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);

    fputc('\n', stderr);
}
#else
static inline void
_dbg(const char *file, int line, const char *func, const char *fmt, ...)
{}
#endif
#define DBG(fmt, ...)                                                   \
   _dbg(__FILE__, __LINE__, __FUNCTION__, fmt, ## __VA_ARGS__)

static inline unsigned long
tv2ms(const struct timeval *tv)
{
    return tv->tv_sec * 1000 + tv->tv_usec / 1000;
}

static inline void
_freeze(struct priv *priv)
{
    Evas_List *itr;

    evas_event_freeze(priv->evas);
    for (itr = priv->objs; itr != NULL; itr = itr->next)
        edje_object_freeze(itr->data);
}

static inline void
_thaw(struct priv *priv)
{
    Evas_List *itr;

    for (itr = priv->objs; itr != NULL; itr = itr->next)
        edje_object_thaw(itr->data);

    evas_event_thaw(priv->evas);
}


static struct item *
_item_new(const char *text, void *data, int flags)
{
    struct item *item;

    item = malloc(sizeof(*item));
    item->data = data;
    item->obj = NULL;
    item->flags = flags;
    if (!text || *text == '\0')
        item->text = NULL;
    else {
        if (flags & VLIST_APPEND_SHARE)
            item->text = (char *)text;
        else
            item->text = strdup(text);
    }

    return item;
}

static void
_item_del(struct item *item)
{
    if (item->text && !(item->flags & VLIST_APPEND_SHARE))
        free(item->text);

    if (item->obj)
        evas_object_data_del(item->obj, DATA_KEY);

    free(item);
}

static inline void
_obj_content_node_del(Evas_Object *child)
{
    Evas_List *old;

    old = evas_object_data_del(child, DATA_KEY);
    if (old && old->data) {
        struct item *old_item = old->data;
        old_item->obj = NULL;
    }

    edje_object_part_text_set(child, LABEL, "");
}

static inline Evas_List *
_obj_content_node_get(Evas_Object *child)
{
    return evas_object_data_get(child, DATA_KEY);
}

static inline void
_obj_content_node_set(Evas_Object *child, Evas_List *node)
{
    edje_object_freeze(child);
    _obj_content_node_del(child);

    if (node) {
        struct item *item = node->data;

        edje_object_part_text_set(child, LABEL, item->text);
        item->obj = child;
    }

    evas_object_data_set(child, DATA_KEY, node);
    edje_object_thaw(child);
}

static inline int
_vlist_fill_objs(struct priv *priv, Evas_List *obj_itr, Evas_List *cont_itr)
{
    int i;

    i = 0;
    while (obj_itr && cont_itr) {
        priv->last_used_obj = obj_itr;
        _obj_content_node_set(obj_itr->data, cont_itr);

        obj_itr = obj_itr->next;
        cont_itr = cont_itr->next;
        i++;
    }

    return i;
}

static inline void
_vlist_fill_blanks(struct priv *priv)
{
    Evas_List *itr;

    for (itr = priv->last_used_obj; itr != NULL; itr = itr->next)
        _obj_content_node_set(itr->data, NULL);
}

static void
_vlist_recalc(struct priv *priv)
{
    Evas_List *obj_itr, *cont_itr;

    if (priv->last_used_obj) {
        obj_itr = priv->last_used_obj->next;
        cont_itr = _obj_content_node_get(priv->last_used_obj->data);
        if (cont_itr)
            cont_itr = cont_itr->next;
    } else {
        int i;

        obj_itr = priv->objs;
        for (i=0; i < SELECTED_ITEM_OFFSET && obj_itr; i++)
            obj_itr = obj_itr->next;

        cont_itr = priv->contents;
        priv->selected_content = priv->contents;
    }

    _vlist_fill_objs(priv, obj_itr, cont_itr);
}

static inline void
_vlist_update_objs_pos(struct priv *priv)
{
    Evas_List *itr;
    Evas_Coord x, y;

    x = priv->geometry.x;
    y = priv->geometry.y + priv->scroll.param.y;

    for (itr = priv->objs; itr != NULL; itr = itr->next) {
        Evas_Object *child;

        child = itr->data;
        evas_object_move(child, x, y);
        y += priv->item_h;
    }
}

static void
_vlist_scroll_end(struct priv *priv)
{
    DECL_SCROLL_PARAM(priv);

    priv->scroll.anim = NULL;
    scroll_param->stop = STOP_NONE;
    scroll_param->dir = VLIST_SCROLL_DIR_NONE;
    scroll_param->v0 = 0.0;
    scroll_param->accel = 0.0;
}

static inline void
_vlist_scroll_fix_stop(struct priv *priv, int y, const struct timeval now,
                       int t)
{
    DECL_SCROLL_PARAM(priv);
    int y1, idx;

    if (scroll_param->stop != STOP_INIT) {
        DBG("scroll.stop != STOP_INIT, %d", scroll_param->stop);
        return;
    }

    scroll_param->stop = STOP_CHECK;

    scroll_param->v0 += scroll_param->accel * t;
    scroll_param->t0 = now;
    scroll_param->y0 = y;

/*     idx = app->current; */
/*     if (scroll_param->dir == VLIST_SCROLL_DIR_DOWN) */
/*         do { */
/*             y1 = item_pos(app, idx); */
/*             idx++; */
/*         } while (y1 <= y); */
/*     else */
/*         do { */
/*             y1 = item_pos(app, idx); */
/*             idx--; */
/*         } while (y1 >= y); */

    if (y1 < priv->scroll.y_min)
        y1 = priv->scroll.y_min;

    if (y1 > priv->scroll.y_max)
        y1 = priv->scroll.y_max;

    if (y1 == y)
        _vlist_scroll_end(priv);
    else {
        double v2;

        v2 = scroll_param->v0 * scroll_param->v0;
        scroll_param->accel = -v2 / (2 * (y1 - y));
    }

    DBG("fix stop!");
}

/*
 * Promote last item to head, rotating downwards.
 *
 * Assumes:
 *  * items_over < evas_list_count(priv->objs)
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_down(struct priv *priv, int items_over)
{
    Evas_List *last, *cont_itr;
    int i;

    DBG("BEG items_over=%d", items_over);

    last = evas_list_last(priv->objs);
    cont_itr = priv->selected_content;

    for (i = 0; cont_itr && i < SELECTED_ITEM_OFFSET + 1; i++)
        cont_itr = cont_itr->prev;

    for (; cont_itr && items_over > 0; items_over--) {
        Evas_List *tmp;

        _obj_content_node_set(last->data, cont_itr);

        if (priv->last_used_obj == last)
            priv->last_used_obj = last->prev;

        tmp = last->prev;
        priv->objs = evas_list_promote_list(priv->objs, last);
        last = tmp;

        cont_itr = cont_itr->prev;
        priv->selected_content = priv->selected_content->prev;
    }

    DBG("END items_over=%d", items_over);
    return items_over == 0;
}

/*
 * Remove head, append it's data, rotating upwards
 *
 * Assumes:
 *  * items_over < evas_list_count(priv->objs)
 *  * priv->last_used_obj != NULL
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_up(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;

    DBG("BEG items_over=%d", items_over);

    cont_itr = _obj_content_node_get(priv->last_used_obj->data);
    cont_itr = cont_itr->next;

    for (; priv->selected_content->next && items_over > 0; items_over--) {
        Evas_Object *child;

        if (priv->last_used_obj == priv->objs)
            priv->last_used_obj = NULL;

        child = priv->objs->data;
        priv->objs = evas_list_remove_list(priv->objs, priv->objs);
        priv->objs = evas_list_append(priv->objs, child);

        if (cont_itr) {
            _obj_content_node_set(child, cont_itr);
            cont_itr = cont_itr->next;
            priv->last_used_obj = evas_list_last(priv->objs);
        }

        priv->selected_content = priv->selected_content->next;
    }

    DBG("END items_over=%d", items_over);

    return items_over == 0;
}

static inline int
_vlist_scroll_fix_y_down_complete(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;
    int pages, page_size;

    DBG("BEG items_over=%d", items_over);

    page_size = evas_list_count(priv->objs);
    pages = items_over / page_size;
    items_over = items_over % page_size;

    /* go to first item to be used */
    cont_itr = _obj_content_node_get(priv->last_used_obj->data);
    for (; cont_itr && pages > 0; pages--) {
        int i;
        for (i = 0; cont_itr && i < page_size; i++)
            cont_itr = cont_itr->next;
    }

    items_over -= _vlist_fill_objs(priv, priv->objs, cont_itr);
    _vlist_fill_blanks(priv);

    DBG("END items_over=%d", items_over);

    return items_over == 0;
}

static inline int
_vlist_scroll_fix_y_up_complete(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;

    DBG("BEG items_over=%d", items_over);

    /* go to first item to be used */
    cont_itr = _obj_content_node_get(priv->objs->data);
    for (; cont_itr && items_over > 0; items_over--)
        cont_itr = cont_itr->prev;

    _vlist_fill_objs(priv, priv->objs, cont_itr);
    _vlist_fill_blanks(priv);

    DBG("END items_over=%d", items_over);

    return items_over == 0;
}

static inline int
_vlist_scroll_fix_y(struct priv *priv, double *py)
{
    DECL_SCROLL_PARAM(priv);
    int items_over, y;

    DBG("y=%f", *py);

    y = (*py);

    items_over = y / priv->item_h;
    *py = y % priv->item_h;

    if (items_over < 0)
        items_over = -items_over;

    /* Check if to do rotation and how to do it */
    if (items_over > evas_list_count(priv->objs)) {
        if (scroll_param->dir == VLIST_SCROLL_DIR_DOWN)
            return _vlist_scroll_fix_y_down_complete(priv, items_over);
        else if (scroll_param->dir == VLIST_SCROLL_DIR_UP)
            return _vlist_scroll_fix_y_up_complete(priv, items_over);
    } else {
        if (scroll_param->dir == VLIST_SCROLL_DIR_DOWN)
            return _vlist_scroll_fix_y_down(priv, items_over);
        else if (scroll_param->dir == VLIST_SCROLL_DIR_UP)
            return _vlist_scroll_fix_y_up(priv, items_over);
    }

    DBG("SHOULD NOT REACH");
    return 0;
}

static int
_vlist_scroll(void *data)
{
    Evas_Object *o = (Evas_Object *)data;
    DECL_PRIV(o);
    DECL_SCROLL_PARAM(priv);
    struct timeval now, dif;
    int t, r, idx;
    double y, v;

    if (scroll_param->v0 < F_PRECISION &&
        scroll_param->v0 > -F_PRECISION &&
        scroll_param->accel < F_PRECISION &&
        scroll_param->accel > -F_PRECISION) {

        _vlist_scroll_end(priv);
        return 0;
    }

    gettimeofday(&now, NULL);
    timersub(&now, &scroll_param->t0, &dif);
    t = tv2ms(&dif);

    v = scroll_param->v0 + scroll_param->accel * t;
    y = scroll_param->y0 + scroll_param->v0 * t +
        scroll_param->accel * t * t / 2;

    /* bounds checking */
    if (y < priv->scroll.y_min || y > priv->scroll.y_max)
        r = _vlist_scroll_fix_y(priv, &y);
    else
        r = 1;

    /* check current item */
/*     idx = item_at_pos(app, y); */
/*     if (idx != app->current) { */
/*         app->current = idx; */
/*         //dim_arrows(app); */
/*     } */

    switch (scroll_param->stop) {
    case STOP_NONE:
        break;
    case STOP_INIT:
        _vlist_scroll_fix_stop(priv, y, now, t);
        break;
    case STOP_CHECK:
        if (scroll_param->dir * v < F_PRECISION) {
/*             y = item_pos(app, app->current); */
            r = 0;
        }
        break;
    }

    scroll_param->y = y;
    _vlist_update_objs_pos(priv);

    if (r == 0)
        _vlist_scroll_end(priv);

    return r;
}

/***********************************************************************
 * Public API
 **********************************************************************/
Evas_Object *
vlist_new(Evas *evas)
{
    Evas_Object *obj;

    _vlist_error = VLIST_ERROR_NONE;

    obj = evas_object_smart_add(evas, _vlist_get_smart());
    if (!evas_object_smart_data_get(obj)) {
        evas_object_del(obj);
        return NULL;
    }

    return obj;
}

int
vlist_error_get(void)
{
    return _vlist_error;
}

void
vlist_append(Evas_Object *o, const char *text, void *data, int flags)
{
    struct item *item;
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    item = _item_new(text, data, flags);
    RETURN_IF_NULL(item);

    priv->contents = evas_list_append(priv->contents, item);
    _vlist_recalc(priv);
}

void
vlist_scroll_start(Evas_Object *o, vlist_scroll_dir_t dir)
{
    DECL_PRIV_SAFE(o);
    DECL_SCROLL_PARAM_SAFE(priv);
    RETURN_IF_NULL(priv);

    if (dir >= 0)
        dir = VLIST_SCROLL_DIR_DOWN;
    else
        dir = VLIST_SCROLL_DIR_UP;

    scroll_param->dir = dir;

    gettimeofday(&scroll_param->t0, NULL);
    scroll_param->y0 = 0;
    scroll_param->v0 = dir * priv->scroll.init.speed;
    scroll_param->accel = dir * priv->scroll.init.accel;
    scroll_param->stop = STOP_NONE;

    DBG("dir=%d", dir);

    if (!priv->scroll.anim)
        priv->scroll.anim = ecore_animator_add(_vlist_scroll, o);
}

void
vlist_scroll_stop(Evas_Object *o, vlist_scroll_dir_t dir)
{
    DECL_PRIV_SAFE(o);
    DECL_SCROLL_PARAM_SAFE(priv);
    RETURN_IF_NULL(priv);

    DBG("dir=%d", dir);

    if (scroll_param->dir == dir)
        scroll_param->stop = STOP_INIT;
}

/***********************************************************************
 * Private API
 **********************************************************************/
static Evas_Object *
_edje_item_new(const struct priv *priv)
{
    Evas_Object *o;

    o = edje_object_add(priv->evas);
    edje_object_file_set(o, priv->theme, ITEM);

    return o;
}

static Evas_Object *
_vlist_child_new(Evas_Object *o)
{
    Evas_Object *child;
    DECL_PRIV(o);

    child = _edje_item_new(priv);
    edje_object_part_text_set(child, LABEL, "");
    evas_object_resize(child, priv->geometry.w, priv->item_h);
    evas_object_smart_member_add(child, o);
    evas_object_clip_set(child, priv->clip);
    evas_object_show(child);

    return child;
}

static void
_vlist_child_del(Evas_Object *child)
{
    evas_object_hide(child);

    _obj_content_node_del(child);
    evas_object_smart_member_del(child);
    evas_object_clip_unset(child);
    evas_object_del(child);
}

static int
_test_and_cache_edje(struct priv *priv)
{
    Evas_Object *tmp_obj;
    int r;

    tmp_obj = _edje_item_new(priv);

    r = edje_object_load_error_get(tmp_obj);
    if (r != EDJE_LOAD_ERROR_NONE) {
        priv->theme = NULL;
        _vlist_error = VLIST_ERROR_NO_EDJE;
    } else {
        edje_object_size_min_get(tmp_obj, NULL, &priv->item_h);
        if (priv->item_h < 1)
            _vlist_error = VLIST_ERROR_NO_ITEM_SIZE;
    }
    evas_object_del(tmp_obj);

    return (priv->theme && priv->item_h > 0);
}

static void
_vlist_add(Evas_Object *o)
{
    struct priv *priv;

    priv = calloc(1, sizeof(*priv));
    RETURN_IF_NULL(priv);

    priv->evas = evas_object_evas_get(o);
    priv->theme = evas_object_data_get(o, "edje_file");

    if (!priv->theme) {
        Evas_Hash *hash;

        hash = evas_data_attach_get(priv->evas);
        priv->theme = evas_hash_find(hash, "edje_file");
    }

    if (!priv->theme) {
        free(priv);
        return;
    }

    if (!_test_and_cache_edje(priv)) {
        free(priv);
        return;
    }

    priv->clip = evas_object_rectangle_add(priv->evas);
    evas_object_smart_member_add(priv->clip, o);
    evas_object_color_set(priv->clip, 255, 255, 255, 255);

    priv->scroll.y_min = -priv->item_h;
    priv->scroll.y_max = priv->item_h;
    priv->scroll.init.speed = 0.2;
    priv->scroll.init.accel = 0.0001;

    evas_object_smart_data_set(o, priv);
}

static void
_vlist_del(Evas_Object *o)
{
    Evas_List *itr;
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    _freeze(priv);

    itr = priv->contents;
    while (itr) {
        struct item *item;

        item = itr->data;
        _item_del(item);

        itr = evas_list_remove_list(itr, itr);
    }

    itr = priv->objs;
    while (itr) {
        Evas_Object *child;

        child = itr->data;
        _vlist_child_del(child);

        itr = evas_list_remove_list(itr, itr);
    }

    evas_object_del(priv->clip);

    _thaw(priv);

    free(priv);
}

static void
_vlist_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    DECL_PRIV(o);

    priv->geometry.x = x;
    priv->geometry.y = y;

    _freeze(priv);
    evas_object_move(priv->clip, x, y);
    _vlist_update_objs_pos(priv);
    _thaw(priv);
}

static void
_vlist_resize(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    Evas_List *itr;
    int y, n_items;
    DECL_PRIV(o);

    n_items = h / priv->item_h;
    h = n_items * priv->item_h; /* just show full items */

    if (priv->geometry.w == w && priv->geometry.h == h)
        return;

    _freeze(priv);

    priv->geometry.w = w;
    priv->geometry.h = h;
    evas_object_resize(priv->clip, w, h);

    n_items += 2; /* spare items before and after visible area */

    /* If shrink, remove extra objects */
    while (n_items < evas_list_count(priv->objs)) {
        Evas_List *n;

        n = evas_list_last(priv->objs);
        _vlist_child_del(n->data);

        if (priv->last_used_obj == n)
            priv->last_used_obj = n->prev;

        priv->objs = evas_list_remove_list(priv->objs, n);
    }

    /* Resize existing objects */
    for (itr = priv->objs; itr != NULL; itr = itr->next)
        evas_object_resize(itr->data, w, priv->item_h);

    y = priv->geometry.y + priv->scroll.param.y +
        evas_list_count(priv->objs) * priv->item_h;

    /* If grow, create new objects */
    if (n_items > evas_list_count(priv->objs)) {
        while (n_items > evas_list_count(priv->objs)) {
            Evas_Object *child;

            child = _vlist_child_new(o); /* size is automatic */
            evas_object_move(child, priv->geometry.x, y);

            y += priv->item_h;
            priv->objs = evas_list_append(priv->objs, child);
        }
        _vlist_recalc(priv);
    }

    _thaw(priv);
}

static void
_vlist_show(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_show(priv->clip);
}

static void
_vlist_hide(Evas_Object *o)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv); /* in case that _vlist_add failed */

    evas_object_hide(priv->clip);
}

static void
_vlist_color_set(Evas_Object *o, int r, int g, int b, int a)
{
    DECL_PRIV(o);

    evas_object_color_set(priv->clip, r, g, b, a);
}

static void
_vlist_clip_set(Evas_Object *o, Evas_Object *clip)
{
    DECL_PRIV(o);

    evas_object_clip_set(priv->clip, clip);
}

static void
_vlist_clip_unset(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_clip_unset(priv->clip);
}

static inline Evas_Smart *
_vlist_get_smart(void)
{
    static Evas_Smart *smart = NULL;

    if (!smart) {
        smart = evas_smart_new("vlist",
                               _vlist_add,
                               _vlist_del,
                               NULL, /* layer_set */
                               NULL, /* raise */
                               NULL, /* lower */
                               NULL, /* stack_above */
                               NULL, /* stack_below */
                               _vlist_move,
                               _vlist_resize,
                               _vlist_show,
                               _vlist_hide,
                               _vlist_color_set,
                               _vlist_clip_set,
                               _vlist_clip_unset,
                               NULL /* data */
            );
    }

    return smart;
}
