from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from cyber_engine.adapters import execute
from cyber_engine.scope import Scope


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/redirect':
            self.send_response(302);self.send_header('Location','http://not-authorized.invalid/');self.end_headers()
        else:
            self.send_response(200);self.end_headers();self.wfile.write(b'local-fixture')
    def log_message(self,*args):pass


class HTTPTests(unittest.TestCase):
    def test_actual_request_origin_and_redirect_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            scope=Scope(dict(authorization='local HTTP test fixture',roots=[d],adapters=['http_probe'],origins=[base]))
            try:
                self.assertEqual(execute('http_probe',dict(url=base+'/'),scope)['status_code'],200)
                self.assertEqual(execute('http_probe',dict(url=base+'/redirect'),scope)['status_code'],302)
                with self.assertRaises(ValueError):execute('http_probe',dict(url='https://example.com'),scope)
            finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
