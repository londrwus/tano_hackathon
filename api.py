"""Modal wrapper — ONE container, ONE URL, so judges can open it on their own phones.

Not needed for throughput. One process already does ~2,535 judgments/sec; the workload is
network-bound and Jev's servers are the parallelism. This exists only so the demo has a
shareable https:// URL, which is what "Would I share it?" actually costs.

    modal secret create jev JEV_API_KEY=apikey_...
    cd frontend && npm run build          # must run FIRST — dist/ is baked into the image
    python -m backend.warm                # must run FIRST — cache/ is baked in too
    modal serve api.py                    # hot-reloading dev URL
    modal deploy api.py                   # -> https://<workspace>--tano-heist-web.modal.run

Deploy at ~17:00, not at 10:30. NEVER pass gpu= anywhere in this file: Jev is an HTTPS call,
a CPU container is ~$0.01/hr and a GPU is what would burn the credit.
"""
import modal

app = modal.App("tano-heist")

# Pinned to the versions this actually runs on locally, not to older ones nobody tested.
# fonts-dejavu-core is for og.py: it looks in /usr/share/fonts and falls back to PIL's
# bitmap default, which makes a share card look broken. Two megabytes buys real type.
_IGNORE = ["**/__pycache__", "**/*.pyc", "**/.DS_Store"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("fonts-dejavu-core")
    .pip_install(
        "fastapi[standard]==0.141.*",
        "httpx==0.27.2",
        "python-dotenv==1.0.*",
        "pillow==12.1.*",
    )
    # Order matters: code, then the frozen evidence, then the built frontend.
    # Every path below is resolved from backend/__file__.parent.parent, so all four
    # MUST land as siblings under /root or cache.py and engine.py look in the wrong place.
    .add_local_dir("backend", remote_path="/root/backend", copy=True, ignore=_IGNORE)
    .add_local_dir("data", remote_path="/root/data", copy=True, ignore=_IGNORE)
    .add_local_dir("cache", remote_path="/root/cache", copy=True, ignore=_IGNORE)
    .add_local_dir("frontend/dist", remote_path="/root/frontend/dist", copy=True,
                   ignore=_IGNORE)
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("jev")],
    min_containers=1,      # ON only during the demo window, otherwise it idles on credit
    scaledown_window=300,
    timeout=600,
)
@modal.concurrent(max_inputs=100)   # one container serves the whole room
@modal.asgi_app()
def web():
    import os
    from pathlib import Path

    os.chdir("/root")

    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    from backend.main import app as api, root as route_index

    dist = Path("/root/frontend/dist")

    # main.py registers GET "/" as a JSON route index. That is right when the API runs
    # on its own port, and wrong here: this process also serves the site, so "/" is the
    # bare link a judge opens and it must be the home page, not {"ok": true}. Routes
    # match in registration order, so the JSON one has to come out before the SPA
    # fallback below can have the root. It keeps its listing, at /api.
    for r in [x for x in api.routes
              if getattr(x, "path", None) == "/"
              and "GET" in (getattr(x, "methods", None) or ())]:
        api.routes.remove(r)
    api.get("/api", include_in_schema=False)(route_index)

    # SPA fallback: /maya, /ask, /c/<id>, /onboard are client routes with no file on disk.
    # Registered BEFORE the mount so it only catches what StaticFiles would 404 on.
    @api.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")

    # Mount LAST so every /api/* route above wins over a static file of the same name.
    api.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
    return api
