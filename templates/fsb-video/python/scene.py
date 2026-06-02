from manim import *

class MainScene(Scene):
    def construct(self):
        title = Text("{{NASLOV_VIDEA}}")
        self.play(Write(title))
        self.wait(1)
        
        # {{SADRZAJ}}
        
        self.play(FadeOut(title))
