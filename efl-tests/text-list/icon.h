#ifndef __ICON_H__
#define __ICON_H__

#include <Evas.h>

Evas_Object *icon_new(Evas *evas);
void icon_image_set(Evas_Object *o, const char *path);
void icon_text_set(Evas_Object *o, const char *text);

#endif /* __ICON_H__ */
