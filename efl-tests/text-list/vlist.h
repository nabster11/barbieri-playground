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

Evas_Object *vlist_new(Evas *evas);
void vlist_append(Evas_Object *o, const char *text, void *data, int flags);
int vlist_error_get(void);

#endif /* __VLIST_H__ */
