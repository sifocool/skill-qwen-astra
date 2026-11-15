from . import static,dynamic,protocol

REGISTRY={"python_ast":static.python_ast,"semantic_diff":static.semantic_diff,
    "dependencies":static.dependencies,"binary":static.binary,
    "replay":dynamic.replay,"compare":dynamic.compare,"fuzz":dynamic.fuzz,
    "minimize":dynamic.minimize,"sanitizer":dynamic.sanitizer,
    "deserialize_trace":dynamic.deserialize_trace,"http_probe":protocol.http_probe,
    "protocol":protocol.protocol,
    "radare2":lambda a,s:static.external(a,s,"radare2"),
    "ghidra":lambda a,s:static.external(a,s,"ghidra")}


def execute(adapter,args,scope):
    scope.adapter(adapter)
    if adapter not in REGISTRY:
        raise ValueError("unknown adapter")
    return REGISTRY[adapter](args,scope)
