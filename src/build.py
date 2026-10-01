import json, base64, re, io, numpy as np
from PIL import Image
from glassmaps import filt
GK = {  # w, h, radius, bezel, displacement scale, blur, dispersion
 'phone':(440,900,88,46,80,7,True),'orb':(440,440,220,200,150,1.2,True),'chip':(250,78,39,24,40,6,False),
 'search':(392,64,32,20,34,6,False),'badge':(168,54,27,16,26,5,False),'seg':(392,60,30,18,30,6,False),
 'row':(392,78,26,18,30,6,False),'tab':(300,76,38,22,36,6,False),'call':(290,58,29,16,26,6,False),
 'flight':(440,210,42,28,54,7,True),'stay':(390,230,42,28,54,7,False),'wx':(250,100,50,26,44,6,False),
 'hud':(380,250,32,24,44,7,False),'pass':(580,260,38,28,54,6,True),'card':(340,440,44,30,60,5,False),
 'icon':(260,260,64,56,96,2.5,True),'cta':(320,88,44,30,48,5,True),'wipe':(620,1400,140,240,230,2.5,True)}
filters=''.join(filt(k,w,h,r,b,s,blur=bl,disperse=d) for k,(w,h,r,b,s,bl,d) in GK.items())
gk={k:{'w':v[0],'h':v[1],'r':v[2]} for k,v in GK.items()}
css=open('fonts/local.css').read()
def emb(m):
    return 'url(data:font/woff2;base64,'+base64.b64encode(open('fonts/'+m.group(1),'rb').read()).decode()+')'
css=re.sub(r'url\(([\w-]+\.woff2)\)',emb,css)
rs=np.random.RandomState(4); n=(rs.rand(256,256)*255).astype(np.uint8)
buf=io.BytesIO(); Image.fromarray(n,'L').save(buf,'PNG')
noise='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
t=open('template.html').read()
t=t.replace('/*FONTS*/',css).replace('<!--FILTERS-->',filters).replace('/*GK*/',json.dumps(gk)).replace('/*LAND*/',open('land_pts.json').read()).replace('/*NOISE*/',json.dumps(noise))
open('../ad.html','w').write(t); print('ok', len(t)//1024,'KB')
