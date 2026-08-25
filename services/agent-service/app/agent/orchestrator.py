import os
import json
from sqlalchemy.orm import Session
import google.generativeai as genai
import google.generativeai.protos as genai_protos
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

# Manual tool declarations for Gemini Function Calling
DB_SEARCH_SERVICES_TOOL = {
    "function_declarations": [
        {
            "name": "search_services",
            "description": "Queries the knowledge base for details about Autexa's services, packages, pricing, subscription options, and FAQs. Frame pricing as rough estimates.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "The search term or query relating to services, packages, pricing, and FAQs."
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_case_studies",
            "description": "Queries the knowledge base for specific client case studies, success stories, and metrics.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "The search term or query relating to case studies."
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "qualify_lead",
            "description": "Qualifies a lead by setting their intent (buying, browsing, support) and priority (hot, warm, cold). Also updates lead status to qualified. Call this when intent is clear.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "lead_id": {
                        "type": "INTEGER",
                        "description": "The database ID of the lead to qualify."
                    },
                    "intent": {
                        "type": "STRING",
                        "description": "The intent of the lead. Must be one of: 'buying', 'browsing', 'support'."
                    },
                    "priority": {
                        "type": "STRING",
                        "description": "The priority of the lead. Must be one of: 'hot', 'warm', 'cold'."
                    }
                },
                "required": ["lead_id", "intent", "priority"]
            }
        },
        {
            "name": "update_lead",
            "description": "Updates an existing lead's fields as new information (such as name, email, business type, or service requested) is gathered during the conversation.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "lead_id": {
                        "type": "INTEGER",
                        "description": "The database ID of the lead to update."
                    },
                    "name": {
                        "type": "STRING",
                        "description": "The name of the lead."
                    },
                    "email": {
                        "type": "STRING",
                        "description": "The email address of the lead."
                    },
                    "phone": {
                        "type": "STRING",
                        "description": "The phone number of the lead."
                    },
                    "business_type": {
                        "type": "STRING",
                        "description": "The type of business (e.g. gym, e-commerce, real estate)."
                    },
                    "service_requested": {
                        "type": "STRING",
                        "description": "The service or package they are interested in."
                    }
                },
                "required": ["lead_id"]
            }
        }
    ]
}

class AgentOrchestrator:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name="models/gemini-3.5-flash-lite",
            system_instruction=SYSTEM_INSTRUCTION
        )

    def execute_tool(self, db: Session, lead_id: int, name: str, args: dict) -> str:
        """Executes the Python tool function, logs the call to ToolCallLog, and returns the result."""
        # 1. Log the tool invocation
        log_entry = ToolCallLog(
            lead_id=lead_id,
            tool_name=name,
            arguments=args
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        print(f"[Orchestrator] Executing tool '{name}' for lead {lead_id} with args: {args}")
        
        # 2. Match and execute the tool
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

        # 3. Update log entry with the result
        try:
            log_entry.result = {"output": result}
            db.commit()
        except Exception as log_err:
            print(f"Failed to update tool log result: {log_err}")

        return result

    def generate_reply(self, db: Session, lead: Lead, message_history: list) -> str:
        """Runs the main agent dialog loop, resolving tool calls recursively until a text reply is returned."""
        # Convert internal message history to Gemini format
        history = []
        for msg in message_history:
            role = "user" if msg["role"] == "user" else "model"
            history.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        # Run recursion loop up to 5 steps to avoid infinite loops
        for step in range(5):
            try:
                response = self.model.generate_content(
                    contents=history,
                    tools=[DB_SEARCH_SERVICES_TOOL]
                )
            except Exception as e:
                print(f"Error generating content: {e}")
                return "I apologize, but I am currently unavailable. Please try again later."

            # Check if Gemini decided to invoke any function calls
            function_calls = []
            if hasattr(response, "function_calls") and response.function_calls:
                function_calls = response.function_calls
            elif response.candidates and len(response.candidates) > 0:
                parts = getattr(response.candidates[0].content, "parts", [])
                for part in parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        function_calls.append(fc)

            if function_calls:
                # CRITICAL: append the raw model Content object (preserves thought_signature)
                history.append(response.candidates[0].content)

                # Execute all tools and build function response parts
                function_response_parts = []
                for fc in function_calls:
                    # In case the model forgot lead_id, inject it automatically
                    args = dict(fc.args)
                    if "lead_id" in args:
                        args["lead_id"] = lead.id
                    elif fc.name in ["qualify_lead", "update_lead"]:
                        args["lead_id"] = lead.id

                    tool_result = self.execute_tool(db, lead.id, fc.name, args)
                    function_response_parts.append(
                        genai_protos.Part(
                            function_response=genai_protos.FunctionResponse(
                                name=fc.name,
                                response={"result": tool_result}
                            )
                        )
                    )
                # Gemini requires function responses submitted with role 'user'
                history.append(genai_protos.Content(role="user", parts=function_response_parts))
                # Loop back to let Gemini compose a final text reply using tool results
                continue
            
            # If no function calls, return the final text response
            return response.text if response.text else "I am here to help you."

        return "I apologize, but I need to process this request further. Please contact our support team."

orchestrator = AgentOrchestrator()
