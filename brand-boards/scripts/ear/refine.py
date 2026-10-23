import os
import cv2, numpy as np
from scipy.ndimage import gaussian_filter1d, binary_fill_holes
W=os.environ.get('MD_WORK', 'work/ear/')
OUT=os.environ.get('MD_OUT', 'out/ear/')
P=np.array
cfg={
 'big':dict(n=1,sig=26,protect=[(665,985,70,7)],hints=[]),
 'small':dict(n=2,sig=18,protect=[(445,500,45,8)],hints=[('bg',[(368,92),(452,92),(452,192),(433,176),(406,136),(377,110)])]),
 'side':dict(n=3,sig=32,inset=(8.0,1.5),band=6,hints=[
    ('bg',[(0,300),(70,300),(70,1388),(0,1388)]),
    ('bg',[(60,1170),(98,1170),(108,1225),(128,1262),(155,1290),(200,1312),(200,1388),(60,1388)]),
    ('bg',[(436,430),(520,430),(520,600),(440,600)]),
    ('bg',[(0,0),(520,0),(520,70),(0,70)]),
    ('bg',[(60,60),(170,60),(110,150),(80,300),(60,300)]),
 ]),
}
def smooth_contour(m,sig,protect=()):
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    c=max(cs,key=cv2.contourArea)[:,0,:].astype(np.float64)
    def g(s): return np.stack([gaussian_filter1d(c[:,0],s,mode='wrap'),gaussian_filter1d(c[:,1],s,mode='wrap')],1)
    out=g(sig)
    for (px,py,r,s2) in protect:
        d2=((c[:,0]-px)**2+(c[:,1]-py)**2); w=np.exp(-d2/(2*r*r))[:,None]
        out=out*(1-w)+g(s2)*w
    return out
def render(poly,shape,ss=4):
    big=np.zeros((shape[0]*ss,shape[1]*ss),np.uint8)
    pts=np.round((poly+0.5)*ss-0.5).astype(np.int32)
    cv2.fillPoly(big,[pts],255,cv2.LINE_8)
    return cv2.resize(big,(shape[1],shape[0]),interpolation=cv2.INTER_AREA).astype(np.float32)/255.
for name,c in cfg.items():
    up=cv2.imread(W+f'up_{name}.png'); m0=cv2.imread(W+f'gc1_{name}.png',0)>127
    k=lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
    m0u=m0.astype(np.uint8)
    mask=np.full(m0.shape,cv2.GC_BGD,np.uint8)
    mask[cv2.dilate(m0u,k(28))>0]=cv2.GC_PR_BGD
    mask[m0]=cv2.GC_PR_FGD
    mask[cv2.erode(m0u,k(22))>0]=cv2.GC_FGD
    for kind,poly in c['hints']:
        cv2.fillPoly(mask,[P(poly,np.int32)],cv2.GC_BGD if kind=='bg' else cv2.GC_FGD)
    bg=np.zeros((1,65)); fg=np.zeros((1,65))
    cv2.grabCut(up,mask,None,bg,fg,6,cv2.GC_INIT_WITH_MASK)
    m=((mask==1)|(mask==3)).astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,k(3)); m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,k(6))
    n,lab,st,_=cv2.connectedComponentsWithStats(m)
    m=(lab==1+np.argmax(st[1:,cv2.CC_STAT_AREA])).astype(np.uint8)*255
    m=binary_fill_holes(m>0).astype(np.uint8)*255
    poly=smooth_contour(m,c['sig'],c.get('protect',()))
    a=render(poly,m.shape)              # anti-aliased, smooth
    # 1px inset then ~1px feather at output scale (4x)
    ab=(a>0.5).astype(np.uint8)
    ins=c.get('inset',1)
    if isinstance(ins,tuple):   # (left inset, right inset): ramps smoothly across the ear's width
        ys_,xs_=np.where(ab>0); cx=xs_.mean(); wv=(xs_.max()-xs_.min())*0.18
        xx=np.arange(ab.shape[1],dtype=np.float32)
        insx=np.interp(xx,[cx-wv,cx+wv],[ins[0],ins[1]])[None,:]
        d=cv2.distanceTransform(ab,cv2.DIST_L2,5)
        ab=(d>insx).astype(np.uint8)
    else:
        ab=cv2.erode(ab,k(ins))
    alpha=cv2.GaussianBlur(ab.astype(np.float32),(0,0),1.1)
    alpha=np.clip(alpha,0,1)
    # mild sharpen first (offsets upscale softness), then colour decontamination
    srcf=up.astype(np.float32)
    bl=cv2.GaussianBlur(srcf,(0,0),2.0); srcf=np.clip(srcf*1.3-bl*0.3,0,255)
    bd=c.get('band',4)
    core=cv2.erode(ab,k(bd)).astype(np.float32)
    num=cv2.GaussianBlur(srcf*core[...,None],(0,0),bd*0.9+2); den=cv2.GaussianBlur(core,(0,0),bd*0.9+2)[...,None]
    ext=num/np.maximum(den,1e-4)
    dist=cv2.distanceTransform((1-core).astype(np.uint8),cv2.DIST_L2,5)
    t=np.clip(dist/(bd+1.5),0,1)[...,None]
    col=np.clip(srcf*(1-t)+ext*t,0,255).round().astype(np.uint8)
    rgba=np.dstack([col,(alpha*255).round().astype(np.uint8)])
    ys,xs=np.where(alpha>0.004); p=4
    y0,y1,x0,x1=max(ys.min()-p,0),ys.max()+p+1,max(xs.min()-p,0),xs.max()+p+1
    rgba=rgba[y0:y1,x0:x1]
    cv2.imwrite(OUT+f'ear_{c["n"]}_cutout.png',rgba)
    np.save(W+f'poly_{name}.npy',poly-[x0,y0])
    cv2.imwrite(W+f'mask2_{name}.png',(a>0.5).astype(np.uint8)*255)
    o=up.copy(); cv2.polylines(o,[np.round(poly).astype(np.int32)],True,(0,0,255),2,cv2.LINE_AA)
    for kind,pp in c['hints']: cv2.polylines(o,[P(pp,np.int32)],True,(255,0,0),1)
    cv2.imwrite(W+f'ctr2_{name}.png',o)
    print(name,'->',OUT+f'ear_{c["n"]}_cutout.png',rgba.shape)
