# Monitoring & Insights

## 1. Overview

**What it does:** This module is an automated AI-powered analyst that collects logs, metrics, and status information from the Render services, synthesizes the data, and uses a Large Language Model (LLM) to generate a daily human-readable report on system health, performance, and usage patterns.

**Why it exists:** It exists to bridge the gap between raw, high-volume monitoring data and actionable human understanding. Instead of engineers manually sifting through thousands of log lines, this system provides a daily executive summary that highlights trends, flags potential issues, and identifies optimization opportunities, saving significant analysis time.

---

## 2. Technical Details

**What would break if this disappeared?**
- The core Surf Lamp system would continue to function without any user-facing impact.
- The automated generation of daily health and performance reports would cease.
- Proactive identification of trends, performance degradation, and non-critical error patterns would be lost, forcing the team into a more reactive maintenance posture.

**What assumptions does it make?**
- **Environment:** It assumes it can find and load environment variables from two `.env` files: a main one at `./.env` and a specific one at `./render-mcp-server/.env`. It requires keys like `GEMINI_API_KEY` (or `OPENAI_API_KEY`) and email server credentials to be configured.
- **Tooling:** It assumes the `render-mcp-server` tools (like `render_logs`, `render_service_status`) are available in its Python path (`sys.path.append('./render-mcp-server')`).
- **Network:** It assumes it has network access to both the Render API (via the MCP tools) and the configured LLM provider's API (e.g., Google AI).
- **Scheduler:** The `setup_insights.sh` script prepares a cron job. The system assumes a `cron` daemon is running and configured to execute the `run_daily_insights.py` script daily.

**Where does complexity hide?**
- **Prompt Engineering:** The greatest complexity is in the `prompt` sent to the LLM inside the `generate_llm_insights` function. The quality, accuracy, and safety of the output are entirely dependent on the detailed instructions, constraints, and data structures provided in this prompt.
- **Data Aggregation:** The `collect_system_data` function is complex. It orchestrates numerous asynchronous calls to the Render MCP tools and then parses their varied string outputs into a structured `SystemSnapshot` object. This parsing logic is brittle and will break if the output format of the MCP tools changes.
- **Configuration Hell:** The `load_config` function pulls settings from environment variables which are themselves loaded from multiple files. Tracking down where a specific setting (`INSIGHTS_LOOKBACK_HOURS`, `EMAIL_SMTP_SERVER`, etc.) is defined can be confusing.

**What stories does the code tell?**
- The existence of two separate runner scripts, `run_daily_insights.py` and `run_insights.py`, suggests an evolution from a simple, manually-triggered script to a scheduled, production-ready daily job.
- The `_validate_analysis_only` function, with its long list of forbidden keywords (`ALTER TABLE`, `pip install`, ````python`), tells a clear story of a past failure where the LLM responded with unsafe or unhelpful implementation code, forcing the developers to add a safety guardrail to constrain the AI's output.
- The support for both Gemini and OpenAI (`llm_provider`) indicates flexibility and a desire to not be locked into a single LLM vendor.

---

## 3. Architecture & Implementation

**How does data flow through this component?**
1. A cron job executes `run_daily_insights.py`.
2. The `SurfLampInsights` class is instantiated, loading all configuration.
3. `collect_system_data` is called, which in turn calls various tools from the `render-mcp-server` to fetch logs, deployment history, and service status.
4. This raw data is parsed and structured into a `SystemSnapshot` dataclass.
5. The `SystemSnapshot` is serialized to JSON and embedded into a large prompt for the configured LLM.
6. The LLM processes the data and prompt, returning a natural language analysis.
7. The script saves this analysis to a `.md` or `.txt` file in the `./insights` directory.
8. If configured, the script sends the report as an email.

**Key Functions/Classes:**
- `SurfLampInsights`: The main class orchestrating the entire process.
- `SystemSnapshot`: A dataclass that serves as the clean, structured data model for all collected information. This is the "source of truth" for the analysis.
- `collect_system_data()`: The core data gathering function. It's an `async` function that runs all the MCP tool calls.
- `generate_llm_insights()`: The function that constructs the prompt and communicates with the LLM.
- `run_daily_insights.py`: The entry point for the scheduled daily job.

**Configuration:**
The system is configured entirely through environment variables, which can be set in `./.env` or `./render-mcp-server/.env`. Key variables include:
- `INSIGHTS_LLM_PROVIDER`: `gemini` or `openai`.
- `GEMINI_API_KEY` / `OPENAI_API_KEY`: API credentials.
- `INSIGHTS_LOOKBACK_HOURS`: How many hours of data to analyze (e.g., `24`).
- `INSIGHTS_OUTPUT_DIR`: Where to save report files.
- `INSIGHTS_EMAIL`: Set to `true` to enable email reports.
- `EMAIL_*`: SMTP server settings for sending emails.

---

## 4. Integration Points

**What calls this component?**
- A Linux cron job, configured by `setup_insights.sh`, calls the `run_daily_insights.py` script.
- A developer can also call it manually from the command line.

**What does this component call?**
- It **imports and directly calls** functions from the `render-mcp-server` module (e.g., `render_logs`, `render_service_status`). This is a tight, code-level dependency.
- It makes external network calls to the configured LLM's API endpoint.
- It makes external network calls to an SMTP server to send email.

**Data Formats/Contracts:**
- **Input:** It consumes the string-based output of the `render-mcp-server` tools.
- **Internal:** The `SystemSnapshot` dataclass is the primary internal data contract.
- **Output:** It produces a text or markdown file and can send an email with the same content.

---

## 5. Troubleshooting & Failure Modes

**How do you detect issues?**
- **No new reports:** The most common symptom is the absence of new report files in the `./insights` directory.
- **Cron Logs:** The `setup_insights.sh` script configures the cron job to log output to `logs/insights.log`. This file will contain any exceptions or errors from the daily run.
- **Manual Execution:** Running `python3 run_daily_insights.py` from the command line will print errors directly to the console.

**What are the recovery procedures?**
1. **Check the logs (`logs/insights.log`):** The Python traceback will usually identify the problem.
2. **API Key Failure:** If the error is related to authentication, verify that the `GEMINI_API_KEY` or `OPENAI_API_KEY` is correct in the `.env` file.
3. **MCP Tool Failure:** If the error comes from a `render-mcp-server` tool, it's likely that the tool's output format has changed, breaking the parsing logic in `collect_system_data`. The parsing functions (`_parse_log_lines`, `_parse_deployments`, etc.) will need to be updated.
4. **Email Failure:** Check the `EMAIL_*` environment variables and ensure the credentials are correct and the SMTP server is accessible.

**What scaling concerns exist?**
- **LLM Costs:** The primary scaling concern is cost. Each daily run makes a large call to a powerful LLM. If the volume of logs increases significantly, the size of the prompt will grow, leading to higher token usage and increased cost per run.
- **API Rate Limits:** The `collect_system_data` function makes multiple calls to the Render API via the MCP tools. While not currently an issue, a massive increase in the number of services or log volume could potentially hit Render API rate limits.
- **Cron Job Overlap:** The script can take a minute or more to run. It's essential to ensure the cron schedule (`daily`) is infrequent enough that a new job doesn't start before the previous one has finished.
