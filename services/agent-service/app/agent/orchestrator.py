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
5. Once you understand their intent (buying, browsing, support) and priority (hot, warm, cold) (usually by the 2nd or 3rd turn), call the `qualify_lead` tool.
6. If you cannot find the answer in the retrieved documents, politely explain that you don't have that information and ask for their email/phone so a human can follow up.
"""

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="search_services",
            description="Queries the knowledge base for details about Autexa's services, packages, pricing, subscription options, and FAQs. Frame pricing as rough estimates.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="The search term or query relating to services, packages, pricing, and FAQs.")
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
                    "query": types.Schema(type=types.Type.STRING, description="The search term or query relating to case studies.")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="qualify_lead",
            description="Qualifies a lead by setting their intent (buying, browsing, support) and priority (hot, warm, cold). Also updates lead status to qualified. Call this when intent is clear.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead to qualify."),
                    "intent": types.Schema(type=types.Type.STRING, description="The intent of the lead. Must be one of: 'buying', 'browsing', 'support'."),
                    "priority": types.Schema(type=types.Type.STRING, description="The priority of the lead. Must be one of: 'hot', 'warm', 'cold'.")
                },
                required=["lead_id", "intent", "priority"]
            )
        ),
        types.FunctionDeclaration(
            name="update_lead",
            description="Updates an existing lead's fields as new information (such as name, email, business type, or service requested) is gathered during the conversation.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "lead_id": types.Schema(type=types.Type.INTEGER, description="The database ID of the lead to update."),
                    "name": types.Schema(type=types.Type.STRING, description="The name of the lead."),
                    "email": types.Schema(type=types.Type.STRING, description="The email address of the lead."),
                    "phone": types.Schema(type=types.Type.STRING, description="The phone number of the lead."),
                    "business_type": types.Schema(type=types.Type.STRING, description="The type of business (e.g. gym, e-commerce, real estate)."),
                    "service_requested": types.Schema(type=types.Type.STRING, description="The service or package they are interested in.")
                },
                required=["lead_id"]
            )
        )
    ])
]


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
            if name == "search_services":
                result = tools.search_services(db, args.get("query", ""))
            elif name == "search_case_studies":
                result = tools.search_case_studies(db, args.get("query", ""))
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
        # Convert internal message history to google-genai Content format
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

        # Run agentic loop up to 5 steps
        for step in range(5):
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
                # Append the model's response (with function calls) to history
                history.append(response.candidates[0].content)

                # Execute all tools and build function response parts
                function_response_parts = []
                for fc in function_calls:
                    args = dict(fc.args) if fc.args else {}
                    # Always enforce the correct lead_id for lead-mutating tools
                    if fc.name in ["qualify_lead", "update_lead"]:
                        args["lead_id"] = lead.id

                    tool_result = self.execute_tool(db, lead.id, fc.name, args)
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": tool_result}
                        )
                    )

                # Append tool results as a user turn (Gemini convention)
                history.append(types.Content(role="user", parts=function_response_parts))
                continue

            # No function calls — return the final text reply
            if response.text:
                return response.text

        return "I apologize, but I need to process this request further. Please contact our support team."


orchestrator = AgentOrchestrator()
