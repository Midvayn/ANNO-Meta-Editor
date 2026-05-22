# ANNO Meta Editor

ANNO Meta Editor is a small local web tool for viewing, editing, formatting, and saving metadata in `.safetensors` model files and AI-generated image files.

It is especially useful for LoRA creators, ComfyUI users, dataset builders, and anyone who needs to inspect or clean metadata without uploading files to an external service.

## Screenshots

![ANNO-Meta-Editor](screenshots/screenshot1.jpg)

## Features

- Load `.safetensors` model metadata without manually digging through headers
- View tensor information from `.safetensors` files
- Edit writable metadata as JSON
- Format JSON with one click
- Validate JSON while editing
- Read PNG metadata from ComfyUI-generated images
- Extract ComfyUI prompts and workflow-related metadata
- Save metadata back to supported files
- Automatic backup before writing changes
- Local Gradio browser interface

## Supported Files

```text
.safetensors
.png
.jpg
.jpeg
.webp
```

PNG files are recommended for image metadata editing because they support text metadata best. JPG and WEBP support is more limited.

## Project Structure

```text
ANNO-MetaEditor/
├─ ANNO_MetaEditor.py
├─ Run_ANNO_MetaEditor.bat
├─ requirements.txt
├─ README.md
├─ LICENSE.txt
└─ .gitignore
```

## Installation

Install Python 3.10 or newer.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

On Windows, run:

```bat
Run_ANNO_MetaEditor.bat
```

Or start it manually:

```bash
python ANNO_MetaEditor.py
```

Then open this address in your browser:

```text
http://127.0.0.1:7860
```

The app also tries to open the browser automatically.

## Basic Workflow

1. Load a `.safetensors` model or an AI-generated image.
2. Review the full metadata in the read-only panel.
3. Edit the available metadata in JSON format.
4. Use **Format JSON** when needed.
5. Check the JSON validation status.
6. Click **Save changes**.
7. For ComfyUI images, use **Extract ComfyUI prompt** to pull prompt/workflow text from metadata.

## Notes

- The app runs locally.
- No files are uploaded to the cloud.
- A backup is created before metadata changes are written.
- JSON must be valid before saving.
- For strings, use double quotes, for example: `"model_name": "my_model"`.
- Editing `.safetensors` metadata rewrites the file with the original tensors and new metadata.

## Credits

Powered by ChatGPT and ANNO.
