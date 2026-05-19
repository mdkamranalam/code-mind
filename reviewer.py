import os
import re
import asyncio
import hashlib
import warnings
import requests

import gradio as gr

from datetime import datetime
from dataclasses import dataclass

from hindsight_client import Hindsight
from cascadeflow.agent import CascadeAgent
from cascadeflow.schema.config import ModelConfig

# =========================================================
# ENV
# =========================================================

from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIG
# =========================================================

HINDSIGHT_URL = os.getenv(
    "HINDSIGHT_URL",
    "http://localhost:8888"
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

BANK_ID = os.getenv(
    "BANK_ID",
    "code-review-memory"
)

REQUEST_TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        180
    )
)

MAX_MEMORY_ITEMS = int(
    os.getenv(
        "MAX_MEMORY_ITEMS",
        8
    )
)

MAX_REFLECTION_ITEMS = int(
    os.getenv(
        "MAX_REFLECTION_ITEMS",
        5
    )
)

load_dotenv()

warnings.filterwarnings(
    "ignore",
    category=UserWarning
)

# =========================================================
# HINDSIGHT
# =========================================================

hindsight = Hindsight(
    base_url=HINDSIGHT_URL
)

# =========================================================
# LOCKS
# =========================================================

memory_lock = asyncio.Lock()

# =========================================================
# CACHE
# =========================================================

review_cache = {}

# =========================================================
# REVIEW ENTRY
# =========================================================

@dataclass
class ReviewEntry:

    time: str
    file: str
    language: str
    review: str
    score: str
    summary: str

# =========================================================
# HEALTH CHECKS
# =========================================================

def check_hindsight():

    try:

        response = requests.get(
            HINDSIGHT_URL + "/health",
            timeout=5
        )

        return response.status_code == 200

    except Exception:

        return False


def check_ollama():

    try:

        response = requests.get(
            OLLAMA_URL + "/api/tags",
            timeout=5
        )

        return response.status_code == 200

    except Exception:

        return False

# =========================================================
# CASCADEFLOW
# =========================================================

def create_cascade_agent():

    models = [

        # =================================================
        # FAST MODEL
        # =================================================

        ModelConfig(
            name="qwen2.5-coder:7b",
            provider="ollama",
            cost=0.00005,
            keywords=[
                "simple",
                "quick",
                "basic",
                "fast"
            ],
            domains=["code"],
            max_tokens=8192,
            temperature=0.2,
            quality_score=0.65,
        ),

        # =================================================
        # HIGH QUALITY MODEL
        # =================================================

        ModelConfig(
            name="qwen2.5-coder:14b",
            provider="ollama",
            cost=0.00020,
            keywords=[
                "security",
                "architecture",
                "performance",
                "complex",
                "reasoning"
            ],
            domains=["code"],
            max_tokens=8192,
            temperature=0.2,
            quality_score=0.92,
        )
    ]

    return CascadeAgent(
        models=models,

        enable_cascade=True,

        enable_domain_detection=False,

        use_semantic_domains=False,
    )


cascade_agent = create_cascade_agent()

# =========================================================
# MEMORY
# =========================================================

def build_memory_query(
    file_path,
    language
):

    return (
        "Code review memory\n"
        "File: " + (file_path or "project") + "\n"
        "Language: " + language + "\n\n"
        "Coding style\n"
        "Architecture decisions\n"
        "Security issues\n"
        "Performance bottlenecks\n"
        "Refactoring patterns\n"
        "Recurring bugs\n"
        "Developer preferences"
    )


async def get_project_memory(query):

    try:

        results = await hindsight.arecall(
            bank_id=BANK_ID,
            query=query
        )

        if not results:
            return ""

        if not results.results:
            return ""

        memory_items = []

        for item in results.results[:MAX_MEMORY_ITEMS]:

            memory_items.append(
                "- " + item.text
            )

        return "\n".join(memory_items)

    except Exception as e:

        print(
            "Memory recall error:",
            e
        )

        return ""


async def retain_learning(
    observations,
    language="unknown"
):

    if isinstance(observations, str):
        observations = [observations]

    async with memory_lock:

        for observation in observations:

            content = (
                observation
                .strip()[:1200]
            )

            if not content:
                continue

            try:

                await hindsight.aretain(
                    bank_id=BANK_ID,
                    content=content,
                    tags=[
                        "code-review",
                        language.lower(),
                        "engineering"
                    ]
                )

            except Exception as e:

                print(
                    "Memory retain error:",
                    e
                )

# =========================================================
# REFLECTION
# =========================================================

async def reflect_on_reviews():

    try:

        reflection_query = (
            "Summarize recurring engineering issues, "
            "security problems, performance bottlenecks, "
            "architecture weaknesses, and coding patterns."
        )

        results = await hindsight.arecall(
            bank_id=BANK_ID,
            query=reflection_query
        )

        if not results:
            return "No reflections available."

        if not results.results:
            return "No reflections available."

        reflection_items = []

        for item in results.results[:MAX_REFLECTION_ITEMS]:

            reflection_items.append(
                "- " + item.text
            )

        return "\n".join(reflection_items)

    except Exception as e:

        print(
            "Reflection error:",
            e
        )

        return "Reflection failed."

# =========================================================
# HELPERS
# =========================================================

def estimate_complexity(code):

    complexity = 0

    complexity += len(code.splitlines())

    complexity += code.count("class ")
    complexity += code.count("async ")
    complexity += code.count("await ")
    complexity += code.count("thread")
    complexity += code.count("security")
    complexity += code.count("sql")
    complexity += code.count("docker")

    return complexity


def get_complexity_hint(code):

    score = estimate_complexity(code)

    if score > 500:
        return "large architecture review"

    if score > 200:
        return "complex code review"

    return "simple code review"


def get_overall_score(review_text):

    patterns = [
        r"Overall Score\s*[:\-]\s*(.+)",
        r"\*\*Overall Score\*\*\s*[:\-]?\s*(.+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            review_text,
            re.I
        )

        if match:

            return (
                match
                .group(1)
                .strip()
            )

    return "N/A"


def extract_summary(review):

    match = re.search(
        r"\*\*Summary\*\*(.*?)(\*\*Critical Issues\*\*|\Z)",
        review,
        re.S
    )

    if match:

        return (
            match
            .group(1)
            .strip()[:250]
        )

    return review[:250]


def extract_memory_observations(review_text):

    observations = []

    sections = [
        "Critical Issues",
        "Suggestions for Improvement",
        "Positive Aspects"
    ]

    for section in sections:

        pattern = (
            r"\*\*" +
            re.escape(section) +
            r"\*\*(.*?)(\*\*[A-Za-z ]+\*\*|\Z)"
        )

        match = re.search(
            pattern,
            review_text,
            re.S
        )

        if not match:
            continue

        section_text = (
            match
            .group(1)
            .strip()
        )

        bullets = re.findall(
            r"^[\-\*]\s*(.+)$",
            section_text,
            re.M
        )

        if not bullets:

            bullets = []

            for line in section_text.splitlines():

                clean = line.strip()

                if clean:
                    bullets.append(clean)

        for bullet in bullets[:3]:

            observations.append(
                section + ": " + bullet
            )

    score = get_overall_score(
        review_text
    )

    if score != "N/A":

        observations.append(
            "Overall Score: " + score
        )

    return observations

# =========================================================
# HISTORY
# =========================================================

def build_history_table(history):

    table = []

    for item in history:

        table.append([
            item.time,
            item.file,
            item.language,
            item.score,
            item.summary
        ])

    return table

# =========================================================
# REVIEW ENGINE
# =========================================================

async def get_code_review(
    code_snippet,
    language,
    file_path,
    user_feedback=""
):

    # =====================================================
    # CACHE
    # =====================================================

    cache_key = hashlib.sha256(
        (
            code_snippet +
            language +
            file_path +
            user_feedback
        ).encode()
    ).hexdigest()

    if cache_key in review_cache:

        return review_cache[cache_key]

    # =====================================================
    # MEMORY
    # =====================================================

    memory_query = build_memory_query(
        file_path,
        language
    )

    memory_context = await get_project_memory(
        memory_query
    )

    reflection_context = await reflect_on_reviews()

    # =====================================================
    # COMPLEXITY
    # =====================================================

    complexity_hint = get_complexity_hint(
        code_snippet
    )

    is_diff = (
        "diff --git"
        in code_snippet.lower()
        or "@@ -"
        in code_snippet.lower()
    )

    # =====================================================
    # PROMPT
    # =====================================================

    prompt_parts = []

    prompt_parts.append(
        "You are a principal software engineer."
    )

    prompt_parts.append(
        "Language: " + language
    )

    prompt_parts.append(
        "File: " +
        (file_path or "Untitled")
    )

    prompt_parts.append(
        "Review Complexity: " +
        complexity_hint
    )

    if memory_context:

        prompt_parts.append(
            "Project Memory:\n" +
            memory_context
        )

    if reflection_context:

        prompt_parts.append(
            "Historical Reflections:\n" +
            reflection_context
        )

    if user_feedback:

        prompt_parts.append(
            "User Feedback:\n" +
            user_feedback
        )

    code_block_language = (
        "diff"
        if is_diff
        else language
    )

    prompt_parts.append(
        "Code:\n```" +
        code_block_language +
        "\n" +
        code_snippet +
        "\n```"
    )

    prompt_parts.append(
        (
            "Review Criteria:\n"
            "- Correctness\n"
            "- Security\n"
            "- Performance\n"
            "- Maintainability\n"
            "- Readability\n"
            "- Architecture\n"
            "- Best Practices\n\n"
            "Return response in EXACT markdown format:\n\n"
            "**Summary**\n"
            "- ...\n\n"
            "**Critical Issues**\n"
            "- ...\n\n"
            "**Suggestions for Improvement**\n"
            "- ...\n\n"
            "**Positive Aspects**\n"
            "- ...\n\n"
            "**Overall Score**\n"
            "8/10"
        )
    )

    prompt = "\n\n".join(
        prompt_parts
    )

    # =====================================================
    # INFERENCE
    # =====================================================

    try:

        result = await asyncio.wait_for(

            cascade_agent.run(
                prompt,
                max_tokens=1600,
                temperature=0.2,
                complexity_hint=complexity_hint,
                domain_hint="code",
            ),

            timeout=REQUEST_TIMEOUT
        )

        review = (
            result
            .content
            .strip()
        )

        model_used = str(
            getattr(
                result,
                "model_used",
                "unknown"
            )
        )

        cascaded = str(
            getattr(
                result,
                "cascaded",
                False
            )
        )

        latency = (
            getattr(
                result,
                "latency_ms",
                0
            )
            or 0
        )

        runtime_trace = (
            "**Runtime Trace**\n"
            "- Model Used: " +
            model_used + "\n"
            "- Cascaded: " +
            cascaded + "\n"
            "- Cost: Local Ollama\n"
            "- Latency: " +
            format(latency, ".0f") +
            " ms\n"
            "- Routing Strategy: "
            "Qwen 7B handles fast reviews, "
            "Qwen 14B handles deep reasoning\n"
        )

        if memory_context:

            runtime_trace = (
                "**Recalled Project Memory**\n" +
                memory_context +
                "\n\n" +
                runtime_trace
            )

        response = (
            review,
            runtime_trace,
            memory_context
        )

        review_cache[cache_key] = response

        return response

    except asyncio.TimeoutError:

        return (
            (
                "## Timeout Error\n\n"
                "The review took too long.\n"
                "Try smaller code snippets."
            ),
            "",
            memory_context
        )

    except Exception as e:

        error_message = (
            "## Error\n\n"
            "CascadeFlow/Ollama failed.\n\n"
            "### Possible Fixes\n"
            "- Ensure Ollama is running\n"
            "- Run: ollama list\n"
            "- Verify models exist\n\n"
            "### Actual Error\n"
            + str(e)
        )

        return (
            error_message,
            "",
            memory_context
        )

# =========================================================
# UI
# =========================================================

with gr.Blocks(
    title="Intelligent Code Review Agent",
    theme=gr.themes.Soft()
) as demo:

    gr.Markdown(
        "# 🧠 Intelligent Code Review Agent\n"
    )

    history_state = gr.State([])

    with gr.Tabs():

        # =================================================
        # REVIEW TAB
        # =================================================

        with gr.Tab("🔍 Code Review"):

            with gr.Row():

                with gr.Column(scale=2):

                    code_input = gr.Code(
                        label="Paste Code or Git Diff",
                        lines=22
                    )

                    with gr.Row():

                        language = gr.Dropdown(
                            [
                                "Python",
                                "JavaScript",
                                "TypeScript",
                                "Java",
                                "Go",
                                "Rust",
                                "C++"
                            ],
                            value="Python",
                            label="Language"
                        )

                        filename = gr.Textbox(
                            label="File Name",
                            value="main.py"
                        )

                    feedback = gr.Textbox(
                        label="Developer Feedback",
                        lines=2,
                        placeholder=(
                            "Example: prefer type hints"
                        )
                    )

                    review_btn = gr.Button(
                        "🚀 Review Code",
                        variant="primary"
                    )

                with gr.Column(scale=2):

                    review_output = gr.Markdown()

                    memory_preview = gr.Markdown(
                        value="No memory loaded yet."
                    )

                    memory_refresh = gr.Button(
                        "Refresh Memory"
                    )

        # =================================================
        # HISTORY TAB
        # =================================================

        with gr.Tab("📜 Review History"):

            history_table = gr.Dataframe(
                headers=[
                    "Time",
                    "File",
                    "Language",
                    "Score",
                    "Summary"
                ],
                value=[],
                interactive=False
            )

            selected_review = gr.Markdown()

        # =================================================
        # REFLECTION TAB
        # =================================================

        with gr.Tab("🧠 Reflection"):

            reflection_output = gr.Markdown()

            reflection_btn = gr.Button(
                "Generate Reflections"
            )

    # =====================================================
    # ACTIONS
    # =====================================================

    async def review_action(
        code,
        lang,
        fname,
        fb,
        history
    ):

        # =================================================
        # HEALTH CHECKS
        # =================================================

        if not check_hindsight():

            return (
                "Hindsight server offline.",
                [],
                "Memory unavailable.",
                history
            )

        if not check_ollama():

            return (
                "Ollama server offline.",
                [],
                "Ollama unavailable.",
                history
            )

        # =================================================
        # INPUT VALIDATION
        # =================================================

        if not code or not code.strip():

            return (
                "Please enter code.",
                [],
                "No memory loaded.",
                history
            )

        # =================================================
        # REVIEW
        # =================================================

        review, runtime_trace, memory_context = (
            await get_code_review(
                code,
                lang,
                fname,
                fb
            )
        )

        full_output = (
            review +
            "\n\n---\n\n" +
            runtime_trace
        )

        score = get_overall_score(
            review
        )

        summary = extract_summary(
            review
        )

        new_entry = ReviewEntry(
            time=datetime.now().strftime("%H:%M:%S"),
            file=fname,
            language=lang,
            review=full_output,
            score=score,
            summary=summary
        )

        history.append(new_entry)

        observations = (
            extract_memory_observations(
                review
            )
        )

        if fb and fb.strip():

            observations.append(
                "Developer Feedback: " +
                fb.strip()
            )

        if not observations:

            observations = [
                "Reviewed " + fname
            ]

        await retain_learning(
            observations,
            lang
        )

        history_table_data = (
            build_history_table(
                history
            )
        )

        memory_display = (
            memory_context
            if memory_context
            else "No memory found yet."
        )

        return (
            full_output,
            history_table_data,
            memory_display,
            history
        )

    async def get_memory_preview(
        lang,
        fname
    ):

        memory_query = build_memory_query(
            fname,
            lang
        )

        memory_context = (
            await get_project_memory(
                memory_query
            )
        )

        if memory_context:
            return memory_context

        return "No memory found yet."

    async def generate_reflections():

        return await reflect_on_reviews()

    def show_full_review(
        evt: gr.SelectData,
        history
    ):

        if not history:
            return "No review selected."

        row_index = evt.index[0]

        if row_index >= len(history):
            return "Invalid selection."

        return history[row_index].review

    # =====================================================
    # EVENTS
    # =====================================================

    review_btn.click(
        review_action,
        inputs=[
            code_input,
            language,
            filename,
            feedback,
            history_state
        ],
        outputs=[
            review_output,
            history_table,
            memory_preview,
            history_state
        ]
    )

    memory_refresh.click(
        get_memory_preview,
        inputs=[
            language,
            filename
        ],
        outputs=[
            memory_preview
        ]
    )

    history_table.select(
        show_full_review,
        inputs=[
            history_state
        ],
        outputs=[
            selected_review
        ]
    )

    reflection_btn.click(
        generate_reflections,
        outputs=[
            reflection_output
        ]
    )

    gr.Markdown(
        (
            "### 💡 Features\n"
            "- Persistent memory with Hindsight\n"
            "- Runtime intelligence with CascadeFlow\n"
            "- Multi-model routing with Ollama\n"
            "- Reflection-based learning\n"
            "- Review caching\n"
            "- Timeout protection\n"
            "- Adaptive code review behavior"
        )
    )

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    demo.launch(
        share=False
    )