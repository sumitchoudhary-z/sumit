;;; TalkToCAD.lsp - Talk-To-CAD AutoCAD Plugin
;;; Final Year Project by Sumit Choudhary, SKIT Jaipur (2023-2027)
;;;
;;; HOW TO LOAD:
;;;   In AutoCAD type APPLOAD, select this file, click Load.
;;;   Add it to the Startup Suite if you want it in every drawing.
;;;
;;; COMMANDS ADDED INSIDE AUTOCAD:
;;;   TALKFLANGE - asks for OD, PCD, bore, hole dia, no. of holes, thickness.
;;;                Draws the 2D flange and (on request) builds a native
;;;                3D solid with CYLINDER + SUBTRACT, inside AutoCAD itself.
;;;   TALKPLATE  - asks for length, width, thickness, hole dia. Draws 2D plate.
;;;   TALKGEAR   - asks for outer dia, teeth, thickness, bore. Draws a
;;;                simplified gear outline (top view) as a closed polyline.
;;;   TALKSHAFT  - asks for diameter and length. Draws side + end view.
;;;
;;; All units are millimetres. All geometry is drawn at the origin.

(defun ttc:layer (name colour /)
  (if (not (tblsearch "LAYER" name))
    (command "_.-LAYER" "_Make" name "_Color" colour "" "")
    (command "_.-LAYER" "_Set" name "")
  )
)

(defun c:TALKFLANGE (/ od pcd bore hd n th make3d i ang pt main cutter)
  (setq od   (getreal "\nFlange outer diameter (mm) <100>: "))
  (if (null od) (setq od 100.0))
  (setq pcd  (getreal "\nPCD (mm) <80>: "))
  (if (null pcd) (setq pcd 80.0))
  (setq bore (getreal "\nCentre bore diameter (mm) <40>: "))
  (if (null bore) (setq bore 40.0))
  (setq hd   (getreal "\nBolt hole diameter (mm) <10>: "))
  (if (null hd) (setq hd 10.0))
  (setq n    (getint "\nNumber of bolt holes <6>: "))
  (if (null n) (setq n 6))
  (setq th   (getreal "\nThickness (mm) <12>: "))
  (if (null th) (setq th 12.0))
  ;; --- 2D drawing ---
  (ttc:layer "OUTLINE" 7)
  (command "_CIRCLE" "0,0" (/ od 2.0))
  (command "_CIRCLE" "0,0" (/ bore 2.0))
  (ttc:layer "PCD" 5)
  (command "_CIRCLE" "0,0" (/ pcd 2.0))
  (ttc:layer "HOLES" 1)
  (setq i 0)
  (while (< i n)
    (setq ang (* 2.0 pi (/ (float i) n)))
    (setq pt (list (* (/ pcd 2.0) (cos ang)) (* (/ pcd 2.0) (sin ang))))
    (command "_CIRCLE" pt (/ hd 2.0))
    (setq i (+ i 1))
  )
  (ttc:layer "CENTER" 3)
  (command "_LINE" (list (- 0 (+ (/ od 2.0) 10.0)) 0.0) (list (+ (/ od 2.0) 10.0) 0.0) "")
  (command "_LINE" (list 0.0 (- 0 (+ (/ od 2.0) 10.0))) (list 0.0 (+ (/ od 2.0) 10.0)) "")
  (command "_TEXT" (list 0.0 (- 0 (+ (/ od 2.0) 18.0))) 4.0 0.0
           (strcat "FLANGE OD " (rtos od 2 1) " PCD " (rtos pcd 2 1) " "
                   (itoa n) "x HOLE " (rtos hd 2 1) " BORE " (rtos bore 2 1)
                   " THK " (rtos th 2 1) " - TALK-TO-CAD"))
  ;; --- optional native 3D solid, built by AutoCAD itself ---
  (initget "Yes No")
  (setq make3d (getkword "\nBuild native 3D solid flange? [Yes/No] <No>: "))
  (if (= make3d "Yes")
    (progn
      (command "_CYLINDER" "0,0,0" (/ od 2.0) th)
      (setq main (entlast))
      (command "_CYLINDER" "0,0,0" (/ bore 2.0) th)
      (setq cutter (entlast))
      (command "_SUBTRACT" main "" cutter "")
      (setq main (entlast))
      (setq i 0)
      (while (< i n)
        (setq ang (* 2.0 pi (/ (float i) n)))
        (setq pt (list (* (/ pcd 2.0) (cos ang)) (* (/ pcd 2.0) (sin ang)) 0.0))
        (command "_CYLINDER" pt (/ hd 2.0) th)
        (setq cutter (entlast))
        (command "_SUBTRACT" main "" cutter "")
        (setq main (entlast))
        (setq i (+ i 1))
      )
      (princ "\nTalk-To-CAD: 3D solid flange created.")
    )
  )
  (princ)
)

(defun c:TALKPLATE (/ len wid th hd o x y)
  (setq len (getreal "\nPlate length (mm) <150>: "))
  (if (null len) (setq len 150.0))
  (setq wid (getreal "\nPlate width (mm) <100>: "))
  (if (null wid) (setq wid 100.0))
  (setq th  (getreal "\nPlate thickness (mm) <10>: "))
  (if (null th) (setq th 10.0))
  (setq hd  (getreal "\nCorner hole diameter (mm) <8>: "))
  (if (null hd) (setq hd 8.0))
  (setq o 15.0)
  (ttc:layer "OUTLINE" 7)
  (command "_RECTANG" (list (- 0 (/ len 2.0)) (- 0 (/ wid 2.0)))
                      (list (/ len 2.0) (/ wid 2.0)))
  (ttc:layer "HOLES" 1)
  (foreach x (list (- (/ len 2.0) o) (- o (/ len 2.0)))
    (foreach y (list (- (/ wid 2.0) o) (- o (/ wid 2.0)))
      (command "_CIRCLE" (list x y) (/ hd 2.0))
    )
  )
  (command "_TEXT" (list (- 0 (/ len 2.0)) (- 0 (+ (/ wid 2.0) 12.0))) 4.0 0.0
           (strcat "PLATE " (rtos len 2 1) " x " (rtos wid 2 1) " x "
                   (rtos th 2 1) " THK - TALK-TO-CAD"))
  (princ)
)

(defun c:TALKGEAR (/ od teeth th bore root i ang r pt pts)
  (setq od (getreal "\nGear outer diameter (mm) <80>: "))
  (if (null od) (setq od 80.0))
  (setq teeth (getint "\nNumber of teeth <24>: "))
  (if (null teeth) (setq teeth 24))
  (setq th (getreal "\nGear thickness (mm) <12>: "))
  (if (null th) (setq th 12.0))
  (setq bore (getreal "\nBore diameter (mm) <20>: "))
  (if (null bore) (setq bore 20.0))
  (setq root (* (/ od 2.0) 0.88))
  (setq pts nil)
  (setq i 0)
  (while (< i (* teeth 4))
    (if (or (= (rem i 4) 1) (= (rem i 4) 2))
      (setq r (/ od 2.0))
      (setq r root)
    )
    (setq ang (* 2.0 pi (/ (float i) (* teeth 4.0))))
    (setq pt (list (* r (cos ang)) (* r (sin ang)) 0.0))
    (setq pts (append pts (list pt)))
    (setq i (+ i 1))
  )
  (entmake
    (append
      (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 100 "AcDbPolyline")
            (cons 90 (length pts)) (cons 70 1))
      (mapcar (function (lambda (p) (cons 10 (list (car p) (cadr p))))) pts)
    )
  )
  (ttc:layer "HOLES" 1)
  (command "_CIRCLE" "0,0" (/ bore 2.0))
  (command "_TEXT" (list 0.0 (- 0 (+ (/ od 2.0) 14.0))) 4.0 0.0
           (strcat "GEAR OD " (rtos od 2 1) " TEETH " (itoa teeth)
                   " BORE " (rtos bore 2 1) " THK " (rtos th 2 1) " - TALK-TO-CAD"))
  (princ)
)

(defun c:TALKSHAFT (/ d len)
  (setq d (getreal "\nShaft diameter (mm) <30>: "))
  (if (null d) (setq d 30.0))
  (setq len (getreal "\nShaft length (mm) <200>: "))
  (if (null len) (setq len 200.0))
  (ttc:layer "OUTLINE" 7)
  (command "_RECTANG" (list (- 0 (/ len 2.0)) (- 0 (/ d 2.0)))
                      (list (/ len 2.0) (/ d 2.0)))
  (command "_CIRCLE" (list (+ (/ len 2.0) d) 0.0) (/ d 2.0))
  (ttc:layer "CENTER" 3)
  (command "_LINE" (list (- 0 (+ (/ len 2.0) 10.0)) 0.0) (list (+ (/ len 2.0) 10.0) 0.0) "")
  (command "_TEXT" (list (- 0 (/ len 2.0)) (- 0 (+ (/ d 2.0) 14.0))) 4.0 0.0
           (strcat "SHAFT DIA " (rtos d 2 1) " LENGTH " (rtos len 2 1) " - TALK-TO-CAD"))
  (princ)
)

(princ "\nTalk-To-CAD loaded. Commands: TALKFLANGE, TALKPLATE, TALKGEAR, TALKSHAFT")
(princ)
