"""JSON CLI: python -m cyber_engine --state DIR ACTION '{...}'"""
import argparse
import json
import sys
from .engine import Engine,route


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--state",default=".astra/state")
    parser.add_argument("action",choices=["init","observe","hypothesis","plan","select","run","run-next",
        "reject","challenge","gate","conclude","stop","knowledge","status","route"])
    parser.add_argument("payload",nargs="?",default="{}")
    a=parser.parse_args(); engine=Engine(a.state)
    try:
        payload=json.loads(a.payload)
        if a.action=="route":result=route(payload['question'])
        elif a.action=="status": result=engine.store.load()
        elif a.action=="run-next":
            result=engine.select()
            if result["action"]=="run": result={"selection":result,"result":engine.run(result["id"])}
        else: result=getattr(engine,a.action)(**payload)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    except (ValueError,KeyError,TypeError,OSError) as e:
        print(json.dumps({"status":"FAIL","error_type":type(e).__name__,"reason":str(e)}))
        return 1
    finally:engine.store.close()
    return 0

if __name__=="__main__":sys.exit(main())
