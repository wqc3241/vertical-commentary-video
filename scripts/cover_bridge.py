# -*- coding: utf-8 -*-
"""localhost 下载桥(封面/IG图片用): 页面内 fetch->b64->表单POST 到这里,服务端落盘。
用法: python cover_bridge.py [输出目录]   (默认 ./source/photos)
为何这么绕: chatgpt.com 的 CSP connect-src 禁止页面 fetch 127.0.0.1(所以必须用<form>提交);
服务端直接拉图片URL 会 401/403(所以图片数据要在页面里 fetch 好再 POST 过来)。
!!! 表单必须【顶层提交,不带 target】—— target=_blank 被弹窗拦、target=iframe 被 CSP frame 限制挡,
两者都静默失败(f.submit() 不报错但文件不落盘)。配套本桥返回 204 No Content, 浏览器才不会跳走,
从而能在一个 JS 调用里循环下载全部图片。(2026-07-30 实测定论)"""
import http.server, urllib.request, os, sys, base64
from urllib.parse import parse_qs
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "source", "photos")
os.makedirs(OUT, exist_ok=True)
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            l=int(self.headers.get('Content-Length',0)); body=self.rfile.read(l).decode()
            d=parse_qs(body); name=os.path.basename(d.get('name',['img.jpg'])[0])
            if 'b64' in d:
                data=base64.b64decode(d['b64'][0].split(',')[-1])
            else:
                req=urllib.request.Request(d['url'][0], headers={'User-Agent':'Mozilla/5.0'})
                data=urllib.request.urlopen(req, timeout=60).read()
            open(os.path.join(OUT,name),'wb').write(data)
            print("saved", name, len(data), flush=True)
            self.send_response(204)          # 204 = 顶层表单提交后浏览器不跳转(关键)
            self.send_header('Content-Length','0'); self.end_headers(); return
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(("ERR %r"%e).encode())
    def log_message(self,*a): pass
print("bridge on 127.0.0.1:8765 ->", OUT)
http.server.HTTPServer(('127.0.0.1',8765),H).serve_forever()
