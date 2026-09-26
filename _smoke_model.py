from shared.model import build_project

for label, path in [
    ("baseline", "poc/case01_legitimate_move/baseline"),
    ("candidate", "poc/case01_legitimate_move/candidate"),
]:
    p = build_project(path)
    print("==", label, "hash", p.content_hash[:12])
    for address, node in p.nodes.items():
        print(f"  {address}  kind={node.kind} type={node.type} ord={node.ordinal} file={node.file}:{node.line}")
        print(f"      refs={node.refs}")
        print(f"      refkinds={node.ref_kinds}")
    print("  moved:", [(m.from_address, m.to_address, m.source) for m in p.moved])
    print("  warnings:", p.warnings)
    bucket = [n for n in p.nodes.values() if n.type == "aws_s3_bucket"][0]
    print("  bucket signature:", bucket.signature())
    print("  incoming:", [n.address for n in p.incoming(bucket.address)])
