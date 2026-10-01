import numpy as np, base64, io
from PIL import Image

def rr_map(w, h, r, bezel, power=2.4):
    """Displacement map for a rounded-rect convex glass lens. Inside the bezel,
    pixels sample inward along the surface normal; flat centre is neutral."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    px = xs + .5 - w/2; py = ys + .5 - h/2
    bx, by = w/2 - r, h/2 - r
    qx = np.abs(px) - bx; qy = np.abs(py) - by
    outside = np.sqrt(np.maximum(qx,0)**2 + np.maximum(qy,0)**2)
    d = outside + np.minimum(np.maximum(qx,qy),0) - r   # signed distance (neg inside)
    gy, gx = np.gradient(d)
    n = np.sqrt(gx*gx+gy*gy)+1e-6
    nx, ny = gx/n, gy/n                                   # outward normal
    e = -d
    t = np.clip(1 - e/bezel, 0, 1)
    m = t**power
    m[d > 0] = 0
    dx, dy = -nx*m, -ny*m                                 # sample inward
    R = np.clip(128 + dx*127, 0, 255); G = np.clip(128 + dy*127, 0, 255)
    img = np.stack([R, G, np.full_like(R,128), np.full_like(R,255)], -1).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(img, 'RGBA').save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

def filt(name, w, h, r, bezel, scale, blur=6, sat=1.6, disperse=False):
    uri = rr_map(w, h, r, bezel)
    head = f'<filter id="f-{name}" x="0" y="0" width="{w}" height="{h}" filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse" color-interpolation-filters="sRGB">'
    img = f'<feImage href="{uri}" x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="none" result="map"/>'
    bl = f'<feGaussianBlur in="SourceGraphic" stdDeviation="{blur}" edgeMode="duplicate" result="bl"/>'
    if disperse:
        body = (f'<feDisplacementMap in="bl" in2="map" scale="{scale}" xChannelSelector="R" yChannelSelector="G" result="d1"/>'
                f'<feColorMatrix in="d1" type="matrix" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="cr"/>'
                f'<feDisplacementMap in="bl" in2="map" scale="{scale*0.9:.1f}" xChannelSelector="R" yChannelSelector="G" result="d2"/>'
                f'<feColorMatrix in="d2" type="matrix" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0" result="cg"/>'
                f'<feDisplacementMap in="bl" in2="map" scale="{scale*0.8:.1f}" xChannelSelector="R" yChannelSelector="G" result="d3"/>'
                f'<feColorMatrix in="d3" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="cb"/>'
                f'<feBlend in="cr" in2="cg" mode="screen" result="rg"/><feBlend in="rg" in2="cb" mode="screen" result="dd"/>')
        src = 'dd'
    else:
        body = f'<feDisplacementMap in="bl" in2="map" scale="{scale}" xChannelSelector="R" yChannelSelector="G" result="dd"/>'
        src = 'dd'
    tail = f'<feColorMatrix in="{src}" type="saturate" values="{sat}"/></filter>'
    return head + img + bl + body + tail

if __name__ == '__main__':
    print(len(rr_map(440, 900, 88, 40)))
