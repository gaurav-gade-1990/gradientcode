def run(ns, reidentify_roles, ops):
    """Run redact / reidentify calls through your vault. `text_from: i` reuses the output of op i as the text."""
    vault = ns["PiiVault"](list(reidentify_roles))
    results = []
    for op in ops:
        text = results[op["text_from"]] if "text_from" in op else op["text"]
        try:
            if op["op"] == "redact":
                out = vault.redact(op["tenant"], text)
            else:
                out = vault.reidentify(op["tenant"], op["role"], text)
        except PermissionError:
            out = {"error": "PermissionError"}
        results.append(out)
    return {"results": results, "audit": [dict(a, tokens=list(a["tokens"])) for a in vault.audit]}
