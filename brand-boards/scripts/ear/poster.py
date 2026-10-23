import os
import cv2,numpy as np,sys
W=os.environ.get('MD_WORK', 'work/ear/')
A=os.environ.get('MD_OUT', 'out/ear/')
im=cv2.imread(A+'ear_1_cutout.png',cv2.IMREAD_UNCHANGED)   # 644x1162
bgr=im[...,:3].copy()
for _ in range(3): bgr=cv2.bilateralFilter(bgr,9,18,9)
L=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB)[...,0].astype(np.float32)/255
a=im[...,3].astype(np.float32)/255
m=a>0.5
# local contrast so creases read independent of global light falloff
Lm=L.copy(); Lm[~m]=np.median(L[m])
loc=L-cv2.GaussianBlur(Lm,(0,0),40)
def make(thr,k_loc,out,size=(1600,2000),scale=2.25,cx=0.47,cy=0.50,rot=-6):
    f=np.clip(0.5+k_loc*loc+0.6*(L-np.median(L[m])),0,1)
    f[~m]=0
    # place on poster canvas (scale, rotate about centre)
    Wp,Hp=size
    M=cv2.getRotationMatrix2D((im.shape[1]/2,im.shape[0]/2),rot,scale)
    M[0,2]+=Wp*cx-im.shape[1]/2; M[1,2]+=Hp*cy-im.shape[0]/2
    F=cv2.warpAffine(f,M,(Wp,Hp),flags=cv2.INTER_CUBIC,borderValue=0)
    Aw=cv2.warpAffine(a,M,(Wp,Hp),flags=cv2.INTER_LINEAR,borderValue=0)
    # fill outside with neighbouring interior tone so the silhouette edge stays clean
    inside=(Aw>0.5).astype(np.float32)
    dist=cv2.distanceTransform((Aw>0.5).astype(np.uint8),cv2.DIST_L2,5)
    F=F+0.9*np.exp(-dist/(26*scale/1.12))
    num=cv2.GaussianBlur(F*inside,(0,0),12); den=cv2.GaussianBlur(inside,(0,0),12)
    Ff=np.where(inside>0,F,np.maximum(num/np.maximum(den,1e-4),thr+0.15))
    Ff=cv2.GaussianBlur(Ff,(0,0),4.0*scale/2.25)
    b=(Ff>thr).astype(np.uint8)
    # remove specks of either colour
    from scipy import ndimage as ndi
    minA=int(Wp*Hp*0.0004)
    for val in (0,1):
        lab,n=ndi.label(b==val); sz=ndi.sum(np.ones_like(b),lab,range(1,n+1))
        small=np.zeros(n+1,bool); small[1:]=sz<minA
        b[small[lab]]=1-val
    sm=3.0*scale/1.12
    t=cv2.GaussianBlur(b.astype(np.float32),(0,0),sm)       # curvature-flow style smoothing of ragged edges
    t=np.clip((t-0.5)*(sm*1.6)+0.5,0,1)
    # clean silhouette: smooth AA mask
    ma=cv2.GaussianBlur(Aw,(0,0),1.0); ma=np.clip((ma-0.5)*3+0.5,0,1)
    t=t*ma
    # drop thin cream slivers hugging the silhouette (shadowed lobe edge): merge them into the background
    rr=int(round(5*scale/1.12)); kk=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*rr+1,2*rr+1))
    opened=cv2.morphologyEx((t>0.5).astype(np.uint8),cv2.MORPH_OPEN,kk)
    near=dist<(45*scale/1.12)
    lab,n=ndi.label((t>0.5)&near&(opened==0))
    if n:
        sz=ndi.sum(np.ones_like(lab),lab,range(1,n+1)); 
        kill=np.zeros(n+1,bool); kill[1:]=sz>0
        kz=cv2.GaussianBlur((kill[lab]).astype(np.float32),(0,0),1.0)
        t=t*(1-np.clip(kz*2,0,1))
    ink=np.array([0x10,0x11,0x11],np.float32); cream=np.array([0xEA,0xF1,0xF4],np.float32)
    o=ink*(1-t[...,None])+cream*t[...,None]
    cv2.imwrite(out,o.astype(np.uint8))
if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='final':
        make(0.43,1.6,A+'ear_poster_crop.png',size=(1600,2000),scale=2.24)
    else:
        for thr in (0.41,0.43,0.45):
            make(thr,1.6,W+f'poster_t{int(thr*100)}.png',size=(800,1000),scale=1.12)
