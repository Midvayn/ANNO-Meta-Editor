#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple

import gradio as gr
from PIL import Image
from PIL.ExifTags import TAGS
from safetensors.torch import load_file, save_file


class MetadataEditor:
    def __init__(self):
        self.current_file = None
        self.current_metadata = {}
        self.file_type = None

    def load_safetensors_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "rb") as f:
                header_size = int.from_bytes(f.read(8), "little")
                header = json.loads(f.read(header_size))

            metadata = header.get("__metadata__", {})
            tensors_info = {}

            for key, value in header.items():
                if key != "__metadata__":
                    tensors_info[key] = {
                        "dtype": value.get("dtype"),
                        "shape": value.get("shape"),
                        "data_offsets": value.get("data_offsets"),
                    }

            return {
                "metadata": metadata,
                "tensors_info": tensors_info,
                "total_tensors": len(tensors_info),
            }
        except Exception as e:
            return {"error": str(e)}

    def save_safetensors_metadata(self, file_path: str, new_metadata: Dict[str, Any]) -> bool:
        backup_path = file_path + ".backup"
        try:
            shutil.copy2(file_path, backup_path)
            tensors = load_file(file_path)
            save_file(tensors, file_path, metadata=new_metadata)
            os.remove(backup_path)
            return True
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.move(backup_path, file_path)
            print(f"Save error: {e}")
            return False

    def load_image_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            with Image.open(file_path) as img:
                metadata = {
                    "file_info": {
                        "format": img.format,
                        "mode": img.mode,
                        "size": img.size,
                        "filename": Path(file_path).name,
                    }
                }

                exif_data = {}
                try:
                    if hasattr(img, "_getexif") and img._getexif():
                        for tag_id, value in img._getexif().items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_data[tag] = str(value)
                except Exception:
                    pass

                if exif_data:
                    metadata["exif"] = exif_data

                png_info = {}
                if hasattr(img, "info") and img.info:
                    for key, value in img.info.items():
                        try:
                            if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
                                png_info[key] = json.loads(value)
                            else:
                                png_info[key] = value
                        except Exception:
                            png_info[key] = value

                if png_info:
                    metadata["png_info"] = png_info

                comfyui_data = {}
                for key in ["workflow", "prompt", "extra_pnginfo"]:
                    if key in png_info:
                        try:
                            if isinstance(png_info[key], str):
                                comfyui_data[key] = json.loads(png_info[key])
                            else:
                                comfyui_data[key] = png_info[key]
                        except Exception:
                            comfyui_data[key] = png_info[key]

                if comfyui_data:
                    metadata["comfyui"] = comfyui_data

                return metadata
        except Exception as e:
            return {"error": str(e)}

    def save_image_metadata(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        backup_path = file_path + ".backup"
        try:
            with Image.open(file_path) as img:
                shutil.copy2(file_path, backup_path)

                if file_path.lower().endswith(".png"):
                    from PIL.PngImagePlugin import PngInfo

                    png_info = PngInfo()
                    for key, value in metadata.items():
                        if isinstance(value, (dict, list)):
                            png_info.add_text(key, json.dumps(value, ensure_ascii=False))
                        else:
                            png_info.add_text(key, str(value))

                    img.save(file_path, pnginfo=png_info)
                else:
                    img.save(file_path, quality=95)
                    print(f"Warning: {Path(file_path).suffix} does not support editable text metadata.")

            if os.path.exists(backup_path):
                os.remove(backup_path)
            return True
        except Exception as e:
            print(f"Image save error: {e}")
            if os.path.exists(backup_path):
                shutil.move(backup_path, file_path)
            return False


editor = MetadataEditor()


def load_file_metadata(file_path: str) -> Tuple[str, str, str]:
    if not file_path or not os.path.exists(file_path):
        return "File not found", "", ""

    editor.current_file = file_path
    file_ext = Path(file_path).suffix.lower()

    if file_ext == ".safetensors":
        editor.file_type = "safetensors"
        metadata = editor.load_safetensors_metadata(file_path)
    elif file_ext in [".png", ".jpg", ".jpeg", ".webp"]:
        editor.file_type = "image"
        metadata = editor.load_image_metadata(file_path)
    else:
        return "Unsupported file type", "", ""

    if "error" in metadata:
        return f"Load error: {metadata['error']}", "", ""

    editor.current_metadata = metadata
    display_text = json.dumps(metadata, ensure_ascii=False, indent=2)

    if editor.file_type == "safetensors":
        editable_metadata = metadata.get("metadata", {})
    else:
        editable_metadata = metadata.get("png_info", {})

    editable_text = json.dumps(editable_metadata, ensure_ascii=False, indent=2)
    return display_text, editable_text, f"Loaded {editor.file_type} file: {Path(file_path).name}"


def validate_json(json_text: str) -> str:
    if not json_text.strip():
        return "✅ Field is empty"

    try:
        json.loads(json_text)
        return "✅ Valid JSON"
    except json.JSONDecodeError as e:
        return f"❌ JSON error: {e.msg} (line {e.lineno})"
    except Exception as e:
        return f"❌ Error: {e}"


def format_json(json_text: str) -> str:
    if not json_text.strip():
        return "{}"

    try:
        parsed = json.loads(json_text)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        return json_text


def save_metadata(editable_metadata: str) -> str:
    if not editor.current_file:
        return "No file loaded"

    if not editable_metadata.strip():
        return "❌ Metadata field is empty"

    try:
        new_metadata = json.loads(editable_metadata)

        if editor.file_type == "safetensors":
            success = editor.save_safetensors_metadata(editor.current_file, new_metadata)
        elif editor.file_type == "image":
            success = editor.save_image_metadata(editor.current_file, new_metadata)
        else:
            return "Unsupported file type"

        if success:
            return f"✅ Metadata saved to {Path(editor.current_file).name}"
        return "❌ Metadata save failed"
    except json.JSONDecodeError as e:
        return f"❌ JSON error on line {e.lineno}: {e.msg}\n💡 Check quotes and commas."
    except Exception as e:
        return f"❌ Error: {e}"


def extract_comfyui_prompt(metadata_text: str) -> str:
    try:
        metadata = json.loads(metadata_text)

        prompt_sources = [
            metadata.get("comfyui", {}).get("prompt", ""),
            metadata.get("comfyui", {}).get("workflow", ""),
            metadata.get("png_info", {}).get("prompt", ""),
            metadata.get("png_info", {}).get("workflow", ""),
            metadata.get("png_info", {}).get("parameters", ""),
            metadata.get("prompt", ""),
            metadata.get("parameters", ""),
            metadata.get("workflow", ""),
        ]

        source_names = [
            "ComfyUI Prompt",
            "ComfyUI Workflow",
            "PNG Prompt",
            "PNG Workflow",
            "PNG Parameters",
            "Direct Prompt",
            "Direct Parameters",
            "Direct Workflow",
        ]

        extracted_info = {}

        for i, source in enumerate(prompt_sources):
            if source:
                if isinstance(source, dict):
                    if "prompt" in str(source).lower():
                        text_prompts = []
                        for key, value in source.items():
                            if isinstance(value, dict):
                                inputs = value.get("inputs", {})
                                if "text" in inputs:
                                    text_prompts.append(f"{key}: {inputs['text']}")

                        if text_prompts:
                            extracted_info[source_names[i]] = "\n".join(text_prompts)
                        else:
                            extracted_info[source_names[i]] = json.dumps(source, ensure_ascii=False, indent=2)
                    else:
                        extracted_info[source_names[i]] = json.dumps(source, ensure_ascii=False, indent=2)
                else:
                    extracted_info[source_names[i]] = str(source)

        if extracted_info:
            result = []
            for name, content in extracted_info.items():
                result.append(f"=== {name} ===")
                result.append(content)
                result.append("")
            return "\n".join(result)

        return "❌ No prompt found in metadata"
    except Exception as e:
        return f"❌ Prompt extraction error: {e}"


def create_gradio_interface():
    with gr.Blocks(title="ANNO Meta Editor", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🔧 ANNO Meta Editor")
        gr.Markdown("Local metadata editor for `.safetensors` models and ComfyUI-generated images.")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📁 Load file")
                file_input = gr.File(
                    label="Select a file (.safetensors, .png, .jpg, .webp)",
                    file_types=[".safetensors", ".png", ".jpg", ".jpeg", ".webp"],
                )

                status_output = gr.Textbox(label="Status", interactive=False, lines=1)

                gr.Markdown("## 🛠️ Actions")
                save_btn = gr.Button("💾 Save changes", variant="primary")
                format_btn = gr.Button("🎨 Format JSON")
                extract_prompt_btn = gr.Button("📝 Extract ComfyUI prompt")

                json_status = gr.Textbox(
                    label="JSON validation",
                    interactive=False,
                    lines=1,
                    value="✅ Ready for input",
                )

            with gr.Column(scale=2):
                gr.Markdown("## 👁️ Full metadata view")
                full_metadata_display = gr.Textbox(
                    label="All metadata (read-only)",
                    lines=15,
                    interactive=False,
                    show_copy_button=True,
                )

                gr.Markdown("## ✏️ Editable metadata")
                editable_metadata = gr.Textbox(
                    label="Editable metadata (JSON)",
                    lines=10,
                    interactive=True,
                    show_copy_button=True,
                    placeholder="Load a file to edit its metadata",
                )

                gr.Markdown("## 📝 Extracted prompt")
                extracted_prompt = gr.Textbox(
                    label="ComfyUI prompt",
                    lines=8,
                    interactive=False,
                    show_copy_button=True,
                )

        file_input.change(
            fn=load_file_metadata,
            inputs=[file_input],
            outputs=[full_metadata_display, editable_metadata, status_output],
        )

        save_btn.click(fn=save_metadata, inputs=[editable_metadata], outputs=[status_output])
        format_btn.click(fn=format_json, inputs=[editable_metadata], outputs=[editable_metadata])
        editable_metadata.change(fn=validate_json, inputs=[editable_metadata], outputs=[json_status])
        extract_prompt_btn.click(fn=extract_comfyui_prompt, inputs=[full_metadata_display], outputs=[extracted_prompt])

        gr.Markdown(
            """
### Instructions

1. Load a `.safetensors` model or an image file.
2. Review the full metadata in the read-only panel.
3. Edit the available metadata fields in JSON format.
4. Check the JSON validation indicator.
5. Use **Format JSON** when needed.
6. Save changes with **Save changes**.
7. Use **Extract ComfyUI prompt** for ComfyUI images.

### Important

- A backup is created before writing changes.
- JSON must be valid before saving.
- Use double quotes for strings: `"key": "value"`.
- Supported files: `.safetensors`, `.png`, `.jpg`, `.jpeg`, `.webp`.
- PNG files support text metadata best. JPG and WEBP metadata support is limited.

### Example JSON

```json
{
  "model_name": "test_model",
  "description": "Model description",
  "version": "1.0"
}
```
"""
        )

    return interface


def main():
    print("Starting ANNO Meta Editor...")
    print("Server address: http://127.0.0.1:7860")

    interface = create_gradio_interface()

    try:
        interface.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            debug=False,
            show_error=True,
            inbrowser=True,
        )
    except Exception as e:
        print(f"Launch error: {e}")
        print("Try another port or check that port 7860 is free.")


if __name__ == "__main__":
    main()
