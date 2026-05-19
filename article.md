# How I made a code review agent remember with Hindsight

I wanted a code review assistant that felt like a teammate, not a stateless chatbot. The core problem was the same one every AI agent hits: without memory, the agent repeats the same surface-level feedback every session, even when the project clearly has a preferred style.

## What this system does

This repo is a Gradio-based code review agent that uses Hindsight for persistent project memory. A reviewer can paste code or a git diff, choose a language and filename, and receive a structured review. Behind the scenes, the agent stores a lightweight memory bank of prior review decisions and recalls it in future runs.

The result is a review assistant that can gradually learn a project’s own conventions instead of answering every request from scratch.

## Why memory matters for code review

In a normal code review flow, the agent sees one file and gives generic advice: "use better names", "fix indentation", "add tests". That is useful, but it’s not what makes a real code reviewer valuable.

What really matters is when the system starts to say things like:

- "This project prefers `snake_case` for helper functions"
- "The style here already matches the earlier review of `main.py`"
- "I’m skipping basic formatting checks because the repository memory says you already enforce it"

That kind of behavior comes from project memory.

## How I wired Hindsight into the agent

The implementation is small but deliberate. The key pieces are:

- `Hindsight(base_url=HINDSIGHT_URL)` to connect to a local Hindsight instance
- `retain_learning()` to store what the agent learned after each review
- `get_project_memory()` to retrieve relevant recall before building the prompt

Here’s the recall helper:

```python
def get_project_memory(query: str) -> str:
    try:
        results = hindsight.recall(bank_id=BANK_ID, query=query)
        if results and results.results:
            return "\n".join([f"- {r.text}" for r in results.results[:8]])
        return ""
    except:
        return ""
```

The agent stores a record in a simple bank named `code-review-memory`. This keeps the logic separate from the review prompt and makes the memory layer reusable.

```python
def retain_learning(observation: str):
    try:
        hindsight.retain(bank_id=BANK_ID, content=observation[:1200], tags=["code-review"])
    except:
        pass
```

That means after any review, the agent can retain a compact statement such as `Reviewed main.py` or `Recommended consistent naming for package utilities`.

## Building the review prompt with memory

The most important design decision was to keep the memory retrieval step simple and explicit. The `get_code_review()` function composes the prompt like this:

````python
memory_context = get_project_memory("code style and issues in " + (file_path or "project"))

prompt = f"You are an expert senior software engineer.\nLanguage: {language}\nFile: {file_path or 'Untitled'}\n\n"
if memory_context:
    prompt += f"Project Memory:\n{memory_context}\n\n"
if user_feedback:
    prompt += f"User Feedback: {user_feedback}\n\n"

prompt += f"Code:\n```{language if not is_diff else 'diff'}\n{code_snippet}\n```\n\n"
prompt += "Give structured review: **Summary**, **Critical Issues**, **Suggestions for Improvement**, **Positive Aspects**, **Overall Score**."
````

That means memory is not hidden deep in a chain. It is a first-class part of the prompt.

Because Hindsight can recall multiple related items, the same project memory evolves over time without requiring a separate database schema.

## What the UI looks like

The Gradio interface has three tabs:

- Code Review
- Generate Unit Tests
- Review History

The Review History tab stores a simple timeline of past reviews and lets users inspect the full review text. Every time a review runs, the agent appends a new history entry and calls `retain_learning()`.

This is the main loop that connects the UI with memory:

```python
review = get_code_review(code, lang, fname, fb)
review_history.append({
    "time": datetime.now().strftime("%H:%M:%S"),
    "file": fname,
    "language": lang,
    "review": review,
    "summary": summary.strip()
})
retain_learning(f"Reviewed {fname}")
```

A real reviewer would probably keep more structured metadata, but for a first version the lightweight approach is enough to show how Hindsight changes behavior.

## A concrete behavior change

The most convincing part of this project is the before/after story.

First run:

- Paste a new Python file
- Receive a generic review about docstrings, naming, and formatting
- The review agent has no project context

Second run:

- Paste another file from the same project
- The prompt includes `Project Memory:`
- The agent now references prior issues and avoids repeating low-value advice

That difference is what makes Hindsight feel useful.

If the project has already established a preference for `pytest` over `unittest`, or for a specific import order, that preference can be surfaced automatically in the next review.

## Why I picked Hindsight here

I chose Hindsight because it is designed for exactly this pattern: retain short observations, recall them by query, and let the prompt use the results directly. The repo is effectively a small agent that benefits from:

- persistent, project-level context
- query-based retrieval instead of a fixed config file
- fast recall for relevant code review patterns

The Hindsight memory layer is the part of the stack that turns a one-off review into a multi-session project assistant.

If you want to read more, the official [Hindsight docs](https://hindsight.vectorize.io/) explain the API and the memory model. The [Hindsight GitHub](https://github.com/vectorize-io/hindsight) repo is also a good reference.

## What I learned

### 1. Memory should be simple and query-driven

I avoided building a custom database schema. Instead, I store plain text observations in Hindsight and query them with a short phrase like `code style and issues in main.py`.

This keeps the project flexible: the same memory bank can store reviews, style observations, and even user preferences later.

### 2. Put memory in the prompt before the code

If the agent sees the code before it sees project memory, the recall feels like an afterthought. I made the memory block the first thing after the context header so it influences review generation directly.

### 3. Give the agent a reason to retain useful things

My first version retained the full review text. That worked, but it was noisy. The current version retains compact, intent-focused observations. That makes recall more stable and easier to inspect.

### 4. Use the same memory bank across sessions

By naming the bank `code-review-memory`, this app keeps the same project memory across launches. That is the difference between stateless code review and a system that actually learns.

### 5. A small agent can still feel useful

The app is not a full IDE plugin, but it is enough to prove the key idea: an AI review assistant can improve over time with memory. That is the story I want to tell.

## What’s next

A next step would be to store more structured review metadata and surface it as explicit project rules:

- preferred test framework
- naming conventions
- dependency patterns
- security checks to run first

I could also extend the same memory layer to support developer feedback, for example by retaining notes like `The user prefers fewer style comments and more architecture feedback`.

For now, the important result is this: one small addition of Hindsight memory turns a generic code review assistant into a service that carries project context across sessions.

If you want to explore this pattern yourself, start with a local Hindsight instance and a prompt that includes a `Project Memory` block. It is a small change, but it makes an agent feel much more grounded.

---

If you want to understand the agent memory layer in general, check out [Vectorize agent memory](https://vectorize.io/what-is-agent-memory).
