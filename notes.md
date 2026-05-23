## Project Notes / Next Steps

- Start a small side project focused on learning **shaders** and understanding how to layer multiple shader effects on different rendering layers in Pygame.  
  Explore implementations using **ModernGL** or another library that is compatible with **WebAssembly**, so the project can potentially run in the browser.

- Continue development of the main **Pygame** version of the project.

- Test the Pygame port more thoroughly.  
  This task can be done offline or during low-energy periods since it mainly involves validation and bug detection.

- Research the capabilities and limitations of **WebAssembly** to better understand what types of systems and features can realistically run in a browser-based game.


The Short Answer: Yes, but with some caveats.

Pygame → WebAssembly Pipeline
Pygbag is the main tool for compiling Pygame games to WebAssembly. It packages your Python/Pygame code using CPython compiled to WASM via Emscripten.
bashpip install pygbag
pygbag your_game_folder/
This generates a build/web folder you can upload directly to itch.io.

Shaders in Pygame for the Web
This is where it gets nuanced. Pygame itself doesn't natively support GLSL shaders — but there are two solid approaches:
Option 1: pygame + ModernGL (Recommended for shaders)
ModernGL is an OpenGL wrapper that works alongside Pygame. You render your game to a surface, upload it as a texture, then apply GLSL shaders via ModernGL.
pythonimport pygame
import moderngl

# Pygame handles game logic/input
# ModernGL handles shader rendering
ctx = moderngl.create_context()
Web compatibility: ModernGL targets OpenGL, but browsers use WebGL. Pygbag + ModernGL has limited/experimental support — it's the hardest path.
Option 2: pygame-ce + GLSL via pygame's built-in GL support
pygame-ce (Community Edition) has better OpenGL integration. Combined with Pygbag, this has better web export support than vanilla pygame + ModernGL.
Option 3: Skip shaders in the web build
Keep shaders for native builds only, and use Pygame's software rendering (Surface effects, pixel arrays) as fallback for the web build. Many itch.io Pygame games do this.

Recommended Stack for itch.io
GoalToolWeb exportPygbagShaders (native)ModernGL or pygame-ceShaders (web)pygame-ce + WebGL (experimental)Easy shaders alternativeConsider Godot or Defold instead

Practical Advice

Start with Pygbag first — get your game running in the browser without shaders, then layer in shader support
Use #ifdef-style conditional loading — detect if running under Pygbag and skip shaders
pygame-ce is a drop-in replacement for pygame and has better long-term web support
For post-processing effects (bloom, CRT, etc.), the ModernGL + Pygbag combo can work but expect to debug WebGL context issues

The ecosystem is moving fast — Pygbag's GitHub issues/discussions are the best place to check current WebGL shader compatibility status.

[ ] - fix button shadow glitch, flickers as you let go of a button 
[ ] - bug: when continueing the game the next cards are always the same (decending spades)