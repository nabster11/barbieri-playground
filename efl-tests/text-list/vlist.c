#include "vlist.h"
#include <Edje.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h> /* XXXXX */
#include <stdarg.h>
#include <strings.h>
#include <assert.h>

#define ITEM "list_item"
#define LABEL "label"
#define DATA_KEY "vlist_node"

static int _vlist_error = VLIST_ERROR_NONE;
static inline Evas_Smart *_vlist_get_smart(void);

struct priv
{
    Evas *evas;
    const char *theme;
    Evas_Coord item_h;
    Evas_List *contents;
    Evas_List *objs;
    Evas_List *last_used_obj;
    Evas_Object *clip;
    struct {
        Evas_Coord x;
        Evas_Coord y;
        Evas_Coord w;
        Evas_Coord h;
    } geometry;
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

static inline void
_freeze(Evas_Object *o)
{
    Evas_List *itr;
    DECL_PRIV(o);

    evas_event_freeze(priv->evas);
    for (itr = priv->objs; itr != NULL; itr = itr->next)
        edje_object_freeze(itr->data);
}

static inline void
_thaw(Evas_Object *o)
{
    Evas_List *itr;
    DECL_PRIV(o);

    for (itr = priv->objs; itr != NULL; itr = itr->next)
        edje_object_thaw(itr->data);

    evas_event_thaw(priv->evas);
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

static void
_vlist_recalc(Evas_Object *o)
{
    Evas_List *obj_itr, *cont_itr;
    DECL_PRIV(o);

    if (priv->last_used_obj) {
        obj_itr = priv->last_used_obj->next;
        cont_itr = _obj_content_node_get(priv->last_used_obj->data);
        if (cont_itr)
            cont_itr = cont_itr->next;
    } else {
        obj_itr = priv->objs;
        cont_itr = priv->contents;
    }

    _freeze(o);
    while (obj_itr && cont_itr) {
        priv->last_used_obj = obj_itr;
        _obj_content_node_set(obj_itr->data, cont_itr);

        obj_itr = obj_itr->next;
        cont_itr = cont_itr->next;
    }
    _thaw(o);
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
    _vlist_recalc(o);
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

    evas_object_smart_data_set(o, priv);
}

static void
_vlist_del(Evas_Object *o)
{
    Evas_List *itr;
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    _freeze(o);

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

    _thaw(o);

    free(priv);
}

static void
_vlist_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    DECL_PRIV(o);
    Evas_List *itr;
    Evas_Coord dx, dy;

    dx = x - priv->geometry.x;
    dy = y - priv->geometry.y;

    priv->geometry.x = x;
    priv->geometry.y = y;

    _freeze(o);

    evas_object_move(priv->clip, x, y);

    for (itr = priv->objs; itr != NULL; itr = itr->next) {
        Evas_Object *child;
        Evas_Coord cx, cy;

        child = itr->data;
        evas_object_geometry_get(child, &cx, &cy, NULL, NULL);
        evas_object_move(child, cx + dx, cy + dy);
    }

    _thaw(o);
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

    _freeze(o);

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

    y = priv->geometry.y + evas_list_count(priv->objs) * priv->item_h;

    /* If grow, create new objects */
    if (n_items > evas_list_count(priv->objs)) {
        while (n_items > evas_list_count(priv->objs)) {
            Evas_Object *child;

            child = _vlist_child_new(o); /* size is automatic */
            evas_object_move(child, priv->geometry.x, y);

            y += priv->item_h;
            priv->objs = evas_list_append(priv->objs, child);
        }

        _vlist_recalc(o);
    }

    _thaw(o);
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
