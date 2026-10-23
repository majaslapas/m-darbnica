import os
import cv2, numpy as np, sys
SRC=os.environ.get('MD_FACADE', 'facade.webp')  # the client's facade photo
W=os.environ.get('MD_WORK', 'work/ear/')
img=cv2.imread(SRC)  # opencv may not read webp? check
if img is None:
    from PIL import Image
    img=cv2.cvtColor(np.array(Image.open(SRC).convert('RGB')),cv2.COLOR_RGB2BGR)
print(img.shape)
ears={'big':(692,672,862,975),'small':(271,572,382,734),'side':(930,503,1032,822)}
S=4
for name,(x0,y0,x1,y1) in ears.items():
    pad=14
    X0,Y0,X1,Y1=x0-pad,y0-pad,x1+pad,min(y1+pad,img.shape[0])
    X1=min(X1,img.shape[1])
    crop=img[Y0:Y1,X0:X1]
    up=cv2.resize(crop,None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(W+f'up_{name}.png',up)
    mask=np.zeros(up.shape[:2],np.uint8)
    rect=((x0-X0)*S,(y0-Y0)*S,(x1-x0)*S,(y1-y0)*S)
    bg=np.zeros((1,65),np.float64); fg=np.zeros((1,65),np.float64)
    cv2.grabCut(up,mask,rect,bg,fg,6,cv2.GC_INIT_WITH_RECT)
    m=np.where((mask==1)|(mask==3),255,0).astype(np.uint8)
    cv2.imwrite(W+f'gc1_{name}.png',m)
    ov=up.copy(); ov[m==0]=(ov[m==0]*0.25).astype(np.uint8)
    cv2.imwrite(W+f'gc1ov_{name}.png',ov)
    print(name, up.shape, rect)
