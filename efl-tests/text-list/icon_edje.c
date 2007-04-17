#include "icon.h"
#include <Edje.h>
#include <stdlib.h>
#include <stdio.h> /* XXXXX */

#define LABEL "label"
#define IMAGE "image"

static inline Evas_Smart *_icon_get_smart(void);

struct priv
{
    Evas_Object *edje;
    Evas_Object *image;
};

#define DECL_PRIV(o) struct priv *priv = evas_object_smart_data_get((o))
#define RETURN_IF_ZERO(v) do { if ((v) == 0) return; } while (0)

/***********************************************************************
 * Public API
 **********************************************************************/
Evas_Object *
icon_new(Evas *evas)
{
    Evas_Object *obj;

    obj = evas_object_smart_add(evas, _icon_get_smart());

    return obj;
}

static void
_image_recalc_size(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    Evas_Coord x, y, iw, ih, nw, nh;
    DECL_PRIV(o);
    double pw, ph, p;

    RETURN_IF_ZERO(w);
    RETURN_IF_ZERO(h);

    evas_object_image_size_get(priv->image, &iw, &ih);
    RETURN_IF_ZERO(iw);
    RETURN_IF_ZERO(ih);

    pw = (double)w / (double)iw;
    ph = (double)h / (double)ih;

    p = pw;
    if (p > ph)
        p = ph;

    nw = iw * p;
    nh = ih * p;
    x = (w - nw) / 2;
    y = (h - nh) / 2;

    edje_extern_object_aspect_set(priv->image, EDJE_ASPECT_CONTROL_BOTH,
                                  nw, nh);
    evas_object_image_fill_set(priv->image, 0, 0, nw, nh);
}

void
icon_image_set(Evas_Object *o, const char *path)
{
    Evas_Coord w, h;
    DECL_PRIV(o);

    edje_object_freeze(priv->edje);

    evas_object_image_file_set(priv->image, path, NULL);

    edje_object_part_geometry_get(priv->edje, IMAGE, NULL, NULL, &w, &h);
    _image_recalc_size(o, w, h);

    edje_object_thaw(priv->edje);
}

void
icon_text_set(Evas_Object *o, const char *text)
{
    DECL_PRIV(o);

    edje_object_part_text_set(priv->edje, LABEL, text);
}



/***********************************************************************
 * Private API
 **********************************************************************/
static void
_icon_add(Evas_Object *o)
{
    struct priv *priv;
    Evas *evas;
    const char *theme;
    int w, h;

    priv = calloc(1, sizeof(*priv));
    if (!priv)
        return;

    evas_object_smart_data_set(o, priv);
    evas = evas_object_evas_get(o);
    theme = evas_object_data_get(o, "edje_file");

    if (!theme)
        theme = evas_hash_find(evas_data_attach_get(evas), "edje_file");

    if (!theme) {
        fprintf(stderr, "No edje_file found on evas or icon_edje object.\n");
        return;
    }

    priv->edje = edje_object_add(evas);
    edje_object_file_set(priv->edje, theme, "icon_edje");
    edje_object_size_min_get(priv->edje, &w, &h);
    evas_object_resize(priv->edje, w, h);
    evas_object_resize(o, w, h);

    priv->image = evas_object_image_add(evas_object_evas_get(o));
    edje_object_part_swallow(priv->edje, IMAGE, priv->image);
}

static void
_icon_del(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_del(priv->image);
    evas_object_del(priv->edje);
    free(priv);
}

static void
_icon_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    DECL_PRIV(o);

    evas_object_move(priv->edje, x, y);
}

static void
_icon_resize(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    DECL_PRIV(o);

    edje_object_freeze(priv->edje);

    evas_object_resize(priv->edje, w, h);
    _image_recalc_size(o, w, h);

    edje_object_thaw(priv->edje);
}

static void
_icon_show(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_show(priv->edje);
}

static void
_icon_hide(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_hide(priv->edje);
}

static inline Evas_Smart *
_icon_get_smart(void)
{
    static Evas_Smart *smart = NULL;

    if (!smart) {
        smart = evas_smart_new("icon_edje",
                               _icon_add,
                               _icon_del,
                               NULL, /* layer_set */
                               NULL, /* raise */
                               NULL, /* lower */
                               NULL, /* stack_above */
                               NULL, /* stack_below */
                               _icon_move,
                               _icon_resize,
                               _icon_show,
                               _icon_hide,
                               NULL, /* color_set */
                               NULL, /* clip_set */
                               NULL, /* clip_unset */
                               NULL /* data */
            );
    }

    return smart;
}
