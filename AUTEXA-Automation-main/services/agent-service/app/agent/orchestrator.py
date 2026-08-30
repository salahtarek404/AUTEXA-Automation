import json
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from app.core.config import settings
from app.models.tool_call_log import ToolCallLog
from app.models.lead import Lead
from app.agent import tools

SYSTEM_INSTRUCTION = """You are Autexa's intelligent AI Business Automation Agent.
Your job is to interact with potential leads, answer their questions accurately using the search tools, gather their information, and qualify them.

Rules:
1. Always frame pricing and estimates as rough ranges, never state a final number as fact.
2. Use the `search_services` tool to look up service details, subscription tiers, and FAQs.
3. Use the `search_case_studies` tool to look up case study metrics.
4. When you learn new information about a lead (like their name, email, business type, or service requested), update the lead using `update_lead`.
5. Once you understand their intent (buying, browsing, support) and priority (hot, warm, cold) — usually by the 2nd or 3rd turn — call the `qualify_lead` tool.
6. If you cannot find the answer in the retrieved documents, politely explain that you don't have that information and ask for their email/phone so a human can follow up.
7. If the lead has gone quiet or conversation stalled (no new intent), call `schedule_followup` to set a reminder in 48 hours. Do not call it more than once per conversation.
8. When a lead is qualified as `hot` with intent `buying` AND you have their name and the service they want, call `generate_proposal` to create a draft. NEVER tell the customer the proposal has been sent — it is a draft awaiting human approval.
9. `notify_sales_team` is called automatically when `qualify_lead` resolves with priority=hot. You may also call it independently if urgent human escalation is needed.
"""

TOOLS = [
    types.Tool(function_declarations=[
        # --- Phase 2 tools ---
        types.FunctionDeclaration(
            name="search_services",
            description="Queries the knowledge base for details about Autexa's services, packages, pricing, subscription options, and FAQs. Frame pricing as rough estimates.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Search term relating to services, packages, pricing, or FAQs.")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="search_case_studies",
            description="Queries the knowledge base for specific client case studies, success stories, and metrics.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Search term relating to case studies.")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="qualify_lead",
            description="Qualifies a lead by setting their intent (buying, browsing, support) and priority (hot, warm, cold). Also updates lead status to 'qualified'. Automatically notifies the sales team if priority is 'hot'.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead."),
                    "intent": types.Schema(type=types.Type.STRING, description="Lead intent. One of: 'buying', 'browsing', 'support'."),
                    "priority": types.Schema(type=types.Type.STRING, description="Lead priority. One of: 'hot', 'warm', 'cold'.")
                },
                required=["lead_id", "intent", "priority"]
            )
        ),
        types.FunctionDeclaration(
            name="update_lead",
            description="Updates a lead's fields (name, email, phone, business_type, service_requested) as new information is gathered.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead."),
                    "name": types.Schema(type=types.Type.STRING, description="The lead's name."),
                    "email": types.Schema(type=types.Type.STRING, description="The lead's email address."),
                    "phone": types.Schema(type=types.Type.STRING, description="The lead's phone number."),
                    "business_type": types.Schema(type=types.Type.STRING, description="Type of business (e.g. gym, e-commerce, real estate)."),
                    "service_requested": types.Schema(type=types.Type.STRING, description="The service or package they are interested in.")
                },
                required=["lead_id"]
            )
        ),
        # --- Phase 3 tools ---
        types.FunctionDeclaration(
            name="schedule_followup",
            description="Schedules an automated follow-up message to be sent to the lead after a delay. Use when the conversation has stalled or the lead has gone quiet. Do not call more than once per conversation.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead."),
                    "hours_from_now": types.Schema(type=types.Type.NUMBER, description="How many hours from now to send the follow-up. Default is 48."),
                    "message_type": types.Schema(type=types.Type.STRING, description="Type of follow-up. One of: 'auto_message', 'reminder'. Default is 'auto_message'.")
                },
                required=["lead_id"]
            )
        ),
        types.FunctionDeclaration(
            name="notify_sales_team",
            description="Fires an alert to the human sales team via n8n (Slack/email). Called automatically for hot leads. Only call this manually if urgent human escalation is required for a non-hot lead.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead to escalate.")
                },
                required=["lead_id"]
            )
        ),
        types.FunctionDeclaration(
            name="generate_proposal",
            description="Creates a draft proposal for a qualified hot/buying lead based on pricing.md estimates. Status is 'draft' — it requires human approval in the dashboard before being sent. NEVER tell the customer it has been sent.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the qualified lead.")
                },
                required=["lead_id"]
            )
        ),
    ])
]

# Tools the LLM is allowed to call (lead_id is always overridden server-side)
LEAD_SCOPED_TOOLS = {"qualify_lead", "update_lead", "schedule_followup", "notify_sales_team", "generate_proposal"}


class AgentOrchestrator:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-3.5-flash-lite"

    def execute_tool(self, db: Session, lead_id: int, name: str, args: dict) -> str:
        """Executes the Python tool function, logs the call to ToolCallLog, and returns the result."""
        log_entry = ToolCallLog(
            lead_id=lead_id,
            tool_name=name,
            arguments=args
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        print(f"[Orchestrator] Executing tool '{name}' for lead {lead_id} with args: {args}")

        try:
            lead_obj = db.query(Lead).filter(Lead.id == lead_id).first()
            tenant_id = lead_obj.tenant_id if lead_obj else "autexa"

            if name == "search_services":
                result = tools.search_services(db, args.get("query", ""), tenant_id=tenant_id)
            elif name == "search_case_studies":
                result = tools.search_case_studies(db, args.get("query", ""), tenant_id=tenant_id)
            elif name == "qualify_lead":
                result = tools.qualify_lead(db, lead_id, args.get("intent", ""), args.get("priority", ""))
            elif name == "update_lead":
                result = tools.update_lead(
                    db,
                    lead_id=lead_id,
                    name=args.get("name"),
                    email=args.get("email"),
                    phone=args.get("phone"),
                    business_type=args.get("business_type"),
                    service_requested=args.get("service_requested")
                )
            elif name == "schedule_followup":
                result = tools.schedule_followup(
                    db,
                    lead_id=lead_id,
                    hours_from_now=args.get("hours_from_now", 48.0),
                    message_type=args.get("message_type", "auto_message")
                )
            elif name == "notify_sales_team":
                result = tools.notify_sales_team(db, lead_id=lead_id)
            elif name == "generate_proposal":
                result = tools.generate_proposal(db, lead_id=lead_id)
            else:
                result = f"Error: Tool '{name}' is not supported."
        except Exception as e:
            result = f"Error executing tool '{name}': {e}"
            print(f"[Orchestrator] Error: {e}")

        try:
            log_entry.result = {"output": result}
            db.commit()
        except Exception as log_err:
            print(f"Failed to update tool log result: {log_err}")

        return result

    def generate_reply(self, db: Session, lead: Lead, message_history: list) -> str:
        """Runs the main agent dialog loop, resolving tool calls until a text reply is returned."""
        history = []
        for msg in message_history:
            role = "user" if msg["role"] == "user" else "model"
            history.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=TOOLS,
        )

        # Run agentic loop up to 8 steps (6 tools may require more resolution steps)
        for step in range(8):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=history,
                    config=config
                )
            except Exception as e:
                print(f"Error generating content: {e}")
                return "I apologize, but I am currently unavailable. Please try again later."

            # Check for function calls in the response
            function_calls = []
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.function_call and part.function_call.name:
                        function_calls.append(part.function_call)

            if function_calls:
                history.append(response.candidates[0].content)

                function_response_parts = []
                for fc in function_calls:
                    args = dict(fc.args) if fc.args else {}
                    # Enforce correct lead_id server-side — LLM cannot spoof it
                    if fc.name in LEAD_SCOPED_TOOLS:
                        args["lead_id"] = lead.id

                    tool_result = self.execute_tool(db, lead.id, fc.name, args)
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": tool_result}
                        )
                    )

                history.append(types.Content(role="user", parts=function_response_parts))
                continue

            # No function calls — return the final text reply
            if response.text:
                return response.text

        return "I apologize, but I need to process this request further. Please contact our support team."


orchestrator = AgentOrchestrator()
