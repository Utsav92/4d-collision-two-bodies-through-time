import time, json, urllib.request, sys
def q(code):
    req = urllib.request.Request('http://127.0.0.1:9981/api/td/server/exec', data=json.dumps({'script': code}).encode(), headers={'Content-Type':'application/json'})
    t=time.time(); r=json.loads(urllib.request.urlopen(req, timeout=60).read()); return t, r['data']['result']
def measure(sec=4):
    code="result=[absTime.frame]"
    t0,a=q(code); time.sleep(sec); t1,b=q(code)
    return (b[0]-a[0])/(t1-t0)
if __name__=='__main__':
    for pre in sys.argv[1:]:
        if pre: q(pre); time.sleep(1.0)
        print('%.1f fps   after: %s' % (measure(), pre[:90]))
