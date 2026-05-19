# How I fixed LLM code review amnesia using Hindsight

We've all piped git diffs into a local LLM and gotten decent, albeit generic, feedback. But after the fifth time the model suggests the exact same architectural anti-pattern you explicitly rejected yesterday, you realize something fundamental: stateless AI is infuriatingly amnesiac.

Building a local code review assistant is a rite of passage for engineers exploring the current wave of AI tools. Most implementations, however, stop at the wrapper level. They take your code, hurl it at an endpoint with a massive system prompt, and return a Markdown summary. They don't learn your project's architecture, they ignore your team's idiosyncratic coding style, and they gleefully repeat past mistakes. Working with them feels like onboarding a new junior engineer every single morning.

I wanted a reviewer that acts like a senior engineer who has actually been on the team for six months. It needed to remember past pull requests, learn from my explicit feedback, and be smart enough to know when to skim and when to read closely. To achieve this, I built an intelligent code review agent using local Qwen models, [cascadeflow](https://github.com/lemony-ai/cascadeflow) for dynamic model routing, and Hindsight to provide persistent [Vectorize agent memory](https://vectorize.io/what-is-agent-memory).

Here is how I designed the system, the architectural decisions I made, and what I learned trying to give a local LLM a long-term memory.

## The Architecture: Fast, Stateful, and Local

To make this practical for everyday use, the system had to be local-first. I cannot risk shipping proprietary, unreleased backend logic or sensitive infrastructure configurations over the wire to a third-party API.

The stack breaks down into three core components:
1. **The Brains**: Two local models running via Ollama: `qwen2.5-coder:7b` for speed, and `qwen2.5-coder:14b` for deep reasoning.
2. **The Router**: Cascadeflow dynamically routes reviews between the models based on the diff's complexity.
3. **The Memory**: An embedded PostgreSQL instance running via the [Hindsight GitHub](https://github.com/vectorize-io/hindsight) project, providing a semantic memory layer.

When a diff comes in, the system checks Hindsight for relevant context, calculates a complexity score for the code, lets Cascadeflow pick the right model, and generates a review. Critically, after the review is returned to the developer, it extracts key learnings from its own output and writes them back to Hindsight for future context.

## Solving Model Exhaustion with Dynamic Routing

My initial prototype just threw everything at the 14B parameter model. It worked, but waiting thirty seconds for it to review a two-line CSS change or a simple docstring update was agonizing. Conversely, when I tried forcing everything through the 7B model, it was blazing fast but would completely miss subtle race conditions in asynchronous database operations or complex architectural smells.

I needed the system to be smart about *how* it allocated compute. Reading the [cascadeflow docs](https://docs.cascadeflow.ai/), I realized I could configure a tiered model approach to let the agent decide how hard it needs to think.

```python
def create_cascade_agent():
    models = [
        # Fast Model
        ModelConfig(
            name="qwen2.5-coder:7b",
            provider="ollama",
            cost=0.00005,
            keywords=["simple", "quick", "basic", "fast"],
            domains=["code"],
            max_tokens=8192,
            temperature=0.2,
            quality_score=0.65,
        ),
        # High Quality Model
        ModelConfig(
            name="qwen2.5-coder:14b",
            provider="ollama",
            cost=0.00020,
            keywords=["security", "architecture", "performance", "complex", "reasoning"],
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
        use_semantic_domains=False
    )
```

Before sending the prompt to the LLM, I run a lightweight `estimate_complexity(code)` heuristic that counts lines and high-friction keywords (like `async`, `sql`, `thread`, `security`). This score feeds directly into Cascadeflow. If it's a simple change, it hits the 7B model. If the complexity score spikes, the request cleanly escalates to the 14B model.

This simple routing logic cut my average local inference time in half while preserving the deep reasoning required for the commits that actually needed it. It stopped my laptop fans from spinning up like jet engines for trivial tasks.

## Curing Amnesia with Hindsight

Model routing makes the system fast, but persistent memory is what makes it genuinely useful. I needed a way to store and recall engineering context seamlessly without rebuilding a vector database pipeline from scratch.

Instead of writing a custom Retrieval-Augmented Generation (RAG) implementation, I opted for the Hindsight MCP (Model Context Protocol) server. Hindsight is purpose-built for agent memory, allowing you to store raw observations and perform semantic recall over them natively. If you want to dive into the API mechanics, check out the [Hindsight docs](https://hindsight.vectorize.io/).

When a review starts, the agent queries Hindsight to build a focused context window out of past project history.

```python
def build_memory_query(file_path, language):
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
        if not results or not results.results:
            return ""
            
        memory_items = []
        for item in results.results[:MAX_MEMORY_ITEMS]:
            memory_items.append("- " + item.text)
            
        return "\n".join(memory_items)
    except Exception as e:
        print("Memory recall error:", e)
        return ""
```

By querying for specific angles like "Architecture decisions" and "Developer preferences," the LLM is primed with the exact requirements relevant to the file it is reviewing before it generates a single token.

## The Magic Loop: Retaining Learnings and Reflecting

Read-only memory is just documentation. A true agent needs to learn asynchronously from its own behavior and user corrections. The most powerful part of this system is the extraction phase.

After the LLM generates its code review, I parse the output, extract the "Critical Issues" and "Suggestions for Improvement", and push them back into Hindsight as discrete observations.

```python
async def retain_learning(observations, language="unknown"):
    if isinstance(observations, str):
        observations = [observations]

    async with memory_lock:
        for observation in observations:
            content = observation.strip()[:1200]
            if not content:
                continue
            try:
                await hindsight.aretain(
                    bank_id=BANK_ID,
                    content=content,
                    tags=["code-review", language.lower(), "engineering"]
                )
            except Exception as e:
                print("Memory retain error:", e)
```

Notice the explicit `memory_lock` via `asyncio`. I learned the hard way that when you're dealing with asynchronous LLM requests firing off concurrently during a busy coding session, you can easily encounter race conditions when writing to the local database. Locking ensures the memory bank remains stable and uncorrupted.

But raw observations aren't enough. If you dump every minor review comment into memory, the database becomes cluttered with hyper-specific noise (e.g., "Line 42 missing type hint in utils.py"). To combat this, I implemented a `reflect_on_reviews()` function that queries Hindsight to synthesize these granular observations into broader project-level constraints.

```python
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
        
        if not results or not results.results:
            return "No reflections available."
            
        reflection_items = []
        for item in results.results[:MAX_REFLECTION_ITEMS]:
            reflection_items.append("- " + item.text)
            
        return "\n".join(reflection_items)
    except Exception as e:
        return "Reflection failed."
```

This ensures that the LLM is not just memorizing the past, but actually deriving generalizable rules from it.

## Real-World Results

The difference between a stateless reviewer and a stateful one is staggering in practice.

In one session, I submitted a Python file where I carelessly relied on global state for a configuration dictionary. The agent caught it, but suggested wrapping it in a singleton pattern. I rejected that in my feedback, noting we strictly prefer dependency injection for easier testing.

In a stateless system, the LLM would forget this interaction the moment the script terminated. Tomorrow, if my colleague made the same global state mistake, the AI would gleefully suggest the singleton pattern all over again.

With this setup, the interaction went differently:
1. **Day 1:** The agent reviews the config file, I correct it, and the agent silently runs `retain_learning` to store: *"Developer preference: Avoid global state and singleton patterns for configuration; strictly prefer dependency injection to facilitate unit testing."*
2. **Day 2:** I submit a new database connection manager. Before reviewing, the agent recalls the memory. The review output specifically references the past context: *"As noted in previous project memory, ensure we are injecting the configuration dependency here rather than instantiating it globally."*

Furthermore, the routing logs consistently demonstrate the value of Cascadeflow. The 7B model reliably handles quick CSS tweaks and docstring formatting, executing in seconds, while the 14B takes over the heavy lifting when I introduce complex asynchronous state machines.

## Lessons Learned

Building a local, stateful code reviewer taught me a few hard truths about current AI engineering tooling:

1. **Context Memory > Raw Model Size:** A smaller, 7B model armed with deep, project-specific memory will provide a vastly more useful code review than a stateless 400B parameter behemoth that doesn't know your specific database schema or team preferences. Context is the ultimate lever for utility.
2. **Complexity-Aware Routing is Mandatory:** Running a massive LLM locally on every tiny syntax change will destroy your hardware resources and your patience. Use routing tools to act as an intelligent gateway. Let the fast, cheap models handle the noise, and reserve the massive models for architectural heavy lifting.
3. **Reflection is Necessary to Prevent Noise:** If you simply append every review output into a memory bank, your context window will eventually choke on trivialities. You need an asynchronous reflection process that reads raw memories and synthesizes them into broader project rules.
4. **Treat Memory Like a Database, Because It Is:** When building agents, it is easy to treat memory as a magical, always-available resource. In reality, it's stateful IO. If your agent processes multiple files or receives rapid-fire feedback concurrently, use async locks. Failure to do so will corrupt your context state.

By chaining local inference, dynamic model routing, and persistent memory, we can finally stop treating LLMs like generic text generators. The tools exist today to build agents that actually learn from their environment. Once you have a code reviewer that remembers your mistakes so you don't have to, you will never tolerate a stateless prompt again.
