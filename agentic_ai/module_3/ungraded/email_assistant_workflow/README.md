# 🤖 Tools-in-Agents — Email Management Demo

This repository is part of a hands-on course from **DeepLearning.AI**, designed to teach you how large language models (LLMs) can be equipped with **tools** to perform complex, real-world tasks like managing an inbox. It’s not just about generating text — it’s about **thinking and acting**.

You’ll build and observe an LLM-based agent that:
- Thinks about what it needs to do
- Calls Python tools (functions or API endpoints)
- Uses the results to plan the next step

All using a ReAct-style loop: **Reason → Act → Observe → Repeat**

---

## 🚀 Getting Started

### 1. Prepare the notebook

From the repository root, prepare the lab and enter its directory.

```bash
python3 tools/prepare.py agentic_ai/module_3/ungraded/email_assistant_workflow
source .venv/bin/activate
cd agentic_ai/module_3/ungraded/email_assistant_workflow
```

Create a local `.env` file in the lab directory with your OpenAI key and the local service URLs.

```env
OPENAI_API_KEY=...
M3_EMAIL_SERVER_API_URL=http://localhost:5000
M3_LLM_SERVER_URL=http://localhost:5001
```

### 2. Start the local services

Run the mail service in the lab directory. It creates a SQLite database and loads six unread sample emails.

```bash
python -m uvicorn email_server.email_service:app --port 5000 --timeout-keep-alive 1200
```

In another terminal, activate the same environment, enter the lab directory, and start the agent.

```bash
python -m uvicorn email_server.llm_service:app --port 5001 --timeout-keep-alive 1200
```

### 3. Open the lab

Open [M3_UGL_2.ipynb](M3_UGL_2.ipynb) with the repository’s Jupyter kernel. The [local inbox](http://localhost:5000/) is also available in a browser.

---

## 🧠 Key Concept: Tools in Agents

Tools are Python functions that the LLM can invoke when it needs to **act**.

For example, given this prompt:

> "Check for unread emails from boss@email.com and reply politely."

The agent may:
1. Call `list_unread_emails()`
2. Filter for sender
3. Call `mark_email_as_read(email_id=...)`
4. Call `send_email(...)`

The entire decision chain is made by the LLM, not hardcoded. You can inspect every step.

---

## 🔧 Tools Available to the Agent

These are defined in `email_tools.py`:

```python
list_unread_emails()
search_emails(query: str)
get_email(email_id: int)
mark_email_as_read(email_id: int)
send_email(recipient: str, subject: str, body: str)
search_unread_from_sender(sender: str)
```

They are passed to the agent via:

```python
client.chat.completions.create(
    model="openai:gpt-5-mini",
    messages=[{"role": "user", "content": prompt}],
    tools=[...],
    max_turns=5
)
```

---

## 📡 Backend API Reference

The email system is backed by FastAPI and offers these endpoints:

| Method   | Route                       | Description                     |
|----------|----------------------------|---------------------------------|
| `GET`    | `/reset_database`          | Reloads the six sample emails    |
| `POST`   | `/send`                    | Sends a mock email              |
| `GET`    | `/emails`                  | Lists all emails                |
| `GET`    | `/emails/unread`           | Lists unread emails             |
| `GET`    | `/emails/search?q=...`     | Search by subject/body/sender   |
| `GET`    | `/emails/filter`           | Filter by recipient or date     |
| `GET`    | `/emails/{email_id}`       | Get email by ID                 |
| `PATCH`  | `/emails/{email_id}/read`  | Mark as read                    |
| `PATCH`  | `/emails/{email_id}/unread`| Mark as unread                  |
| `DELETE` | `/emails/{email_id}`       | Delete email                    |

---

## 🧪 Try This Prompt

Paste this into the notebook and watch the tools fire:

```text
Check for unread emails from boss@email.com,
mark them as read,
and send a polite follow-up.
```

You'll see:
- Tool calls executed
- Responses interpreted
- Final message generated

All automatically, via agent reasoning.

---

## ✅ Summary

This project is designed for learners. You’ll:
- Build and run your own agent system
- Watch LLMs call functions, not just generate text
- Understand how reasoning and actions can be chained
- Use `aisuite` to connect prompts to tool execution
