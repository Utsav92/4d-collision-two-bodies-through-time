# Minimal exec bridge for TouchDesigner. Load from Textport with:
#   exec(open(r'C:\Users\Utsav\bear-collision\td_bridge.py').read())
# Serves POST /api/td/server/exec {"script": "..."} on port 9981 and returns
# {"data": {"stdout", "stderr", "result"}, "error": null}, the same shape tdrun.py already expects.
PORT = 9981

CALLBACKS = '''
import json, io, sys, traceback, contextlib

_G = {}

def onHTTPRequest(webServerDAT, request, response):
    response['headers'] = {'Content-Type': 'application/json'}
    response['statusCode'] = 200
    response['statusReason'] = 'OK'
    out = {'data': {'stdout': '', 'stderr': '', 'result': None}, 'error': None}
    try:
        body = request.get('data') or b''
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        script = json.loads(body)['script'] if body else ''
        _G.update({'op': op, 'root': root, 'app': app, 'project': project, 'ui': ui, 'td': td, 'result': None})
        so, se = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
                exec(compile(script, '<td_exec>', 'exec'), _G)
        except Exception:
            se.write(traceback.format_exc())
        out['data'] = {'stdout': so.getvalue(), 'stderr': se.getvalue(), 'result': _G.get('result')}
    except Exception:
        out['error'] = traceback.format_exc()
    response['data'] = json.dumps(out, default=str)
    return response
'''

for _n in ('bc_bridge', 'bc_bridge_callbacks'):
    _o = root.op(_n)
    if _o is not None:
        _o.destroy()
_cb = root.create(textDAT, 'bc_bridge_callbacks')
_cb.text = CALLBACKS
_ws = root.create(webserverDAT, 'bc_bridge')
_ws.par.callbacks = _cb
_ws.par.port = PORT
_ws.par.active = True
print('bc_bridge listening on', PORT)
