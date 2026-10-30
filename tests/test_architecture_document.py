from __future__ import annotations

import json
import re
from pathlib import Path


def test_architecture_paths_and_walkthroughs_resolve() -> None:
    """Keep the portable diagram's code links and narrated paths usable."""
    root = Path(__file__).resolve().parents[1]
    html = (root / "C4-Documentation/nexaassist-architecture.html").read_text()
    match = re.search(
        r'<script id="architecture-data" type="application/json">(.*?)</script>', html, re.DOTALL
    )
    assert match is not None
    data = json.loads(match.group(1))
    for component in data["catalog"].values():
        for path, _symbol in component["code"]:
            assert (root / path).is_file(), path
    for view in data["views"].values():
        nodes = [node[0] for node in view["nodes"]]
        edges = {edge["id"]: edge for edge in view["edges"]}
        assert len(nodes) == len(set(nodes))
        assert len(edges) == len(view["edges"])
        assert set(nodes) <= data["catalog"].keys()
        assert view["default"] in nodes
        for edge in edges.values():
            assert {edge["from"], edge["to"]} <= set(nodes)
        for step in view["steps"]:
            assert step["focus"] in nodes
            assert set(step["edges"]) <= edges.keys()
