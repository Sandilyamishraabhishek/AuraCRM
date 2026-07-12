import os
import json
import datetime
from typing import Dict, Any, List, TypedDict, Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
import models

# Environment config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Try loading langchain / langgraph conditionally to avoid Pydantic V1 warnings on Python 3.14 when running in simulation mode
HAS_LANGCHAIN = False
if GROQ_API_KEY:
    try:
        from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
        from langchain_groq import ChatGroq
        from langgraph.graph import StateGraph, START, END
        from langgraph.prebuilt import ToolNode
        from langchain_core.tools import tool
        HAS_LANGCHAIN = True
    except ImportError:
        HAS_LANGCHAIN = False

# Database helper for tools
def get_db_context():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

# Definitions of tools using standard python functions (works in both real & simulated modes)

def search_hcp_fn(query: str) -> str:
    """Search for healthcare professionals (HCPs) by name, specialty, or clinic."""
    db = get_db_context()
    try:
        hcps = db.query(models.HCP).filter(
            (models.HCP.name.ilike(f"%{query}%")) |
            (models.HCP.specialty.ilike(f"%{query}%")) |
            (models.HCP.clinic.ilike(f"%{query}%"))
        ).all()
        results = []
        for h in hcps:
            results.append({
                "id": h.id,
                "name": h.name,
                "specialty": h.specialty,
                "clinic": h.clinic,
                "email": h.email,
                "phone": h.phone
            })
        return json.dumps(results)
    finally:
        db.close()

def list_materials_and_samples_fn() -> str:
    """Get list of available marketing materials and drug samples, along with their stock levels."""
    db = get_db_context()
    try:
        items = db.query(models.Material).all()
        results = []
        for item in items:
            results.append({
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "stock": item.stock
            })
        return json.dumps(results)
    finally:
        db.close()

def log_interaction_fn(
    hcp_id: int,
    interaction_type: str,
    date: str,
    time: str,
    attendees: str = "",
    topics_discussed: str = "",
    sentiment: str = "Neutral",
    outcomes: str = "",
    follow_up_actions: str = "",
    materials_shared: str = "",
    samples_distributed: str = ""
) -> str:
    """Log a new interaction with an HCP."""
    db = get_db_context()
    try:
        hcp = db.query(models.HCP).filter(models.HCP.id == hcp_id).first()
        if not hcp:
            return json.dumps({"error": f"HCP with ID {hcp_id} not found."})
        
        # Deduct stocks for samples if applicable
        if samples_distributed:
            samples_list = [s.strip() for s in samples_distributed.split(",") if s.strip()]
            for sname in samples_list:
                mat = db.query(models.Material).filter(models.Material.name.ilike(sname), models.Material.type == "Sample").first()
                if mat and mat.stock > 0:
                    mat.stock -= 1

        new_interaction = models.Interaction(
            hcp_id=hcp_id,
            interaction_type=interaction_type,
            date=date,
            time=time,
            attendees=attendees,
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            materials_shared=materials_shared,
            samples_distributed=samples_distributed
        )
        db.add(new_interaction)
        db.commit()
        db.refresh(new_interaction)
        return json.dumps({
            "status": "success",
            "message": "Interaction logged successfully",
            "interaction_id": new_interaction.id,
            "hcp_name": hcp.name
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()

def edit_interaction_fn(interaction_id: int, updates: Dict[str, Any]) -> str:
    """Edit an existing logged interaction."""
    db = get_db_context()
    try:
        interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"Interaction with ID {interaction_id} not found."})
        
        allowed_fields = [
            "interaction_type", "date", "time", "attendees", "topics_discussed",
            "sentiment", "outcomes", "follow_up_actions", "materials_shared", "samples_distributed"
        ]
        for key, val in updates.items():
            if key in allowed_fields:
                setattr(interaction, key, val)
        
        db.commit()
        db.refresh(interaction)
        return json.dumps({
            "status": "success",
            "message": f"Interaction {interaction_id} updated successfully",
            "interaction_id": interaction.id
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()

def schedule_follow_up_fn(hcp_id: int, title: str, due_date: str) -> str:
    """Schedule a follow-up action or task for an HCP."""
    db = get_db_context()
    try:
        hcp = db.query(models.HCP).filter(models.HCP.id == hcp_id).first()
        if not hcp:
            return json.dumps({"error": f"HCP with ID {hcp_id} not found."})
        
        # We append/update the latest interaction's follow-up actions, or simulate scheduling
        latest_interaction = db.query(models.Interaction).filter(models.Interaction.hcp_id == hcp_id).order_by(models.Interaction.id.desc()).first()
        new_follow_up = f"{title} (Due: {due_date})"
        if latest_interaction:
            existing = latest_interaction.follow_up_actions or ""
            latest_interaction.follow_up_actions = f"{existing}, {new_follow_up}".strip(", ")
            db.commit()
            msg = f"Scheduled follow-up '{title}' on {due_date} and appended to latest interaction ID {latest_interaction.id}."
        else:
            msg = f"Scheduled follow-up '{title}' on {due_date} for HCP {hcp.name}."
            
        return json.dumps({
            "status": "success",
            "message": msg,
            "hcp_id": hcp_id,
            "title": title,
            "due_date": due_date
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# Now expose standard langchain tools if packages are available
if HAS_LANGCHAIN:
    @tool
    def search_hcp(query: str) -> str:
        """Search for healthcare professionals (HCPs) by name, specialty, or clinic."""
        return search_hcp_fn(query)

    @tool
    def list_materials_and_samples() -> str:
        """Get list of available marketing materials and drug samples, along with their stock levels."""
        return list_materials_and_samples_fn()

    @tool
    def log_interaction(
        hcp_id: int,
        interaction_type: str,
        date: str,
        time: str,
        attendees: str = "",
        topics_discussed: str = "",
        sentiment: str = "Neutral",
        outcomes: str = "",
        follow_up_actions: str = "",
        materials_shared: str = "",
        samples_distributed: str = ""
    ) -> str:
        """Log a new interaction with an HCP. Fields should be populated based on the conversation detail."""
        return log_interaction_fn(hcp_id, interaction_type, date, time, attendees, topics_discussed, sentiment, outcomes, follow_up_actions, materials_shared, samples_distributed)

    @tool
    def edit_interaction(interaction_id: int, updates: Dict[str, Any]) -> str:
        """Edit fields of an existing logged interaction, such as sentiment, outcomes, or follow-ups."""
        return edit_interaction_fn(interaction_id, updates)

    @tool
    def schedule_follow_up(hcp_id: int, title: str, due_date: str) -> str:
        """Schedule a follow-up action or task with a given due date for a specific HCP."""
        return schedule_follow_up_fn(hcp_id, title, due_date)

    tools_list = [search_hcp, list_materials_and_samples, log_interaction, edit_interaction, schedule_follow_up]


# State Graph configuration
class AgentState(TypedDict):
    messages: List[Any]
    extracted_form: Dict[str, Any]
    tool_calls_executed: List[str]


def run_agent_workflow(user_message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Runs the agent. If GROQ_API_KEY is present and dependencies are installed, uses LangGraph workflow.
    Otherwise, runs a rule-based intelligent simulation that handles entity extraction, tool triggers, and responds.
    """
    if history is None:
        history = []
        
    db = get_db_context()
    # Pre-fetch some data for context-aware rule-based parsing
    all_hcps = db.query(models.HCP).all()
    all_mats = db.query(models.Material).all()
    db.close()
    
    use_groq = bool(GROQ_API_KEY and HAS_LANGCHAIN)
    
    # ----------------- SIMULATED FALLBACK MODE OR NO GROQ KEY -----------------
    if not use_groq:
        extracted = {}
        tool_calls = []
        reply = ""
        
        text = user_message.lower()
        
        # 1. Match HCP Name
        matched_hcp = None
        for hcp in all_hcps:
            if hcp.name.lower() in text:
                matched_hcp = hcp
                break
        
        # 2. Extract Type
        itype = "Meeting"
        if "email" in text:
            itype = "Email"
        elif "call" in text or "phone" in text:
            itype = "Call"
        elif "video" in text or "zoom" in text or "teams" in text:
            itype = "Video Call"
            
        # 3. Extract Sentiment
        sentiment = "Neutral"
        if "positive" in text or "great" in text or "happy" in text or "interested" in text:
            sentiment = "Positive"
        elif "negative" in text or "angry" in text or "unhappy" in text or "not interested" in text or "complained" in text:
            sentiment = "Negative"
            
        # 4. Extract Materials & Samples
        mats_shared = []
        samps_dist = []
        for m in all_mats:
            if m.name.lower() in text:
                if m.type == "Material":
                    mats_shared.append(m.name)
                else:
                    samps_dist.append(m.name)
                    
        # 5. Extract Follow ups
        follow_up = ""
        if "follow up" in text or "schedule" in text or "next week" in text or "next month" in text:
            if "next week" in text:
                follow_up = "Follow up next week"
            elif "next month" in text:
                follow_up = "Follow up next month"
            else:
                follow_up = "Follow up meeting"
                
        # Fill in extracted data if HCP is found
        if matched_hcp:
            extracted = {
                "hcp_id": matched_hcp.id,
                "hcp_name": matched_hcp.name,
                "interaction_type": itype,
                "date": datetime.date.today().isoformat(),
                "time": datetime.datetime.now().strftime("%H:%M"),
                "topics_discussed": f"Discussed with {matched_hcp.name}. Details: {user_message}",
                "sentiment": sentiment,
                "materials_shared": ", ".join(mats_shared),
                "samples_distributed": ", ".join(samps_dist),
                "follow_up_actions": follow_up
            }
            
        # Determine intent / Action
        if "log" in text or "save" in text or "record" in text or ("met with" in text and len(text) > 30):
            if matched_hcp:
                # Execute log interaction tool
                res_str = log_interaction_fn(
                    hcp_id=matched_hcp.id,
                    interaction_type=itype,
                    date=extracted["date"],
                    time=extracted["time"],
                    topics_discussed=extracted["topics_discussed"],
                    sentiment=sentiment,
                    materials_shared=extracted["materials_shared"],
                    samples_distributed=extracted["samples_distributed"],
                    follow_up_actions=follow_up
                )
                res = json.loads(res_str)
                if "error" not in res:
                    tool_calls.append(f"log_interaction(hcp_id={matched_hcp.id})")
                    reply = f"I've successfully logged the interaction with {matched_hcp.name}. Sentiment is marked as {sentiment}."
                    if samps_dist:
                        reply += f" Distributed samples: {', '.join(samps_dist)} (stock updated)."
                else:
                    reply = f"Failed to log interaction: {res['error']}"
            else:
                reply = "I identified that you want to log an interaction, but I couldn't match the doctor's name. Please select or search for the HCP first."
                
        elif "edit" in text or "change" in text or "update" in text:
            # Try to edit the latest interaction
            db = get_db_context()
            latest = db.query(models.Interaction).order_by(models.Interaction.id.desc()).first()
            if latest:
                updates = {}
                if "positive" in text:
                    updates["sentiment"] = "Positive"
                elif "negative" in text:
                    updates["sentiment"] = "Negative"
                elif "neutral" in text:
                    updates["sentiment"] = "Neutral"
                
                if updates:
                    res_str = edit_interaction_fn(latest.id, updates)
                    res = json.loads(res_str)
                    if "error" not in res:
                        tool_calls.append(f"edit_interaction(id={latest.id})")
                        reply = f"Updated the last logged interaction (ID {latest.id}) sentiment to {updates['sentiment']}."
                    else:
                        reply = f"Failed to update: {res['error']}"
                else:
                    reply = "What would you like to update? You can say 'change sentiment to positive' or specify updates."
            else:
                reply = "No logged interactions found to update."
            db.close()
            
        elif "list" in text or "materials" in text or "samples" in text:
            res_str = list_materials_and_samples_fn()
            items = json.loads(res_str)
            tool_calls.append("list_materials_and_samples()")
            reply = "Here are the available materials and samples:\n" + "\n".join([f"- {i['name']} ({i['type']}, Stock: {i['stock']})" for i in items])
            
        elif "search" in text or "find" in text:
            q = user_message.replace("search", "").replace("find", "").replace("hcp", "").replace("doctor", "").strip()
            if q:
                res_str = search_hcp_fn(q)
                hcps = json.loads(res_str)
                tool_calls.append(f"search_hcp(query='{q}')")
                if hcps:
                    reply = f"Found {len(hcps)} HCPs matching '{q}':\n" + "\n".join([f"- {h['name']} ({h['specialty']} at {h['clinic']})" for h in hcps])
                else:
                    reply = f"No HCPs found matching '{q}'."
            else:
                reply = "What is the name or specialty of the HCP you'd like to search for?"
                
        else:
            # Default response/extraction helper
            if matched_hcp:
                reply = f"I've extracted interaction details for {matched_hcp.name}. You can click 'Log Interaction' to save this, or tell me 'log this interaction' to save it."
            else:
                reply = "Hello! I can help you log interactions, update entries, search HCPs, or list materials. Tell me about your interaction (e.g., 'Met with Dr. Emily Smith to discuss OncoBoost')."
                
        return {
            "reply": reply,
            "form_data": extracted,
            "tool_calls_executed": tool_calls
        }

    # ----------------- REAL LANGGRAPH / GROQ MODE -----------------
    else:
        # Construct graph, use ChatGroq with Gemma-2-9b or Llama-3
        try:
            llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name="gemma2-9b-it",
                temperature=0.1
            )
            
            # Bind tools
            llm_with_tools = llm.bind_tools(tools_list)
            
            # Simple agent node
            def call_model(state: AgentState):
                messages = state["messages"]
                response = llm_with_tools.invoke(messages)
                return {"messages": [response]}
                
            # Tool invocation node
            tool_node = ToolNode(tools_list)
            
            # Routing logic
            def should_continue(state: AgentState):
                last_message = state["messages"][-1]
                if last_message.tool_calls:
                    return "tools"
                return END
                
            # Build workflow
            workflow = StateGraph(AgentState)
            workflow.add_node("agent", call_model)
            workflow.add_node("tools", tool_node)
            
            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges("agent", should_continue, {
                "tools": "tools",
                END: END
            })
            workflow.add_edge("tools", "agent")
            
            app = workflow.compile()
            
            # Prepare state
            sys_msg = SystemMessage(content=(
                "You are an AI assistant in a CRM HCP (Healthcare Professional) Module. "
                "Your role is to help field representatives manage and log interactions, search HCPs, "
                "or list materials. Use the tools provided when the user requests those actions. "
                "If the user describes a meeting/interaction, extract details and invoke the log_interaction tool if requested. "
                "Always respond politely and clearly."
            ))
            
            langchain_history = [sys_msg]
            for h in history:
                if h["role"] == "user":
                    langchain_history.append(HumanMessage(content=h["content"]))
                else:
                    langchain_history.append(AIMessage(content=h["content"]))
                    
            langchain_history.append(HumanMessage(content=user_message))
            
            # Execute
            initial_state = {
                "messages": langchain_history,
                "extracted_form": {},
                "tool_calls_executed": []
            }
            
            output = app.invoke(initial_state)
            
            # Parse responses
            final_messages = output["messages"]
            final_reply = final_messages[-1].content
            
            # Gather track of tool execution
            executed_tools = []
            for msg in final_messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        executed_tools.append(f"{tc['name']}({tc['args']})")
            
            # Optional: do a mini extraction for form sync
            extracted_info = {}
            # We can extract fields if a tool was called
            for msg in final_messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc["name"] == "log_interaction":
                            args = tc["args"]
                            extracted_info = {
                                "hcp_id": args.get("hcp_id"),
                                "interaction_type": args.get("interaction_type", "Meeting"),
                                "date": args.get("date", datetime.date.today().isoformat()),
                                "time": args.get("time", datetime.datetime.now().strftime("%H:%M")),
                                "topics_discussed": args.get("topics_discussed", ""),
                                "sentiment": args.get("sentiment", "Neutral"),
                                "materials_shared": args.get("materials_shared", ""),
                                "samples_distributed": args.get("samples_distributed", ""),
                                "follow_up_actions": args.get("follow_up_actions", "")
                            }
            
            return {
                "reply": final_reply,
                "form_data": extracted_info,
                "tool_calls_executed": executed_tools
            }
            
        except Exception as e:
            # Fallback to simulated mode if any runtime error occurs with Groq
            return {
                "reply": f"[Groq LLM error, falling back to simulator] Error: {str(e)}",
                "form_data": {},
                "tool_calls_executed": []
            }
