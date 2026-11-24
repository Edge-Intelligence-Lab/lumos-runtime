"""Command-line tools for inspecting the MuJoCo workbench."""

import json


def simulate(args) -> None:
    import mujoco

    from . import load_workbench

    if args.steps < 0:
        raise ValueError("--steps must be nonnegative")
    model, data = load_workbench(args.assets_dir, args.wrist_calibration)
    for _ in range(args.steps):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)

    if args.wrist_image is not None:
        from PIL import Image

        width, height = map(int, model.cam_resolution[model.camera("wrist").id])
        with mujoco.Renderer(model, height=height, width=width) as renderer:
            renderer.update_scene(data, camera="wrist")
            Image.fromarray(renderer.render()).save(args.wrist_image)

    if args.web:
        from mujoco.studio import app, launch_web, viewer_protocol

        launch_web.run(
            viewer_protocol.ViewerConfig(title="LumosTouch V3 Workbench", http_port=args.port),
            model=model,
            data=data,
            plugins=[app.App(), *app.SIM_PLUGINS],
        )
        return

    print(json.dumps({
        "joints": model.njnt,
        "actuators": model.nu,
        "meshes": model.nmesh,
        "simulation_time_s": data.time,
        "wrist_camera": "configured_pinhole" if args.wrist_calibration else "preview_only",
    }, indent=2))
