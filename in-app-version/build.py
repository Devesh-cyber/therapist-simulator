"""Builds the single-file in-app (claude.ai artifact) version by inlining the shared scene module."""
import pathlib, re
root = pathlib.Path(__file__).resolve().parent
scene = (root.parent / "frontend/src/game/scene.js").read_text()
scene = re.sub(r"^export ", "", scene, flags=re.M)
html = (root / "template.html").read_text().replace("/*SCENE*/", scene)
(root / "quiet-room-clinic.html").write_text(html)
print("wrote", root / "quiet-room-clinic.html", len(html), "bytes")
