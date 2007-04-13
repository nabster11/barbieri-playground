#ifndef __VLIST_H__
#define __VLIST_H__

#include <Evas.h>

#define VLIST_APPEND_NONE  0
#define VLIST_APPEND_SHARE 1 /* share text, don't duplicate it */

typedef struct _Evas_List vlist_item_handle_t;

enum
{
    VLIST_ERROR_NONE = 0,
    VLIST_ERROR_NO_EDJE,
    VLIST_ERROR_NO_ITEM_SIZE
};

typedef enum
{
    VLIST_SCROLL_DIR_UP = -1,
    VLIST_SCROLL_DIR_NONE = 0,
    VLIST_SCROLL_DIR_DOWN = 1
} vlist_scroll_dir_t;

typedef void (*vlist_selection_changed_cb_t)(Evas_Object *o, const char *text, void *item_data, int index, void *user_data);

Evas_Object *vlist_new(Evas *evas);
void vlist_append(Evas_Object *o, const char *text, void *data, int flags);
int  vlist_error_get(void);
void vlist_scroll_start(Evas_Object *o, vlist_scroll_dir_t dir);
void vlist_scroll_stop(Evas_Object *o, vlist_scroll_dir_t dir);
int  vlist_count(Evas_Object *o);
void vlist_selected_content_get(Evas_Object *o, const char **text, void **item_data, int *index);
void vlist_connect_selection_changed(Evas_Object *o, vlist_selection_changed_cb_t func, void *user_data);

#endif /* __VLIST_H__ */
