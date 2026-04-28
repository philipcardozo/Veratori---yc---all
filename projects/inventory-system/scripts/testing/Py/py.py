# Tracks per-image metrics and overlays a bottom-left panel (TP/FP/FN, mean conf, mean IoU)
import os, glob, cv2, numpy as np
from ultralytics import YOLO

def load_yolo_labels(lbl_path, img_w, img_h):
    if not os.path.isfile(lbl_path): return np.zeros((0,6),dtype=float)  # [cls,x1,y1,x2,y2,1.0]
    rows=[]
    with open(lbl_path,'r') as f:
        for ln in f:
            a=ln.strip().split()
            if len(a)<5: continue
            c=float(a[0]); x,y,w,h=map(float,a[1:5])
            x1=(x-w/2)*img_w; y1=(y-h/2)*img_h; x2=(x+w/2)*img_w; y2=(y+h/2)*img_h
            rows.append([c,x1,y1,x2,y2,1.0])
    return np.array(rows,dtype=float)

def iou_matrix(boxes1, boxes2):
    # boxes: [N,4] xyxy
    if len(boxes1)==0 or len(boxes2)==0: return np.zeros((len(boxes1),len(boxes2)))
    x11,y11,x12,y12=np.split(boxes1,4,axis=1); x21,y21,x22,y22=np.split(boxes2,4,axis=1)
    xi1=np.maximum(x11,x21.T); yi1=np.maximum(y11,y21.T); xi2=np.minimum(x12,x22.T); yi2=np.minimum(y12,y22.T)
    inter=np.clip(xi2-xi1,0,None)*np.clip(yi2-yi1,0,None)
    a1=(x12-x11)*(y12-y11); a2=(x22-x21)*(y22-y21)
    return inter/(a1+a2.T-inter+1e-9)

def match_preds_to_gts(p_cls, p_xyxy, g_cls, g_xyxy, iou_thr=0.5):
    M=iou_matrix(p_xyxy,g_xyxy)
    used_g=set(); TP,IoUs=[],[]
    for i in np.argsort(-p_cls.size) if len(p_cls)>0 else []:  # arbitrary stable order
        # best gt by IoU with same class
        j=np.argmax(M[i]) if M.shape[1]>0 else -1
        if j!=-1 and j not in used_g and M[i,j]>=iou_thr and int(p_cls[i])==int(g_cls[j]):
            TP.append((i,j)); IoUs.append(float(M[i,j])); used_g.add(j)
    tp=len(TP); fp=len(p_cls)-tp; fn=len(g_cls)-tp
    mean_iou=float(np.mean(IoUs)) if IoUs else 0.0
    return tp,fp,fn,mean_iou

def draw_bottom_left_panel(img, lines, pad=8, lh=18, font=cv2.FONT_HERSHEY_SIMPLEX, fs=0.5, th=1):
    h,w=img.shape[:2]
    tw=max(cv2.getTextSize(s,font,fs,th)[0][0] for s in lines)
    th_box=int(pad*2+lh*len(lines))
    cv2.rectangle(img,(0,h-th_box),(pad*2+tw,h),(0,0,0),-1)
    y=h-th_box+pad+lh-4
    for s in lines:
        cv2.putText(img,s,(pad,y),font,fs,(255,255,255),th,lineType=cv2.LINE_AA); y+=lh
    return img

# ---- CONFIG ----
model = YOLO('yolo11n.pt')  # or your trained weights path, e.g., 'runs/detect/train/weights/best.pt'
weights = getattr(model, 'ckpt_path', None) or 'runs/detect/train/weights/best.pt'
if os.path.exists(weights): model = YOLO(weights)
val_img_dir = '/content/dataset/images/val'
val_lbl_dir = '/content/dataset/labels/val'
save_dir = '/content/preds_metrics'; os.makedirs(save_dir, exist_ok=True)
names = model.names if hasattr(model,'names') else {}

# ---- RUN ----
img_paths=sorted([os.path.join(val_img_dir,f) for f in os.listdir(val_img_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.bmp','.tif','.tiff','.webp'))])
for ip in img_paths:
    img=cv2.imread(ip); h,w=img.shape[:2]
    lp=os.path.join(val_lbl_dir, os.path.splitext(os.path.basename(ip))[0]+'.txt')
    gts=load_yolo_labels(lp,w,h); g_cls=gts[:,0].astype(int); g_xyxy=gts[:,1:5]

    r=model.predict(source=ip, imgsz=640, conf=0.25, verbose=False)[0]
    p_xyxy=r.boxes.xyxy.cpu().numpy() if r.boxes is not None else np.zeros((0,4))
    p_cls=r.boxes.cls.cpu().numpy().astype(int) if r.boxes is not None else np.zeros((0,),dtype=int)
    p_conf=r.boxes.conf.cpu().numpy() if r.boxes is not None else np.zeros((0,),dtype=float)

    tp,fp,fn,miou=match_preds_to_gts(p_cls,p_xyxy,g_cls,g_xyxy,iou_thr=0.5)
    mean_conf=float(np.mean(p_conf)) if p_conf.size else 0.0

    # draw predictions (boxes + labels)
    for bb,cc,cf in zip(p_xyxy,p_cls,p_conf):
        x1,y1,x2,y2=bb.astype(int)
        cv2.rectangle(img,(x1,y1),(x2,y2),(255,255,255),2)
        lbl=(names.get(int(cc),str(int(cc))) if isinstance(names,dict) else str(int(cc)))+f" {cf:.2f}"
        cv2.putText(img,lbl,(x1,max(0,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2,cv2.LINE_AA)

    panel=[f"TP {tp}  FP {fp}  FN {fn}", f"mean conf {mean_conf:.2f}", f"mean IoU@0.5 {miou:.2f}"]
    img=draw_bottom_left_panel(img,panel)
    out=os.path.join(save_dir, os.path.basename(ip))
    cv2.imwrite(out,img)

print(f"Saved with metrics → {save_dir}")
