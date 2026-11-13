import json, os, urllib.request
from pathlib import Path
req=json.loads(Path("/staging/request.json").read_text())
raw=json.dumps(req,sort_keys=True,separators=(",",":")).encode()
r=urllib.request.Request(os.environ.get("OLLAMA_URL","http://host.docker.internal:11434/api/chat"),data=raw,headers={"content-type":"application/json"})
with urllib.request.urlopen(r,timeout=300) as resp:
    data=json.loads(resp.read())
Path("/out/response.json").write_text(json.dumps(data,sort_keys=True)+chr(10))
print("ok", data.get("prompt_eval_count"), data.get("eval_count"))
