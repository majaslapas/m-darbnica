import os
import cv2,numpy as np,sys
W=os.environ.get('MD_WORK', 'work/ear/')
A=os.environ.get('MD_OUT', 'out/ear/')
PAD=24
def load(H=1400):
    im=cv2.imread(A+'ear_1_cutout.png',cv2.IMREAD_UNCHANGED)
    s=H/im.shape[0]; im=cv2.resize(im,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)
    im=cv2.copyMakeBorder(im,PAD,PAD,PAD,PAD,cv2.BORDER_CONSTANT,value=(0,0,0,0))
    a=im[...,3].astype(np.float32)/255
    bgr=im[...,:3].copy()
    for _ in range(2): bgr=cv2.bilateralFilter(bgr,9,16,7)
    L=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB)[...,0].astype(np.float32)
    return L,a
def tone_map(L,a,lo_p=1.5,hi_p=96,gamma=1.45,base=0.045,span=0.93,edge=0.3):
    m=a>0.5
    lo,hi=np.percentile(L[m],[lo_p,hi_p])
    d=np.clip((hi-L)/(hi-lo),0,1)**gamma
    # local contrast: unsharp the darkness map a little so folds read
    d=np.clip(d+0.6*(d-cv2.GaussianBlur(d,(0,0),18)),0,1)
    t=base+span*d
    # darken a thin rim along the silhouette so the shape reads on any background
    dist=cv2.distanceTransform(m.astype(np.uint8),cv2.DIST_L2,5)
    t=t+edge*np.exp(-dist/8.0)
    return np.clip(t,0,0.97)
def screen(T,M,cell=13.0,angle=45,seed=1,rough=0.35,jit=0.06,shift=(0,0)):
    h,w=T.shape; th=np.deg2rad(angle); c,s=np.cos(th),np.sin(th)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32); xx-=shift[0]; yy-=shift[1]
    u=(xx*c+yy*s)/cell; v=(-xx*s+yy*c)/cell
    fu,fv=np.floor(u),np.floor(v)
    rng=np.random.default_rng(seed)
    noise=cv2.GaussianBlur(rng.standard_normal((h,w)).astype(np.float32),(0,0),1.2); noise/=noise.std()+1e-6
    out=np.zeros((h,w),np.float32)
    for du in (-1,0,1):
        for dv in (-1,0,1):
            cu=fu+0.5+du; cv_=fv+0.5+dv
            X=(cu*c-cv_*s)*cell+shift[0]; Y=(cu*s+cv_*c)*cell+shift[1]
            X=X.astype(np.float32); Y=Y.astype(np.float32); Tc=cv2.remap(T.astype(np.float32),X,Y,cv2.INTER_LINEAR,borderValue=0)
            Mc=cv2.remap(M.astype(np.float32),X,Y,cv2.INTER_LINEAR,borderValue=0)
            hsh=np.sin(cu*12.9898+cv_*78.233)*43758.5453; hsh=hsh-np.floor(hsh)
            r=cell*np.sqrt(np.maximum(Tc,0)/np.pi)*(1+jit*(hsh*2-1))
            d=np.sqrt((xx+shift[0]-X)**2+(yy+shift[1]-Y)**2)
            cov=np.clip(r-d+0.5+rough*noise,0,1)*(Mc>0.5)
            out=np.maximum(out,cov)
    return out
def rgba(cov,hexcol,clip=None):
    col=tuple(int(hexcol[i:i+2],16) for i in (1,3,5))
    h,w=cov.shape; o=np.zeros((h,w,4),np.uint8)
    o[...,0]=col[2];o[...,1]=col[1];o[...,2]=col[0]
    if clip is not None: cov=cov*clip
    o[...,3]=np.round(np.clip(cov,0,1)*255).astype(np.uint8); return o
if __name__=='__main__':
    L,a=load()
    T=tone_map(L,a)
    M=(a>0.5).astype(np.float32)
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9))
    clip=cv2.GaussianBlur(cv2.dilate(M,k),(0,0),1.0)
    cov=screen(T,M,cell=13,angle=45)
    np.save(W+'ht_cov.npy',cov)
    cv2.imwrite(A+'ear_halftone_ink.png',rgba(cov,'#111110',clip))
    cv2.imwrite(A+'ear_halftone_rose.png',rgba(cov,'#D8606A',clip))
    # bonus duotone: rose plate at 15deg (lighter), ink plate at 75deg slightly off-register
    covR=screen(np.clip(T*0.85+0.12,0,0.97)*M,M,cell=13,angle=15,seed=2)
    Tk=np.clip((T-0.28)/0.72,0,1)*0.9
    covK=screen(Tk,M,cell=13,angle=75,seed=3,shift=(3,2))
    h,w=cov.shape; out=np.zeros((h,w,4),np.float32)
    rose=np.array([0x6A,0x60,0xD8],np.float32); ink=np.array([0x10,0x11,0x11],np.float32)
    # multiply-style overprint on transparent: alpha = union, colour = rose, darkened where ink overlaps
    aU=1-(1-covR)*(1-covK)
    colr=(rose*covR[...,None]*(1-covK[...,None]) + (ink*0.85+rose*0.15)*covK[...,None])/np.maximum(aU[...,None],1e-4)
    out[...,:3]=colr; out[...,3]=aU*255*clip
    cv2.imwrite(A+'ear_halftone_duotone.png',np.clip(out,0,255).astype(np.uint8))
    print(cov.shape)
