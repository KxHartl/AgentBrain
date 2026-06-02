# AI Agent Instructions for Manim Video

You are generating a ManimCE script for mathematical animations.
- **ALWAYS** output by modifying the corresponding `.py` file in `src/` directory.

## Structure

- Write Python code using the ManimCE library.
- Place all animation logic inside the `construct` method of `MainScene`.
- To render the video, use the command: `manim -pql src/scene.py MainScene` (for low-quality preview) or `manim -pqh src/scene.py MainScene` (for high quality).
- Place final renders into `dist/`.
