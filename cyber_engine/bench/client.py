"""One local Anthropic-compatible Qwen client, no fallback model or hidden retries."""
import json
import os
import urllib.request
from urllib.parse import urlsplit


class Client:
    def __init__(self,base_url="http://127.0.0.1:8095",model="qwen3.8-27b",timeout=120):
        if urlsplit(base_url).hostname not in ("localhost","127.0.0.1","::1"):
            raise ValueError("benchmark model endpoint must be local; configure a local tunnel explicitly")
        self.base=base_url.rstrip("/");self.model=model;self.timeout=timeout

    def models(self):
        with urllib.request.urlopen(self.base+"/v1/models",timeout=10) as r:return json.load(r)

    def complete(self,messages,system,max_tokens=1024):
        body={"model":self.model,"max_tokens":max_tokens,"temperature":0,"stream":False,
              "system":system,"messages":messages}
        req=urllib.request.Request(self.base+"/v1/messages",data=json.dumps(body).encode(),
            headers={"Content-Type":"application/json","anthropic-version":"2023-06-01",
                     "x-api-key":os.environ.get("ASTRA_LOCAL_API_KEY","local")})
        with urllib.request.urlopen(req,timeout=self.timeout) as r:return json.load(r)


if __name__=="__main__":
    c=Client();print(json.dumps(c.models()))
    r=c.complete([{"role":"user","content":"Réponds exactement ASTRA_OK."}],"Réponse brève.",128)
    print(json.dumps({"model":r.get("model"),"content":r.get("content"),"usage":r.get("usage"),"stop_reason":r.get("stop_reason")}))
