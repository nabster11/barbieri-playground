;;; edje-mode-el -- Major mode for editing Edje files

;; Author: Gustavo Sverzut Barbieri <barbieri@gmail.com>
;; Created: 2007-07-23
;; Keywords: Edje major-mode

;; Copyright (C) 2007 Gustavo Sverzut Barbieri <barbieri@gmail.com>

;; This program is free software; you can redistribute it and/or
;; modify it under the terms of the GNU General Public License as
;; published by the Free Software Foundation; either version 2 of
;; the License, or (at your option) any later version.

;; This program is distributed in the hope that it will be
;; useful, but WITHOUT ANY WARRANTY; without even the implied
;; warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
;; PURPOSE.  See the GNU General Public License for more details.

;; You should have received a copy of the GNU General Public
;; License along with this program; if not, write to the Free
;; Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
;; MA 02111-1307 USA

;;; Commentary:
;;
;; This mode is based on tutorial from Scott Andrew Borton:
;; http://two-wugs.net/emacs/mode-tutorial.html


(defvar edje-mode-hook nil)

(defvar edje-mode-map
  (let ((edje-mode-map (make-sparse-keymap)))
    (define-key edje-mode-map "\C-j" 'newline-and-indent)
    edje-mode-map)
  "Keymap for Edje major mode")


(add-to-list 'auto-mode-alist '("\\.edc$" . edje-mode))

(defconst edje-font-lock-keywords-1
  (eval-when-compile
    (list
     (list (concat "\\<" (regexp-opt '("action"
                                       "after"
                                       "alias"
                                       "align"
                                       "angle"
                                       "aspect"
                                       "aspect_preference"
                                       "base"
                                       "border"
                                       "clip_to"
                                       "collections"
                                       "color"
                                       "color2"
                                       "color3"
                                       "color_class"
                                       "color_classes"
                                       "confine"
                                       "data"
                                       "description"
                                       "dragable"
                                       "effect"
                                       "elipsis"
                                       "events"
                                       "fill"
                                       "fit"
                                       "fixed"
                                       "font"
                                       "fonts"
                                       "gradient"
                                       "group"
                                       "image"
                                       "images"
                                       "in"
                                       "inherit"
                                       "item"
                                       "max"
                                       "middle"
                                       "min"
                                       "mouse_events"
                                       "name"
                                       "normal"
                                       "offset"
                                       "origin"
                                       "part"
                                       "parts"
                                       "pointer_mode"
                                       "precise_is_inside"
                                       "program"
                                       "programs"
                                       "rel1"
                                       "rel2"
                                       "relative"
                                       "repeat_events"
                                       "signal"
                                       "size"
                                       "smooth"
                                       "source"
                                       "spectra"
                                       "spectrum"
                                       "spread"
                                       "state"
                                       "step"
                                       "style"
                                       "styles"
                                       "tag"
                                       "target"
                                       "text"
                                       "text_class"
                                       "text_source"
                                       "to"
                                       "to_x"
                                       "to_y"
                                       "transition"
                                       "tween"
                                       "type"
                                       "use_alternate_font_metrics"
                                       "visible"
                                       "x"
                                       "y") t) "\\>")
           '(1 font-lock-keyword-face))

     ))
  "Expressions to highlight")

(defconst edje-font-lock-keywords-2
  (eval-when-compile
    (append edje-font-lock-keywords-1
            (list
             (list
              (concat "\\<"
                      (regexp-opt
                       '(; image options (st_images_image)
                         "RAW"
                         "COMP"
                         "LOSSY"
                         "USER"
                         ; part types (st_collections_group_parts_part_type)
                         "NONE"
                         "RECT"
                         "TEXT"
                         "IMAGE"
                         "SWALLOW"
                         "TEXTBLOCK"
                         "GRADIENT"
                         "GROUP"
                         ; pointer mode (st_collections_group_parts_part_pointer_mode)
                         "AUTOGRAB"
                         "NOGRAB"
                         ; aspect (st_collections_group_parts_part_description_aspect_preference)
                         "NONE"
                         "VERTICAL"
                         "HORIZONTAL"
                         "BOTH"
                         ; text effect (st_collections_group_parts_part_effect)
                         "NONE"
                         "PLAIN"
                         "OUTLINE"
                         "SOFT_OUTLINE"
                         "SHADOW"
                         "SOFT_SHADOW"
                         "OUTLINE_SHADOW"
                         "OUTLINE_SOFT_SHADOW"
                         "FAR_SHADOW"
                         "FAR_SOFT_SHADOW"
                         "GLOW"
                         ; image fill (st_collections_group_parts_part_description_fill_type)
                         "SCALE"
                         "TILE"
                                        ; program action (st_collections_group_programs_program_action)
                         "STATE_SET"
                         "ACTION_STOP"
                         "SIGNAL_EMIT"
                         "DRAG_VAL_SET"
                         "DRAG_VAL_STEP"
                         "DRAG_VAL_PAGE"
                         "SCRIPT"
                         ; program transition (st_collections_group_programs_program_transition)
                         "LINEAR"
                         "SINUSOIDAL"
                         "ACCELERATE"
                         "DECELERATE"
                         ) t) "\\>")
              '(1 font-lock-builtin-face))
             )))
  "Enumerate values")

(defvar edje-font-lock-keywords edje-font-lock-keywords-2)

(define-derived-mode edje-mode c-mode "Edje"
  "Major mode for editing Edje files"
  (interactive)
  (use-local-map edje-mode-map)
  (set (make-local-variable 'font-lock-defaults) '(edje-font-lock-keywords))
  (set (make-local-variable 'require-final-newline) t)
  (run-hooks 'edje-mode-hook)
  )

(provide 'edje-mode)

;;; edje-mode.el ends here
