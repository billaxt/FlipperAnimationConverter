import os
import sys
import glob
import subprocess
from PIL import Image, ImageEnhance

# ================= CONFIGURATION =================
# Automatically find the exe in the same folder as this script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG2FBM_PATH = os.path.join(CURRENT_DIR, "img2fbm.exe")

TARGET_SIZE = (128, 64)
FPS = 6

# Image Quality Settings
CONTRAST_FACTOR = 1.5
BRIGHTNESS_FACTOR = 1.1
SHARPNESS_FACTOR = 1.8

# Manifest Settings
MANIFEST_MIN_BUTTHURT = 0
MANIFEST_MAX_BUTTHURT = 18
MANIFEST_MIN_LEVEL = 1
MANIFEST_MAX_LEVEL = 30
MANIFEST_WEIGHT = 3
# =================================================

def convert_png_to_bm(png_path):
    """Runs the external img2fbm tool on a single PNG file."""
    if not os.path.exists(IMG2FBM_PATH):
        print(f"Error: img2fbm not found at: {IMG2FBM_PATH}")
        return False

    try:
        # Run the command: img2fbm.exe <path_to_png>
        subprocess.run([IMG2FBM_PATH, png_path], check=True, stdout=subprocess.DEVNULL)
        print(f"  [OK] Converted BM: {os.path.basename(png_path)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [!] Failed to convert {os.path.basename(png_path)}: {e}")
        return False

def generate_main_manifest(output_root):
    """Generates the master manifest.txt for all folders in Output."""
    print(f"\n--- Generating Manifest for {output_root} ---")
    
    # Find all subdirectories in the output folder
    # We assume every folder here is an animation
    subfolders = [f.name for f in os.scandir(output_root) if f.is_dir()]
    
    if not subfolders:
        print("No animation folders found to add to manifest.")
        return

    manifest_path = os.path.join(output_root, "manifest.txt")
    
    with open(manifest_path, "w") as f:
        # Write Header
        f.write("Filetype: Flipper Animation Manifest\n")
        f.write("Version: 1\n\n")
        
        # Write Entry for each folder
        for folder_name in subfolders:
            f.write(f"Name: {folder_name}\n")
            f.write(f"Min butthurt: {MANIFEST_MIN_BUTTHURT}\n")
            f.write(f"Max butthurt: {MANIFEST_MAX_BUTTHURT}\n")
            f.write(f"Min level: {MANIFEST_MIN_LEVEL}\n")
            f.write(f"Max level: {MANIFEST_MAX_LEVEL}\n")
            f.write(f"Weight: {MANIFEST_WEIGHT}\n\n")
            
    print(f"-> Created manifest.txt with {len(subfolders)} entries.")

def process_single_gif(input_path, output_root):
    filename = os.path.basename(input_path)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Create output folder
    folder_name = os.path.join(output_root, name_without_ext)
    os.makedirs(folder_name, exist_ok=True)

    print(f"Processing: {filename}...")

    img = Image.open(input_path)
    frames = []

    # --- PART 1: EXTRACT AND ENHANCE FRAMES ---
    try:
        while True:
            # Handle Transparency
            frame = img.convert("RGBA")
            background = Image.new("RGBA", frame.size, (255, 255, 255, 255))
            background.paste(frame, (0, 0), frame)
            frame = background.convert("RGB")

            # Resize
            frame = frame.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
            
            # Enhance
            enhancer = ImageEnhance.Sharpness(frame)
            frame = enhancer.enhance(SHARPNESS_FACTOR)
            enhancer = ImageEnhance.Contrast(frame)
            frame = enhancer.enhance(CONTRAST_FACTOR)
            enhancer = ImageEnhance.Brightness(frame)
            frame = enhancer.enhance(BRIGHTNESS_FACTOR)
            
            # Convert to 1-bit Dithered
            frame = frame.convert("L")
            frame = frame.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
            
            frames.append(frame)
            img.seek(img.tell() + 1)
    except EOFError:
        pass

    # --- PART 2: CONVERT TO BM & CLEANUP ---
    frame_order = []
    for i, frame in enumerate(frames):
        # 1. Save PNG temporarily
        png_filename = f"frame_{i}.png"
        png_full_path = os.path.join(folder_name, png_filename)
        frame.save(png_full_path, "PNG")
        frame_order.append(str(i))
        
        # 2. Create BM
        success = convert_png_to_bm(png_full_path)
        
        # 3. DELETE PNG (Cleanup)
        if success and os.path.exists(png_full_path):
            try:
                os.remove(png_full_path)
            except OSError:
                print(f"  [!] Warning: Could not delete temp file {png_filename}")

    # --- PART 3: CREATE PREVIEW GIF ---
    preview_path = os.path.join(folder_name, "_preview.gif")
    if frames:
        frames[0].save(
            preview_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000/FPS),
            loop=0
        )
        print(f"  [View] Created preview animation: {os.path.basename(preview_path)}")

    # --- PART 4: GENERATE META.TXT (Per Animation) ---
    duration_sec = 30
    
    with open(os.path.join(folder_name, "meta.txt"), "w") as f:
        f.write("Filetype: Flipper Animation\n")
        f.write("Version: 1\n\n")
        f.write("Width: 128\n")
        f.write("Height: 64\n")
        f.write(f"Passive frames: {len(frames)}\n")
        f.write("Active frames: 0\n")
        f.write(f"Frames order: {' '.join(frame_order)}\n")
        f.write("Active cycles: 0\n")
        f.write(f"Frame rate: {FPS}\n")
        f.write(f"Duration: {duration_sec}\n")
        f.write("Active cooldown: 0\n\n")
        f.write("Bubble slots: 0\n")

    print(f" -> Done! Output located in: {folder_name}\n")

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Batch Mode: python script.py <Output_Folder> <Input_Folder>")
        return

    output_folder = sys.argv[1]
    input_target = sys.argv[2]

    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if not os.path.exists(IMG2FBM_PATH):
        print(f"\nCRITICAL ERROR: img2fbm executable not found!")
        print(f"Looked for: {IMG2FBM_PATH}")
        print("Please verify the file is named 'img2fbm-win-x86_64.exe' and is in the same folder.\n")
        return

    # Check if input is folder or file
    if os.path.isdir(input_target):
        print(f"--- BATCH MODE: Scanning {input_target} for GIFs ---")
        gif_files = glob.glob(os.path.join(input_target, "*.gif"))
        
        if not gif_files:
            print("No .gif files found in that folder!")
            return

        for gif_path in gif_files:
            process_single_gif(gif_path, output_folder)
            
    elif os.path.isfile(input_target):
        process_single_gif(input_target, output_folder)
        
    else:
        print("Error: Input path not found.")
        return

    # --- PART 5: GENERATE ROOT MANIFEST ---
    # We do this at the very end to include ALL folders in Output
    generate_main_manifest(output_folder)

if __name__ == "__main__":
    main()