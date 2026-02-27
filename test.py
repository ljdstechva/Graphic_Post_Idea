from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
import sys
import zipfile
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk


EXCLUDED_FALLBACK_FILENAMES = {
    "CLIENT_PROFILE.md",
    "ADDITIONAL_INSTRUCTION.md",
    "HISTORY_TITLE.md",
    "CAPTION_SAMPLES.md",
}
CLIENTS_DIRNAME = "Clients"
DELETED_CLIENTS_DIRNAME = "Deleted Clients"
AGENTS_DIRNAME = "Agents"
SOURCE_SCRIPT_FILENAME = "test.py"
TEST_SCRIPT_FILENAME = "test.py"
SMARCOMMS_FILENAME = "SMARCOMMS.md"
REGENERATE_FILENAME = "REGENERATE.md"
CLIENT_PROFILE_AUTOFILL_FILENAME = "CLIENT_PROFILE_AUTOFILL.md"
AGENTS_CONTROL_FILENAMES = {"AGENTS.md", "AGENTS.override.md"}
AGENTS_RUNBOOK_LABEL = f"{AGENTS_DIRNAME}/{SMARCOMMS_FILENAME}"
AGENTS_REGENERATE_LABEL = f"{AGENTS_DIRNAME}/{REGENERATE_FILENAME}"
AGENTS_CLIENT_PROFILE_AUTOFILL_LABEL = f"{AGENTS_DIRNAME}/{CLIENT_PROFILE_AUTOFILL_FILENAME}"
CAPTION_SAMPLES_FILENAME = "CAPTION_SAMPLES.md"
CAPTION_SAMPLE_MINIMUM_COUNT = 5
APP_LOGO_FILENAME = "graphic_post_logo.png"
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
WEEK_OPTIONS = [1, 2, 3, 4]
DEFAULT_CODEX_MODEL = "gpt-5.3-codex"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_CODEX_REASONING_EFFORT = "medium"
DEFAULT_CODEX_MODEL_DISCOVERY_TIMEOUT_SECONDS = 15.0
DEFAULT_CODEX_STATUS_TIMEOUT_SECONDS = 45.0
NODEJS_DOWNLOAD_URL = "https://nodejs.org/en/download"
POST_DETAILS_VALUE_ENTRY_WIDTH = 72
POST_DETAILS_COPY_BUTTON_WIDTH = 12
COPY_TOAST_TEXT = "Copied to Clipboard"
COPY_TOAST_STEPS = 10
COPY_TOAST_STEP_DELAY_MS = 40
COPY_TOAST_FLOAT_PIXELS = 24
_AUTO_CTRL_BREAK_EVENT = object()

DEFAULT_REGENERATE_CONTENT = """# REGENERATE Post Idea

## Objective
- You have been invoked to completely rewrite and replace a specific graphic post idea for a client.
- The user prompt will provide the `[Client Name]`, the `[Graphic Title]` of the targeted post, and the `[Remarks/Reason]` for regeneration.

## Execution Steps
1. Navigate to the `Clients/[Client Name]/` directory.
2. Carefully review `CLIENT_PROFILE.md` and `CAPTION_SAMPLES.md` to ensure deep alignment with the client's tone, brand voice, and required formatting.
3. Locate the latest generated `[Client Name]_*.md` or `Graphic_Post_Ideas_*.md` file.
4. Inside that file, find the exact post section that matches the provided `[Graphic Title]`.
5. Read the `[Remarks/Reason]` provided in the user prompt. Use this as your primary directive.
6. COMPLETELY REWRITE the entire post from scratch. Do not just lightly edit the existing fields. You must generate a brand new Graphic Title, Graphic Subtitle, CTA, Optional List Title, Optional List, Canva Picture Keyword, Canva Design Keyword, and 3 brand new Captions. Use the exact fields required by the SMARCOMMS standard.
7. Pull the Website, Phone Number, and Email fresh from the `CLIENT_PROFILE.md`.
8. Replace the ENTIRE OLD POST BLOCK (from its `Post #` header down to its last caption) with your entirely new generated block.

## Critical Output Formatting
Your replaced block MUST strictly follow this exact format for parsing to work correctly:
```markdown
Post [Number] - [Optional Brief Header]
1. Graphic Title: [Your New Engaging Title]
2. Graphic Subtitle: [Your New Subtitle]
3. CTA: [Max 2 words]
4. Title for Optional List: [New List Title]
5. Optional List:
- [Point 1]
- [Point 2]
- [Point 3]
- [Point 4]
- [Point 5]
- [Point 6]
6. Website: [From Profile]
7. Phone Number: [From Profile]
8. Email: [From Profile]
9. Canva Picture Keyword: [New Keywords]
10. Canva Design Keyword: [New Keywords]
11. Caption 1:
[Your New Caption 1 paragraphs...]

12. Caption 2:
[Your New Caption 2 paragraphs...]

13. Caption 3:
[Your New Caption 3 paragraphs...]
```

## Safety Guardrails
- **Critical:** Do NOT touch, modify, or delete any other posts or sections in the file. Keep the rest of the file perfectly intact.
- Do NOT output extra text, commentary, or markdown formatting outside the replaced block.
"""

DEFAULT_SMARCOMMS_CONTENT = """# SMARCOMMS Runbook

## Scope and Safety
- Root workspace for this runbook is the folder where `SMARCOMMS.md` exists.
- Only perform CRUD inside this root folder and its subfolders.
- Never create, update, move, or delete files/folders outside this root.
- File deletion is strictly limited to generated graphic idea files only: `Graphic_Post_Ideas_*.md` and `[Client Name]_*.md` that contain graphic post ideas.
- Do not delete any other files.

## Required Skill
- Always use `$content-creator` when generating graphic post ideas for any client.
- Apply the skill's social media workflow to keep voice, quality, and platform fit consistent.

## Client Source of Truth
- Each client folder must be treated independently.
- Read `CLIENT_PROFILE.md` first in each client folder.
- Before any task in a client folder, check for `ADDITIONAL_INSTRUCTION.md`.
- If `ADDITIONAL_INSTRUCTION.md` does not exist, proceed with the task.
- If `ADDITIONAL_INSTRUCTION.md` exists, strictly follow it before proceeding.
- This `ADDITIONAL_INSTRUCTION.md` check is mandatory and prioritized for every client folder.
- Read `CAPTION_SAMPLES.md` before generating captions.
- `CAPTION_SAMPLES.md` must contain at least 5 approved caption samples.
- Match caption format, length, perspective, spacing, word choice, and tone to `CAPTION_SAMPLES.md`.
- Use client website links from the profile for factual references.
- Do not use unrelated external sources.
- If phone or email is not available on the approved source, write `N/A`.

## Post Volume Logic
- Use the `## Posts Per Week` section in `CLIENT_PROFILE.md` as the required volume.
- If you ever receive only monthly totals, convert as follows:
  - `10 posts/month` -> Week 1: 2, Week 2: 3, Week 3: 2, Week 4: 3
  - `12 posts/month` -> 3 posts each week
  - `20 posts/month` -> 5 posts each week

## Output File Rules
- Generate an additional markdown file in each client folder for post ideas.
- Do not overwrite existing idea files.
- File naming format:
  - `[Client Name]_YYYY-MM-DD_HH-mm.md`
- If the same timestamp filename already exists, append a version suffix:
  - `[Client Name]_YYYY-MM-DD_HH-mm_v2.md`

## Title History Guard
- Before generating any new post ideas, always open and review `HISTORY_TITLE.md` in the same client folder.
- If `HISTORY_TITLE.md` does not exist yet, create it first.
- Before generating new ideas, scan the client folder for existing `Graphic_Post_Ideas_*.md` files and existing `[Client Name]_*.md` idea files.
- Extract all `Graphic Title` entries from those existing idea files and append them to `HISTORY_TITLE.md` with source file reference.
- While appending history entries, keep `HISTORY_TITLE.md` clean by avoiding duplicate title entries.
- Delete existing `[Client Name]_*.md` files before generating new one. Strictly delete only this file and nothing else.
- Before finalizing new generation, run a title analysis against all titles in `HISTORY_TITLE.md`.
- Any generated `Graphic Title` that exactly matches or closely repeats a title in `HISTORY_TITLE.md` must be rejected and regenerated.
- Every generated `Graphic Title` must be unique versus all existing titles in `HISTORY_TITLE.md`.
- After generating a new `[Client Name]_*.md` file, append all newly generated graphic titles to `HISTORY_TITLE.md` with source file reference.

## Output Requirements (Per Post)
Post # - Type of Post
1. Graphic Title - engaging, unique, click-driven, 4-10 words.
2. Graphic Subtitle - concise, informative, audience-focused, one sentence.
3. CTA (max 2 words) - action-oriented and aligned with the topic.
4. Optional List Title - 1-4 words, aligned with Optional List.
5. Optional List - exactly 6 points, each 2-5 words, Proper Casing.
6. Website - client website or relevant approved service link.
7. Phone Number - from approved source, else `N/A`.
8. Email - from approved source, else `N/A`.
9. Canva Picture Keyword - max 3 words, image search focused.
10. Canva Design Keyword - max 3 words, design style focused.
11. Caption 1 - social caption aligned to `CAPTION_SAMPLES.md` style and spacing.
12. Caption 2 - social caption aligned to `CAPTION_SAMPLES.md` style and spacing.
13. Caption 3 - social caption aligned to `CAPTION_SAMPLES.md` style and spacing.

## Formatting Rules
- Generate ideas starting from `Post 1` and continue sequentially.
- Keep every post idea unique within the same client file.
- Keep output in markdown.
- Keep tone aligned with each client profile.
- Keep caption paragraph spacing consistent with `CAPTION_SAMPLES.md`.

## Quality Loop (Must Pass)
- Pass 1: Completeness check against all required fields.
- Pass 2: Brand-fit and tone check against `CLIENT_PROFILE.md`.
- Pass 3: Uniqueness check to remove repeated angles/titles.
- Pass 4: `HISTORY_TITLE.md` analysis check to confirm no generated `Graphic Title` already exists or closely repeats an existing history title.
- Pass 5: Source check for website, product/service, phone, and email accuracy.
- Self-score quality from 0-100.
- If score is below 100, revise and rerun checks until 100.
"""

DEFAULT_CLIENT_PROFILE_AUTOFILL_CONTENT = """# Client Profile Auto-Fill Runbook

## Scope
- Root workspace is where this runbook exists.
- Only perform CRUD inside this workspace and subfolders.
- Update only the selected `Clients/[Client Name]/CLIENT_PROFILE.md`.
- Do not modify any other file.

## Required Skill
- Use `$content-creator` if available in the runtime.
- Apply it to keep profile writing factual and brand-aware.

## Source Constraints
- If a website URL is provided:
  - Only use that website and pages linked from it.
  - Do not use search engines or external websites.
- If no website URL is provided:
  - Use only the exact pasted client information.
- Never invent facts or fill unknown values with guesses.

## Editing Rules
- Keep all field names and order exactly as-is in `CLIENT_PROFILE.md`.
- Fill only values supported by allowed sources.
- If a field has no supported information, leave it blank.
- Preserve markdown format with `Field: Value` or blank value.
"""

POST_METADATA_FIELDS = {"Post Number", "Post Header"}
PREFERRED_DISPLAY_FIELD_ORDER = [
    "Graphic Title",
    "Graphic Subtitle",
    "CTA",
    "Title for Optional List",
    "Optional List",
    "Website",
    "Phone Number",
    "Email",
    "Canva Picture Keyword",
    "Canva Design Keyword",
    "Caption 1",
    "Caption 2",
    "Caption 3",
]

CANONICAL_FIELD_NAME_MAP = {
    "graphic title": "Graphic Title",
    "graphic subtitle": "Graphic Subtitle",
    "cta": "CTA",
    "title for optional list": "Title for Optional List",
    "optional list title": "Title for Optional List",
    "optional list": "Optional List",
    "website": "Website",
    "phone number": "Phone Number",
    "email": "Email",
    "canva picture keyword": "Canva Picture Keyword",
    "canva design keyword": "Canva Design Keyword",
    "caption 1": "Caption 1",
    "caption 2": "Caption 2",
    "caption 3": "Caption 3",
}

CONTEXT_PERCENT_KEYS = {
    "contextleftpercent",
    "contextleft",
    "remainingcontextpercent",
    "remainingcontext",
    "contextremainingpercent",
}
CONTEXT_LEFT_TEXT_PATTERN = re.compile(
    r"(?i)(?:context(?:\s+left)?\s*[:=]\s*(\d{1,3})\s*%|(\d{1,3})\s*%\s*context(?:\s+left)?)"
)
GRAPHIC_POST_IDEAS_PATTERN = re.compile(r"^Graphic_Post_Ideas_.*\.md$", re.IGNORECASE)
NUMBERED_FIELD_PATTERN = re.compile(r"^\s*(\d+[A-Za-z]?)\.\s+(.*\S)\s*$")
FIELD_WITH_COLON_PATTERN = re.compile(r"^\s*(.+?)\s*:(?!/)\s*(.*)$")
FIELD_WITH_DASH_PATTERN = re.compile(r"^\s*(.+?)\s+-\s*(.*)$")
POST_FILENAME_TIMESTAMP_PATTERN = re.compile(
    r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})\.md$",
    re.IGNORECASE,
)
CLIENT_PROFILE_FIELD_PATTERN = re.compile(r"^\s*([^:\n][^:]*)\s*:\s*(.*)$")
INVALID_CLIENT_NAME_CHARS = set('<>:"/\\|?*')
CLIENT_PROFILE_FIELDS = [
    "Client Name",
    "Website",
    "Business Name",
    "What does your business do?",
    "Who is your target audience?",
    "Are there any products/services we should focus on promoting?",
    "Are there any hashtags you would like us to include?",
    "Do any celebrities or top brands use your products/services?",
    "What are your brand colours?",
    "Who are your biggest competitors?",
    "Tone of voice",
    "I agree to the terms and conditions",
    "Business scope (intake form)",
    "Focus services/products (intake form)",
    "Content focus themes from weekly planning",
    "Type of Posts Per Week - Week 1",
    "Type of Posts Per Week - Week 2",
    "Type of Posts Per Week - Week 3",
    "Type of Posts Per Week - Week 4",
    "Tone",
    "Posts Per Week - Week 1",
    "Posts Per Week - Week 2",
    "Posts Per Week - Week 3",
    "Posts Per Week - Week 4",
    "Country",
    "Remarks",
]
CLIENT_PROFILE_DEFAULT_VALUES = {
    "I agree to the terms and conditions": "Yes",
    "Country": "US",
}
CAPTION_SAMPLE_FIELDS = [
    f"Caption Sample {index}"
    for index in range(1, CAPTION_SAMPLE_MINIMUM_COUNT + 1)
]
MULTILINE_POST_FIELDS = {"Caption 1", "Caption 2", "Caption 3"}


def normalize_client_name(client_name: str) -> str:
    return re.sub(r"\s+", " ", client_name).strip()


def build_client_profile_default_values(client_name: str) -> dict[str, str]:
    values = {field: "" for field in CLIENT_PROFILE_FIELDS}
    values.update(CLIENT_PROFILE_DEFAULT_VALUES)
    values["Client Name"] = normalize_client_name(client_name)
    return values


def parse_client_profile_markdown(content: str, client_name: str) -> dict[str, str]:
    values = build_client_profile_default_values(client_name)
    known_fields = set(CLIENT_PROFILE_FIELDS)
    current_field: str | None = None

    for raw_line in content.splitlines():
        field_match = CLIENT_PROFILE_FIELD_PATTERN.match(raw_line)
        if field_match is not None:
            field_name = re.sub(r"\s+", " ", field_match.group(1)).strip()
            if field_name in known_fields:
                values[field_name] = field_match.group(2).strip()
                current_field = field_name
            else:
                current_field = None
            continue

        if current_field is None:
            continue

        continuation = raw_line.strip()
        if not continuation:
            continue
        if values[current_field]:
            values[current_field] = f"{values[current_field]}\n{continuation}"
        else:
            values[current_field] = continuation

    if not values["Client Name"]:
        values["Client Name"] = normalize_client_name(client_name)
    return values


def build_client_profile_markdown(
    client_name: str,
    field_values: dict[str, str] | None = None,
) -> str:
    values = build_client_profile_default_values(client_name)
    if field_values is not None:
        for field in CLIENT_PROFILE_FIELDS:
            if field in field_values:
                values[field] = field_values[field].strip()

    if not values["Client Name"]:
        values["Client Name"] = normalize_client_name(client_name)

    lines: list[str] = []
    for field in CLIENT_PROFILE_FIELDS:
        field_value = values[field].strip()
        if field_value and "\n" not in field_value:
            lines.append(f"{field}: {field_value}")
            continue
        lines.append(f"{field}:")
        if field_value:
            lines.extend(fragment.rstrip() for fragment in field_value.splitlines())

    return "\n".join(lines).rstrip() + "\n"


def build_history_title_markdown(client_name: str) -> str:
    normalized_name = normalize_client_name(client_name)
    return f"# {normalized_name} History Title\n"


def parse_caption_samples_markdown(content: str) -> dict[str, str]:
    values = {field: "" for field in CAPTION_SAMPLE_FIELDS}
    known_fields = set(CAPTION_SAMPLE_FIELDS)
    current_field: str | None = None

    for raw_line in content.splitlines():
        field_match = CLIENT_PROFILE_FIELD_PATTERN.match(raw_line)
        if field_match is not None:
            field_name = re.sub(r"\s+", " ", field_match.group(1)).strip()
            if field_name in known_fields:
                values[field_name] = field_match.group(2).rstrip()
                current_field = field_name
            else:
                current_field = None
            continue

        heading_match = re.match(r"^\s*#{1,6}\s*(Caption Sample \d+)\s*$", raw_line, re.IGNORECASE)
        if heading_match is not None:
            heading_field = re.sub(r"\s+", " ", heading_match.group(1)).strip().title()
            if heading_field in known_fields:
                current_field = heading_field
            else:
                current_field = None
            continue

        if current_field is None:
            continue

        continuation = raw_line.rstrip()
        if values[current_field]:
            values[current_field] = f"{values[current_field]}\n{continuation}"
        else:
            values[current_field] = continuation

    return values


def build_caption_samples_markdown(
    client_name: str,
    field_values: dict[str, str] | None = None,
) -> str:
    normalized_name = normalize_client_name(client_name)
    values = {field: "" for field in CAPTION_SAMPLE_FIELDS}
    if field_values is not None:
        for field in CAPTION_SAMPLE_FIELDS:
            if field in field_values:
                values[field] = field_values[field]

    lines = [
        f"# {normalized_name} Caption Samples",
        "",
        f"Provide at least {CAPTION_SAMPLE_MINIMUM_COUNT} caption samples in this Field: Value format.",
        "",
    ]

    for field in CAPTION_SAMPLE_FIELDS:
        lines.append(f"{field}:")
        field_value = values[field].rstrip()
        if field_value:
            lines.extend(fragment.rstrip() for fragment in field_value.splitlines())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def create_client_scaffold_files(client_dir: Path, client_name: str) -> None:
    (client_dir / "CLIENT_PROFILE.md").write_text(
        build_client_profile_markdown(client_name),
        encoding="utf-8",
    )
    (client_dir / "HISTORY_TITLE.md").write_text(
        build_history_title_markdown(client_name),
        encoding="utf-8",
    )
    (client_dir / CAPTION_SAMPLES_FILENAME).write_text(
        build_caption_samples_markdown(client_name),
        encoding="utf-8",
    )


def ensure_caption_samples_files_for_clients(base_dir: Path) -> None:
    clients_root = get_clients_root(base_dir)
    if not clients_root.is_dir():
        return

    for child in clients_root.iterdir():
        if not child.is_dir():
            continue
        caption_samples_path = child / CAPTION_SAMPLES_FILENAME
        if caption_samples_path.exists():
            continue
        try:
            caption_samples_path.write_text(
                build_caption_samples_markdown(child.name),
                encoding="utf-8",
            )
        except OSError:
            continue


def _sort_paths_by_newest(paths: list[Path]) -> list[Path]:
    return sorted(
        paths,
        key=lambda p: (p.stat().st_mtime, p.name.lower()),
        reverse=True,
    )


def _discover_client_files(client_dir: Path, client_name: str) -> list[Path]:
    preferred = [p for p in client_dir.rglob(f"{client_name}_*.md") if p.is_file()]
    if preferred:
        return _sort_paths_by_newest(preferred)

    graphic_posts = [p for p in client_dir.rglob("Graphic_Post_Ideas_*.md") if p.is_file()]
    if graphic_posts:
        return _sort_paths_by_newest(graphic_posts)

    generic = [
        p
        for p in client_dir.rglob("*_*.md")
        if p.is_file() and p.name not in EXCLUDED_FALLBACK_FILENAMES
    ]
    return _sort_paths_by_newest(generic)


def get_clients_root(base_dir: Path) -> Path:
    return base_dir / CLIENTS_DIRNAME


def get_general_agents_root(base_dir: Path) -> Path:
    return base_dir / AGENTS_DIRNAME


def get_smarcomms_runbook_path(base_dir: Path) -> Path:
    return get_general_agents_root(base_dir) / SMARCOMMS_FILENAME


def get_client_profile_autofill_instruction_path(base_dir: Path) -> Path:
    return get_general_agents_root(base_dir) / CLIENT_PROFILE_AUTOFILL_FILENAME


def ensure_client_profile_autofill_instruction(base_dir: Path) -> Path:
    instruction_path = get_client_profile_autofill_instruction_path(base_dir)
    instruction_path.parent.mkdir(parents=True, exist_ok=True)
    if not instruction_path.exists():
        instruction_path.write_text(DEFAULT_CLIENT_PROFILE_AUTOFILL_CONTENT, encoding="utf-8")
    return instruction_path


def sync_legacy_general_agents_into_agents(base_dir: Path) -> list[Path]:
    agents_root = get_general_agents_root(base_dir)
    agents_root.mkdir(parents=True, exist_ok=True)

    copied_paths: list[Path] = []
    for source_path in base_dir.glob("*.md"):
        if not source_path.is_file():
            continue
        if source_path.name in AGENTS_CONTROL_FILENAMES:
            continue

        destination_path = agents_root / source_path.name
        if destination_path.exists():
            continue

        shutil.copy2(source_path, destination_path)
        copied_paths.append(destination_path)

    return copied_paths


def should_use_multiline_post_field(field_name: str) -> bool:
    return field_name in MULTILINE_POST_FIELDS


def resolve_runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_bundled_resource(file_name: str, runtime_base_dir: Path) -> Path | None:
    candidates: list[Path] = [runtime_base_dir / file_name]

    if getattr(sys, "frozen", False):
        meipass_dir = getattr(sys, "_MEIPASS", None)
        if meipass_dir:
            candidates.insert(0, Path(meipass_dir) / file_name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_editable_source_text(runtime_base_dir: Path) -> str | None:
    source_path = resolve_bundled_resource(SOURCE_SCRIPT_FILENAME, runtime_base_dir)
    if source_path is None and not getattr(sys, "frozen", False):
        source_path = Path(__file__).resolve()
    if source_path is None:
        return None

    try:
        return source_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def load_default_smarcomms_text(runtime_base_dir: Path) -> str:
    candidate_paths: list[Path] = []

    candidate_paths.append(get_smarcomms_runbook_path(runtime_base_dir))

    bundled_runbook = resolve_bundled_resource(SMARCOMMS_FILENAME, runtime_base_dir)
    if bundled_runbook is not None:
        candidate_paths.append(bundled_runbook)

    candidate_paths.append(get_smarcomms_runbook_path(runtime_base_dir.parent))

    # Prefer a revised runbook one directory up (for source layouts like repo/subfolder).
    candidate_paths.append(runtime_base_dir.parent / SMARCOMMS_FILENAME)

    if not getattr(sys, "frozen", False):
        script_dir = Path(__file__).resolve().parent
        candidate_paths.append(get_smarcomms_runbook_path(script_dir))
        candidate_paths.append(get_smarcomms_runbook_path(script_dir.parent))
        candidate_paths.append(script_dir / SMARCOMMS_FILENAME)
        candidate_paths.append(script_dir.parent / SMARCOMMS_FILENAME)

    seen_paths: set[Path] = set()
    for candidate in candidate_paths:
        if candidate in seen_paths:
            continue
        seen_paths.add(candidate)
        if not candidate.is_file():
            continue
        try:
            return candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

    return DEFAULT_SMARCOMMS_CONTENT


def get_missing_nodejs_runtime_tools(
    which: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    missing: list[str] = []

    node_executable = which("node.exe") or which("node")
    npm_executable = which("npm.cmd") or which("npm")
    if node_executable is None:
        missing.append("node")
    if npm_executable is None:
        missing.append("npm")

    return missing


def notify_nodejs_install_if_missing(
    *,
    parent: tk.Misc | None = None,
    which: Callable[[str], str | None] = shutil.which,
    askyesno: Callable[..., bool] = messagebox.askyesno,
    open_url: Callable[[str], object] = webbrowser.open,
) -> bool:
    missing_tools = get_missing_nodejs_runtime_tools(which)
    if not missing_tools:
        return False

    missing_label = ", ".join(missing_tools)
    should_open = askyesno(
        "Node.js Required",
        "Required runtime tools are missing:\n"
        f"{missing_label}\n\n"
        "Install Node.js first and ensure it is added to PATH.\n"
        f"Download link: {NODEJS_DOWNLOAD_URL}\n\n"
        "Click Yes to open the Node.js download page now.",
        parent=parent,
    )
    if should_open:
        open_url(NODEJS_DOWNLOAD_URL)
    return True


def maximize_window_on_start(window: tk.Misc) -> None:
    try:
        window.wm_state("zoomed")
        return
    except tk.TclError:
        pass

    try:
        window.state("zoomed")
        return
    except tk.TclError:
        pass

    try:
        window.wm_attributes("-zoomed", True)
    except tk.TclError:
        pass


def find_client_markdown_files(base_dir: Path) -> dict[str, list[Path]]:
    ensure_caption_samples_files_for_clients(base_dir)
    clients_root = get_clients_root(base_dir)
    if not clients_root.is_dir():
        return {}

    results: dict[str, list[Path]] = {}
    for child in sorted(clients_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if not (child / "CLIENT_PROFILE.md").is_file():
            continue
        results[child.name] = _discover_client_files(child, child.name)
    return results


def filter_clients_by_search_term(client_names: list[str], search_term: str) -> list[str]:
    ordered_clients = sorted(client_names, key=str.lower)
    normalized_search = search_term.strip().lower()
    if not normalized_search:
        return ordered_clients
    return [client_name for client_name in ordered_clients if normalized_search in client_name.lower()]


def normalize_field_name(field_name: str) -> str:
    normalized_spaces = re.sub(r"\s+", " ", field_name).strip()
    without_hint = re.sub(r"\s*\([^)]*\)\s*$", "", normalized_spaces).strip()
    canonical = CANONICAL_FIELD_NAME_MAP.get(without_hint.lower())
    if canonical is not None:
        return canonical
    return without_hint


def parse_numbered_field_line(line: str) -> tuple[str, str] | None:
    numbered_match = NUMBERED_FIELD_PATTERN.match(line)
    if not numbered_match:
        return None

    remainder = numbered_match.group(2).strip()
    for separator_pattern in (FIELD_WITH_DASH_PATTERN, FIELD_WITH_COLON_PATTERN):
        field_match = separator_pattern.match(remainder)
        if field_match is None:
            continue
        field_name = normalize_field_name(field_match.group(1))
        field_value = field_match.group(2).strip()
        if field_name:
            return field_name, field_value
    return None


def split_optional_list_items(value: str) -> list[str]:
    normalized_value = value.strip()
    if not normalized_value:
        return []

    if ";" not in normalized_value:
        return [normalized_value]

    return [item.strip() for item in normalized_value.split(";") if item.strip()]


def extract_post_details(markdown_text: str) -> list[dict[str, object]]:
    post_header_pattern = re.compile(
        r"^\s*(?:#{1,6}\s+)?(Post\s+(\d+)\b.*)$",
        re.IGNORECASE,
    )
    bullet_pattern = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")

    posts: list[dict[str, object]] = []
    current_post: dict[str, object] | None = None

    lines = markdown_text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()

        post_header_match = post_header_pattern.match(line)
        if post_header_match:
            if current_post is not None:
                posts.append(current_post)
            current_post = {
                "Post Header": post_header_match.group(1).strip(),
            }
            post_number_text = post_header_match.group(2)
            if post_number_text is not None:
                current_post["Post Number"] = int(post_number_text)
            index += 1
            continue

        if current_post is not None:
            parsed_field = parse_numbered_field_line(line)
            
            # Fallback for unnumbered fields (e.g. "Caption 1: Content")
            if parsed_field is None:
                for separator_pattern in (FIELD_WITH_COLON_PATTERN, FIELD_WITH_DASH_PATTERN):
                    match = separator_pattern.match(line)
                    if match:
                        name = normalize_field_name(match.group(1))
                        if name in PREFERRED_DISPLAY_FIELD_ORDER:
                            parsed_field = (name, match.group(2).strip())
                            break

            if parsed_field is not None:
                field_name, field_value = parsed_field

                if field_name == "Optional List":
                    items: list[str] = split_optional_list_items(field_value)
                    next_index = index + 1
                    while next_index < len(lines):
                        bullet_match = bullet_pattern.match(lines[next_index])
                        if not bullet_match:
                            break
                        items.extend(split_optional_list_items(bullet_match.group(1).strip()))
                        next_index += 1
                    current_post[field_name] = items
                    index = next_index
                    continue

                if field_name in MULTILINE_POST_FIELDS or field_name.lower().startswith("caption"):
                    content_lines = [field_value] if field_value else []
                    next_index = index + 1
                    while next_index < len(lines):
                        next_line = lines[next_index].rstrip()
                        if post_header_pattern.match(next_line):
                            break
                        
                        # Only break if it's CLEARLY a new field from our known list
                        next_field_info = parse_numbered_field_line(next_line)
                        if next_field_info:
                            next_f_name = next_field_info[0]
                            if next_f_name in PREFERRED_DISPLAY_FIELD_ORDER and next_f_name != field_name:
                                break
                        
                        content_lines.append(next_line)
                        next_index += 1
                    current_post[field_name] = "\n".join(content_lines).strip()
                    index = next_index
                    continue

                current_post[field_name] = field_value

        index += 1

    if current_post is not None:
        posts.append(current_post)

    return posts


def format_post_details(posts: list[dict[str, object]]) -> str:
    if not posts:
        return "No structured post fields were detected in this markdown file."

    output_lines: list[str] = []
    for post_index, post in enumerate(posts, start=1):
        output_lines.append(f"Post {post_index}")
        output_lines.append("-" * 40)
        for key, value in post.items():
            if isinstance(value, list):
                output_lines.append(f"{key}:")
                for item in value:
                    output_lines.append(f"- {item}")
            else:
                output_lines.append(f"{key}: {value}")
        output_lines.append("")
    return "\n".join(output_lines).rstrip()


def build_generation_prompt(
    runbook_text: str,
    month: str | None = None,
    weeks: list[int] | None = None,
) -> str:
    scope_line = ""
    if month and weeks:
        selected_weeks = sorted(set(weeks))
        week_text = ", ".join(f"Week {week}" for week in selected_weeks)
        scope_line = (
            f"Generation scope requirement: Month is {month}. "
            f"Generate only for {week_text}. "
            "If week labels are included in output, use only the selected week numbers.\n\n"
        )

    return (
        "Run the SMARCOMMS runbook now from the current workspace root. "
        "Follow all rules exactly and generate graphic post idea files for eligible clients.\n\n"
        f"{scope_line}"
        "BEGIN SMARCOMMS.md\n"
        f"{runbook_text}\n"
        "END SMARCOMMS.md\n"
    )


def build_client_profile_autofill_prompt(
    *,
    client_name: str,
    profile_relative_path: str,
    website_url: str,
    pasted_information: str,
    runbook_text: str,
) -> str:
    normalized_client_name = normalize_client_name(client_name)
    normalized_website_url = website_url.strip()
    normalized_pasted_information = pasted_information.strip()
    source_mode = "website" if normalized_website_url else "pasted information only"
    website_block = normalized_website_url if normalized_website_url else "None provided"
    pasted_block = normalized_pasted_information if normalized_pasted_information else "None provided"
    profile_fields_block = "\n".join(f"- {field}" for field in CLIENT_PROFILE_FIELDS)

    return f"""You are updating one client profile markdown file.

Follow this runbook exactly:
BEGIN {CLIENT_PROFILE_AUTOFILL_FILENAME}
{runbook_text}
END {CLIENT_PROFILE_AUTOFILL_FILENAME}

Task:
- Client Name: {normalized_client_name}
- Target file to edit in-place: {profile_relative_path}
- Source mode: {source_mode}

Allowed source input:
- Website URL: {website_block}
- Pasted Client Information:
{pasted_block}

Hard constraints:
- Use `$content-creator` skill if available.
- If website URL is provided, only use that website and links inside it as sources.
- If website URL is not provided, only use the pasted client information.
- Do not use any outside source.
- Do not invent or infer unsupported details.
- If a field has no supported data, leave its value blank.
- Keep field names and order exactly unchanged.
- Keep all edits limited to the target file only.

Client profile fields that must remain present and ordered:
{profile_fields_block}

Save the file and return a short confirmation only.
"""


def resolve_model_selection_feedback(
    *,
    current_model: str,
    selected_model: str,
) -> tuple[str, str]:
    """Backward-compatible helper kept for legacy tests."""
    normalized_selected_model = selected_model.strip()
    normalized_current_model = current_model.strip()

    if normalized_selected_model != "Codex":
        return (
            "unavailable",
            f"{normalized_selected_model} is currently unavailable. Please use Codex.",
        )

    if normalized_current_model == "Codex":
        return (
            "already_selected",
            "It is already using the selected model (Codex).",
        )

    return ("selected", "Model set to Codex.")


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_codex_exec_command(
    codex_executable: str,
    base_dir: Path,
    *,
    model: str = DEFAULT_CODEX_MODEL,
    reasoning_effort: str = DEFAULT_CODEX_REASONING_EFFORT,
) -> list[str]:
    normalized_model = model.strip() or DEFAULT_CODEX_MODEL
    normalized_reasoning_effort = reasoning_effort.strip() or DEFAULT_CODEX_REASONING_EFFORT
    escaped_reasoning_effort = _escape_toml_string(normalized_reasoning_effort)

    return [
        codex_executable,
        "exec",
        "-m",
        normalized_model,
        "-c",
        f'model_reasoning_effort="{escaped_reasoning_effort}"',
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--color",
        "never",
        "-C",
        str(base_dir),
        "-",
    ]


def build_gemini_exec_command(
    gemini_executable: str,
    base_dir: Path,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
) -> list[str]:
    normalized_model = model.strip() or DEFAULT_GEMINI_MODEL

    return [
        gemini_executable,
        "-m",
        normalized_model,
        "-y", # YOLO mode to bypass approvals
        "-C",
        str(base_dir),
        "-p", # Prompt will be appended
    ]


def parse_codex_model_catalog(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []

    result = payload.get("result")
    if not isinstance(result, dict):
        return []

    raw_models = result.get("data")
    if not isinstance(raw_models, list):
        raw_models = result.get("items")
    if not isinstance(raw_models, list):
        return []

    catalog: list[dict[str, object]] = []
    for raw_model in raw_models:
        if not isinstance(raw_model, dict):
            continue

        model_value = raw_model.get("id", raw_model.get("model"))
        if not isinstance(model_value, str):
            continue
        model_name = model_value.strip()
        if not model_name:
            continue

        raw_efforts = raw_model.get("supportedReasoningEfforts")
        efforts: list[str] = []
        if isinstance(raw_efforts, list):
            for raw_effort in raw_efforts:
                if not isinstance(raw_effort, dict):
                    continue
                effort_value = raw_effort.get("reasoningEffort")
                if not isinstance(effort_value, str):
                    continue
                effort_text = effort_value.strip()
                if not effort_text or effort_text in efforts:
                    continue
                efforts.append(effort_text)

        if not efforts:
            efforts = [DEFAULT_CODEX_REASONING_EFFORT]

        default_effort_value = raw_model.get("defaultReasoningEffort")
        if isinstance(default_effort_value, str) and default_effort_value.strip():
            default_effort = default_effort_value.strip()
        else:
            default_effort = efforts[0]

        if default_effort not in efforts:
            default_effort = efforts[0]

        catalog.append(
            {
                "model": model_name,
                "efforts": efforts,
                "is_default": bool(raw_model.get("isDefault")),
                "default_effort": default_effort,
            }
        )

    return catalog


def parse_codex_rate_limits_response(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None

    result = payload.get("result")
    if isinstance(result, dict):
        rate_limits = result.get("rateLimits")
        if isinstance(rate_limits, dict):
            return rate_limits

    if payload.get("method") == "account/rateLimits/updated":
        params = payload.get("params")
        if isinstance(params, dict):
            rate_limits = params.get("rateLimits")
            if isinstance(rate_limits, dict):
                return rate_limits

    return None


def parse_codex_thread_start_model_response(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    model_value = result.get("model")
    if not isinstance(model_value, str):
        return None
    model_name = model_value.strip()
    return model_name or None


def _format_rate_limit_reset_time_for_display(value: object) -> str:
    if not isinstance(value, int):
        return "Unknown"
    try:
        timestamp = datetime.fromtimestamp(value)
    except (OSError, OverflowError, ValueError):
        return "Unknown"
    hour_12 = timestamp.hour % 12 or 12
    return (
        f"{timestamp.strftime('%B')} {timestamp.day}, {timestamp.year} - "
        f"{hour_12}:{timestamp.strftime('%M')} {timestamp.strftime('%p')}"
    )


def _format_percent_left(used_percent: object) -> str:
    if not isinstance(used_percent, (int, float)):
        return "Unknown"
    percent_left = int(round(100 - float(used_percent)))
    percent_left = max(0, min(100, percent_left))
    return f"{percent_left}%"


def build_compact_model_status_lines(
    *,
    current_model: str | None,
    rate_limits: dict[str, object],
) -> list[str]:
    model_text = current_model.strip() if isinstance(current_model, str) else ""
    if not model_text:
        model_text = "Unknown"

    lines = [f"Current Model Used: {model_text}"]
    for label, window_name in (("5h Usage Left", "primary"), ("Weekly Usage Left", "secondary")):
        window = rate_limits.get(window_name)
        if isinstance(window, dict):
            used_percent = window.get("usedPercent")
            resets_at = window.get("resetsAt")
            left_text = _format_percent_left(used_percent)
            reset_text = _format_rate_limit_reset_time_for_display(resets_at)
        else:
            left_text = "Unknown"
            reset_text = "Unknown"
        lines.append(f"{label}: {left_text} (Resets: {reset_text})")

    return lines


def _build_background_creation_flags() -> int:
    creation_flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creation_flags |= subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return creation_flags


def _start_codex_app_server(
    codex_executable: str,
    *,
    base_dir: Path,
) -> subprocess.Popen[str]:
    popen_kwargs: dict[str, object] = {
        "cwd": base_dir,
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    creation_flags = _build_background_creation_flags()
    if creation_flags:
        popen_kwargs["creationflags"] = creation_flags

    return subprocess.Popen(
        [codex_executable, "app-server", "--listen", "stdio://"],
        **popen_kwargs,
    )


def _send_json_line_to_process(process: subprocess.Popen[str], payload: dict[str, object]) -> None:
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin is unavailable.")
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()


def _start_process_stdout_reader(process: subprocess.Popen[str]) -> queue.Queue[str]:
    output_queue: queue.Queue[str] = queue.Queue()

    def reader() -> None:
        if process.stdout is None:
            return
        for raw_line in process.stdout:
            output_queue.put(raw_line.rstrip("\r\n"))

    threading.Thread(target=reader, daemon=True).start()
    return output_queue


def _collect_json_messages_until(
    output_queue: queue.Queue[str],
    process: subprocess.Popen[str],
    *,
    timeout_seconds: float,
    stop_predicate: Callable[[dict[str, object]], bool],
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    matched_payload: dict[str, object] | None = None
    collected_payloads: list[dict[str, object]] = []
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if process.poll() is not None and output_queue.empty():
            break

        remaining = max(0.01, deadline - time.monotonic())
        wait_timeout = min(0.5, remaining)
        try:
            raw_line = output_queue.get(timeout=wait_timeout)
        except queue.Empty:
            continue

        if not raw_line.strip():
            continue

        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        collected_payloads.append(payload)
        if stop_predicate(payload):
            matched_payload = payload
            break

    return collected_payloads, matched_payload


def _close_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2.5)
    except subprocess.TimeoutExpired:
        process.kill()


def fetch_codex_model_catalog(
    codex_executable: str,
    *,
    base_dir: Path,
    timeout_seconds: float = DEFAULT_CODEX_MODEL_DISCOVERY_TIMEOUT_SECONDS,
) -> list[dict[str, object]]:
    process = _start_codex_app_server(codex_executable, base_dir=base_dir)
    output_queue = _start_process_stdout_reader(process)

    request_id = "model-list-request"
    try:
        _send_json_line_to_process(
            process,
            {
                "method": "initialize",
                "id": "initialize-request",
                "params": {
                    "clientInfo": {
                        "name": "graphic-post-model-picker",
                        "title": "Graphic Post Model Picker",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "experimentalApi": True,
                        "optOutNotificationMethods": None,
                    },
                },
            },
        )
        _send_json_line_to_process(process, {"method": "initialized"})
        _send_json_line_to_process(
            process,
            {
                "method": "model/list",
                "id": request_id,
                "params": {"includeHidden": False},
            },
        )

        _, response_payload = _collect_json_messages_until(
            output_queue,
            process,
            timeout_seconds=timeout_seconds,
            stop_predicate=lambda payload: payload.get("id") == request_id,
        )
        if response_payload is None:
            raise RuntimeError("Timed out while loading models from Codex.")
        catalog = parse_codex_model_catalog(response_payload)
        if not catalog:
            raise RuntimeError("Codex returned an empty model catalog.")
        return catalog
    finally:
        _close_process(process)


def run_codex_status_request(
    codex_executable: str,
    *,
    base_dir: Path,
    timeout_seconds: float = DEFAULT_CODEX_STATUS_TIMEOUT_SECONDS,
) -> list[str]:
    process = _start_codex_app_server(codex_executable, base_dir=base_dir)
    output_queue = _start_process_stdout_reader(process)

    current_model: str | None = None
    rate_limits: dict[str, object] | None = None
    try:
        _send_json_line_to_process(
            process,
            {
                "method": "initialize",
                "id": "initialize-status",
                "params": {
                    "clientInfo": {
                        "name": "graphic-post-model-status",
                        "title": "Graphic Post Model Status",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "experimentalApi": True,
                        "optOutNotificationMethods": None,
                    },
                },
            },
        )
        _send_json_line_to_process(process, {"method": "initialized"})
        _send_json_line_to_process(
            process,
            {
                "method": "thread/start",
                "id": "thread-start-status",
                "params": {},
            },
        )

        _, thread_start_response = _collect_json_messages_until(
            output_queue,
            process,
            timeout_seconds=timeout_seconds,
            stop_predicate=lambda payload: payload.get("id") == "thread-start-status",
        )
        if thread_start_response is None:
            raise RuntimeError("Timed out while reading the current model from Codex.")
        current_model = parse_codex_thread_start_model_response(thread_start_response)

        _send_json_line_to_process(
            process,
            {
                "method": "account/rateLimits/read",
                "id": "rate-limits-read",
                "params": {},
            },
        )

        collected_payloads, rate_limits_response = _collect_json_messages_until(
            output_queue,
            process,
            timeout_seconds=timeout_seconds,
            stop_predicate=lambda payload: payload.get("id") == "rate-limits-read",
        )
        if rate_limits_response is None:
            raise RuntimeError("Timed out while reading account rate limits from Codex.")

        for payload in collected_payloads:
            parsed = parse_codex_rate_limits_response(payload)
            if parsed is not None:
                rate_limits = parsed
                break
    finally:
        _close_process(process)

    if rate_limits is None:
        raise RuntimeError("Codex did not return rate limit data.")

    return build_compact_model_status_lines(
        current_model=current_model,
        rate_limits=rate_limits,
    )


def launch_codex_login_terminal(
    codex_executable: str,
    *,
    base_dir: Path,
    popen: Callable[..., object] = subprocess.Popen,
    platform_name: str | None = None,
    create_new_console_flag: int | None = None,
) -> bool:
    if platform_name is None:
        platform_name = os.name

    command: list[str]
    popen_kwargs: dict[str, object] = {"cwd": base_dir}
    if platform_name == "nt":
        command = ["cmd.exe", "/k", f"\"{codex_executable}\" login"]
        resolved_create_new_console_flag = create_new_console_flag
        if resolved_create_new_console_flag is None:
            resolved_create_new_console_flag = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        if isinstance(resolved_create_new_console_flag, int) and resolved_create_new_console_flag:
            popen_kwargs["creationflags"] = resolved_create_new_console_flag
    else:
        command = [codex_executable, "login"]

    try:
        popen(command, **popen_kwargs)
    except OSError:
        return False
    return True


def is_generation_process_running(process: subprocess.Popen[str] | None) -> bool:
    return process is not None and process.poll() is None


def should_enable_stop_generation_button(
    process: subprocess.Popen[str] | None,
    *,
    stop_requested: bool,
) -> bool:
    return is_generation_process_running(process) and not stop_requested


def should_continue_generation_polling(
    *,
    generation_running: bool,
    model_status_in_progress: bool,
    event_queue_empty: bool,
) -> bool:
    return generation_running or model_status_in_progress or not event_queue_empty


def request_generation_stop_signal(
    process: subprocess.Popen[str],
    *,
    platform_name: str | None = None,
    ctrl_break_event: int | None | object = _AUTO_CTRL_BREAK_EVENT,
) -> str:
    if platform_name is None:
        platform_name = os.name
    resolved_ctrl_break_event = ctrl_break_event
    if resolved_ctrl_break_event is _AUTO_CTRL_BREAK_EVENT:
        resolved_ctrl_break_event = getattr(signal, "CTRL_BREAK_EVENT", None)

    if platform_name == "nt" and isinstance(resolved_ctrl_break_event, int):
        process.send_signal(resolved_ctrl_break_event)
        return "ctrl_break"

    process.terminate()
    return "terminate"


def force_kill_generation_process_tree(process: subprocess.Popen[str]) -> bool:
    if process.poll() is not None:
        return False

    if os.name == "nt":
        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags |= subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=creation_flags,
            )
        except OSError:
            pass

    if process.poll() is not None:
        return True

    process.kill()
    return True


def _extract_percent_from_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 100 else None
    if isinstance(value, float):
        rounded = int(round(value))
        return rounded if 0 <= rounded <= 100 else None
    if isinstance(value, str):
        text = value.strip().rstrip("%")
        if not text:
            return None
        if text.isdigit():
            percent = int(text)
            return percent if 0 <= percent <= 100 else None
    return None


def _find_context_left_percent(data: object) -> int | None:
    if isinstance(data, dict):
        lowered_keys = {re.sub(r"[^a-z]", "", key.lower()): key for key in data.keys()}

        for normalized_key, original_key in lowered_keys.items():
            if normalized_key in CONTEXT_PERCENT_KEYS:
                percent = _extract_percent_from_value(data[original_key])
                if percent is not None:
                    return percent

        max_context = data.get("max_context_tokens")
        used_tokens = data.get("prompt_tokens", data.get("input_tokens"))
        if isinstance(max_context, (int, float)) and isinstance(used_tokens, (int, float)):
            if max_context > 0:
                remaining = max_context - used_tokens
                percent = int(round((remaining / max_context) * 100))
                return max(0, min(100, percent))

        for value in data.values():
            nested = _find_context_left_percent(value)
            if nested is not None:
                return nested

    if isinstance(data, list):
        for item in data:
            nested = _find_context_left_percent(item)
            if nested is not None:
                return nested

    return None


def extract_context_left_percent_from_line(raw_line: str) -> int | None:
    line = raw_line.strip()
    if not line:
        return None

    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        percent = _find_context_left_percent(payload)
        if percent is not None:
            return percent

    match = CONTEXT_LEFT_TEXT_PATTERN.search(line)
    if not match:
        return None
    candidate = match.group(1) or match.group(2)
    if candidate is None:
        return None
    return _extract_percent_from_value(candidate)


def is_graphic_idea_file(client_name: str, file_name: str) -> bool:
    if GRAPHIC_POST_IDEAS_PATTERN.match(file_name):
        return True
    client_pattern = re.compile(rf"^{re.escape(client_name)}_.*\.md$", re.IGNORECASE)
    return bool(client_pattern.match(file_name))


def list_general_settings_files(base_dir: Path) -> list[Path]:
    agents_root = get_general_agents_root(base_dir)
    if not agents_root.is_dir():
        return []

    return sorted(
        [path for path in agents_root.glob("*.md") if path.is_file()],
        key=lambda p: p.name.lower(),
    )


def list_client_settings_files(base_dir: Path, client_name: str) -> list[Path]:
    client_dir = get_clients_root(base_dir) / client_name
    if not client_dir.is_dir():
        return []

    files = [
        path
        for path in client_dir.rglob("*.md")
        if path.is_file() and not is_graphic_idea_file(client_name, path.name)
    ]
    return sorted(
        files,
        key=lambda p: (
            0 if p.name.lower() == "client_profile.md" else 1,
            1 if p.name.lower() == CAPTION_SAMPLES_FILENAME.lower() else 2,
            str(p.relative_to(client_dir)).lower(),
        ),
    )


def build_workspace_md_signature(base_dir: Path) -> tuple[tuple[str, int], ...]:
    records: list[tuple[str, int]] = []
    # Only scan Clients and Agents directories for signature changes
    for sub_dir in (CLIENTS_DIRNAME, AGENTS_DIRNAME):
        target = base_dir / sub_dir
        if not target.is_dir():
            continue
        for path in target.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                continue
            relative = str(path.relative_to(base_dir)).replace("\\", "/")
            records.append((relative, mtime))
    records.sort(key=lambda record: record[0].lower())
    return tuple(records)


def format_post_created_text(created_at: datetime) -> str:
    hour_12 = created_at.hour % 12 or 12
    return (
        f"{created_at.strftime('%B')} {created_at.day}, {created_at.year} - "
        f"{hour_12}:{created_at.strftime('%M')} {created_at.strftime('%p')}"
    )


def parse_post_created_datetime_from_filename(file_name: str) -> datetime | None:
    match = POST_FILENAME_TIMESTAMP_PATTERN.search(file_name)
    if match is None:
        return None

    timestamp_text = match.group(1)
    try:
        return datetime.strptime(timestamp_text, "%Y-%m-%d_%H-%M")
    except ValueError:
        return None


def resolve_post_file_created_text(path: Path) -> str:
    parsed_from_name = parse_post_created_datetime_from_filename(path.name)
    if parsed_from_name is not None:
        return format_post_created_text(parsed_from_name)

    try:
        created_at = datetime.fromtimestamp(path.stat().st_ctime)
    except (OSError, OverflowError, ValueError):
        try:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        except (OSError, OverflowError, ValueError):
            return "--"
    return format_post_created_text(created_at)


def format_single_post_view(posts: list[dict[str, object]], current_index: int) -> str:
    if not posts:
        return "No structured post fields were detected in this markdown file."

    bounded_index = max(0, min(current_index, len(posts) - 1))
    post = posts[bounded_index]

    detected_number = post.get("Post Number")
    header = post.get("Post Header")
    if isinstance(header, str) and header:
        title_line = header
    elif isinstance(detected_number, int):
        title_line = f"Post {detected_number}"
    else:
        title_line = f"Post {bounded_index + 1}"

    output_lines: list[str] = [
        title_line,
        f"Viewing {bounded_index + 1} of {len(posts)}",
        "-" * 40,
    ]

    for key, value in post.items():
        if key in POST_METADATA_FIELDS:
            continue
        if isinstance(value, list):
            output_lines.append(f"{key}:")
            for item in value:
                output_lines.append(f"- {item}")
        else:
            output_lines.append(f"{key}: {value}")

    return "\n".join(output_lines).rstrip()


def build_post_display_fields(post: dict[str, object]) -> list[tuple[str, str]]:
    normalized: dict[str, object] = {}
    for key, value in post.items():
        if key in POST_METADATA_FIELDS:
            continue
        normalized[key] = value

    ordered_fields: list[tuple[str, str]] = []

    def append_field_rows(field_name: str, value: object) -> None:
        if isinstance(value, list):
            if not value:
                ordered_fields.append((field_name, ""))
                return
            for index, item in enumerate(value, start=1):
                ordered_fields.append((f"{field_name} {index}", str(item)))
            return

        if value is None:
            ordered_fields.append((field_name, ""))
            return

        ordered_fields.append((field_name, str(value)))

    for field_name in PREFERRED_DISPLAY_FIELD_ORDER:
        if field_name in normalized:
            append_field_rows(field_name, normalized.pop(field_name))

    for field_name, value in normalized.items():
        append_field_rows(field_name, value)

    return ordered_fields


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, _event: tk.Event[tk.Misc]) -> None:
        if self.tip_window or not self.text:
            return
        x, y, _cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Determine theme from the widget's master (Tk object)
        bg_color = "#334155" # Default dark-ish
        fg_color = "#f8fafc"
        try:
            # Safely check if widget's root has a theme_var
            root = self.widget.winfo_toplevel()
            if hasattr(root, "theme_var") and root.theme_var.get() == "light":
                bg_color = "#ffffe0"
                fg_color = "#0f172a"
        except:
            pass

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background=bg_color,
            foreground=fg_color,
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", "9", "normal"),
            padx=10,
            pady=5,
        )
        label.pack(ipadx=1)

    def hide_tip(self, _event: tk.Event[tk.Misc]) -> None:
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ClientMarkdownViewer(tk.Tk):
    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.clients_dir = get_clients_root(self.base_dir)
        self.title("Client Markdown Studio")
        self.geometry("1420x900")
        self.minsize(1240, 760)

        self.client_files: dict[str, list[Path]] = {}

        self.client_var = tk.StringVar()
        self.file_var = tk.StringVar()
        self.post_counter_var = tk.StringVar(value="Post 0 of 0")
        self.post_created_var = tk.StringVar(value="Created: --")
        self.status_var = tk.StringVar(
            value=f"Workspace: {self.base_dir} | Clients: {self.clients_dir}"
        )
        self.context_left_var = tk.StringVar(value="Context left: --")
        self.model_usage_status_var = tk.StringVar(value="Usage: 5h: -- | Weekly: --")
        self.generation_state_var = tk.StringVar(value="Generation: idle")
        self.selected_backend = tk.StringVar(value="Codex")
        self.selected_codex_model = DEFAULT_CODEX_MODEL
        self.selected_gemini_model = DEFAULT_GEMINI_MODEL
        self.selected_reasoning_effort = DEFAULT_CODEX_REASONING_EFFORT
        self.codex_model_catalog: list[dict[str, object]] = []
        self.settings_mode_var = tk.StringVar(value="general")
        self.settings_title_var = tk.StringVar(value="General Setting")
        self.settings_status_var = tk.StringVar(value="Select a markdown file to edit.")

        self.file_lookup: dict[str, Path] = {}
        self.current_file_path: Path | None = None
        self.current_posts: list[dict[str, object]] = []
        self.current_post_index = 0
        self.last_rendered_fields_signature: tuple[object, ...] | None = None
        self.last_rendered_field_message: str | None = None
        self.last_selected_client = ""
        self.field_value_vars: list[tk.StringVar] = []
        self.generation_process: subprocess.Popen[str] | None = None
        self.generation_log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.generation_poll_handle: str | None = None
        self.generation_stop_requested = False
        self.generation_instance_counter = 0
        self.current_generation_instance = 0
        self.stop_generation_button: ttk.Button | None = None
        self.select_model_button: ttk.Button | None = None
        self.model_status_button: ttk.Button | None = None
        self.model_status_in_progress = False

        self.settings_window: tk.Toplevel | None = None
        self.settings_file_lookup: dict[str, Path] = {}
        self.current_settings_file_path: Path | None = None
        self.selected_settings_key: str | None = None
        self.settings_editor_dirty = False
        self._is_updating_settings_list = False
        self.settings_file_listbox: tk.Listbox | None = None
        self.settings_content_text: tk.Text | None = None
        self.save_settings_button: ttk.Button | None = None
        self.reload_settings_button: ttk.Button | None = None
        self.auto_fill_profile_button: ttk.Button | None = None
        self.settings_general_mode_button: ttk.Button | None = None
        self.settings_client_mode_button: ttk.Button | None = None
        self.open_general_settings_button: ttk.Button | None = None
        self.open_client_settings_button: ttk.Button | None = None
        self.create_client_button: ttk.Button | None = None
        self.settings_content_scrollbar: ttk.Scrollbar | None = None
        self.settings_profile_form_container: ttk.Frame | None = None
        self.settings_profile_canvas: tk.Canvas | None = None
        self.settings_profile_scrollbar: ttk.Scrollbar | None = None
        self.settings_profile_inner_frame: ttk.Frame | None = None
        self.settings_profile_window_id: int | None = None
        self.settings_profile_field_vars: dict[str, tk.StringVar] = {}
        self.settings_caption_form_container: ttk.Frame | None = None
        self.settings_caption_canvas: tk.Canvas | None = None
        self.settings_caption_scrollbar: ttk.Scrollbar | None = None
        self.settings_caption_inner_frame: ttk.Frame | None = None
        self.settings_caption_window_id: int | None = None
        self.settings_caption_field_texts: dict[str, tk.Text] = {}
        self.settings_editor_mode = "text"
        self._is_loading_profile_fields = False
        self._is_loading_caption_fields = False
        self.theme_var = tk.StringVar(value="light")
        self.client_search_var = tk.StringVar()
        self.client_search_results_listbox: tk.Listbox | None = None
        self.client_search_results_scrollbar: ttk.Scrollbar | None = None
        self.client_search_results_popup: tk.Toplevel | None = None
        self.profile_autofill_in_progress = False
        self.auto_refresh_handle: str | None = None
        self.auto_refresh_interval_ms = 2000
        self.refresh_idle_guard_seconds = 0.75
        self.last_user_interaction_time = time.monotonic()
        self.global_mousewheel_binding_ready = False
        self.local_wheel_only_text_widgets: set[str] = set()
        self.last_md_signature = build_workspace_md_signature(self.base_dir)
        self.app_icon_image: tk.PhotoImage | None = None
        self.copy_feedback_toast: tk.Toplevel | None = None

        self._apply_window_logo()
        self._configure_styles()
        self._build_ui()
        self._ensure_test_script_for_editing()
        self.bind("<Left>", self._on_prev_post_key)
        self.bind("<Right>", self._on_next_post_key)
        self.bind("<Control-g>", lambda e: self._on_generate_clicked())
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.bind("<Control-d>", lambda e: self._toggle_theme())
        self.bind("<F5>", lambda e: self._refresh_from_workspace_if_changed())
        self.bind("<Configure>", self._on_root_configure, add="+")
        self._bind_global_interaction_tracking()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._run_startup_setup_if_needed()
        self.client_files = find_client_markdown_files(self.base_dir)
        self._populate_clients()
        self._schedule_auto_refresh()
        self.after(1000, self._on_model_status_clicked)

    def _apply_window_logo(self) -> None:
        logo_path = resolve_bundled_resource(APP_LOGO_FILENAME, self.base_dir)
        if logo_path is None:
            return

        try:
            self.app_icon_image = tk.PhotoImage(master=self, file=str(logo_path))
            self.iconphoto(True, self.app_icon_image)
        except tk.TclError:
            self.app_icon_image = None

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        theme = self.theme_var.get()
        if theme == "dark":
            self.colors = {
                "bg": "#0a0f1e",          # Deep Night
                "surface": "#161e31",     # Deep Slate
                "header": "#020617",      # Blackest Blue
                "primary": "#6366f1",     # Vibrant Indigo
                "secondary": "#a855f7",   # Vibrant Purple
                "accent": "#f43f5e",      # Vibrant Rose
                "border": "#2e3a59",      # Muted Blue-Grey
                "text": "#f8fafc",        # Bright White-Slate
                "text_muted": "#cbd5e1",  # Slate 300 (Higher contrast)
                "success": "#10b981",     # Emerald 500
                "warning": "#f59e0b",     # Amber 500
                "danger": "#ef4444",      # Red 500
            }
            # Style widgets globally to ensure dark mode consistency
            self.option_add("*TCombobox*Listbox.background", self.colors["surface"])
            self.option_add("*TCombobox*Listbox.foreground", self.colors["text"])
            self.option_add("*TCombobox*Listbox.selectBackground", self.colors["primary"])
            self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
            self.option_add("*Listbox.background", self.colors["surface"])
            self.option_add("*Listbox.foreground", self.colors["text"])
            self.option_add("*Listbox.selectBackground", self.colors["primary"])
            self.option_add("*Listbox.selectForeground", "#ffffff")
            self.option_add("*Entry.insertBackground", self.colors["text"])
            self.option_add("*Text.insertBackground", self.colors["text"])
        else:
            self.colors = {
                "bg": "#f8fafc",          # Slate 50
                "surface": "#ffffff",     # White
                "header": "#0f172a",      # Slate 900
                "primary": "#6366f1",     # Indigo 500
                "secondary": "#a855f7",   # Violet 500
                "accent": "#f43f5e",      # Rose 500
                "border": "#e2e8f0",      # Slate 200
                "text": "#0f172a",        # Slate 900
                "text_muted": "#64748b",  # Slate 500
                "success": "#10b981",     # Emerald 500
                "warning": "#f59e0b",     # Amber 500
                "danger": "#ef4444",      # Red 500
            }
            self.option_add("*TCombobox*Listbox.background", "#ffffff")
            self.option_add("*TCombobox*Listbox.foreground", "#000000")
            self.option_add("*TCombobox*Listbox.selectBackground", self.colors["primary"])
            self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
            self.option_add("*Listbox.background", "#ffffff")
            self.option_add("*Listbox.foreground", "#000000")
            self.option_add("*Listbox.selectBackground", self.colors["primary"])
            self.option_add("*Listbox.selectForeground", "#ffffff")
            self.option_add("*Entry.insertBackground", "#000000")
            self.option_add("*Text.insertBackground", "#000000")

        self.configure(background=self.colors["bg"])
        self.option_add("*Font", ("Segoe UI", 10))

        # Frames
        style.configure("TopBar.TFrame", background=self.colors["header"])
        style.configure("Control.TFrame", background=self.colors["surface"])
        style.configure("Content.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["surface"])
        style.configure("Hover.TFrame", background=self.colors["bg"])
        style.configure("TFrame", background=self.colors["bg"])
        
        # Labels
        style.configure("TopBar.TLabel", background=self.colors["header"], foreground="#f1f5f9", font=("Segoe UI", 10))
        style.configure("AppTitle.TLabel", 
                        background=self.colors["header"], 
                        foreground="#ffffff", 
                        font=("Segoe UI Semibold", 16))
        
        style.configure("SubtleTop.TLabel", 
                        background=self.colors["header"], 
                        foreground="#94a3b8", 
                        font=("Segoe UI", 9))

        style.configure("CardHeader.TLabel", 
                        background=self.colors["surface"], 
                        foreground=self.colors["text"], 
                        font=("Segoe UI Semibold", 12))

        style.configure("FieldName.TLabel", 
                        background=self.colors["surface"], 
                        foreground=self.colors["text_muted"], 
                        font=("Segoe UI", 8, "bold"))

        style.configure("FieldValue.TLabel", 
                        background=self.colors["surface"], 
                        foreground=self.colors["text"], 
                        font=("Segoe UI", 10))

        style.configure("Status.TLabel", 
                        background=self.colors["bg"], 
                        foreground=self.colors["text_muted"],
                        font=("Segoe UI", 9))

        style.configure("SettingsInfo.TLabel", 
                        background=self.colors["surface"], 
                        foreground=self.colors["text_muted"], 
                        font=("Segoe UI", 9))

        # Buttons
        style.configure("TButton", padding=(12, 6), font=("Segoe UI Semibold", 9), background=self.colors["surface"], foreground=self.colors["text"])
        style.map("TButton",
                  background=[("active", self.colors["bg"]), ("disabled", self.colors["border"])],
                  foreground=[("disabled", self.colors["text_muted"])])
        
        # Custom Accent Button (Vibrant Indigo)
        style.configure("Accent.TButton", 
                        background=self.colors["primary"], 
                        foreground="#ffffff")
        style.map("Accent.TButton",
                  background=[("active", self.colors["secondary"]), ("disabled", self.colors["border"])])

        # Ghost / Outline Button Style
        style.configure("Ghost.TButton", background=self.colors["bg"], foreground=self.colors["primary"])
        
        style.configure("Copy.TButton", padding=(8, 2), font=("Segoe UI Semibold", 8))

        # Combobox
        style.configure("TCombobox", padding=5, fieldbackground=self.colors["surface"], background=self.colors["surface"], foreground=self.colors["text"])
        style.map("TCombobox", 
                  fieldbackground=[("readonly", self.colors["surface"]), ("disabled", self.colors["bg"]), ("active", self.colors["surface"])],
                  foreground=[("readonly", self.colors["text"]), ("disabled", self.colors["text_muted"]), ("active", self.colors["text"])])
        
        # Entry
        style.configure("TEntry", padding=5, fieldbackground=self.colors["surface"], foreground=self.colors["text"])
        style.map("TEntry", 
                  fieldbackground=[("readonly", self.colors["surface"]), ("disabled", self.colors["bg"]), ("active", self.colors["surface"])],
                  foreground=[("readonly", self.colors["text"]), ("disabled", self.colors["text_muted"]), ("active", self.colors["text"])])

        style.configure("CopyToast.TLabel",
                        background=self.colors["header"],
                        foreground="#ffffff",
                        font=("Segoe UI Semibold", 9),
                        padding=(12, 8))

        # Checkbutton / Radiobutton
        style.configure("TCheckbutton", background=self.colors["surface"], foreground=self.colors["text"])
        style.configure("TRadiobutton", background=self.colors["surface"], foreground=self.colors["text"])


    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=0)

        self._build_top_bar()
        self._build_control_bar()
        self._build_main_content()
        self._build_log_panel()
        self._build_status_bar()

    def _build_top_bar(self) -> None:
        top_bar = ttk.Frame(self, style="TopBar.TFrame", padding=(20, 15))
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.columnconfigure(0, weight=1)

        # Title and Stats
        title_group = ttk.Frame(top_bar, style="TopBar.TFrame")
        title_group.grid(row=0, column=0, sticky="w")
        
        ttk.Label(title_group, text="Client Markdown Studio", style="AppTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(title_group, textvariable=self.generation_state_var, style="SubtleTop.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

        # Actions in Top Bar (Right-aligned)
        top_actions = ttk.Frame(top_bar, style="TopBar.TFrame")
        top_actions.grid(row=0, column=1, rowspan=2, sticky="e")

        self.theme_button = ttk.Button(
            top_actions,
            text="🌙" if self.theme_var.get() == "light" else "☀️",
            width=3,
            command=self._toggle_theme,
        )
        self.theme_button.grid(row=0, column=0, padx=(0, 10))
        Tooltip(self.theme_button, "Toggle Dark/Light Mode (Ctrl+D)")

        self.generate_button = ttk.Button(
            top_actions,
            text="Generate Ideas",
            style="Accent.TButton",
            command=self._on_generate_clicked,
        )
        self.generate_button.grid(row=0, column=1, sticky="e", padx=(0, 15))
        Tooltip(self.generate_button, "Generate new post ideas using SMARCOMMS runbook (Ctrl+G)")

        ttk.Label(top_actions, textvariable=self.context_left_var, style="TopBar.TLabel").grid(
            row=0, column=2, sticky="w"
        )

    def _build_control_bar(self) -> None:
        controls = ttk.Frame(self, style="Control.TFrame", padding=(20, 12))
        controls.grid(row=1, column=0, sticky="ew")

        # Group 1: Client Selection & Search
        client_group = ttk.Frame(controls, style="Control.TFrame")
        client_group.grid(row=0, column=0, rowspan=2, sticky="sw")
        client_group.columnconfigure(0, weight=1)
        
        ttk.Label(client_group, text="CLIENT SEARCH", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(
            client_group,
            textvariable=self.client_search_var,
            width=20,
        )
        self.search_entry.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.client_search_var.trace_add("write", self._on_client_search_changed)
        self.search_entry.bind("<Down>", self._focus_client_search_results)
        self.search_entry.bind("<Escape>", lambda _event: self._hide_client_search_results())
        self.search_entry.bind(
            "<FocusOut>",
            lambda _event: self.after(50, self._hide_client_search_results_if_focus_lost),
        )

        ttk.Label(client_group, text="SELECT", style="FieldName.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.client_combo = ttk.Combobox(
            client_group,
            textvariable=self.client_var,
            state="readonly",
            width=24,
            postcommand=self._on_client_search_changed,
        )
        self.client_combo.grid(row=1, column=1, sticky="w", pady=(4, 0), padx=(10, 0))
        self.client_combo.bind("<<ComboboxSelected>>", self._on_client_selected)

        self.create_client_button = ttk.Button(
            controls,
            text="+ NEW",
            width=6,
            command=self._on_create_client_clicked,
        )
        self.create_client_button.grid(row=1, column=1, sticky="sw", padx=(5, 5))
        Tooltip(self.create_client_button, "Create a new client folder")

        self.delete_client_button = ttk.Button(
            controls,
            text="- DELETE",
            width=8,
            command=self._on_delete_client_clicked,
        )
        self.delete_client_button.grid(row=1, column=2, sticky="sw", padx=(0, 15))
        Tooltip(self.delete_client_button, "Move selected client to Deleted Clients folder")

        # Group 2: File Selection
        ttk.Label(controls, text="MARKDOWN FILE", style="FieldName.TLabel").grid(row=0, column=3, sticky="w")
        self.file_combo = ttk.Combobox(
            controls,
            textvariable=self.file_var,
            state="readonly",
            width=42,
        )
        self.file_combo.grid(row=1, column=3, sticky="w", pady=(4, 0))
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)

        # Group 3: Settings Buttons
        settings_group = ttk.Frame(controls, style="Control.TFrame")
        settings_group.grid(row=1, column=4, sticky="sw", padx=(15, 0))

        self.open_general_settings_button = ttk.Button(
            settings_group,
            text="Settings",
            command=lambda: self._open_settings_window("general"),
        )
        self.open_general_settings_button.grid(row=0, column=0)

        self.open_client_settings_button = ttk.Button(
            settings_group,
            text="Profile",
            command=lambda: self._open_settings_window("client"),
        )
        self.open_client_settings_button.grid(row=0, column=1, padx=(5, 0))

    def _build_main_content(self) -> None:
        main_content = ttk.Frame(self, style="Content.TFrame", padding=(20, 0, 20, 20))
        main_content.grid(row=2, column=0, sticky="nsew")
        main_content.columnconfigure(0, weight=1)
        main_content.rowconfigure(0, weight=1)

        # Post Details Card
        post_card = ttk.Frame(main_content, style="Card.TFrame", padding=20)
        post_card.grid(row=0, column=0, sticky="nsew")
        post_card.columnconfigure(0, weight=1)
        post_card.rowconfigure(2, weight=1)

        # Compact Navigation Header
        nav_header = ttk.Frame(post_card, style="Card.TFrame")
        nav_header.grid(row=0, column=0, sticky="w", pady=(0, 15))

        self.prev_button = ttk.Button(
            nav_header,
            text="←",
            width=3,
            command=self._show_previous_post,
            state="disabled",
        )
        self.prev_button.grid(row=0, column=0, sticky="w")

        header_info = ttk.Frame(nav_header, style="Card.TFrame")
        header_info.grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(header_info, textvariable=self.post_counter_var, style="CardHeader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header_info, textvariable=self.post_created_var, style="SettingsInfo.TLabel").grid(row=1, column=0, sticky="w")

        self.next_button = ttk.Button(
            nav_header,
            text="→",
            width=3,
            command=self._show_next_post,
            state="disabled",
        )
        self.next_button.grid(row=0, column=2, sticky="w")

        self.regenerate_button = ttk.Button(
            nav_header,
            text="Regenerate Idea",
            style="Ghost.TButton",
            command=self._on_regenerate_clicked,
            state="disabled",
        )
        self.regenerate_button.grid(row=0, column=3, sticky="w", padx=(20, 0))
        Tooltip(self.regenerate_button, "Regenerate only this specific post idea")

        # Table Header
        table_header = ttk.Frame(post_card, style="Card.TFrame")
        table_header.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        table_header.columnconfigure(1, weight=1)
        
        ttk.Label(table_header, text="FIELD", style="FieldName.TLabel", width=25).grid(row=0, column=0, sticky="w")
        ttk.Label(table_header, text="CONTENT", style="FieldName.TLabel").grid(row=0, column=1, sticky="w")

        # Scrollable Fields Area
        fields_container = ttk.Frame(post_card, style="Card.TFrame")
        fields_container.grid(row=2, column=0, sticky="nsew")
        fields_container.columnconfigure(0, weight=1)
        fields_container.rowconfigure(0, weight=1)

        self.fields_canvas = tk.Canvas(fields_container, background=self.colors["surface"], highlightthickness=0)
        self.fields_canvas.grid(row=0, column=0, sticky="nsew")
        
        fields_scroll = ttk.Scrollbar(fields_container, orient="vertical", command=self.fields_canvas.yview)
        fields_scroll.grid(row=0, column=1, sticky="ns")
        self.fields_canvas.configure(yscrollcommand=fields_scroll.set)

        self.fields_rows_frame = ttk.Frame(self.fields_canvas, style="Card.TFrame")
        self.fields_rows_frame.columnconfigure(1, weight=1)
        
        self.fields_window = self.fields_canvas.create_window((0, 0), window=self.fields_rows_frame, anchor="nw")

        self.fields_rows_frame.bind("<Configure>", lambda e: self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all")))
        self.fields_canvas.bind("<Configure>", lambda e: self.fields_canvas.itemconfigure(self.fields_window, width=e.width))
        self._bind_mousewheel(self.fields_canvas)

    def _bind_mousewheel(self, _widget: tk.Canvas) -> None:
        # Keep the existing call sites, but route wheel handling through one global dispatcher.
        if self.global_mousewheel_binding_ready:
            return
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_global_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_global_mousewheel, add="+")
        self.global_mousewheel_binding_ready = True

    def _bind_text_scroll_redirect(self, text_widget: tk.Text) -> None:
        text_widget.bind("<MouseWheel>", self._on_global_mousewheel, add="+")
        text_widget.bind("<Button-4>", self._on_global_mousewheel, add="+")
        text_widget.bind("<Button-5>", self._on_global_mousewheel, add="+")

    def _register_local_wheel_only_text_widget(self, text_widget: tk.Text) -> None:
        self.local_wheel_only_text_widgets.add(str(text_widget))

    def _bind_global_interaction_tracking(self) -> None:
        self.bind_all("<KeyPress>", self._mark_user_interaction, add="+")
        self.bind_all("<ButtonPress>", self._mark_user_interaction, add="+")
        self.bind_all("<MouseWheel>", self._mark_user_interaction, add="+")
        self.bind_all("<ButtonPress>", self._hide_client_search_results_on_global_click, add="+")

    def _mark_user_interaction(self, _event: tk.Event[tk.Misc]) -> None:
        self.last_user_interaction_time = time.monotonic()

    def _on_root_configure(self, _event: tk.Event[tk.Misc]) -> None:
        if self._is_client_search_popup_visible():
            self._position_client_search_results_popup()

    def _on_global_mousewheel(self, event: tk.Event[tk.Misc]) -> str | None:
        self._mark_user_interaction(event)
        source_widget = self._get_mousewheel_source_widget(event)
        if source_widget is None:
            return None
        if self._is_local_wheel_only_widget(source_widget):
            # Let the Text widget keep wheel behavior local to itself.
            return None
        target = self._resolve_mousewheel_target(event, source_widget=source_widget)
        if target is None:
            return None
        steps = self._normalize_mousewheel_steps(event)
        if steps == 0:
            return "break"
        try:
            target.yview_scroll(steps, "units")
        except tk.TclError:
            return None
        return "break"

    def _normalize_mousewheel_steps(self, event: tk.Event[tk.Misc]) -> int:
        event_num = getattr(event, "num", None)
        if event_num == 4:
            return -1
        if event_num == 5:
            return 1

        delta = getattr(event, "delta", 0)
        if not isinstance(delta, (int, float)) or delta == 0:
            return 0
        # On Windows delta is usually +/-120; trackpad deltas can be smaller.
        steps = int(delta / 120)
        if steps == 0:
            steps = 1 if delta > 0 else -1
        return -steps

    def _get_mousewheel_source_widget(self, event: tk.Event[tk.Misc]) -> tk.Misc | None:
        source_widget = self.winfo_containing(event.x_root, event.y_root)
        if source_widget is None and isinstance(event.widget, tk.Misc):
            source_widget = event.widget
        if source_widget is None or not isinstance(source_widget, tk.Misc):
            return None
        return source_widget

    def _is_local_wheel_only_widget(self, widget: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if str(current) in self.local_wheel_only_text_widgets:
                return True
            current = self._get_parent_widget(current)
        return False

    def _resolve_mousewheel_target(
        self,
        event: tk.Event[tk.Misc],
        source_widget: tk.Misc | None = None,
    ) -> tk.Misc | None:
        if source_widget is None:
            source_widget = self._get_mousewheel_source_widget(event)
        if source_widget is None:
            return None

        fallback_scroll_widget: tk.Misc | None = None
        fallback_text_widget: tk.Misc | None = None
        current: tk.Misc | None = source_widget
        while current is not None:
            if isinstance(current, tk.Canvas) and self._widget_can_scroll_vertically(current):
                return current

            if self._widget_can_scroll_vertically(current):
                if isinstance(current, tk.Text):
                    if fallback_text_widget is None:
                        fallback_text_widget = current
                elif fallback_scroll_widget is None:
                    fallback_scroll_widget = current

            current = self._get_parent_widget(current)

        return fallback_scroll_widget or fallback_text_widget

    def _get_parent_widget(self, widget: tk.Misc) -> tk.Misc | None:
        parent_name = widget.winfo_parent()
        if not parent_name:
            return None
        try:
            parent_widget = widget.nametowidget(parent_name)
        except KeyError:
            return None
        return parent_widget if isinstance(parent_widget, tk.Misc) else None

    def _widget_can_scroll_vertically(self, widget: tk.Misc) -> bool:
        yview = getattr(widget, "yview", None)
        if yview is None or not callable(yview):
            return False
        try:
            first, last = yview()
        except (tk.TclError, TypeError, ValueError):
            return False
        try:
            first_value = float(first)
            last_value = float(last)
        except (TypeError, ValueError):
            return False
        return first_value > 0.0 or last_value < 1.0

    def _build_log_panel(self) -> None:
        log_panel = ttk.Frame(self, style="Content.TFrame", padding=(20, 0, 20, 20))
        log_panel.grid(row=3, column=0, sticky="ew")
        log_panel.columnconfigure(0, weight=1)

        log_card = ttk.Frame(log_panel, style="Card.TFrame", padding=15)
        log_card.grid(row=0, column=0, sticky="ew")
        log_card.columnconfigure(0, weight=1)

        log_actions = ttk.Frame(log_card, style="Card.TFrame")
        log_actions.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        log_actions.columnconfigure(1, weight=1)

        ttk.Label(log_actions, text="CODEX ACTIVITY", style="FieldName.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(log_actions, textvariable=self.model_usage_status_var, style="FieldName.TLabel").grid(row=0, column=1, sticky="w", padx=(20, 0))

        model_tools = ttk.Frame(log_actions, style="Card.TFrame")
        model_tools.grid(row=0, column=2, sticky="e")

        self.stop_generation_button = ttk.Button(
            model_tools, text="Stop", command=self._on_stop_generation_clicked, state="disabled"
        )
        self.stop_generation_button.grid(row=0, column=0)

        self.select_model_button = ttk.Button(
            model_tools, text="Model", command=self._on_select_model_clicked
        )
        self.select_model_button.grid(row=0, column=1, padx=5)

        self.model_status_button = ttk.Button(
            model_tools, text="Status", command=self._on_model_status_clicked
        )
        self.model_status_button.grid(row=0, column=2)

        self.generation_log_text = tk.Text(
            log_card,
            wrap="word",
            height=6,
            font=("Consolas", 9),
            background=self.colors["bg"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground=self.colors["primary"],
            selectforeground="#ffffff",
            state="disabled",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.generation_log_text.grid(row=1, column=0, sticky="ew")
        self._bind_text_scroll_redirect(self.generation_log_text)
        self._setup_log_tags()

    def _build_status_bar(self) -> None:
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", padding=(20, 5)).grid(
            row=4, column=0, sticky="ew"
        )

    def _setup_log_tags(self) -> None:
        self.generation_log_text.tag_configure("error", foreground=self.colors["danger"])
        self.generation_log_text.tag_configure("status", foreground=self.colors["primary"])
        self.generation_log_text.tag_configure("system", foreground=self.colors["success"])
        self.generation_log_text.tag_configure("model", foreground=self.colors["secondary"])

    def _toggle_theme(self) -> None:
        current = self.theme_var.get()
        new_theme = "dark" if current == "light" else "light"
        self.theme_var.set(new_theme)
        self._configure_styles()
        self._refresh_ui_colors()
        self.theme_button.configure(text="🌙" if new_theme == "light" else "☀️")

    def _refresh_ui_colors(self) -> None:
        self.configure(background=self.colors["bg"])
        if hasattr(self, "fields_canvas"):
            self.fields_canvas.configure(background=self.colors["surface"])
        if hasattr(self, "generation_log_text"):
            self.generation_log_text.configure(
                background=self.colors["bg"],
                foreground=self.colors["text"],
                insertbackground=self.colors["text"],
            )
            self._setup_log_tags()
        if self.client_search_results_listbox is not None:
            self.client_search_results_listbox.configure(
                background=self.colors["surface"],
                foreground=self.colors["text"],
                selectbackground=self.colors["primary"],
                selectforeground="#ffffff",
            )
        if (
            self.client_search_results_popup is not None
            and self.client_search_results_popup.winfo_exists()
        ):
            self.client_search_results_popup.configure(background=self.colors["border"])
        
        # Refresh settings window non-ttk widgets if open
        if self.settings_window is not None and self.settings_window.winfo_exists():
            if hasattr(self, "settings_file_listbox") and self.settings_file_listbox:
                self.settings_file_listbox.configure(
                    background=self.colors["bg"],
                    foreground=self.colors["text"],
                )
            if hasattr(self, "settings_content_text") and self.settings_content_text:
                self.settings_content_text.configure(
                    background=self.colors["surface"],
                    foreground=self.colors["text"],
                    insertbackground=self.colors["primary"],
                )
            if hasattr(self, "settings_profile_canvas") and self.settings_profile_canvas:
                self.settings_profile_canvas.configure(background=self.colors["surface"])
            if hasattr(self, "settings_caption_canvas") and self.settings_caption_canvas:
                self.settings_caption_canvas.configure(background=self.colors["surface"])
            if hasattr(self, "settings_caption_field_texts"):
                for txt in self.settings_caption_field_texts.values():
                    txt.configure(
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        insertbackground=self.colors["primary"],
                    )

        self._render_current_post() # Redraw fields with new colors

    def _hide_client_search_results(self) -> None:
        if (
            self.client_search_results_popup is not None
            and self.client_search_results_popup.winfo_exists()
        ):
            self.client_search_results_popup.withdraw()

    def _is_client_search_popup_visible(self) -> bool:
        popup = self.client_search_results_popup
        if popup is None or not popup.winfo_exists():
            return False
        try:
            return popup.state() != "withdrawn"
        except tk.TclError:
            return False

    def _is_widget_within(self, widget: tk.Misc, ancestor: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if current is ancestor:
                return True
            current = self._get_parent_widget(current)
        return False

    def _hide_client_search_results_on_global_click(self, event: tk.Event[tk.Misc]) -> None:
        if not self._is_client_search_popup_visible():
            return
        popup = self.client_search_results_popup
        if popup is None or not popup.winfo_exists():
            return
        widget = event.widget
        if not isinstance(widget, tk.Misc):
            self._hide_client_search_results()
            return
        if self._is_widget_within(widget, self.search_entry):
            return
        if self._is_widget_within(widget, popup):
            return
        self._hide_client_search_results()

    def _hide_client_search_results_if_focus_lost(self) -> None:
        if not self._is_client_search_popup_visible():
            return
        focus_widget = self.focus_get()
        if not isinstance(focus_widget, tk.Misc):
            self._hide_client_search_results()
            return
        popup = self.client_search_results_popup
        if popup is None or not popup.winfo_exists():
            self._hide_client_search_results()
            return
        if self._is_widget_within(focus_widget, self.search_entry):
            return
        if self._is_widget_within(focus_widget, popup):
            return
        self._hide_client_search_results()

    def _focus_client_search_results(self, _event: tk.Event[tk.Misc]) -> str | None:
        if (
            not self._is_client_search_popup_visible()
            or self.client_search_results_listbox is None
            or self.client_search_results_listbox.size() == 0
        ):
            return None
        listbox = self.client_search_results_listbox
        target_index = listbox.curselection()[0] if listbox.curselection() else 0
        listbox.activate(target_index)
        listbox.see(target_index)
        listbox.focus_set()
        return "break"

    def _ensure_client_search_results_popup(self) -> bool:
        if (
            self.client_search_results_popup is not None
            and self.client_search_results_popup.winfo_exists()
            and self.client_search_results_listbox is not None
            and self.client_search_results_scrollbar is not None
        ):
            return True

        try:
            popup = tk.Toplevel(self)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.transient(self)
            popup.configure(background=self.colors["border"], padx=1, pady=1)
            popup.columnconfigure(0, weight=1)
            popup.rowconfigure(0, weight=1)

            listbox = tk.Listbox(
                popup,
                exportselection=False,
                activestyle="dotbox",
                font=("Segoe UI", 10),
                width=20,
                height=6,
                background=self.colors["surface"],
                foreground=self.colors["text"],
                selectbackground=self.colors["primary"],
                selectforeground="#ffffff",
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
            )
            listbox.grid(row=0, column=0, sticky="nsew")
            listbox.bind("<<ListboxSelect>>", self._on_client_search_result_selected)
            listbox.bind("<Double-Button-1>", self._on_client_search_result_selected)
            listbox.bind("<Return>", self._on_client_search_result_selected)
            listbox.bind("<Escape>", lambda _event: self._hide_client_search_results())
            listbox.bind(
                "<FocusOut>",
                lambda _event: self.after(50, self._hide_client_search_results_if_focus_lost),
            )

            scrollbar = ttk.Scrollbar(
                popup,
                orient="vertical",
                command=listbox.yview,
            )
            scrollbar.grid(row=0, column=1, sticky="ns")
            listbox.configure(yscrollcommand=scrollbar.set)

            self.client_search_results_popup = popup
            self.client_search_results_listbox = listbox
            self.client_search_results_scrollbar = scrollbar
            return True
        except tk.TclError:
            self.client_search_results_popup = None
            self.client_search_results_listbox = None
            self.client_search_results_scrollbar = None
            return False

    def _position_client_search_results_popup(self) -> None:
        if (
            self.client_search_results_popup is None
            or not self.client_search_results_popup.winfo_exists()
            or self.client_search_results_listbox is None
        ):
            return
        self.update_idletasks()
        popup = self.client_search_results_popup
        x_pos = self.search_entry.winfo_rootx()
        y_pos = self.search_entry.winfo_rooty() + self.search_entry.winfo_height() + 2
        width = max(180, self.search_entry.winfo_width())
        if (
            self.client_search_results_scrollbar is not None
            and self.client_search_results_scrollbar.winfo_manager()
        ):
            width += self.client_search_results_scrollbar.winfo_reqwidth()
        height = self.client_search_results_listbox.winfo_reqheight() + 2
        popup.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def _show_client_search_results(self, client_names: list[str]) -> None:
        if not client_names:
            self._hide_client_search_results()
            return
        if not self._ensure_client_search_results_popup():
            return
        if self.client_search_results_listbox is None:
            return

        self.client_search_results_listbox.delete(0, "end")
        for client_name in client_names:
            self.client_search_results_listbox.insert("end", client_name)

        visible_rows = min(max(len(client_names), 1), 6)
        self.client_search_results_listbox.configure(height=visible_rows)
        if self.client_search_results_scrollbar is not None:
            if len(client_names) > visible_rows:
                self.client_search_results_scrollbar.grid()
            else:
                self.client_search_results_scrollbar.grid_remove()
        if self.client_search_results_popup is not None and self.client_search_results_popup.winfo_exists():
            self._position_client_search_results_popup()
            self.client_search_results_popup.deiconify()
            self.client_search_results_popup.lift()

    def _on_client_search_result_selected(self, _event: tk.Event[tk.Misc]) -> None:
        if self.client_search_results_listbox is None:
            return

        selection = self.client_search_results_listbox.curselection()
        if not selection:
            return
        selected_client = self.client_search_results_listbox.get(selection[0]).strip()
        if not selected_client:
            return

        self.client_var.set(selected_client)
        self.client_search_var.set("")
        self._hide_client_search_results()
        self._on_client_selected(_event)

    def _on_client_search_changed(self, *_args: object) -> None:
        filtered = filter_clients_by_search_term(
            list(self.client_files.keys()),
            self.client_search_var.get(),
        )
        self.client_combo["values"] = filtered
        if self.client_search_var.get().strip() and filtered:
            self._show_client_search_results(filtered)
        else:
            self._hide_client_search_results()
        
    def _build_ui_legacy(self) -> None:
        # Keep original _build_ui as a reference if needed, but we'll replace it
        pass


        self.model_status_button = ttk.Button(
            model_tools, text="Status", command=self._on_model_status_clicked
        )
        self.model_status_button.grid(row=0, column=2)

        self.generation_log_text = tk.Text(
            log_card,
            wrap="word",
            height=6,
            font=("Consolas", 9),
            background=self.colors["bg"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground=self.colors["primary"],
            selectforeground="#ffffff",
            state="disabled",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.generation_log_text.grid(row=1, column=0, sticky="ew")

        # Bottom Status Bar
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", padding=(20, 5)).grid(
            row=4, column=0, sticky="ew"
        )

    def _ensure_test_script_for_editing(self) -> None:
        target_path = self.base_dir / TEST_SCRIPT_FILENAME
        source_text = load_editable_source_text(self.base_dir)
        if source_text is None:
            self._append_generation_log(
                "[setup] Unable to generate test.py because source script data is unavailable."
            )
            return

        try:
            if target_path.is_file():
                existing_text = target_path.read_text(encoding="utf-8", errors="replace")
                if existing_text == source_text:
                    self._append_generation_log(f"[setup] test.py is up to date: {target_path}")
                else:
                    self._append_generation_log(
                        f"[setup] test.py already exists; keeping your editable file: {target_path}"
                    )
                return
            target_path.write_text(source_text, encoding="utf-8")
        except OSError as error:
            self._append_generation_log(f"[setup] Failed to write test.py: {error}")
            return

        self._append_generation_log(f"[setup] Generated editable source copy: {target_path}")

    def _run_startup_setup_if_needed(self) -> None:
        try:
            migrated_files = sync_legacy_general_agents_into_agents(self.base_dir)
            for migrated_path in migrated_files:
                self._append_generation_log(
                    f"[setup] Copied general agent file into {AGENTS_DIRNAME}/: {migrated_path.name}"
                )
        except OSError as error:
            self._append_generation_log(
                f"[setup] Failed to initialize {AGENTS_DIRNAME}/ from legacy files: {error}"
            )

        try:
            profile_instruction_path = ensure_client_profile_autofill_instruction(self.base_dir)
            self._append_generation_log(
                f"[setup] Ensured client profile auto-fill runbook: {profile_instruction_path}"
            )
        except OSError as error:
            self._append_generation_log(
                f"[setup] Failed to ensure client profile auto-fill runbook: {error}"
            )

        node_runtime_missing = notify_nodejs_install_if_missing(parent=self)
        if node_runtime_missing:
            self.status_var.set(
                "Node.js/npm not found. Install Node.js, ensure PATH is updated, then restart the app."
            )

        missing_items = self._collect_setup_gaps()
        if not missing_items:
            return

        missing_lines = "\n".join(f"- {item}" for item in missing_items)
        should_setup = messagebox.askyesno(
            "Setup Required",
            "This app is missing required workspace/runtime items:\n\n"
            f"{missing_lines}\n\n"
            "Create/install these requirements now?",
        )
        if not should_setup:
            self.status_var.set("Startup setup skipped. Some features may not work.")
            return

        summary_lines = self._attempt_auto_setup(missing_items)
        final_missing = self._collect_setup_gaps()
        if final_missing:
            unresolved = "\n".join(f"- {item}" for item in final_missing)
            messagebox.showwarning(
                "Setup Partially Complete",
                "Some requirements are still missing:\n\n"
                f"{unresolved}\n\n"
                "Check the setup report in the logs panel for details.",
            )
        else:
            messagebox.showinfo(
                "Setup Complete",
                "Startup requirements were created/installed successfully.",
            )

        for line in summary_lines:
            self._append_generation_log(f"[setup] {line}")

    def _collect_setup_gaps(self) -> list[str]:
        missing: list[str] = []

        if not self.clients_dir.exists():
            missing.append("Clients folder")

        agents_root = get_general_agents_root(self.base_dir)
        if not agents_root.is_dir():
            missing.append("Agents folder")

        runbook_path = get_smarcomms_runbook_path(self.base_dir)
        if not runbook_path.is_file():
            missing.append(AGENTS_RUNBOOK_LABEL)
        profile_autofill_runbook_path = get_client_profile_autofill_instruction_path(self.base_dir)
        if not profile_autofill_runbook_path.is_file():
            missing.append(AGENTS_CLIENT_PROFILE_AUTOFILL_LABEL)

        skills_root = Path.home() / ".codex" / "skills"
        if not skills_root.exists():
            missing.append("Codex skills directory (~/.codex/skills)")

        content_creator_skill = skills_root / "content-creator" / "SKILL.md"
        if not content_creator_skill.is_file():
            if resolve_bundled_resource("content-creator.zip", self.base_dir) is None:
                missing.append(
                    "content-creator Codex skill (bundle not found; manual installation may be required)"
                )
            else:
                missing.append("content-creator Codex skill")

        codex_executable = self._resolve_codex_executable()
        if codex_executable is None:
            missing.append("Codex CLI")
            npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
            if npm_executable is None:
                missing.append("Node.js/npm (required to auto-install Codex CLI)")
            missing.append("Context7 MCP server (requires Codex CLI)")
            missing.append("Chrome DevTools MCP server (requires Codex CLI)")
            return missing

        missing_mcp = self._detect_missing_mcp_servers(codex_executable)
        if "context7" in missing_mcp:
            missing.append("Context7 MCP server")
        if "chrome-devtools" in missing_mcp:
            missing.append("Chrome DevTools MCP server")
        return missing

    def _attempt_auto_setup(self, missing_items: list[str]) -> list[str]:
        report_lines: list[str] = []
        codex_installed_during_setup = False

        def add_report(message: str) -> None:
            report_lines.append(message)
            self._append_generation_log(f"[setup] {message}")
            self.update_idletasks()

        if "Clients folder" in missing_items:
            self.clients_dir.mkdir(parents=True, exist_ok=True)
            add_report(f"Created folder: {self.clients_dir}")

        agents_root = get_general_agents_root(self.base_dir)
        if "Agents folder" in missing_items:
            agents_root.mkdir(parents=True, exist_ok=True)
            add_report(f"Created folder: {agents_root}")

        try:
            migrated_files = sync_legacy_general_agents_into_agents(self.base_dir)
        except OSError as error:
            migrated_files = []
            add_report(f"Failed to copy legacy general agent files into Agents: {error}")
        else:
            for migrated_path in migrated_files:
                add_report(f"Copied general agent file into Agents: {migrated_path}")

        runbook_path = get_smarcomms_runbook_path(self.base_dir)
        if AGENTS_RUNBOOK_LABEL in missing_items and not runbook_path.is_file():
            runbook_content = load_default_smarcomms_text(self.base_dir)
            runbook_path.write_text(runbook_content, encoding="utf-8")
            bundled_runbook = resolve_bundled_resource(SMARCOMMS_FILENAME, self.base_dir)
            if bundled_runbook is not None:
                add_report(
                    f"Created file from bundled runbook content: {runbook_path}"
                )
            else:
                add_report(f"Created file from fallback template: {runbook_path}")

        profile_autofill_path = get_client_profile_autofill_instruction_path(self.base_dir)
        if AGENTS_CLIENT_PROFILE_AUTOFILL_LABEL in missing_items and not profile_autofill_path.is_file():
            profile_autofill_path.write_text(
                DEFAULT_CLIENT_PROFILE_AUTOFILL_CONTENT,
                encoding="utf-8",
            )
            add_report(f"Created file from template: {profile_autofill_path}")

        skills_root = Path.home() / ".codex" / "skills"
        if "Codex skills directory (~/.codex/skills)" in missing_items:
            skills_root.mkdir(parents=True, exist_ok=True)
            add_report(f"Ensured skills directory: {skills_root}")

        codex_executable = self._resolve_codex_executable()
        if codex_executable is None and "Codex CLI" in missing_items:
            add_report("Codex CLI missing. Attempting installation via npm...")
            npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
            if npm_executable is None:
                add_report("npm not found. Cannot auto-install Codex CLI.")
            else:
                install_attempts = [
                    [npm_executable, "install", "-g", "@openai/codex"],
                    [npm_executable, "install", "-g", "codex"],
                ]
                installed = False
                for command in install_attempts:
                    ok, output = self._run_setup_command(command, timeout_seconds=900)
                    if ok:
                        installed = True
                        codex_installed_during_setup = True
                        add_report(f"Codex install succeeded: {' '.join(command)}")
                        if output:
                            add_report(output.splitlines()[-1])
                        break
                    add_report(f"Codex install attempt failed: {' '.join(command)}")
                if not installed:
                    add_report("Codex CLI install failed. Please install Codex manually.")

        codex_executable = self._resolve_codex_executable()
        if codex_executable is not None:
            if codex_installed_during_setup:
                login_terminal_opened = launch_codex_login_terminal(
                    codex_executable,
                    base_dir=self.base_dir,
                )
                if login_terminal_opened:
                    add_report("Opened interactive Codex CLI for OAuth login.")
                else:
                    add_report(
                        "Codex installed, but failed to open interactive login terminal. "
                        "Run `codex login` manually."
                    )

            missing_mcp = self._detect_missing_mcp_servers(codex_executable)
            npx_executable = shutil.which("npx.cmd") or shutil.which("npx")
            if "context7" in missing_mcp:
                if npx_executable is None:
                    add_report("Cannot install Context7 MCP server because npx is unavailable.")
                else:
                    ok, _ = self._run_setup_command(
                        [
                            codex_executable,
                            "mcp",
                            "add",
                            "context7",
                            "--",
                            npx_executable,
                            "-y",
                            "@upstash/context7-mcp",
                        ],
                        timeout_seconds=180,
                    )
                    if ok:
                        add_report("Installed Context7 MCP server.")
                    else:
                        add_report("Failed to install Context7 MCP server.")

            if "chrome-devtools" in missing_mcp:
                if npx_executable is None:
                    add_report("Cannot install Chrome DevTools MCP server because npx is unavailable.")
                else:
                    ok, _ = self._run_setup_command(
                        [
                            codex_executable,
                            "mcp",
                            "add",
                            "chrome-devtools",
                            "--",
                            npx_executable,
                            "-y",
                            "chrome-devtools-mcp@latest",
                        ],
                        timeout_seconds=180,
                    )
                    if ok:
                        add_report("Installed Chrome DevTools MCP server.")
                    else:
                        add_report("Failed to install Chrome DevTools MCP server.")
        else:
            add_report("Skipping MCP install because Codex CLI is unavailable.")

        skills_zip = resolve_bundled_resource("content-creator.zip", self.base_dir)
        content_creator_skill = skills_root / "content-creator" / "SKILL.md"
        if not content_creator_skill.exists():
            if skills_zip is not None:
                try:
                    with zipfile.ZipFile(skills_zip, "r") as zip_ref:
                        zip_ref.extractall(skills_root)
                    add_report(f"Installed content-creator skill from bundle: {skills_zip}")
                except (OSError, zipfile.BadZipFile) as error:
                    add_report(f"Failed to extract content-creator skill bundle: {error}")
            else:
                add_report("content-creator skill bundle not found; skipped automatic skill install.")

        return report_lines

    def _run_setup_command(
        self,
        command: list[str],
        timeout_seconds: int = 180,
        input_text: str | None = None,
    ) -> tuple[bool, str]:
        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        try:
            completed = subprocess.run(
                command,
                cwd=self.base_dir,
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                creationflags=creation_flags,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, str(error)

        output = (completed.stdout or "").strip()
        error_output = (completed.stderr or "").strip()
        combined = "\n".join(part for part in [output, error_output] if part).strip()
        return completed.returncode == 0, combined

    def _detect_missing_mcp_servers(self, codex_executable: str) -> set[str]:
        required_servers = {"context7", "chrome-devtools"}
        ok, output = self._run_setup_command(
            [codex_executable, "mcp", "list", "--json"],
            timeout_seconds=60,
        )
        if not ok:
            return required_servers
        if not output:
            return required_servers

        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return required_servers

        configured_servers: set[str] = set()
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if isinstance(name, str):
                    configured_servers.add(name)
        elif isinstance(payload, dict):
            for key, item in payload.items():
                if isinstance(item, dict) and item.get("enabled", True):
                    configured_servers.add(str(key))

        return required_servers.difference(configured_servers)

    def _populate_clients(self) -> None:
        clients = sorted(self.client_files.keys(), key=str.lower)
        self._on_client_search_changed()
        if not clients:
            self.post_created_var.set("Created: --")
            self.status_var.set(
                "No markdown files found in Clients/. Expected [Client Name]_*.md, Graphic_Post_Ideas_*.md, or *_*.md."
            )
            self.last_selected_client = ""
            self._refresh_settings_panel(preserve_selection=False, reload_current=True)
            return

        self.client_var.set(clients[0])
        self.last_selected_client = clients[0]
        self._refresh_files_for_client(clients[0])
        self._refresh_settings_panel(preserve_selection=False, reload_current=True)

    def _refresh_files_for_client(
        self,
        client_name: str,
        preferred_file: str | None = None,
        preferred_post_index: int | None = None,
    ) -> None:
        self.file_lookup = {}
        display_values: list[str] = []
        for md_path in self.client_files.get(client_name, []):
            relative = md_path.relative_to(self.clients_dir / client_name)
            display_name = str(relative)
            self.file_lookup[display_name] = md_path
            display_values.append(display_name)

        self.file_combo["values"] = display_values

        if not display_values:
            self.file_var.set("")
            self.current_file_path = None
            self.post_created_var.set("Created: --")
            self.current_posts = []
            self.current_post_index = 0
            self._update_post_navigation_state()
            self._update_post_counter()
            self._render_field_message("No matching markdown files were found for this client.")
            self.status_var.set(f"{client_name}: no matching markdown file")
            return

        selected_file = display_values[0]
        if preferred_file and preferred_file in self.file_lookup:
            selected_file = preferred_file

        self.file_var.set(selected_file)
        preserve_index = preferred_file is not None and selected_file == preferred_file
        self._load_selected_file(preferred_post_index if preserve_index else None)

    def _load_selected_file(self, preferred_post_index: int | None = None) -> None:
        selected_key = self.file_var.get()
        selected_path = self.file_lookup.get(selected_key)
        if selected_path is None:
            self.current_file_path = None
            self.post_created_var.set("Created: --")
            self.current_posts = []
            self.current_post_index = 0
            self._update_post_navigation_state()
            self._update_post_counter()
            self._render_field_message("Select a valid markdown file from the list.")
            return

        self.current_file_path = selected_path
        self.post_created_var.set(f"Created: {resolve_post_file_created_text(selected_path)}")
        text = selected_path.read_text(encoding="utf-8", errors="replace")
        self.current_posts = extract_post_details(text)
        if preferred_post_index is None or not self.current_posts:
            self.current_post_index = 0
        else:
            self.current_post_index = max(0, min(preferred_post_index, len(self.current_posts) - 1))
        self._render_current_post()
        self.status_var.set(f"Loaded: {selected_path}")

    def _on_create_client_clicked(self) -> None:
        requested_name = simpledialog.askstring(
            "Create Client",
            "Enter the new client name:",
            parent=self,
        )
        if requested_name is None:
            return

        client_name = normalize_client_name(requested_name)
        if not client_name:
            messagebox.showerror("Invalid Name", "Client name cannot be blank.")
            return
        if any(char in INVALID_CLIENT_NAME_CHARS for char in client_name):
            invalid_chars = "".join(sorted(INVALID_CLIENT_NAME_CHARS))
            messagebox.showerror(
                "Invalid Name",
                f"Client name contains invalid characters.\nDisallowed: {invalid_chars}",
            )
            return

        client_dir = self.clients_dir / client_name
        if client_dir.exists():
            messagebox.showerror(
                "Client Exists",
                f"A client folder already exists:\n{client_dir}",
            )
            return

        try:
            self.clients_dir.mkdir(parents=True, exist_ok=True)
            client_dir.mkdir(parents=False, exist_ok=False)
            create_client_scaffold_files(client_dir, client_name)
        except OSError as error:
            messagebox.showerror(
                "Create Client Failed",
                f"Could not create client files for {client_name}.\n\n{error}",
            )
            return

        self.client_files = find_client_markdown_files(self.base_dir)
        self._on_client_search_changed()
        clients = sorted(self.client_files.keys(), key=str.lower)

        if (
            self.settings_window is not None
            and self.settings_window.winfo_exists()
            and self.settings_mode_var.get() == "client"
            and self.settings_editor_dirty
            and not self._confirm_discard_settings_changes()
        ):
            self.last_md_signature = build_workspace_md_signature(self.base_dir)
            self.status_var.set(
                f"Created client: {client_name}. Open Client Setting when you're ready to edit profile."
            )
            return

        self.settings_editor_dirty = False
        self.client_var.set(client_name)
        self.last_selected_client = client_name
        self._refresh_files_for_client(client_name)
        self._open_settings_window("client")
        if self.settings_mode_var.get() == "client":
            self._refresh_settings_panel(
                preserve_selection=False,
                reload_current=True,
                preferred_key="CLIENT_PROFILE.md",
            )

        self.last_md_signature = build_workspace_md_signature(self.base_dir)
        self.status_var.set(f"Created client: {client_name}")

    def _on_delete_client_clicked(self) -> None:
        client_name = self.client_var.get().strip()
        if not client_name:
            messagebox.showwarning("No Client Selected", "Please select a client to delete.")
            return

        should_delete = messagebox.askyesno(
            "Delete Client",
            f"Are you sure you want to move '{client_name}' to the Deleted Clients folder?\n\n"
            "This will temporarily archive the client folder.",
            parent=self,
        )
        if not should_delete:
            return

        client_dir = self.clients_dir / client_name
        deleted_clients_root = self.base_dir / DELETED_CLIENTS_DIRNAME
        
        try:
            deleted_clients_root.mkdir(parents=True, exist_ok=True)
            
            # Handle name collisions in Deleted Clients
            destination = deleted_clients_root / client_name
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination = deleted_clients_root / f"{client_name}_{timestamp}"
            
            shutil.move(str(client_dir), str(destination))
            
            self._append_generation_log(f"[system] Moved client '{client_name}' to {DELETED_CLIENTS_DIRNAME}")
            
            # Refresh data
            self.client_files = find_client_markdown_files(self.base_dir)
            self._populate_clients()
            self.last_md_signature = build_workspace_md_signature(self.base_dir)
            
            messagebox.showinfo("Client Deleted", f"Client '{client_name}' has been moved to Deleted Clients.")
            
        except OSError as error:
            messagebox.showerror(
                "Delete Failed",
                f"Could not move client folder '{client_name}':\n\n{error}",
            )

    def _on_client_selected(self, _event: tk.Event[tk.Misc]) -> None:
        self._hide_client_search_results()
        client_name = self.client_var.get().strip()
        if not client_name:
            return

        if (
            client_name != self.last_selected_client
            and self.settings_mode_var.get() == "client"
            and self.settings_editor_dirty
            and not self._confirm_discard_settings_changes()
        ):
            self.client_var.set(self.last_selected_client)
            return

        self.settings_editor_dirty = False
        self._refresh_files_for_client(client_name)
        self.last_selected_client = client_name
        self._refresh_settings_panel(preserve_selection=False, reload_current=True)

    def _on_file_selected(self, _event: tk.Event[tk.Misc]) -> None:
        self._load_selected_file()

    def _on_prev_post_key(self, _event: tk.Event[tk.Misc]) -> None:
        self._show_previous_post()

    def _on_next_post_key(self, _event: tk.Event[tk.Misc]) -> None:
        self._show_next_post()

    def _show_previous_post(self) -> None:
        if not self.current_posts:
            return
        if self.current_post_index <= 0:
            return
        self.current_post_index -= 1
        self._render_current_post()

    def _show_next_post(self) -> None:
        if not self.current_posts:
            return
        if self.current_post_index >= len(self.current_posts) - 1:
            return
        self.current_post_index += 1
        self._render_current_post()

    def _render_current_post(self) -> None:
        self._update_post_counter()
        self._update_post_navigation_state()

        if self.current_file_path is None:
            self._render_field_message("Select a valid markdown file from the list.")
            return

        if not self.current_posts:
            self._render_field_message(
                "No structured post fields were detected in this markdown file."
            )
            return

        self._render_post_fields(self.current_posts[self.current_post_index])

    def _update_post_counter(self) -> None:
        if not self.current_posts:
            self.post_counter_var.set("Post 0 of 0")
            return

        current_post = self.current_posts[self.current_post_index]
        detected_number = current_post.get("Post Number")
        if isinstance(detected_number, int):
            self.post_counter_var.set(
                f"Post {detected_number} ({self.current_post_index + 1} of {len(self.current_posts)})"
            )
            return
        self.post_counter_var.set(
            f"Post {self.current_post_index + 1} of {len(self.current_posts)}"
        )

    def _update_post_navigation_state(self) -> None:
        can_go_left = bool(self.current_posts) and self.current_post_index > 0
        can_go_right = (
            bool(self.current_posts) and self.current_post_index < len(self.current_posts) - 1
        )
        self.prev_button.configure(state="normal" if can_go_left else "disabled")
        self.next_button.configure(state="normal" if can_go_right else "disabled")
        if hasattr(self, "regenerate_button"):
            is_generating = is_generation_process_running(self.generation_process)
            self.regenerate_button.configure(state="normal" if (self.current_posts and not is_generating) else "disabled")

    def _render_post_fields(self, post: dict[str, object]) -> None:
        fields = build_post_display_fields(post)
        if not fields:
            self._render_field_message("No fields found for this post.")
            return
        file_signature = str(self.current_file_path) if self.current_file_path is not None else ""
        fields_signature = (
            self.theme_var.get(),
            file_signature,
            self.current_post_index,
            tuple(fields),
        )
        if self.last_rendered_fields_signature == fields_signature:
            return

        self._clear_field_rows()

        for row_index, (field_name, field_value) in enumerate(fields):
            is_optional_item = field_name.startswith("Optional List ")
            label_left_padding = 20 if is_optional_item else 0
            
            # Row Container for Hover effect simulation
            row_frame = ttk.Frame(self.fields_rows_frame, style="Card.TFrame")
            row_frame.grid(row=row_index, column=0, columnspan=3, sticky="ew", pady=2)
            row_frame.columnconfigure(1, weight=1)

            def _on_enter(e: tk.Event[tk.Misc], rf=row_frame):
                rf.configure(style="Hover.TFrame")
            def _on_leave(e: tk.Event[tk.Misc], rf=row_frame):
                rf.configure(style="Card.TFrame")
            
            row_frame.bind("<Enter>", _on_enter)
            row_frame.bind("<Leave>", _on_leave)

            # Label (Monospace)
            ttk.Label(row_frame, text=field_name, style="FieldName.TLabel", width=25).grid(
                row=0,
                column=0,
                sticky="nw",
                pady=8,
                padx=(label_left_padding, 10),
            )
            
            is_multiline_field = should_use_multiline_post_field(field_name)
            if is_multiline_field:
                line_count = field_value.count("\n") + 1 if field_value else 1
                field_height = max(3, min(10, line_count))
                value_text = tk.Text(
                    row_frame,
                    wrap="word",
                    height=field_height,
                    width=POST_DETAILS_VALUE_ENTRY_WIDTH,
                    font=("Segoe UI", 10),
                    background=self.colors["surface"],
                    foreground=self.colors["text"],
                    insertbackground=self.colors["text"],
                    selectbackground=self.colors["primary"],
                    selectforeground="#ffffff",
                    relief="flat",
                    padx=10,
                    pady=8,
                    highlightthickness=1,
                    highlightbackground=self.colors["border"],
                    highlightcolor=self.colors["primary"],
                )
                value_text.insert("1.0", field_value)
                value_text.configure(state="disabled")
                value_text.grid(row=0, column=1, sticky="ew", pady=4)
                self._bind_text_scroll_redirect(value_text)
                value_text.bind(
                    "<Button-1>",
                    lambda event, field_name=field_name, field_value=field_value: self._on_value_field_clicked(
                        event, field_name, field_value
                    ),
                )
            else:
                value_var = tk.StringVar(value=field_value)
                self.field_value_vars.append(value_var)

                value_entry = tk.Entry(
                    row_frame,
                    textvariable=value_var,
                    state="readonly",
                    width=POST_DETAILS_VALUE_ENTRY_WIDTH,
                    font=("Segoe UI", 10),
                    background=self.colors["surface"],
                    foreground=self.colors["text"],
                    readonlybackground=self.colors["surface"],
                    insertbackground=self.colors["text"],
                    selectbackground=self.colors["primary"],
                    selectforeground="#ffffff",
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=1,
                    highlightbackground=self.colors["border"],
                )
                value_entry.grid(row=0, column=1, sticky="ew", pady=4, ipady=4)
                value_entry.bind(
                    "<Button-1>",
                    lambda event, field_name=field_name, field_value=field_value: self._on_value_field_clicked(
                        event, field_name, field_value
                    ),
                )

            # Copy Button (Only shows on hover could be cool, but for simplicity let's keep it styled)
            copy_button = ttk.Button(
                row_frame,
                text="COPY",
                style="Copy.TButton",
                width=8,
                command=lambda field_name=field_name, field_value=field_value: self._copy_to_clipboard(
                    field_name, field_value
                ),
            )
            copy_button.grid(
                row=0,
                column=2,
                sticky="ne" if is_multiline_field else "e",
                padx=(10, 0),
                pady=4,
            )
        self.last_rendered_fields_signature = fields_signature
        self.last_rendered_field_message = None

    def _render_field_message(self, message: str) -> None:
        if self.last_rendered_field_message == message:
            return
        self._clear_field_rows()
        ttk.Label(self.fields_rows_frame, text=message, style="FieldValue.TLabel").grid(row=0, column=0, sticky="w")
        self.last_rendered_fields_signature = None
        self.last_rendered_field_message = message

    def _clear_field_rows(self) -> None:
        self.field_value_vars.clear()
        for widget in self.fields_rows_frame.winfo_children():
            widget.destroy()

    def _on_value_field_clicked(
        self,
        event: tk.Event[tk.Misc],
        field_name: str,
        field_value: str,
    ) -> None:
        copied = self._copy_to_clipboard(field_name, field_value)
        if copied:
            self._show_copy_feedback_toast(event.x_root, event.y_root)

    def _show_copy_feedback_toast(self, x_root: int, y_root: int) -> None:
        if self.copy_feedback_toast is not None and self.copy_feedback_toast.winfo_exists():
            self.copy_feedback_toast.destroy()

        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        try:
            toast.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        ttk.Label(
            toast,
            text=f"✓ {COPY_TOAST_TEXT}",
            style="CopyToast.TLabel",
        ).grid(row=0, column=0)

        self.copy_feedback_toast = toast
        self._animate_copy_feedback_toast(toast, x_root, y_root, step=0)

    def _animate_copy_feedback_toast(
        self,
        toast: tk.Toplevel,
        x_root: int,
        y_root: int,
        step: int,
    ) -> None:
        if not toast.winfo_exists():
            return

        progress = step / COPY_TOAST_STEPS
        x_position = int(x_root + 12)
        y_position = int(y_root - 18 - (COPY_TOAST_FLOAT_PIXELS * progress))
        toast.geometry(f"+{x_position}+{y_position}")

        try:
            toast.attributes("-alpha", max(0.0, 0.92 - progress))
        except tk.TclError:
            pass

        if step >= COPY_TOAST_STEPS:
            toast.destroy()
            if self.copy_feedback_toast is toast:
                self.copy_feedback_toast = None
            return

        self.after(
            COPY_TOAST_STEP_DELAY_MS,
            lambda: self._animate_copy_feedback_toast(toast, x_root, y_root, step + 1),
        )

    def _copy_to_clipboard(self, field_name: str, field_value: str) -> bool:
        try:
            self.clipboard_clear()
            self.clipboard_append(field_value)
            self.update()
        except tk.TclError:
            self.status_var.set(f"Unable to copy {field_name} to clipboard.")
            return False

        self.status_var.set(f"Copied {field_name} to clipboard.")
        return True

    def _on_select_model_clicked(self) -> None:
        backend = self.selected_backend.get()
        catalog = []

        if backend == "Codex":
            codex_executable = self._resolve_codex_executable()
            if codex_executable is None:
                messagebox.showerror(
                    "Codex Not Found",
                    "Could not find codex.cmd. Install Codex CLI or add codex.cmd to PATH.",
                )
                return

            self.status_var.set("Loading available Codex models...")
            self._append_generation_log("[model] Loading available models from Codex...")
            try:
                catalog = fetch_codex_model_catalog(codex_executable, base_dir=self.base_dir)
            except (OSError, RuntimeError) as error:
                self.status_var.set("Failed to load models from Codex.")
                self._append_generation_log(f"[model] Failed to load available models: {error}")
                messagebox.showerror(
                    "Model Discovery Failed",
                    f"Could not load model options from Codex.\n\n{error}",
                )
                return
            self.codex_model_catalog = catalog
        else:
            # For Gemini, use a hardcoded list for now as CLI doesn't have model/list yet
            catalog = [
                {"model": "gemini-2.0-flash", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-2.0-flash-lite", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-1.5-pro", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-1.5-flash", "efforts": ["N/A"], "default_effort": "N/A"},
            ]

        selection = self._prompt_model_and_effort_selection(catalog)
        if selection is None:
            self.status_var.set("Model selection cancelled.")
            return

        selected_backend, selected_model, selected_effort = selection
        self.selected_backend.set(selected_backend)
        if selected_backend == "Codex":
            self.selected_codex_model = selected_model
            self.selected_reasoning_effort = selected_effort
        else:
            self.selected_gemini_model = selected_model
            # Gemini doesn't use effort in the same way, but we'll keep the variable for consistency
            self.selected_reasoning_effort = "medium" 

        self.status_var.set(f"Backend: {selected_backend} | Model: {selected_model}")
        self._append_generation_log(
            f"[model] Switched to {selected_backend} backend using model {selected_model}."
        )

    def _prompt_model_and_effort_selection(
        self,
        catalog: list[dict[str, object]],
    ) -> tuple[str, str, str] | None:
        dialog = tk.Toplevel(self)
        dialog.title("Select Model & Backend")
        dialog.geometry("560x360")
        dialog.minsize(540, 340)
        dialog.configure(background=self.colors["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        backend_var = tk.StringVar(value=self.selected_backend.get())
        model_var = tk.StringVar()
        effort_var = tk.StringVar()
        
        result: dict[str, tuple[str, str, str] | None] = {"value": None}

        # Shared data for refreshing
        backend_catalogs = {
            "Codex": catalog if backend_var.get() == "Codex" else [],
            "Gemini": catalog if backend_var.get() == "Gemini" else [
                {"model": "gemini-2.0-flash", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-2.0-flash-lite", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-1.5-pro", "efforts": ["N/A"], "default_effort": "N/A"},
                {"model": "gemini-1.5-flash", "efforts": ["N/A"], "default_effort": "N/A"},
            ]
        }

        content = ttk.Frame(dialog, padding=(25, 20), style="Content.TFrame")
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)

        ttk.Label(
            content,
            text="Choose Generation Backend",
            style="CardHeader.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(content, text="BACKEND", style="FieldName.TLabel").grid(row=1, column=0, sticky="w", pady=(15, 0), padx=(0, 15))
        backend_combo = ttk.Combobox(
            content,
            textvariable=backend_var,
            state="readonly",
            values=["Codex", "Gemini"],
            width=40,
        )
        backend_combo.grid(row=1, column=1, sticky="ew", pady=(15, 0))

        ttk.Label(content, text="MODEL", style="FieldName.TLabel").grid(row=2, column=0, sticky="w", pady=(15, 0), padx=(0, 15))
        model_combo = ttk.Combobox(
            content,
            textvariable=model_var,
            state="readonly",
            width=40,
        )
        model_combo.grid(row=2, column=1, sticky="ew", pady=(15, 0))

        effort_label = ttk.Label(content, text="EFFORT", style="FieldName.TLabel")
        effort_label.grid(row=3, column=0, sticky="w", pady=(15, 0), padx=(0, 15))
        effort_combo = ttk.Combobox(
            content,
            textvariable=effort_var,
            state="readonly",
            width=24,
        )
        effort_combo.grid(row=3, column=1, sticky="w", pady=(15, 0))

        def refresh_models(*_args):
            backend = backend_var.get()
            current_cat = backend_catalogs.get(backend, [])
            
            # Special case: if switching back to Codex but catalog is empty (meaning it was switched away and back)
            if backend == "Codex" and not current_cat:
                # We need to fetch it or use cached one. For simplicity, assume catalog passed in is Codex if current was Codex.
                # Actually, let's just use the cached self.codex_model_catalog if available
                if self.codex_model_catalog:
                    current_cat = self.codex_model_catalog
                    backend_catalogs["Codex"] = current_cat

            model_names = [entry["model"] for entry in current_cat]
            model_combo["values"] = model_names
            
            # Default model selection
            default_model = ""
            if backend == "Codex":
                default_model = self.selected_codex_model if self.selected_codex_model in model_names else (model_names[0] if model_names else "")
                effort_combo.configure(state="readonly")
                effort_label.configure(state="normal")
            else:
                default_model = self.selected_gemini_model if self.selected_gemini_model in model_names else (model_names[0] if model_names else "")
                effort_combo.configure(state="disabled")
                effort_label.configure(state="disabled")
            
            model_var.set(default_model)
            refresh_efforts()

        def refresh_efforts(*_args):
            backend = backend_var.get()
            selected_model = model_var.get()
            current_cat = backend_catalogs.get(backend, [])
            
            efforts = ["N/A"]
            for entry in current_cat:
                if entry["model"] == selected_model:
                    efforts = entry.get("efforts", ["N/A"])
                    break
            
            effort_combo["values"] = efforts
            if backend == "Codex":
                if self.selected_reasoning_effort in efforts:
                    effort_var.set(self.selected_reasoning_effort)
                else:
                    effort_var.set(efforts[0] if efforts else "medium")
            else:
                effort_var.set("N/A")

        backend_combo.bind("<<ComboboxSelected>>", refresh_models)
        model_combo.bind("<<ComboboxSelected>>", refresh_efforts)
        
        # Initial population
        refresh_models()

        action_buttons = ttk.Frame(dialog, padding=(14, 0, 14, 14))
        action_buttons.grid(row=1, column=0, sticky="ew")
        action_buttons.columnconfigure(0, weight=1)

        def confirm_selection() -> None:
            res_backend = backend_var.get()
            res_model = model_var.get()
            res_effort = effort_var.get()
            
            if not res_model:
                messagebox.showwarning("Missing Model", "Please select a model.", parent=dialog)
                return

            result["value"] = (res_backend, res_model, res_effort)
            dialog.destroy()

        ttk.Button(action_buttons, text="Cancel", command=dialog.destroy).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Button(action_buttons, text="Confirm", style="Accent.TButton", command=confirm_selection).grid(
            row=0, column=2, sticky="e", padx=(8, 0)
        )

        self.wait_window(dialog)
        return result["value"]

    def _on_model_status_clicked(self) -> None:
        if self.model_status_in_progress:
            return

        backend = self.selected_backend.get()
        if backend == "Codex":
            executable = self._resolve_codex_executable()
        else:
            executable = self._resolve_gemini_executable()

        if executable is None:
            messagebox.showerror(
                f"{backend} Not Found",
                f"Could not find {backend.lower()} executable. Install {backend} CLI or add it to PATH.",
            )
            return

        self.model_status_in_progress = True
        self._sync_model_status_button_state()
        self._ensure_generation_polling()
        
        if backend == "Codex":
            self.status_var.set("Loading Codex model status...")
            worker = threading.Thread(
                target=self._run_model_status_worker,
                args=(executable,),
                daemon=True,
            )
            worker.start()
        else:
            self.status_var.set("Gemini status check not yet supported via API.")
            self._append_generation_log("[status] Gemini status check is not yet supported via automated API.")
            self.model_status_in_progress = False
            self._sync_model_status_button_state()

    def _run_model_status_worker(self, codex_executable: str) -> None:
        try:
            status_lines = run_codex_status_request(
                codex_executable,
                base_dir=self.base_dir,
            )
            for line in status_lines:
                self._enqueue_generation_event("line", f"[status] {line}")
        except Exception as error:
            self._enqueue_generation_event("line", f"[status] Failed to run /status: {error}")
        finally:
            self._enqueue_generation_event("status_done", "")

    def _on_generate_clicked(self) -> None:
        if is_generation_process_running(self.generation_process):
            messagebox.showinfo(
                "Generation In Progress",
                "Graphic post generation is already running.",
            )
            return

        try:
            sync_legacy_general_agents_into_agents(self.base_dir)
        except OSError:
            # Fall through to explicit runbook existence check for a clear user-facing error.
            pass

        runbook_path = get_smarcomms_runbook_path(self.base_dir)
        if not runbook_path.is_file():
            try:
                runbook_path.parent.mkdir(parents=True, exist_ok=True)
                runbook_path.write_text(load_default_smarcomms_text(self.base_dir), encoding="utf-8")
                self._append_generation_log(f"[setup] Created missing runbook: {runbook_path}")
            except OSError as error:
                messagebox.showerror(
                    "SMARCOMMS.md Missing",
                    f"Could not find or create runbook file:\n{runbook_path}\n\n{error}",
                )
                return

        scope = self._prompt_generation_scope()
        if scope is None:
            return
        selected_month, selected_weeks = scope
        weeks_text = ", ".join(f"Week {week}" for week in selected_weeks)

        should_continue = messagebox.askyesno(
            "Generate Graphic Post Ideas",
            f"Run SMARCOMMS.md for {selected_month} with {weeks_text}?\n\n"
            "This will run Codex in a new background instance and may take a while.",
        )
        if not should_continue:
            return

        backend = self.selected_backend.get()
        if backend == "Codex":
            executable = self._resolve_codex_executable()
            backend_label = "Codex"
        else:
            executable = self._resolve_gemini_executable()
            backend_label = "Gemini"

        if executable is None:
            messagebox.showerror(
                f"{backend_label} Not Found",
                f"Could not find {executable or backend_label.lower()}. Install {backend_label} CLI or add it to PATH.",
            )
            return

        runbook_text = runbook_path.read_text(encoding="utf-8", errors="replace")
        prompt = build_generation_prompt(runbook_text, month=selected_month, weeks=selected_weeks)
        
        if backend == "Codex":
            command = build_codex_exec_command(
                codex_executable=executable,
                base_dir=self.base_dir,
                model=self.selected_codex_model,
                reasoning_effort=self.selected_reasoning_effort,
            )
        else:
            command = build_gemini_exec_command(
                gemini_executable=executable,
                base_dir=self.base_dir,
                model=self.selected_gemini_model,
            )

        self._start_generation_process(command=command, prompt=prompt)

    def _on_regenerate_clicked(self) -> None:
        if is_generation_process_running(self.generation_process):
            messagebox.showinfo("Generation In Progress", "A generation process is already running.")
            return

        if not self.current_posts:
            return

        current_post = self.current_posts[self.current_post_index]
        graphic_title = current_post.get("Graphic Title") or current_post.get("graphic title")

        if not graphic_title or not isinstance(graphic_title, str):
            messagebox.showerror("Missing Data", "Could not find a 'Graphic Title' for the current post.")
            return

        client_name = self.client_var.get().strip()
        if not client_name:
            messagebox.showerror("Missing Data", "No client selected.")
            return

        regenerate_path = get_general_agents_root(self.base_dir) / REGENERATE_FILENAME
        try:
            regenerate_path.parent.mkdir(parents=True, exist_ok=True)
            # Always overwrite to ensure we have the latest updated instructions
            regenerate_path.write_text(DEFAULT_REGENERATE_CONTENT, encoding="utf-8")
        except OSError as error:
            messagebox.showerror("File Error", f"Could not create or update REGENERATE.md:\n\n{error}")
            return

        remarks = simpledialog.askstring(
            "Regenerate Idea",
            f"Regenerating:\nClient: {client_name}\nTitle: {graphic_title}\n\n"
            "Enter remarks or reason for regeneration (e.g., 'Make it more professional', 'Focus on discounts'):",
            parent=self,
        )
        if remarks is None:
            return

        backend = self.selected_backend.get()
        if backend == "Codex":
            executable = self._resolve_codex_executable()
            backend_label = "Codex"
        else:
            executable = self._resolve_gemini_executable()
            backend_label = "Gemini"

        if executable is None:
            messagebox.showerror(
                f"{backend_label} Not Found",
                f"Could not find {executable or backend_label.lower()}. Install {backend_label} CLI or add it to PATH.",
            )
            return

        runbook_text = regenerate_path.read_text(encoding="utf-8", errors="replace")
        
        # Build a text representation of the current post block to help the AI find and replace it exactly
        post_content_str = format_single_post_view(self.current_posts, self.current_post_index)

        prompt = (
            f"Run Agents/REGENERATE.md from the current workspace root.\n\n"
            f"Client Name: {client_name}\n"
            f"Graphic Title: {graphic_title}\n"
            f"Remarks/Reason: {remarks.strip() or 'None provided. Completely rewrite the post.'}\n\n"
            f"--- EXISTING POST BLOCK TO COMPLETELY REPLACE ---\n"
            f"{post_content_str}\n"
            f"--- END OF EXISTING POST BLOCK ---\n\n"
            "BEGIN REGENERATE.md\n"
            f"{runbook_text}\n"
            "END REGENERATE.md\n"
            "\n"
            "CRITICAL DIRECTIVE: You MUST generate a completely new Graphic Title, Subtitle, CTA, List, and Captions. "
            "Do NOT just change a few words in the existing post. Replace the old post with an entirely new one based on the remarks."
        )

        if backend == "Codex":
            command = build_codex_exec_command(
                codex_executable=executable,
                base_dir=self.base_dir,
                model=self.selected_codex_model,
                reasoning_effort=self.selected_reasoning_effort,
            )
        else:
            command = build_gemini_exec_command(
                gemini_executable=executable,
                base_dir=self.base_dir,
                model=self.selected_gemini_model,
            )

        self._start_generation_process(command=command, prompt=prompt)

    def _prompt_generation_scope(self) -> tuple[str, list[int]] | None:
        dialog = tk.Toplevel(self)
        dialog.title("Generation Scope")
        dialog.geometry("560x460")
        dialog.minsize(540, 440)
        dialog.configure(background=self.colors["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        now = datetime.now()
        default_month = MONTH_NAMES[now.month - 1]

        month_var = tk.StringVar(value=default_month)
        week_vars = {week: tk.BooleanVar(value=(week == 1)) for week in WEEK_OPTIONS}
        result: dict[str, tuple[str, list[int]] | None] = {"value": None}

        ttk.Label(
            dialog,
            text="Set Generation Scope",
            style="CardHeader.TLabel",
            padding=(25, 20, 25, 10),
        ).grid(row=0, column=0, sticky="w")

        content = ttk.Frame(dialog, padding=(25, 0, 25, 20), style="Content.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        month_frame = ttk.Frame(content, style="Card.TFrame", padding=15)
        month_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(month_frame, text="MONTH", style="FieldName.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        for idx, month_name in enumerate(MONTH_NAMES):
            ttk.Radiobutton(
                month_frame,
                text=month_name,
                value=month_name,
                variable=month_var,
            ).grid(row=idx + 1, column=0, sticky="w", pady=1)

        week_frame = ttk.Frame(content, style="Card.TFrame", padding=15)
        week_frame.grid(row=0, column=1, sticky="nsew")
        ttk.Label(week_frame, text="WEEKS", style="FieldName.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        for idx, week in enumerate(WEEK_OPTIONS):
            ttk.Checkbutton(
                week_frame,
                text=f"Week {week}",
                variable=week_vars[week],
                onvalue=True,
                offvalue=False,
            ).grid(row=idx + 1, column=0, sticky="w", pady=5)

        buttons = ttk.Frame(dialog, padding=(25, 15), style="Content.TFrame")
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(1, weight=1)

        def submit() -> None:
            selected_month = month_var.get().strip()
            selected_weeks = [week for week in WEEK_OPTIONS if week_vars[week].get()]
            if not selected_month:
                messagebox.showwarning("Missing Month", "Please select a month.", parent=dialog)
                return
            if not selected_weeks:
                messagebox.showwarning("Missing Week", "Please select at least one week.", parent=dialog)
                return
            result["value"] = (selected_month, selected_weeks)
            dialog.destroy()

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Continue", style="Accent.TButton", command=submit).grid(row=0, column=2, sticky="e")

        self.wait_window(dialog)
        return result["value"]

    def _resolve_codex_executable(self) -> str | None:
        candidates: list[Path] = []
        for command_name in ("codex.cmd", "codex"):
            discovered = shutil.which(command_name)
            if discovered:
                candidates.append(Path(discovered))

        fallback = Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd"
        candidates.append(fallback)

        for candidate in candidates:
            if not candidate.exists():
                continue
            if candidate.suffix.lower() == ".ps1":
                continue
            return str(candidate)
        return None

    def _resolve_gemini_executable(self) -> str | None:
        candidates: list[Path] = []
        for command_name in ("gemini.cmd", "gemini"):
            discovered = shutil.which(command_name)
            if discovered:
                candidates.append(Path(discovered))

        fallback = Path.home() / "AppData" / "Roaming" / "npm" / "gemini.cmd"
        candidates.append(fallback)

        for candidate in candidates:
            if not candidate.exists():
                continue
            if candidate.suffix.lower() == ".ps1":
                continue
            return str(candidate)
        return None

    def _start_generation_process(self, command: list[str], prompt: str) -> None:
        self._clear_generation_logs()
        self._clear_generation_event_queue()
        self.context_left_var.set("Context left: --")
        self.generation_state_var.set("Generation: starting...")
        self.generate_button.configure(state="disabled")
        if hasattr(self, "regenerate_button"):
            self.regenerate_button.configure(state="disabled")
        self.generation_stop_requested = False
        self.generation_instance_counter += 1
        self.current_generation_instance = self.generation_instance_counter
        self._sync_stop_generation_button_state()

        backend = self.selected_backend.get()
        final_command = list(command)
        if backend == "Gemini":
            # Gemini CLI expects the prompt as the argument following -p
            final_command.append(prompt)

        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags |= subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        try:
            process = subprocess.Popen(
                final_command,
                cwd=self.base_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation_flags,
            )
        except OSError as error:
            self.generate_button.configure(state="normal")
            self.generation_state_var.set("Generation: failed to start")
            self._append_generation_log(f"[error] Failed to start {backend}: {error}")
            self._sync_stop_generation_button_state()
            return

        self.generation_process = process
        self._sync_stop_generation_button_state()
        self._append_generation_log(
            f"[system] Started {backend} instance #{self.current_generation_instance} (new process)."
        )
        
        if backend == "Codex":
            log_command = f"$ {' '.join(final_command[:-1])} -"
            model_info = f"[model] Running with {self.selected_codex_model} ({self.selected_reasoning_effort})."
        else:
            # Hide the full prompt in the logs if it's too long
            short_prompt = (prompt[:100] + "...") if len(prompt) > 100 else prompt
            log_command = f"$ {' '.join(final_command[:-1])} \"{short_prompt}\""
            model_info = f"[model] Running with Gemini model {self.selected_gemini_model}."

        self._append_generation_log(log_command)
        self._append_generation_log(model_info)
        self._append_generation_log(f"Sending SMARCOMMS.md runbook to {backend}...")
        self.generation_state_var.set("Generation: running")

        if backend == "Codex":
            try:
                if process.stdin is not None:
                    process.stdin.write(prompt)
                    process.stdin.close()
            except OSError as error:
                self._append_generation_log(f"[error] Failed to send prompt: {error}")
        else:
            # Gemini process already has the prompt in final_command
            if process.stdin is not None:
                process.stdin.close()

        worker = threading.Thread(
            target=self._read_generation_output_worker,
            args=(process,),
            daemon=True,
        )
        worker.start()
        self._ensure_generation_polling()

    def _read_generation_output_worker(self, process: subprocess.Popen[str]) -> None:
        try:
            if process.stdout is not None:
                for raw_line in process.stdout:
                    self._enqueue_generation_event("line", raw_line.rstrip("\r\n"))
        finally:
            exit_code = process.wait()
            self._enqueue_generation_event("exit", str(exit_code))

    def _enqueue_generation_event(self, event_type: str, payload: str) -> None:
        self.generation_log_queue.put((event_type, payload))

    def _ensure_generation_polling(self) -> None:
        if self.generation_poll_handle is None:
            self.generation_poll_handle = self.after(150, self._poll_generation_events)

    def _poll_generation_events(self) -> None:
        self.generation_poll_handle = None
        pending_log_lines: list[str] = []
        while True:
            try:
                event_type, payload = self.generation_log_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "line":
                display_line = self._format_generation_log_line(payload)
                if display_line:
                    pending_log_lines.append(display_line)
                context_percent = extract_context_left_percent_from_line(payload)
                if context_percent is not None:
                    self.context_left_var.set(f"Context left: {context_percent}%")

                if "[status]" in payload:
                    if "5h Usage Left:" in payload:
                        m = re.search(r"5h Usage Left:\s*(\d+%)", payload)
                        if m:
                            current = self.model_usage_status_var.get()
                            weekly = re.search(r"Weekly:\s*(\d+%)", current)
                            weekly_val = weekly.group(1) if weekly else "--"
                            self.model_usage_status_var.set(f"Usage: 5h: {m.group(1)} | Weekly: {weekly_val}")
                    elif "Weekly Usage Left:" in payload:
                        m = re.search(r"Weekly Usage Left:\s*(\d+%)", payload)
                        if m:
                            current = self.model_usage_status_var.get()
                            five_h = re.search(r"5h:\s*(\d+%)", current)
                            five_h_val = five_h.group(1) if five_h else "--"
                            self.model_usage_status_var.set(f"Usage: 5h: {five_h_val} | Weekly: {m.group(1)}")

                self._update_generation_state_from_event(payload)
                continue

            if event_type == "exit":
                exit_code = int(payload)
                if self.generation_stop_requested:
                    self.generation_state_var.set("Generation: stopped")
                elif exit_code == 0:
                    self.generation_state_var.set("Generation: completed")
                else:
                    self.generation_state_var.set(f"Generation: failed (exit {exit_code})")
                if self.context_left_var.get() == "Context left: --":
                    self.context_left_var.set("Context left: unavailable")
                self.generate_button.configure(state="normal")
                if hasattr(self, "regenerate_button") and self.current_posts:
                    self.regenerate_button.configure(state="normal")
                self.generation_process = None
                self.generation_stop_requested = False
                self._sync_stop_generation_button_state()
                self.after(500, self._on_model_status_clicked)
                
                # Auto-refresh the current file to show new ideas or regenerated content
                if self.current_file_path is not None:
                    self.after(1000, lambda: self._load_selected_file(self.current_post_index))
                    
                continue

            if event_type == "status_done":
                self.model_status_in_progress = False
                self.status_var.set("Model status updated.")
                self._sync_model_status_button_state()

        if pending_log_lines:
            self._append_generation_logs_batch(pending_log_lines)

        if should_continue_generation_polling(
            generation_running=is_generation_process_running(self.generation_process),
            model_status_in_progress=self.model_status_in_progress,
            event_queue_empty=self.generation_log_queue.empty(),
        ):
            self._ensure_generation_polling()

    def _sync_stop_generation_button_state(self) -> None:
        if self.stop_generation_button is None:
            return
        self.stop_generation_button.configure(
            state=(
                "normal"
                if should_enable_stop_generation_button(
                    self.generation_process,
                    stop_requested=self.generation_stop_requested,
                )
                else "disabled"
            )
        )

    def _sync_model_status_button_state(self) -> None:
        if self.model_status_button is None:
            return
        self.model_status_button.configure(
            state="disabled" if self.model_status_in_progress else "normal"
        )

    def _on_stop_generation_clicked(self) -> None:
        process = self.generation_process
        if not is_generation_process_running(process):
            return

        should_stop = messagebox.askyesno(
            "Stop Generation",
            "Stop the current Codex generation now?",
        )
        if not should_stop:
            return

        self.generation_stop_requested = True
        self._sync_stop_generation_button_state()
        self.generation_state_var.set("Generation: stopping...")
        self._append_generation_log("[system] Stop requested. Sending Ctrl+C-style interrupt to Codex...")
        self._terminate_generation_process()

    def _terminate_generation_process(self) -> None:
        process = self.generation_process
        if not is_generation_process_running(process):
            return

        try:
            signal_name = request_generation_stop_signal(process)
        except OSError as error:
            self._append_generation_log(f"[error] Failed to terminate process: {error}")
            return

        if signal_name == "ctrl_break":
            self._append_generation_log("[system] Sent Ctrl+Break to Codex (Windows Ctrl+C equivalent).")
        else:
            self._append_generation_log("[system] Sent terminate signal to Codex process.")
        self.after(2000, self._force_kill_generation_if_running)

    def _force_kill_generation_if_running(self) -> None:
        process = self.generation_process
        if not is_generation_process_running(process):
            return
        try:
            force_kill_generation_process_tree(process)
            self._append_generation_log("[system] Codex process force-killed after graceful stop timeout.")
        except OSError as error:
            self._append_generation_log(f"[error] Failed to kill process: {error}")

    def _format_generation_log_line(self, raw_line: str) -> str:
        line = raw_line.strip()
        if not line:
            return ""

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return raw_line

        if not isinstance(payload, dict):
            return raw_line

        event_type = payload.get("type")
        fragments = self._extract_log_text_fragments(payload)

        if fragments:
            if isinstance(event_type, str):
                return f"[{event_type}] {' '.join(fragments)}"
            return " ".join(fragments)

        if isinstance(event_type, str):
            if event_type in {"item.started", "item.completed"}:
                item = payload.get("item")
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if isinstance(item_type, str):
                        return f"[{event_type}] {item_type}"
                return ""
            return f"[{event_type}]"

        return raw_line

    def _extract_log_text_fragments(self, data: object) -> list[str]:
        fragments: list[str] = []

        def visit(value: object, depth: int) -> None:
            if depth > 6:
                return

            if isinstance(value, str):
                text = value.strip()
                if text and len(text) <= 500 and not text.startswith("{") and not text.startswith("["):
                    fragments.append(text)
                return

            if isinstance(value, dict):
                for key, nested in value.items():
                    lowered = key.lower()
                    if lowered in {
                        "text",
                        "delta",
                        "output_text",
                        "content",
                        "message",
                        "reason",
                        "error",
                        "stdout",
                        "stderr",
                    }:
                        visit(nested, depth + 1)
                    elif lowered in {"item", "output", "result", "value", "data", "details"}:
                        visit(nested, depth + 1)
                return

            if isinstance(value, list):
                for item in value[:12]:
                    visit(item, depth + 1)

        visit(data, 0)

        deduped: list[str] = []
        seen: set[str] = set()
        for fragment in fragments:
            if fragment in seen:
                continue
            seen.add(fragment)
            deduped.append(fragment)
        return deduped

    def _update_generation_state_from_event(self, raw_line: str) -> None:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        event_type = payload.get("type")
        if not isinstance(event_type, str):
            return
        if event_type == "turn.started":
            self.generation_state_var.set("Generation: turn started")
        elif event_type == "turn.completed":
            self.generation_state_var.set("Generation: turn completed")
        elif event_type == "turn.failed":
            self.generation_state_var.set("Generation: turn failed")
        elif event_type == "error":
            self.generation_state_var.set("Generation: error encountered")

    def _append_generation_log(self, line: str) -> None:
        if not line.strip():
            return
        self.generation_log_text.configure(state="normal")
        tag = self._resolve_generation_log_tag(line)
        self.generation_log_text.insert("end", f"{line}\n", tag)
        self.generation_log_text.see("end")
        self.generation_log_text.configure(state="disabled")

    def _resolve_generation_log_tag(self, line: str) -> str | None:
        lower_line = line.lower()
        if "[error]" in lower_line or "failed" in lower_line:
            return "error"
        if "[status]" in lower_line:
            return "status"
        if "[system]" in lower_line:
            return "system"
        if "[model]" in lower_line:
            return "model"
        return None

    def _append_generation_logs_batch(self, lines: list[str]) -> None:
        if not lines:
            return
        self.generation_log_text.configure(state="normal")
        appended_any = False
        for line in lines:
            if not line.strip():
                continue
            self.generation_log_text.insert("end", f"{line}\n", self._resolve_generation_log_tag(line))
            appended_any = True
        if appended_any:
            self.generation_log_text.see("end")
        self.generation_log_text.configure(state="disabled")

    def _clear_generation_logs(self) -> None:
        self.generation_log_text.configure(state="normal")
        self.generation_log_text.delete("1.0", "end")
        self.generation_log_text.configure(state="disabled")

    def _clear_generation_event_queue(self) -> None:
        while True:
            try:
                self.generation_log_queue.get_nowait()
            except queue.Empty:
                break

    def _open_settings_window(self, mode: str) -> None:
        if mode not in {"general", "client"}:
            return

        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            self._set_settings_mode(mode)
            return

        window = tk.Toplevel(self)
        self.settings_window = window
        window.title("Settings Editor")
        window.geometry("980x650")
        window.minsize(900, 560)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)
        window.protocol("WM_DELETE_WINDOW", self._close_settings_window)
        window.transient(self)

        controls = ttk.Frame(window, padding=12)
        controls.grid(row=0, column=0, sticky="ew")

        self.settings_general_mode_button = ttk.Button(
            controls,
            text="General Setting",
            command=lambda: self._set_settings_mode("general"),
        )
        self.settings_general_mode_button.grid(row=0, column=0, sticky="w")

        self.settings_client_mode_button = ttk.Button(
            controls,
            text="Client Setting",
            command=lambda: self._set_settings_mode("client"),
        )
        self.settings_client_mode_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(window, textvariable=self.settings_title_var, padding=(12, 0, 12, 8)).grid(
            row=1, column=0, sticky="w"
        )

        content_frame = ttk.Frame(window, padding=(12, 0, 12, 12))
        content_frame.grid(row=2, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=7)
        content_frame.rowconfigure(0, weight=1)

        files_frame = ttk.Frame(content_frame)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(2, weight=1)

        ttk.Label(files_frame, text="Markdown Files").grid(row=0, column=0, sticky="w", pady=(0, 6))
        
        self.settings_search_var = tk.StringVar()
        self.settings_search_entry = ttk.Entry(files_frame, textvariable=self.settings_search_var)
        self.settings_search_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.settings_search_var.trace_add("write", lambda *a: self._refresh_settings_panel(preserve_selection=True, reload_current=False))

        self.settings_file_listbox = tk.Listbox(
            files_frame,
            exportselection=False,
            activestyle="dotbox",
            font=("Segoe UI", 10),
            background=self.colors["bg"],
            foreground=self.colors["text"],
            selectbackground=self.colors["primary"],
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        self.settings_file_listbox.grid(row=2, column=0, sticky="nsew")
        self.settings_file_listbox.bind("<<ListboxSelect>>", self._on_settings_file_selected)

        files_scroll = ttk.Scrollbar(files_frame, orient="vertical", command=self.settings_file_listbox.yview)
        files_scroll.grid(row=2, column=1, sticky="ns")
        self.settings_file_listbox.configure(yscrollcommand=files_scroll.set)

        editor_frame = ttk.Frame(content_frame)
        editor_frame.grid(row=0, column=1, sticky="nsew")
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(1, weight=1)

        ttk.Label(editor_frame, text="Editor").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.settings_content_text = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            font=("Consolas", 10),
            background=self.colors["surface"],
            foreground=self.colors["text"],
            insertbackground=self.colors["primary"],
            selectbackground=self.colors["primary"],
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=15,
            pady=15,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        self.settings_content_text.grid(row=1, column=0, sticky="nsew")
        self._bind_text_scroll_redirect(self.settings_content_text)
        self.settings_content_text.bind("<<Modified>>", self._on_settings_editor_modified)

        self.settings_content_scrollbar = ttk.Scrollbar(
            editor_frame,
            orient="vertical",
            command=self.settings_content_text.yview,
        )
        self.settings_content_scrollbar.grid(row=1, column=1, sticky="ns")
        self.settings_content_text.configure(yscrollcommand=self.settings_content_scrollbar.set)

        self.settings_profile_form_container = ttk.Frame(editor_frame)
        self.settings_profile_form_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.settings_profile_form_container.columnconfigure(0, weight=1)
        self.settings_profile_form_container.rowconfigure(0, weight=1)

        self.settings_profile_canvas = tk.Canvas(
            self.settings_profile_form_container,
            background=self.colors["surface"],
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
        )
        self.settings_profile_canvas.grid(row=0, column=0, sticky="nsew")
        self.settings_profile_scrollbar = ttk.Scrollbar(
            self.settings_profile_form_container,
            orient="vertical",
            command=self.settings_profile_canvas.yview,
        )
        self.settings_profile_scrollbar.grid(row=0, column=1, sticky="ns")
        self.settings_profile_canvas.configure(yscrollcommand=self.settings_profile_scrollbar.set)

        self.settings_profile_inner_frame = ttk.Frame(self.settings_profile_canvas, padding=(10, 10, 10, 10))
        self.settings_profile_inner_frame.columnconfigure(1, weight=1)
        self.settings_profile_window_id = self.settings_profile_canvas.create_window(
            (0, 0),
            window=self.settings_profile_inner_frame,
            anchor="nw",
        )

        for row, field in enumerate(CLIENT_PROFILE_FIELDS):
            ttk.Label(self.settings_profile_inner_frame, text=field).grid(
                row=row,
                column=0,
                sticky="nw",
                padx=(0, 12),
                pady=(0, 8),
            )
            value_var = tk.StringVar()
            value_var.trace_add("write", self._on_profile_field_modified)
            field_entry = ttk.Entry(self.settings_profile_inner_frame, textvariable=value_var)
            field_entry.grid(row=row, column=1, sticky="ew", pady=(0, 8))
            self.settings_profile_field_vars[field] = value_var

        self.settings_profile_inner_frame.bind("<Configure>", self._on_profile_form_configure)
        self.settings_profile_canvas.bind("<Configure>", self._on_profile_canvas_configure)
        self._bind_mousewheel(self.settings_profile_canvas)
        self.settings_profile_form_container.grid_remove()

        self.settings_caption_form_container = ttk.Frame(editor_frame)
        self.settings_caption_form_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.settings_caption_form_container.columnconfigure(0, weight=1)
        self.settings_caption_form_container.rowconfigure(0, weight=1)

        self.settings_caption_canvas = tk.Canvas(
            self.settings_caption_form_container,
            background=self.colors["surface"],
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
        )
        self.settings_caption_canvas.grid(row=0, column=0, sticky="nsew")
        self.settings_caption_scrollbar = ttk.Scrollbar(
            self.settings_caption_form_container,
            orient="vertical",
            command=self.settings_caption_canvas.yview,
        )
        self.settings_caption_scrollbar.grid(row=0, column=1, sticky="ns")
        self.settings_caption_canvas.configure(yscrollcommand=self.settings_caption_scrollbar.set)

        self.settings_caption_inner_frame = ttk.Frame(self.settings_caption_canvas, padding=(10, 10, 10, 10))
        self.settings_caption_inner_frame.columnconfigure(1, weight=1)
        self.settings_caption_window_id = self.settings_caption_canvas.create_window(
            (0, 0),
            window=self.settings_caption_inner_frame,
            anchor="nw",
        )

        for row, field in enumerate(CAPTION_SAMPLE_FIELDS):
            ttk.Label(self.settings_caption_inner_frame, text=field).grid(
                row=row,
                column=0,
                sticky="nw",
                padx=(0, 12),
                pady=(0, 8),
            )
            field_text = tk.Text(
                self.settings_caption_inner_frame,
                wrap="word",
                height=7,
                font=("Segoe UI", 10),
                background=self.colors["surface"],
                foreground=self.colors["text"],
                insertbackground=self.colors["primary"],
                selectbackground=self.colors["primary"],
                selectforeground="#ffffff",
                relief="flat",
                borderwidth=0,
                padx=10,
                pady=10,
                highlightthickness=1,
                highlightbackground=self.colors["border"],
            )
            field_text.grid(row=row, column=1, sticky="ew", pady=(0, 8))
            self._register_local_wheel_only_text_widget(field_text)
            field_text.bind("<<Modified>>", self._on_caption_samples_field_modified)
            self.settings_caption_field_texts[field] = field_text

        self.settings_caption_inner_frame.bind("<Configure>", self._on_caption_form_configure)
        self.settings_caption_canvas.bind("<Configure>", self._on_caption_canvas_configure)
        self._bind_mousewheel(self.settings_caption_canvas)
        self.settings_caption_form_container.grid_remove()

        actions = ttk.Frame(window, padding=(12, 0, 12, 12))
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(3, weight=1)

        self.auto_fill_profile_button = ttk.Button(
            actions,
            text="Auto Fill Info",
            command=self._on_auto_fill_profile_clicked,
        )
        self.auto_fill_profile_button.grid(row=0, column=0, sticky="w")
        self.auto_fill_profile_button.grid_remove()

        self.save_settings_button = ttk.Button(
            actions,
            text="Save",
            command=self._save_settings_file,
            state="disabled",
        )
        self.save_settings_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.reload_settings_button = ttk.Button(
            actions,
            text="Reload",
            command=self._reload_settings_file,
            state="disabled",
        )
        self.reload_settings_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

        ttk.Label(actions, textvariable=self.settings_status_var, style="SettingsInfo.TLabel").grid(
            row=0, column=3, sticky="e"
        )

        self._set_settings_mode(mode)

    def _close_settings_window(self) -> None:
        if self.settings_window is None or not self.settings_window.winfo_exists():
            return
        if self.settings_editor_dirty and not self._confirm_discard_settings_changes():
            return

        self.settings_window.destroy()
        self.settings_window = None
        self.settings_file_listbox = None
        self.settings_content_text = None
        self.settings_content_scrollbar = None
        self.settings_profile_form_container = None
        self.settings_profile_canvas = None
        self.settings_profile_scrollbar = None
        self.settings_profile_inner_frame = None
        self.settings_profile_window_id = None
        self.settings_profile_field_vars = {}
        self.settings_caption_form_container = None
        self.settings_caption_canvas = None
        self.settings_caption_scrollbar = None
        self.settings_caption_inner_frame = None
        self.settings_caption_window_id = None
        self.settings_caption_field_texts = {}
        self.save_settings_button = None
        self.reload_settings_button = None
        self.auto_fill_profile_button = None
        self.settings_general_mode_button = None
        self.settings_client_mode_button = None
        self.settings_file_lookup = {}
        self.current_settings_file_path = None
        self.selected_settings_key = None
        self.settings_editor_mode = "text"
        self._is_loading_profile_fields = False
        self._is_loading_caption_fields = False
        self.settings_editor_dirty = False
        self.profile_autofill_in_progress = False
        self.local_wheel_only_text_widgets.clear()

    def _set_settings_mode(self, mode: str) -> None:
        if mode not in {"general", "client"}:
            return

        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_mode_var.set(mode)
            return

        current_mode = self.settings_mode_var.get()
        if mode == current_mode:
            self._update_settings_mode_buttons()
            if mode == "client":
                if self.settings_editor_dirty and not self._confirm_discard_settings_changes():
                    return
                self.settings_editor_dirty = False
                self._refresh_settings_panel(
                    preserve_selection=False,
                    reload_current=True,
                    preferred_key="CLIENT_PROFILE.md",
                )
            else:
                self._refresh_settings_panel(preserve_selection=True, reload_current=False)
            return

        if self.settings_editor_dirty and not self._confirm_discard_settings_changes():
            return

        self.settings_editor_dirty = False
        self.settings_mode_var.set(mode)
        self._update_settings_mode_buttons()
        preferred_key = "CLIENT_PROFILE.md" if mode == "client" else None
        self._refresh_settings_panel(
            preserve_selection=False,
            reload_current=True,
            preferred_key=preferred_key,
        )

    def _update_settings_mode_buttons(self) -> None:
        if self.settings_general_mode_button is not None:
            self.settings_general_mode_button.configure(
                state="disabled" if self.settings_mode_var.get() == "general" else "normal"
            )
        if self.settings_client_mode_button is not None:
            self.settings_client_mode_button.configure(
                state="disabled" if self.settings_mode_var.get() == "client" else "normal"
            )

    def _is_client_profile_selected(self) -> bool:
        path = self.current_settings_file_path
        return path is not None and path.name.lower() == "client_profile.md"

    def _sync_auto_fill_profile_button(self) -> None:
        if self.auto_fill_profile_button is None:
            return
        if not self._is_client_profile_selected():
            self.auto_fill_profile_button.grid_remove()
            return

        self.auto_fill_profile_button.grid()
        self.auto_fill_profile_button.configure(
            state="disabled" if self.profile_autofill_in_progress else "normal"
        )

    def _prompt_profile_auto_fill_inputs(
        self,
        *,
        default_website: str = "",
    ) -> tuple[str, str] | None:
        owner: tk.Misc = self.settings_window if self.settings_window is not None else self
        dialog = tk.Toplevel(owner)
        dialog.title("Auto Fill Client Profile")
        dialog.geometry("760x440")
        dialog.minsize(680, 380)
        dialog.configure(background=self.colors["bg"])
        dialog.transient(owner)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        website_var = tk.StringVar(value=default_website.strip())
        result: dict[str, tuple[str, str] | None] = {"value": None}

        container = ttk.Frame(dialog, padding=(14, 14, 14, 8))
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        ttk.Label(
            container,
            text="Provide website and/or pasted client information.",
            style="SettingsInfo.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="Website URL (optional)",
            style="FieldName.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(10, 4))
        website_entry = ttk.Entry(container, textvariable=website_var)
        website_entry.grid(row=2, column=0, sticky="ew")

        text_frame = ttk.Frame(dialog, padding=(14, 0, 14, 10))
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)

        ttk.Label(
            text_frame,
            text="Pasted client information (optional)",
            style="FieldName.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        info_text = tk.Text(
            text_frame,
            wrap="word",
            height=12,
            font=("Segoe UI", 10),
            background=self.colors["surface"],
            foreground=self.colors["text"],
            insertbackground=self.colors["primary"],
            selectbackground=self.colors["primary"],
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        info_text.grid(row=1, column=0, sticky="nsew")
        self._bind_text_scroll_redirect(info_text)

        info_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=info_text.yview)
        info_scroll.grid(row=1, column=1, sticky="ns")
        info_text.configure(yscrollcommand=info_scroll.set)

        buttons = ttk.Frame(dialog, padding=(14, 0, 14, 14))
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(0, weight=1)

        run_button: ttk.Button | None = None

        def has_any_input() -> bool:
            website_text = website_var.get().strip()
            pasted_text = info_text.get("1.0", "end-1c").strip()
            return bool(website_text or pasted_text)

        def update_submit_state(*_args: object) -> None:
            if run_button is None:
                return
            run_button.configure(state="normal" if has_any_input() else "disabled")

        def submit() -> None:
            website_text = website_var.get().strip()
            pasted_text = info_text.get("1.0", "end-1c").strip()
            if not website_text and not pasted_text:
                messagebox.showwarning(
                    "Missing Input",
                    "Provide at least a website URL or pasted client information.",
                    parent=dialog,
                )
                return
            result["value"] = (website_text, pasted_text)
            dialog.destroy()

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(row=0, column=1, sticky="e")
        run_button = ttk.Button(
            buttons,
            text="Run Auto Fill",
            style="Accent.TButton",
            command=submit,
            state="disabled",
        )
        run_button.grid(
            row=0, column=2, sticky="e", padx=(8, 0)
        )

        website_var.trace_add("write", update_submit_state)
        info_text.bind("<KeyRelease>", update_submit_state)
        info_text.bind("<<Paste>>", lambda _event: dialog.after_idle(update_submit_state))
        info_text.bind("<<Cut>>", lambda _event: dialog.after_idle(update_submit_state))
        update_submit_state()

        website_entry.focus_set()
        self.wait_window(dialog)
        return result["value"]

    def _resolve_latest_codex_model_for_profile_autofill(self, codex_executable: str) -> str:
        fallback = self.selected_codex_model.strip() or DEFAULT_CODEX_MODEL
        try:
            catalog = fetch_codex_model_catalog(codex_executable, base_dir=self.base_dir)
        except Exception:
            return fallback
        if not catalog:
            return fallback

        default_entry = next(
            (entry for entry in catalog if isinstance(entry, dict) and bool(entry.get("is_default"))),
            None,
        )
        if default_entry is not None:
            model_value = default_entry.get("model")
            if isinstance(model_value, str) and model_value.strip():
                return model_value.strip()

        first_entry = catalog[0]
        if isinstance(first_entry, dict):
            model_value = first_entry.get("model")
            if isinstance(model_value, str) and model_value.strip():
                return model_value.strip()
        return fallback

    def _on_auto_fill_profile_clicked(self) -> None:
        if self.profile_autofill_in_progress:
            return
        if not self._is_client_profile_selected() or self.current_settings_file_path is None:
            return

        if self.settings_editor_dirty:
            action = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved profile edits.\n\nSave first before auto fill?",
                parent=self.settings_window,
            )
            if action is None:
                return
            if action:
                self._save_settings_file()
                if self.settings_editor_dirty:
                    return

        profile_path = self.current_settings_file_path
        default_website = ""
        try:
            current_values = parse_client_profile_markdown(
                profile_path.read_text(encoding="utf-8", errors="replace"),
                self.client_var.get().strip() or profile_path.parent.name,
            )
            default_website = current_values.get("Website", "")
        except OSError:
            default_website = ""

        prompt_inputs = self._prompt_profile_auto_fill_inputs(default_website=default_website)
        if prompt_inputs is None:
            return
        website_url, pasted_information = prompt_inputs

        self.profile_autofill_in_progress = True
        self._sync_auto_fill_profile_button()
        if self.reload_settings_button is not None:
            self.reload_settings_button.configure(state="disabled")
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="disabled")
        self.settings_status_var.set("Auto filling CLIENT_PROFILE.md via Codex...")
        self.status_var.set("Running profile auto fill...")

        thread = threading.Thread(
            target=self._run_profile_autofill_worker,
            args=(profile_path, website_url, pasted_information),
            daemon=True,
        )
        thread.start()

    def _run_profile_autofill_worker(
        self,
        profile_path: Path,
        website_url: str,
        pasted_information: str,
    ) -> None:
        success = False
        message = ""
        try:
            codex_executable = self._resolve_codex_executable()
            if codex_executable is None:
                raise RuntimeError("Codex CLI is unavailable.")

            runbook_path = ensure_client_profile_autofill_instruction(self.base_dir)
            runbook_text = runbook_path.read_text(encoding="utf-8", errors="replace")
            model_name = self._resolve_latest_codex_model_for_profile_autofill(codex_executable)
            prompt = build_client_profile_autofill_prompt(
                client_name=self.client_var.get().strip() or profile_path.parent.name,
                profile_relative_path=self._to_relative_path(profile_path),
                website_url=website_url,
                pasted_information=pasted_information,
                runbook_text=runbook_text,
            )
            command = build_codex_exec_command(
                codex_executable,
                self.base_dir,
                model=model_name,
                reasoning_effort="xhigh",
            )
            ok, output = self._run_setup_command(command, timeout_seconds=1200, input_text=prompt)
            if not ok:
                tail_lines = output.splitlines()[-12:] if output else []
                tail_text = "\n".join(tail_lines).strip()
                if not tail_text:
                    tail_text = "Codex execution failed without output."
                raise RuntimeError(tail_text)

            success = True
            message = f"Auto-filled {self._to_relative_path(profile_path)} using {model_name} (xhigh)."
        except Exception as error:
            message = str(error)

        self.after(
            0,
            lambda: self._on_profile_autofill_completed(
                success=success,
                message=message,
                profile_path=profile_path,
            ),
        )

    def _on_profile_autofill_completed(
        self,
        *,
        success: bool,
        message: str,
        profile_path: Path,
    ) -> None:
        self.profile_autofill_in_progress = False
        self._sync_auto_fill_profile_button()
        if self.reload_settings_button is not None and self.current_settings_file_path is not None:
            self.reload_settings_button.configure(state="normal")

        if success:
            self.settings_editor_dirty = False
            if self.current_settings_file_path == profile_path and profile_path.is_file():
                self._load_settings_file(profile_path)
            self.settings_status_var.set(message)
            self.status_var.set(message)
            return

        if self.save_settings_button is not None and self._is_client_profile_selected():
            self.save_settings_button.configure(state="normal" if self.settings_editor_dirty else "disabled")
        self.settings_status_var.set("Auto fill failed. Check status.")
        self.status_var.set("Profile auto fill failed.")
        messagebox.showerror("Auto Fill Failed", message, parent=self.settings_window)

    def _build_settings_file_lookup_for_mode(self, mode: str) -> tuple[dict[str, Path], str, str]:
        if mode == "general":
            try:
                sync_legacy_general_agents_into_agents(self.base_dir)
            except OSError:
                pass
            files = list_general_settings_files(self.base_dir)
            title = f"General Setting ({len(files)} .md files)"
            empty_message = f"No markdown files found in {AGENTS_DIRNAME}/."
            lookup = {
                str(path.relative_to(self.base_dir)).replace("\\", "/"): path
                for path in files
            }
            return lookup, title, empty_message

        client_name = self.client_var.get().strip()
        if not client_name:
            return {}, "Client Setting (no client selected)", "Select a client to view client markdown files."

        client_dir = self.clients_dir / client_name
        files = list_client_settings_files(self.base_dir, client_name)
        title = (
            f"Client Setting: {client_name} "
            f"({len(files)} .md files, excludes graphic idea posts)"
        )
        empty_message = "No editable markdown files found for the selected client."
        lookup = {
            str(path.relative_to(client_dir)).replace("\\", "/"): path
            for path in files
        }
        return lookup, title, empty_message

    def _refresh_settings_panel(
        self,
        preserve_selection: bool,
        reload_current: bool,
        preferred_key: str | None = None,
    ) -> None:
        if self.settings_file_listbox is None:
            return

        mode = self.settings_mode_var.get()
        lookup, title, empty_message = self._build_settings_file_lookup_for_mode(mode)
        
        search_term = ""
        if hasattr(self, "settings_search_var"):
            search_term = self.settings_search_var.get().lower()
            
        if search_term:
            lookup = {k: v for k, v in lookup.items() if search_term in k.lower()}
            
        self.settings_title_var.set(title)
        self.settings_file_lookup = lookup
        keys = list(lookup.keys())

        self._is_updating_settings_list = True
        self.settings_file_listbox.delete(0, "end")
        for key in keys:
            self.settings_file_listbox.insert("end", key)
        self._is_updating_settings_list = False

        if not keys:
            self.current_settings_file_path = None
            self.selected_settings_key = None
            self.settings_editor_dirty = False
            self._set_settings_editor_placeholder(empty_message)
            if self.save_settings_button is not None:
                self.save_settings_button.configure(state="disabled")
            if self.reload_settings_button is not None:
                self.reload_settings_button.configure(state="disabled")
            self.settings_status_var.set(empty_message)
            self._sync_auto_fill_profile_button()
            return

        selected_key: str | None = None
        if preserve_selection and self.current_settings_file_path is not None:
            for key, path in lookup.items():
                if path == self.current_settings_file_path:
                    selected_key = key
                    break

        if selected_key is None and preserve_selection and self.selected_settings_key in lookup:
            selected_key = self.selected_settings_key

        if selected_key is None and preferred_key in lookup:
            selected_key = preferred_key

        if selected_key is None:
            selected_key = keys[0]

        self._set_settings_listbox_selection(selected_key)
        selected_path = lookup[selected_key]
        selected_changed = self.current_settings_file_path != selected_path

        if selected_changed:
            self._load_settings_file(selected_path)
            return

        if reload_current and not self.settings_editor_dirty:
            self._load_settings_file(selected_path)
            return

        if self.current_settings_file_path is not None:
            self.settings_status_var.set(
                f"Editing: {self._to_relative_path(self.current_settings_file_path)}"
            )
        self._sync_auto_fill_profile_button()

    def _set_settings_listbox_selection(self, target_key: str) -> None:
        if self.settings_file_listbox is None:
            return

        self._is_updating_settings_list = True
        self.settings_file_listbox.selection_clear(0, "end")
        for index, key in enumerate(self.settings_file_lookup.keys()):
            if key == target_key:
                self.settings_file_listbox.selection_set(index)
                self.settings_file_listbox.activate(index)
                self.settings_file_listbox.see(index)
                break
        self._is_updating_settings_list = False

    def _on_profile_form_configure(self, _event: tk.Event[tk.Misc]) -> None:
        if self.settings_profile_canvas is None:
            return
        self.settings_profile_canvas.configure(scrollregion=self.settings_profile_canvas.bbox("all"))

    def _on_profile_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        if self.settings_profile_canvas is None or self.settings_profile_window_id is None:
            return
        self.settings_profile_canvas.itemconfigure(self.settings_profile_window_id, width=event.width)

    def _on_caption_form_configure(self, _event: tk.Event[tk.Misc]) -> None:
        if self.settings_caption_canvas is None:
            return
        self.settings_caption_canvas.configure(scrollregion=self.settings_caption_canvas.bbox("all"))

    def _on_caption_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        if self.settings_caption_canvas is None or self.settings_caption_window_id is None:
            return
        self.settings_caption_canvas.itemconfigure(self.settings_caption_window_id, width=event.width)

    def _show_text_settings_editor(self) -> None:
        self.settings_editor_mode = "text"
        if self.settings_profile_form_container is not None:
            self.settings_profile_form_container.grid_remove()
        if self.settings_caption_form_container is not None:
            self.settings_caption_form_container.grid_remove()
        if self.settings_content_text is not None:
            self.settings_content_text.grid(row=1, column=0, sticky="nsew")
        if self.settings_content_scrollbar is not None:
            self.settings_content_scrollbar.grid(row=1, column=1, sticky="ns")

    def _show_profile_settings_editor(self) -> None:
        self.settings_editor_mode = "profile"
        if self.settings_content_text is not None:
            self.settings_content_text.grid_remove()
        if self.settings_content_scrollbar is not None:
            self.settings_content_scrollbar.grid_remove()
        if self.settings_caption_form_container is not None:
            self.settings_caption_form_container.grid_remove()
        if self.settings_profile_form_container is not None:
            self.settings_profile_form_container.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def _show_caption_settings_editor(self) -> None:
        self.settings_editor_mode = "caption_samples"
        if self.settings_content_text is not None:
            self.settings_content_text.grid_remove()
        if self.settings_content_scrollbar is not None:
            self.settings_content_scrollbar.grid_remove()
        if self.settings_profile_form_container is not None:
            self.settings_profile_form_container.grid_remove()
        if self.settings_caption_form_container is not None:
            self.settings_caption_form_container.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def _populate_profile_form_fields(self, values: dict[str, str]) -> None:
        self._is_loading_profile_fields = True
        try:
            for field in CLIENT_PROFILE_FIELDS:
                field_var = self.settings_profile_field_vars.get(field)
                if field_var is None:
                    continue
                field_var.set(values.get(field, ""))
        finally:
            self._is_loading_profile_fields = False

    def _populate_caption_samples_form_fields(self, values: dict[str, str]) -> None:
        self._is_loading_caption_fields = True
        try:
            for field in CAPTION_SAMPLE_FIELDS:
                field_text = self.settings_caption_field_texts.get(field)
                if field_text is None:
                    continue
                field_text.configure(state="normal")
                field_text.delete("1.0", "end")
                field_text.insert("1.0", values.get(field, ""))
                field_text.edit_modified(False)
        finally:
            self._is_loading_caption_fields = False

    def _read_profile_form_fields(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field in CLIENT_PROFILE_FIELDS:
            field_var = self.settings_profile_field_vars.get(field)
            if field_var is None:
                values[field] = ""
            else:
                values[field] = field_var.get().strip()
        return values

    def _read_caption_samples_form_fields(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field in CAPTION_SAMPLE_FIELDS:
            field_text = self.settings_caption_field_texts.get(field)
            if field_text is None:
                values[field] = ""
            else:
                values[field] = field_text.get("1.0", "end-1c").rstrip()
        return values

    def _reset_caption_samples_modified_state(self) -> None:
        for field_text in self.settings_caption_field_texts.values():
            try:
                field_text.edit_modified(False)
            except tk.TclError:
                continue

    def _on_profile_field_modified(self, *_args: object) -> None:
        if self._is_loading_profile_fields:
            return
        if self.settings_editor_mode != "profile":
            return
        if self.current_settings_file_path is None:
            return

        self.settings_editor_dirty = True
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="normal")
        self.settings_status_var.set(
            f"Unsaved changes: {self._to_relative_path(self.current_settings_file_path)}"
        )

    def _on_caption_samples_field_modified(self, event: tk.Event[tk.Misc]) -> None:
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return

        if self._is_loading_caption_fields:
            widget.edit_modified(False)
            return
        if self.settings_editor_mode != "caption_samples":
            widget.edit_modified(False)
            return
        if self.current_settings_file_path is None:
            widget.edit_modified(False)
            return

        if not widget.edit_modified():
            return
        widget.edit_modified(False)

        self.settings_editor_dirty = True
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="normal")
        self.settings_status_var.set(
            f"Unsaved changes: {self._to_relative_path(self.current_settings_file_path)}"
        )

    def _set_settings_editor_placeholder(self, message: str) -> None:
        if self.settings_content_text is None:
            return
        self._show_text_settings_editor()
        self.settings_content_text.configure(state="normal")
        self.settings_content_text.delete("1.0", "end")
        self.settings_content_text.insert("1.0", message)
        self.settings_content_text.edit_modified(False)
        self.settings_content_text.configure(state="disabled")

    def _set_settings_editor_content(self, content: str) -> None:
        if self.settings_content_text is None:
            return
        self._show_text_settings_editor()
        self.settings_content_text.configure(state="normal")
        self.settings_content_text.delete("1.0", "end")
        self.settings_content_text.insert("1.0", content)
        self.settings_content_text.edit_modified(False)

    def _read_settings_editor_content(self) -> str:
        if self.settings_content_text is None:
            return ""
        return self.settings_content_text.get("1.0", "end-1c")

    def _on_settings_file_selected(self, _event: tk.Event[tk.Misc]) -> None:
        if self.settings_file_listbox is None or self._is_updating_settings_list:
            return

        selection = self.settings_file_listbox.curselection()
        if not selection:
            return

        selected_key = self.settings_file_listbox.get(selection[0])
        selected_path = self.settings_file_lookup.get(selected_key)
        if selected_path is None:
            return

        if selected_path == self.current_settings_file_path:
            self.selected_settings_key = selected_key
            return

        if self.settings_editor_dirty and not self._confirm_discard_settings_changes():
            if self.selected_settings_key is not None:
                self._set_settings_listbox_selection(self.selected_settings_key)
            return

        self.settings_editor_dirty = False
        self._load_settings_file(selected_path)

    def _load_settings_file(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            messagebox.showerror("Read Failed", f"Could not read file:\n{path}\n\n{error}")
            return

        self.current_settings_file_path = path
        self.selected_settings_key = None
        for key, candidate in self.settings_file_lookup.items():
            if candidate == path:
                self.selected_settings_key = key
                break

        if path.name.lower() == "client_profile.md":
            self._show_profile_settings_editor()
            default_client_name = self.client_var.get().strip() or path.parent.name
            profile_values = parse_client_profile_markdown(content, default_client_name)
            self._populate_profile_form_fields(profile_values)
        elif path.name.lower() == CAPTION_SAMPLES_FILENAME.lower():
            self._show_caption_settings_editor()
            caption_values = parse_caption_samples_markdown(content)
            self._populate_caption_samples_form_fields(caption_values)
        else:
            self._set_settings_editor_content(content)
        self.settings_editor_dirty = False
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="disabled")
        if self.reload_settings_button is not None:
            self.reload_settings_button.configure(state="normal")
        self.settings_status_var.set(f"Editing: {self._to_relative_path(path)}")
        self._sync_auto_fill_profile_button()

    def _on_settings_editor_modified(self, _event: tk.Event[tk.Misc]) -> None:
        if self.settings_content_text is None:
            return
        if self.settings_editor_mode != "text":
            self.settings_content_text.edit_modified(False)
            return
        if not self.settings_content_text.edit_modified():
            return
        self.settings_content_text.edit_modified(False)

        if self.settings_content_text.cget("state") != "normal":
            return
        if self.current_settings_file_path is None:
            return

        self.settings_editor_dirty = True
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="normal")
        self.settings_status_var.set(
            f"Unsaved changes: {self._to_relative_path(self.current_settings_file_path)}"
        )

    def _save_settings_file(self) -> None:
        if self.current_settings_file_path is None:
            return
        if self.settings_editor_mode == "profile":
            client_name = self.client_var.get().strip() or self.current_settings_file_path.parent.name
            content = build_client_profile_markdown(client_name, self._read_profile_form_fields())
        elif self.settings_editor_mode == "caption_samples":
            client_name = self.client_var.get().strip() or self.current_settings_file_path.parent.name
            content = build_caption_samples_markdown(client_name, self._read_caption_samples_form_fields())
        else:
            if self.settings_content_text is None or self.settings_content_text.cget("state") != "normal":
                return
            content = self._read_settings_editor_content()
        try:
            self.current_settings_file_path.write_text(content, encoding="utf-8")
        except OSError as error:
            messagebox.showerror(
                "Save Failed",
                f"Could not save file:\n{self.current_settings_file_path}\n\n{error}",
            )
            return

        self.settings_editor_dirty = False
        if self.settings_content_text is not None:
            self.settings_content_text.edit_modified(False)
        if self.settings_editor_mode == "caption_samples":
            self._reset_caption_samples_modified_state()
        if self.save_settings_button is not None:
            self.save_settings_button.configure(state="disabled")
        self.settings_status_var.set(f"Saved: {self._to_relative_path(self.current_settings_file_path)}")
        self.status_var.set(f"Saved file: {self.current_settings_file_path}")

        self.last_md_signature = tuple()
        self._refresh_from_workspace_if_changed()

    def _reload_settings_file(self) -> None:
        if self.current_settings_file_path is None:
            return
        if self.settings_editor_dirty and not self._confirm_discard_settings_changes():
            return
        self.settings_editor_dirty = False
        self._load_settings_file(self.current_settings_file_path)

    def _confirm_discard_settings_changes(self) -> bool:
        return messagebox.askyesno(
            "Unsaved Changes",
            "You have unsaved settings edits. Discard those changes?",
        )

    def _to_relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)

    def _schedule_auto_refresh(self) -> None:
        if self.auto_refresh_handle is not None:
            return
        self.auto_refresh_handle = self.after(self.auto_refresh_interval_ms, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self.auto_refresh_handle = None
        idle_time_seconds = time.monotonic() - self.last_user_interaction_time
        if idle_time_seconds >= self.refresh_idle_guard_seconds:
            self._refresh_from_workspace_if_changed()
        self._schedule_auto_refresh()

    def _refresh_from_workspace_if_changed(self) -> None:
        new_signature = build_workspace_md_signature(self.base_dir)
        if new_signature == self.last_md_signature:
            return

        self.last_md_signature = new_signature
        selected_client = self.client_var.get()
        selected_file = self.file_var.get()
        selected_post_index = self.current_post_index

        self.client_files = find_client_markdown_files(self.base_dir)
        clients = sorted(self.client_files.keys(), key=str.lower)
        self._on_client_search_changed()

        if not clients:
            self.client_var.set("")
            self.file_var.set("")
            self.current_file_path = None
            self.post_created_var.set("Created: --")
            self.current_posts = []
            self.current_post_index = 0
            self._update_post_navigation_state()
            self._update_post_counter()
            self._render_field_message("No markdown files found after refresh.")
            self._refresh_settings_panel(preserve_selection=True, reload_current=not self.settings_editor_dirty)
            return

        if selected_client not in clients:
            selected_client = clients[0]
        self.client_var.set(selected_client)
        self.last_selected_client = selected_client
        self._refresh_files_for_client(
            selected_client,
            preferred_file=selected_file,
            preferred_post_index=selected_post_index,
        )
        self._refresh_settings_panel(preserve_selection=True, reload_current=not self.settings_editor_dirty)

    def _on_close(self) -> None:
        if self.auto_refresh_handle is not None:
            self.after_cancel(self.auto_refresh_handle)
            self.auto_refresh_handle = None

        if self.generation_poll_handle is not None:
            self.after_cancel(self.generation_poll_handle)
            self.generation_poll_handle = None

        if is_generation_process_running(self.generation_process):
            self.generation_stop_requested = True
            self._sync_stop_generation_button_state()
            try:
                request_generation_stop_signal(self.generation_process)
                self.generation_process.wait(timeout=1.5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    force_kill_generation_process_tree(self.generation_process)
                except OSError:
                    pass

        if self.settings_window is not None and self.settings_window.winfo_exists():
            self._close_settings_window()
            if self.settings_window is not None and self.settings_window.winfo_exists():
                return

        if self.copy_feedback_toast is not None and self.copy_feedback_toast.winfo_exists():
            self.copy_feedback_toast.destroy()
            self.copy_feedback_toast = None

        if (
            self.client_search_results_popup is not None
            and self.client_search_results_popup.winfo_exists()
        ):
            self.client_search_results_popup.destroy()
        self.client_search_results_popup = None
        self.client_search_results_listbox = None
        self.client_search_results_scrollbar = None

        self.destroy()


def main() -> None:
    base_dir = resolve_runtime_base_dir()
    app = ClientMarkdownViewer(base_dir=base_dir)
    app.mainloop()


if __name__ == "__main__":
    main()
