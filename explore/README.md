# Vikipedia Drive

A self-contained 3D driving portfolio built with Three.js 0.183.2, original procedural geometry and Web Audio synthesis. Inspired by the driving-as-navigation idea of Bruno Simon; no Bruno models or code copied.

## Run

From the parent `vikipedia-demo` directory: `python -m http.server 5188 --bind 127.0.0.1`. Open `http://127.0.0.1:5188/explore/`. A HTTP server is required for ES modules. The committed `vendor/` files make the demo independent of a CDN and npm at runtime. Three.js MIT license is included.

## Features

- Keyboard driving (WASD/arrows), brake (Space), interact (E), map (M), reset (R).
- Pointer-based mobile joystick and brake / interact controls.
- Handcrafted low-poly island, eight destination pavilions, vehicle, roads, trees and signs.
- Simplified planar arcade collision, inertia and turn controls. This is not a suspension or Rapier rigid-body simulation.
- Mini-map, destination teleport, visited progress and persistent preferences.
- Paused driving while dialogs are open or the window loses focus.
- Web Audio synthesized motor, ambient chord and interactive notes; opt-in audio.
- Charging estimator with explicit demo assumptions, scripted AI workflow examples, synthesized musical pads. No live vehicle data, AI backend or actual podcast recordings.
- Original homepage fallback, with direct in-world homepage embedding.

## Content and maintenance

Edit `zones` in `catalog.js` to update project titles, destinations, coordinates and URLs. `app.js` owns DOM panels and input, `world.js` scene geometry, `physics.mjs` deterministic movement, `audio.js` sound. Preferences and visited areas are stored locally only.

Run `npm test` for physics behavior tests. Refresh Three.js vendor files from an audited installed package when upgrading.

## Hosting

Add `explore/` including `vendor/` to the existing Vikipedia repository. Keep the existing root homepage because the viewer embeds it. All internal module and asset paths are relative, so it can live under a GitHub Pages repository subpath. The GitHub upload is a separate branch and pull request; deployment follows merging.

Known validation limitation: the original homepage returns HTTP 200 and opens as a standalone page, but its iframe remained blank in the local in-app browser during the latest check. The new-tab link remains available.
